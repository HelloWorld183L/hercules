import hashlib
import io
import logging
import os

from discord import Client, DMChannel, Intents, Message

import discord
from strands import Agent


class HerculesClient(Client):
    def __init__(
        self, agent: Agent, default_workout_program_name: str = "workout_program.md"
    ):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._agent = agent
        self._default_workout_program_name = default_workout_program_name

    async def on_ready(self):
        print(f"Hercules is online as {self.user}")

    async def setup_hook(self) -> None:
        # If a CommandTree was attached to the client by the module that created
        # the client, sync it here so slash commands are registered before login completes.
        try:
            if hasattr(self, "_tree"):
                # If a dev guild is set, sync only to that guild for immediate availability.
                dev_guild = os.getenv("DISCORD_DEV_GUILD_ID")
                if dev_guild:
                    guild_obj = discord.Object(id=int(dev_guild))
                    await self._tree.sync(guild=guild_obj)
                    print(f"Command tree synced to dev guild {dev_guild}")
                else:
                    await self._tree.sync()
                    print("Command tree synced (global)")
        except Exception:
            logging.exception("Failed to sync command tree")

    async def on_message(self, message: Message):
        # Ignore messages from bots
        if message.author.bot:
            return

        mentioned_or_dmed = self.user.mentioned_in(message) or isinstance(
            message.channel, DMChannel
        )
        if mentioned_or_dmed:
            await message.channel.typing()  # Show typing indicator while processing
            try:
                # Get the message content, removing the bot mention if present
                user_input = message.content.replace(f"<@{self.user.id}>", "").strip()

                hashed_user_id = hashlib.sha256(message.author.id.encode()).hexdigest()
                context_input = f"""
                [user_id: {hashed_user_id}], 
                [user_input: {user_input}]
                """

                result = await self._agent.invoke_async(context_input)
                if isinstance(result.message, dict) and "content" in result.message:
                    response_text = result.message["content"][0]["text"]
                else:
                    response_text = str(result.message)

                skill_metrics = result.metrics.tool_metrics["skills"]
                user_wants_program = skill_metrics.tool.input['skill_name'] == 'program-creator'

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
                logging.exception(f"Error processing message: {e}")
                await message.reply(
                    "Hercules discord bot has failed. Please contact the developer for support."
                )