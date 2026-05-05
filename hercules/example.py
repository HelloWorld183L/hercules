import os

from dotenv import load_dotenv
from strands import Agent
from strands_tools import calculator
from strands.models.openai import OpenAIModel

load_dotenv()

STRANDS_MODEL_ID = os.getenv("STRANDS_MODEL_ID", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

model = OpenAIModel(client_args={"api_key": OPENAI_API_KEY}, model_id=STRANDS_MODEL_ID)
agent = Agent(tools=[calculator], model=model)

response = agent("What's 123 times 456?")

print(response.metrics.tool_metrics)