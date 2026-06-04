from datetime import datetime
import hashlib
import io
import atexit
import logging
import os
import shutil
import tempfile
from typing import Optional
import base64
import httpx

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
        agent: Optional[Agent] = None,
        api_url: Optional[str] = None,
        default_workout_program_name: str = "workout_program.md",
        dev_guild_id: Optional[int] = None,
        **kwargs,
    ):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(*args, **kwargs, intents=intents, command_prefix="")
        self.agent = agent
        # URL of the running Hercules API server (e.g. http://localhost:8000)
        self.api_url = api_url
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

            # Prepare request to API server
            hashed_user_id = str(message.author.id)

            data = {"content": user_input, "user_id": hashed_user_id}

            files = None
            if message.attachments:
                att = message.attachments[0]
                content_type = att.content_type
                if content_type and ";" in content_type:
                    content_type = content_type.split(";")[0].strip()

                file_extension = MIME_TYPES.get(content_type, "ignore")
                attachment_contents = await att.read()

                # Store a persistent copy like before
                if file_extension != "ignore":
                    time_of_upload = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    store_filename = f"{time_of_upload}_{hashlib.sha256(str(message.author.id).encode()).hexdigest()}_attachment.{file_extension}"
                    store_temp_file_path = os.path.join(
                        self.persistent_files_dir, store_filename
                    )
                    with open(store_temp_file_path, "wb") as f:
                        f.write(attachment_contents)
                    self._persistent_files.add(store_temp_file_path)
                    # include as a file in the multipart/form-data
                    files = {
                        "file": (
                            att.filename or store_filename,
                            attachment_contents,
                            content_type,
                        )
                    }
                else:
                    logger.warning(
                        f"Attachment with content type {att.content_type} is not supported and will be ignored."
                    )

            # Call the Hercules API server's /invoke endpoint
            try:
                async with httpx.AsyncClient() as client:
                    if files:
                        resp = await client.post(
                            f"{self.api_url}/invoke",
                            data=data,
                            files=files,
                            timeout=120.0,
                        )
                    else:
                        resp = await client.post(
                            f"{self.api_url}/invoke", data=data, timeout=120.0
                        )
                    resp.raise_for_status()
                    result = resp.json()

                response_text = result.get("text", "")
                image = result.get("image")

                # If the API returned an image payload (base64), attach it
                if image and image.get("data"):
                    img_bytes = base64.b64decode(image["data"])
                    img_type = image.get("format", "png")
                    if len(response_text) < self._DISCORD_MSG_LIMIT:
                        await message.reply(
                            response_text,
                            file=discord.File(
                                io.BytesIO(img_bytes), filename=f"graph.{img_type}"
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
                                io.BytesIO(img_bytes), filename=f"graph.{img_type}"
                            ),
                        )

                else:
                    if len(response_text) > self._DISCORD_MSG_LIMIT:
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
                logger.exception(f"Error calling Hercules API: {e}")
                await message.reply(
                    "Hercules discord bot has failed when contacting API. Please contact the developer for support."
                )

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            await message.reply(
                "Hercules discord bot has failed. Please contact the developer for support."
            )

        finally:
            # Do NOT remove persistent files here; they live for the lifetime
            # of the bot process so the agent can reference them across messages.
            shutil.rmtree(agent_work_dir, ignore_errors=True)
