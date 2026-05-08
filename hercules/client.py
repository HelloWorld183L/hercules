import hashlib
import io
import logging
import os
from typing import Optional

from discord import DMChannel, Intents, Message
from discord.ext import commands

import discord
from strands import Agent

logger = logging.getLogger("hercules")


class HerculesBot(commands.Bot):
    def __init__(
        self,
        *args,
        agent: Agent,
        default_workout_program_name: str = "workout_program.md",
        dev_guild_id: Optional[int],
        **kwargs,
    ):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(*args, **kwargs, intents=intents, command_prefix="")
        self.agent = agent
        self._dev_guild_id = dev_guild_id
        self._default_workout_program_name = default_workout_program_name

    async def on_ready(self):
        logger.info(f"Hercules is online as {self.user}")

    async def setup_hook(self) -> None:
        # Cogs MUST be loaded before command trees are synced
        for filename in os.listdir(os.path.join(os.path.dirname(__file__), "cogs")):
            if filename.endswith(".py"):
                await self.load_extension(name=f"hercules.cogs.{filename[:-3]}")

        logger.info("Cogs loaded")

        if self._dev_guild_id:
            guild = discord.Object(id=self._dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Command tree synced (local)")
        else:
            # Sync for global commands instead if there's no specific guild ID
            await self.tree.sync()
            logger.info("Command tree synced (global)")

    async def on_message(self, message: Message):
        # Ignore messages from bots
        if message.author.bot:
            return

        mentioned_or_dmed = self.user.mentioned_in(message) or isinstance(
            message.channel, DMChannel
        )
        if not mentioned_or_dmed:
            return

        await message.channel.typing()  # Show typing indicator while processing
        try:
            # Get the message content, removing the bot mention if present
            user_input = message.content.replace(f"<@{self.user.id}>", "").strip()

            hashed_user_id = hashlib.sha256(str(message.author.id).encode()).hexdigest()
            context_input = f"""
            [user_id: {hashed_user_id}], 
            [user_input: {user_input}]
            """

            result = await self.agent.invoke_async(context_input)
            if isinstance(result.message, dict) and "content" in result.message:
                response_text = result.message["content"][0]["text"]
            else:
                response_text = str(result.message)

            skill_metrics = result.metrics.tool_metrics["skills"]
            user_wants_program = (
                skill_metrics.tool["input"]["skill_name"] == "program-creator"
            )

            if user_wants_program:
                file_bytes = io.BytesIO(response_text.encode("utf-8"))
                file_bytes.seek(0)
                await message.reply(
                    """
                    I have attached your training program. 
                    Please let me know if you have any questions or need further assistance.
                    """,
                    file=discord.File(
                        file_bytes, filename=self._default_workout_program_name
                    ),
                )
            else:
                await message.reply(response_text)

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            await message.reply(
                "Hercules discord bot has failed. Please contact the developer for support."
            )
