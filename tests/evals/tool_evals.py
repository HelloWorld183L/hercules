"""
Evals for evaluating proper tool usage
"""

import asyncio
import os
from pathlib import Path

from pydantic import TypeAdapter
from strands_evals import Case, DiagnosisConfig, EvaluationReport, Experiment
from strands_evals.detectors import DiagnosisTrigger
from strands_evals.evaluators import TrajectoryEvaluator
from strands_evals.extractors import tools_use_extractor

from hercules.agent import build_agent

# Load test cases with expected tool usage from JSON.
test_case_path = Path(__file__).parent / "test_cases" / "tool_eval_cases.json"
test_cases = TypeAdapter(list[Case[str, str]]).validate_json(
    test_case_path.read_bytes()
)
evaluation_max_workers = int(os.getenv("EVAL_MAX_WORKERS", "1"))
evaluation_max_turns = int(os.getenv("EVAL_MAX_TURNS", "8"))


# Define task function that captures tool usage
async def get_response_with_tools(case: Case) -> dict:
    agent = build_agent()
    response = await agent.invoke_async(
        case.input, limits={"turns": evaluation_max_turns}
    )

    # Extract trajectory efficiently to prevent context overflow
    trajectory = tools_use_extractor.extract_agent_tools_used_from_messages(
        agent.messages
    )
    simple_trajectory = [tool["name"] for tool in trajectory]

    # Update evaluator with tool descriptions to prevent overflow
    tool_descriptions = tools_use_extractor.extract_tools_description(
        agent, is_short=True
    )
    evaluator.update_trajectory_description(tool_descriptions)
    return {"output": str(response), "trajectory": simple_trajectory}


async def run_evaluations_async(
    test_cases: list[Case], evaluators: list[TrajectoryEvaluator]
) -> tuple[EvaluationReport, Experiment]:
    experiment = Experiment[str, str](
        cases=test_cases,
        evaluators=evaluators,
        diagnosis_config=DiagnosisConfig(trigger=DiagnosisTrigger.ON_FAILURE),
    )
    report = await experiment.run_evaluations_async(
        get_response_with_tools, max_workers=evaluation_max_workers
    )
    return report, experiment


# Execute the async evaluation
if __name__ == "__main__":
    # Update evaluator with tool descriptions to prevent context overflow
    sample_agent = build_agent()
    tool_descriptions = tools_use_extractor.extract_tools_description(
        sample_agent, is_short=True
    )

    # Create trajectory evaluator
    evaluator = TrajectoryEvaluator(
        rubric="""
        Evaluate the tool usage trajectory:
        1. Correct tool selection - Were the right tools chosen for the task?
        2. Proper sequence - Were tools used in a logical order?
        3. Efficiency - Were unnecessary tools avoided?

        Use the built-in scoring tools to verify trajectory matches:
        - exact_match_scorer for exact sequence matching
        - in_order_match_scorer for ordered subset matching
        - any_order_match_scorer for unordered matching

        Score 1.0 if optimal tools used correctly.
        Score 0.5 if correct tools used but suboptimal sequence.
        Score 0.0 if wrong tools used or major inefficiencies.
        """,
        include_inputs=True,
        model=sample_agent.model,
    )
    evaluator.update_trajectory_description(tool_descriptions)

    report, experiment = asyncio.run(run_evaluations_async(test_cases, [evaluator]))
    print("=== Tool Usage Evaluation Results ===")
    report.run_display(include_recommendations=True)

    reports_path = os.path.join(os.path.dirname(__file__), "experiment_reports")
    if not os.path.exists(reports_path):
        os.makedirs(reports_path)

    # Save experiment
    experiment.to_file(
        os.path.join(reports_path, "tool_use_trajectory_evaluation.json")
    )
    print(
        f"\nExperiment saved to {os.path.join(reports_path, 'tool_use_trajectory_evaluation.json')}"
    )
