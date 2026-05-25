from datetime import datetime
import hashlib
import io
import atexit
import logging
import os
import shutil
import tempfile
from typing import Optional

from discord import DMChannel, Intents, Message
from discord.ext import commands

import discord
from strands import Agent

from hercules.mime_types import MIME_TYPES

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
        # Persistent storage for uploaded files that should survive the
        # lifecycle of a single message handler. These files will be
        # cleaned up when the process exits.
        self.persistent_files_dir = tempfile.mkdtemp(prefix="hercules_persistent_")
        self._persistent_files = set()
        # Ensure the persistent directory is removed on process exit
        atexit.register(shutil.rmtree, self.persistent_files_dir, ignore_errors=True)

        self._DISCORD_MSG_LIMIT = 2000

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
            agent_work_dir = tempfile.mkdtemp(prefix="hercules_agent_run_")
            # Get the message content, removing the bot mention if present
            user_input = message.content.replace(f"<@{self.user.id}>", "").strip()

            hashed_user_id = hashlib.sha256(str(message.author.id).encode()).hexdigest()
            context_input = f"""
            [user_id: {hashed_user_id}], 
            [user_input: {user_input}]
            """
            if message.attachments:
                logger.info(message.attachments[0].content_type)
                file_extension = MIME_TYPES.get(
                    message.attachments[0].content_type, "ignore"
                )
                if not file_extension == "ignore":
                    attachment_contents = await message.attachments[0].read()
                    time_of_upload = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    # Store the attachment in the bot-level persistent directory
                    store_filename = (
                        f"{time_of_upload}_{hashed_user_id}_attachment.{file_extension}"
                    )
                    store_temp_file_path = os.path.join(
                        self.persistent_files_dir, store_filename
                    )
                    logger.info(f"Storing attachment to {store_temp_file_path}")
                    with open(store_temp_file_path, "wb") as f:
                        f.write(attachment_contents)

                    # Track this file for possible later cleanup or introspection
                    self._persistent_files.add(store_temp_file_path)

                    context_input += f", [file_extension: {file_extension}], [file_path: {store_temp_file_path}]"

            result = await self.agent.invoke_async(context_input)
            if isinstance(result.message, dict) and "content" in result.message:
                response_text = result.message["content"][0]["text"]
            else:
                response_text = str(result.message)

            skill_metrics = result.metrics.tool_metrics.get("skills")
            user_wants_program = (
                skill_metrics
                and skill_metrics.tool["input"]["skill_name"] == "program-creator"
            )
            moving_avg_graph_metrics = result.metrics.tool_metrics.get(
                "create_moving_avg_graph"
            )
            volume_graph_metrics = result.metrics.tool_metrics.get(
                "create_volume_graph"
            )
            graph_metrics = moving_avg_graph_metrics or volume_graph_metrics
            logger.info(f"Moving avg graph metrics: {moving_avg_graph_metrics}")
            logger.info(f"Volume graph metrics: {volume_graph_metrics}")

            if user_wants_program:
                file_bytes = io.BytesIO(response_text.encode("utf-8"))
                file_bytes.seek(0)
                await message.reply(
                    """
                    I have attached your training program. Please let me know if you have any questions or need further assistance.
                    """,
                    file=discord.File(
                        file_bytes, filename=self._default_workout_program_name
                    ),
                )
            # Graph tool call has been made due to user requesting a graph
            elif graph_metrics:
                # For compatibility with OpenAI models, the image responses in base64 format are recorded as user messages
                img_response = [
                    msg for msg in self.agent.messages if msg["role"] == "user"
                ][-1]
                logger.info(f"Image response: {img_response}")
                img_details = img_response["content"][0]["toolResult"]["content"][0][
                    "image"
                ]
                img_bytes = img_details["source"]["bytes"]

                img_type = img_details["format"]
                if len(response_text) < self._DISCORD_MSG_LIMIT:
                    await message.reply(
                        response_text,
                        file=discord.File(
                            io.BytesIO(img_bytes),
                            filename=f"graph.{img_type}",
                        ),
                    )
                else:
                    await message.reply(
                        "The response is quite long and has hit the Discord limit, so I've put it into a markdown file instead.",
                        file=discord.File(
                            io.BytesIO(response_text.encode("utf-8")),
                            filename="response.md",
                        ),
                    )
                    await message.reply(
                        "Graph generated.",
                        file=discord.File(
                            io.BytesIO(img_bytes),
                            filename=f"graph.{img_type}",
                        ),
                    )
            else:
                if len(response_text) > self._DISCORD_MSG_LIMIT:
                    # If the response is too long for a single message, split it into chunks
                    await message.reply(
                        "The response is quite long and has hit the Discord limit, so I've put it into a markdown file instead.",
                        file=discord.File(
                            io.BytesIO(response_text.encode("utf-8")),
                            filename="response.md",
                        ),
                    )
                else:
                    await message.reply(response_text)

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            print(e)
            await message.reply(
                "Hercules discord bot has failed. Please contact the developer for support."
            )

        finally:
            # Do NOT remove persistent files here; they live for the lifetime
            # of the bot process so the agent can reference them across messages.
            shutil.rmtree(agent_work_dir, ignore_errors=True)
