import os
from typing import Literal, cast

from dotenv import load_dotenv
from mcp import StopReason
from pydantic import BaseModel, Field
from strands import Agent
from strands.vended_plugins.steering import Guide, LLMSteeringHandler, ModelSteeringAction, Proceed, SteeringHandler
from strands.models.openai import OpenAIModel
from strands.types.content import Message
from strands.types.streaming import StopReason
from sympy import content

class _SteeringDecision(BaseModel):
    """Structured output for a steering decision."""

    decision: Literal["proceed", "guide"] = Field(
        description="Steering deciison: `proceed` to accept, `guide` to provide feedback"
    )

class WorkoutProgramSteeringHandler(LLMSteeringHandler):
    """Steering handler that validates model responses for effective workout programming."""

    def __init__(self):
        load_dotenv()

        STRANDS_MODEL_ID = os.getenv(
            "STRANDS_MODEL_ID", "gpt-4o"
        )
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        # Load the Agent SOP
        with open(os.path.join(os.path.dirname(__file__), "steering_agent_sop.md"), "r") as f:
            self._sop = f.read()

        self._model = OpenAIModel(
            client_args={"api_key": OPENAI_API_KEY}, 
            model_id=STRANDS_MODEL_ID
        )

        super().__init__(model=self._model, system_prompt=self._sop)

    async def steer_after_model(self, *, agent: Agent, message: Message, stop_reason: StopReason, **kwargs):
        if stop_reason != "end_turn":
            return Proceed(reason="Not a final response")
        
        content = message.get("content", [])
        text = " ".join(block.get("text", "") for block in content if block.get("text"))
        if not text:
            return Proceed(reason="No text content to evaluate")
        
        steering_agent = Agent(
            model=self._model,
            system_prompt=self._sop,
            callback_handler=None
        )
        result = steering_agent(f"Evaluate the following response for effective workout programming:\n\n{text}", structured_output_model=_SteeringDecision)
        decision = cast(_SteeringDecision, result.decision)
        
        match decision.decision:
            case "proceed":
                return Proceed(reason=decision.reason)
            case "guide":
                guidance = f"""
                Your previous response was NOT shown to the user {decision.reason}.
                Please provide a new response.
                """
                return Guide(reason=guidance)
            case _:
                return Proceed(reason="Unknown decision, defaulting to proceed)")