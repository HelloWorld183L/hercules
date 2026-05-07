"""
Hercules - A Discord bot powered by Strands Agents
"""

import hashlib
import io
import logging
import os
from discord import app_commands
import discord
from dotenv import load_dotenv
from strands import Agent, AgentSkills
from strands.models.openai import OpenAIModel
from strands_tools import calculator, current_time
from strands_tools.tavily import tavily_search
from strands_tools import mem0_memory
import warnings

from hercules.client import HerculesClient

# DeprecationWarning interferes with agent outputs
warnings.filterwarnings("ignore", category=DeprecationWarning, module="mem0_memory")

load_dotenv()

STRANDS_MODEL_ID = os.getenv("STRANDS_MODEL_ID", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_WORKOUT_PROGRAM_NAME = "workout_program.md"

model = OpenAIModel(client_args={"api_key": OPENAI_API_KEY}, model_id=STRANDS_MODEL_ID)

# Load the Agent SOP
with open(os.path.join(os.path.dirname(__file__), "sop.md"), "r") as f:
    SYSTEM_PROMPT = f.read()

plugin = AgentSkills(skills=os.path.join(os.path.dirname(__file__), "skills"))

# Create the Strands Agent with the SOP
agent = Agent(
    model=model,
    tools=[calculator, current_time, tavily_search, mem0_memory],
    plugins=[plugin],
    system_prompt=SYSTEM_PROMPT,
)


client = HerculesClient(
    agent, default_workout_program_name=DEFAULT_WORKOUT_PROGRAM_NAME
)
tree = app_commands.CommandTree(client)

# attach the tree to the client so the client can sync it in setup_hook
client._tree = tree


# Run the bot
def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set")

    setup_loggers()
    client.run(token, log_handler=None)


def setup_loggers():
    if not os.path.exists('logs'):
        os.mkdir('logs')

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.DEBUG)
    discord_log_handler = logging.FileHandler(filename="logs/discord.log", encoding="utf-8", mode="w")
    discord_log_handler.setFormatter(formatter)
    discord_logger.addHandler(discord_log_handler)

    strands_logger = logging.getLogger("strands")
    strands_log_handler = logging.FileHandler(filename="logs/agent.log", encoding='utf-8', mode='w')
    strands_log_handler.setFormatter(formatter)
    strands_logger.addHandler(strands_log_handler)
    strands_logger.setLevel(logging.DEBUG)

@tree.command(
    name="create_program", description="Create a workout program based on user input"
)
@app_commands.describe(
    workout_split="Workout split that the user prefers (e.g. full body, push pull legs)"
)
async def create_program(interaction: discord.Interaction, workout_split: str):
    """Create a workout program using the same logic as the message handler.

    The slash command provides `workout_split` as extra context.
    """
    await interaction.response.defer()
    
    # TODO: De-duplicate this code
    try:
        # Get the message content, removing the bot mention if present
        hashed_user_id = hashlib.sha256(str(interaction.user.id).encode()).hexdigest()
        result = await agent.invoke_async(
            f"Create a workout program using the {workout_split} split for user id: {hashed_user_id}"
        )
        if isinstance(result.message, dict) and "content" in result.message:
            response_text = result.message["content"][0]["text"]
        else:
            response_text = str(result.message)
        file_bytes = io.BytesIO(response_text.encode("utf-8"))
        file_bytes.seek(0)

        await interaction.followup.send(
            "I have attached your training program. Please let me know if you have any questions.",
            file=discord.File(file_bytes, filename=DEFAULT_WORKOUT_PROGRAM_NAME),
        )

    except Exception as e:
        logging.exception(f"Error in /create_program: {e}")
        await interaction.followup.send(
            "Hercules failed to create the program. Contact the developer."
        )


if __name__ == "__main__":
    main()
