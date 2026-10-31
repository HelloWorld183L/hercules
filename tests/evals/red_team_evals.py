"""
Evals to test the model's ability to handle red team scenarios and adversarial prompts.
These evals are designed to assess the model's robustness, safety, and ability to avoid
harmful or malicious instructions.

When running attacker model on Ollama, make sure you have decent GPU compute available.
"""

import asyncio
import os
from pathlib import Path

from pydantic import TypeAdapter
from strands import Agent
from strands.models.ollama import OllamaModel
from strands_evals.redteam import (
    CrescendoStrategy,
    RedTeamCase,
    RedTeamExperiment,
)

from hercules.agent import build_agent


def agent_factory() -> Agent:
    """
    Factory function to create a new instance of the agent for each evaluation run.
    This ensures that each evaluation starts with a fresh agent state.
    """
    return build_agent()


# Load test cases with expected tool usage from JSON.
test_case_path = Path(__file__).parent / "test_cases" / "redteam_eval_cases.json"
redteam_test_cases = TypeAdapter(list[RedTeamCase]).validate_json(
    test_case_path.read_bytes()
)

if __name__ == "__main__":
    sample_agent = build_agent()
    attack_model_id = os.getenv("ATTACKER_MODEL_ID")
    attacker_model = OllamaModel(
        host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        model_id=attack_model_id,
    )

    experiment = RedTeamExperiment(
        cases=redteam_test_cases,
        attack_strategies=[CrescendoStrategy(model=attacker_model)],
        model=sample_agent.model,
    )

    report = asyncio.run(experiment.run_evaluations_async(agent_factory=agent_factory))

    reports_path = os.path.join(os.path.dirname(__file__), "experiment_reports")
    if not os.path.exists(reports_path):
        os.makedirs(reports_path)

    # Save evaluation report
    report.to_file(os.path.join(reports_path, "redteam_evaluation.json"))
    print(
        f"\nExperiment saved to {os.path.join(reports_path, 'redteam_evaluation.json')}"
    )

    report.display()
