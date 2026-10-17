"""
Evals for evaluating agent's ability to respond to chaotic or unexpected situations,
including tool timeouts, corrupted data, and other challenging scenarios.
"""

"""
Evals for evaluating proper tool usage
"""

import asyncio
import os
from pathlib import Path

from pydantic import TypeAdapter
from strands import Agent
from strands_evals import TracedHandler, eval_task
from strands_evals.chaos import ChaosCase, ChaosExperiment, ChaosPlugin
from strands_evals.evaluators.chaos import (
    PartialCompletionEvaluator,
    RecoveryStrategyEvaluator,
)

from hercules.agent import build_agent


def extract_effect_maps(chaos_cases: list[ChaosCase]) -> dict[str, dict[str, str]]:
    """
    Extracts a mapping of effect names to their types and descriptions from a list of ChaosCase instances.
    This function is useful for creating a reference of effects that can be used in evaluations.
    """
    return {case.name: case.effects for case in chaos_cases}


def create_task_function(sample_agent: Agent):
    @eval_task(TracedHandler())
    def task_function(case: ChaosCase) -> Agent:
        return build_agent(
            model=sample_agent.model,
            extra_plugins=[ChaosPlugin()],
            trace_attributes={"session.id": case.session_id},
        )

    return task_function


# Load test cases with expected tool usage from JSON.
test_case_path = Path(__file__).parent / "test_cases" / "chaos_eval_cases.json"
chaos_test_cases = TypeAdapter(list[ChaosCase]).validate_json(
    test_case_path.read_bytes()
)

evaluation_max_workers = int(os.getenv("EVAL_MAX_WORKERS", "1"))
evaluation_max_turns = int(os.getenv("EVAL_MAX_TURNS", "8"))


# Execute the async evaluation
if __name__ == "__main__":
    # Update evaluator with tool descriptions to prevent context overflow
    sample_agent = build_agent()
    experiment = ChaosExperiment(
        cases=chaos_test_cases,
        evaluators=[
            # How much was achieved?
            PartialCompletionEvaluator(model=sample_agent.model),
            # Did it try alternatives?
            RecoveryStrategyEvaluator(model=sample_agent.model),
        ],
    )

    report = asyncio.run(
        experiment.run_evaluations_async(
            create_task_function(sample_agent),
            max_workers=evaluation_max_workers,
        )
    )
    print("=== Chaos Test Evaluation Results ===")
    report.run_display(include_recommendations=True)

    reports_path = os.path.join(os.path.dirname(__file__), "experiment_reports")
    if not os.path.exists(reports_path):
        os.makedirs(reports_path)

    # Save evaluation report
    report.to_file(os.path.join(reports_path, "chaos_evaluation.json"))
    print(
        f"\nExperiment saved to {os.path.join(reports_path, 'chaos_evaluation.json')}"
    )
