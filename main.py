"""
Hercules - A Discord bot powered by Strands Agents
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from strands import Agent, AgentSkills
from strands.models.openai import OpenAIModel
from strands_tools import calculator, current_time, file_read
from strands_tools.tavily import tavily_search
from strands_tools import mem0_memory
import warnings

from hercules.client import HerculesBot
from hercules.tools import create_moving_avg_graph

# DeprecationWarning interferes with agent outputs
warnings.filterwarnings("ignore", category=DeprecationWarning, module="mem0_memory")

DEFAULT_WORKOUT_PROGRAM_NAME = "workout_program.md"


# Run the bot
async def main():
    load_dotenv()

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")

    strands_model_id = os.getenv("STRANDS_MODEL_ID")
    if not strands_model_id:
        raise ValueError("STRANDS_MODEL_ID environment variable not set.")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    dev_guild_id = os.getenv("DISCORD_DEV_GUILD_ID")

    model = OpenAIModel(
        client_args={"api_key": openai_api_key}, model_id=strands_model_id
    )

    setup_loggers()

    plugin = AgentSkills(
        skills=os.path.join(os.path.dirname(__file__), "hercules", "skills")
    )

    # Load the Agent SOP
    with open(os.path.join(os.path.dirname(__file__), "hercules", "sop.md"), "r") as f:
        system_prompt = f.read()

    # Create the Strands Agent with the SOP
    agent = Agent(
        model=model,
        tools=[calculator, current_time, file_read, tavily_search, mem0_memory, create_moving_avg_graph],
        plugins=[plugin],
        system_prompt=system_prompt,
    )

    async with HerculesBot(
        agent=agent,
        default_workout_program_name=DEFAULT_WORKOUT_PROGRAM_NAME,
        dev_guild_id=dev_guild_id,
    ) as bot:
        await bot.start(token)


def setup_loggers():
    if not os.path.exists("logs"):
        os.mkdir("logs")

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.DEBUG)
    discord_log_handler = logging.FileHandler(
        filename="logs/discord.log", encoding="utf-8", mode="w"
    )
    discord_log_handler.setFormatter(formatter)
    discord_logger.addHandler(discord_log_handler)

    strands_logger = logging.getLogger("strands")
    strands_log_handler = logging.FileHandler(
        filename="logs/agent.log", encoding="utf-8", mode="w"
    )
    strands_log_handler.setFormatter(formatter)
    strands_logger.addHandler(strands_log_handler)
    strands_logger.setLevel(logging.DEBUG)

    hercules_logger = logging.getLogger("hercules")
    hercules_log_handler = logging.FileHandler(
        filename="logs/hercules.log", encoding="utf-8", mode="w"
    )
    hercules_log_handler.setFormatter(formatter)
    hercules_logger.addHandler(hercules_log_handler)
    hercules_logger.setLevel(logging.DEBUG)


asyncio.run(main())
