"""
Hercules - A Discord bot powered by Strands Agents
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
import warnings

from hercules.agent import build_agent
from hercules.client import HerculesBot

# DeprecationWarning interferes with agent outputs
warnings.filterwarnings("ignore", category=DeprecationWarning, module="mem0_memory")

DEFAULT_WORKOUT_PROGRAM_NAME = "workout_program.md"


# Run the bot
async def main():
    load_dotenv()

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")

    dev_guild_id = os.getenv("DISCORD_DEV_GUILD_ID")

    # If HERCULES_API_URL is set, run the bot in stateless mode and proxy
    # requests to the API server. Otherwise, build a local agent instance.
    api_url = os.getenv("HERCULES_API_URL")
    if api_url:
        agent = None
    else:
        agent = build_agent()

    # Ensure loggers exist
    setup_loggers()

    async with HerculesBot(
        agent=agent,
        api_url=api_url,
        default_workout_program_name=DEFAULT_WORKOUT_PROGRAM_NAME,
        dev_guild_id=dev_guild_id,
    ) as bot:
        await bot.start(token)


def setup_loggers():
    # Use a StreamHandler to send logs to stdout so container logs appear
    # in `docker logs` and other aggregators, while keeping format.
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.DEBUG)
    discord_logger.addHandler(stream_handler)

    strands_logger = logging.getLogger("strands")
    strands_logger.setLevel(logging.DEBUG)
    strands_logger.addHandler(stream_handler)

    hercules_logger = logging.getLogger("hercules")
    hercules_logger.setLevel(logging.DEBUG)
    hercules_logger.addHandler(stream_handler)


asyncio.run(main())
