"""
Module for the Hercules Discord bot that interacts with the Hercules API server.
"""

import atexit
import base64
import io
import logging
import os
import shutil
import tempfile
from datetime import datetime

import discord
import httpx
from discord import DMChannel, Intents, Message
from discord.ext import commands
from strands import Agent

from hercules.mime_types import MIME_TYPES
from hercules.tools.helpers import hash_user_id

logger = logging.getLogger("hercules")


class HerculesBot(commands.Bot):
    def __init__(
        self,
        *args,
        agent: Agent | None = None,
        api_url: str | None = None,
        default_workout_program_name: str = "workout_program.md",
        dev_guild_id: int | None = None,
        api_timeout: float = 120.0,
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
        self._api_timeout = api_timeout

    async def on_ready(self):
        logger.info(f"Hercules is online as {self.user}")

    async def setup_hook(self) -> None:
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

        # Ignore messages that don't mention the bot or are not direct messages
        mentioned_or_dmed = self.user.mentioned_in(message) or isinstance(
            message.channel, DMChannel
        )
        if not mentioned_or_dmed:
            return

        await message.channel.typing()  # Show typing indicator while processing

        # Get the message content, removing the bot mention if present
        user_input = message.content.replace(f"<@{self.user.id}>", "").strip()
        hashed_user_id = hash_user_id(message.author.id)

        if not message.attachments:
            files = {}
        else:
            att = message.attachments[0]
            content_type, file_extension = self._get_content_type_and_extension(att)
            if not content_type:
                files = {}
            else:
                # Separate reading attachment contents to avoid blocking the event loop for too long
                attachment_contents = await att.read()
                files = self._collect_file_attachments(
                    message,
                    content_type,
                    file_extension,
                    att.filename,
                    attachment_contents,
                )

        # Call the Hercules API server's /invoke endpoint
        try:
            result = await self._invoke_hercules_api(user_input, hashed_user_id, files)
        except RuntimeError as e:
            logger.error(f"Error calling Hercules API: {e}")
            await message.reply(
                "Hercules API server is unreachable or returned an error. Please try again later."
            )
            return

        response_text = result.get("text", "")
        image = result.get("image")
        if image and image.get("data"):
            await self._reply_with_image(message, response_text, image)
        elif self._is_long_response(response_text):
            await self._reply_long_text(message, response_text)
        else:
            await message.reply(response_text)

    def _is_long_response(self, text: str) -> bool:
        return len(text) > self._DISCORD_MSG_LIMIT

    async def _reply_long_text(self, message: Message, response_txt: str) -> None:
        await message.reply(
            "The response is quite long and has hit the Discord limit, so I've put it into a markdown file instead.",
            file=discord.File(
                io.BytesIO(response_txt.encode("utf-8")), filename="response.md"
            ),
        )

    async def _reply_with_image(
        self, message: Message, response_text: str, image_payload: dict[str, str]
    ) -> None:
        img_bytes = base64.b64decode(image_payload["data"])
        img_type = image_payload.get("format", "png")
        image_file = discord.File(io.BytesIO(img_bytes), filename=f"graph.{img_type}")

        if self._is_long_response(response_text):
            await self._reply_long_text(message, response_text)
            await message.reply("Graph generated.", file=image_file)
        else:
            await message.reply(response_text, file=image_file)

    async def _invoke_hercules_api(
        self, user_input: str, hashed_user_id: str, files: dict
    ) -> dict:
        """
        Invoke the Hercules API server's /invoke endpoint with the given user input and files.
        Returns the JSON response from the API server.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.api_url}/invoke",
                    data={"content": user_input, "user_id": hashed_user_id},
                    files=files,
                    timeout=self._api_timeout,
                )
                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"Error calling Hercules API: {e}")
            raise RuntimeError(
                "Hercules API server is unreachable or returned an error. Please try again later."
            ) from e

    def _get_content_type_and_extension(
        self, attachment: discord.Attachment
    ) -> tuple[str, str]:
        """
        Determine the content type and file extension for a Discord attachment.
        If the content type is not provided, infer it from the filename.
        """
        content_type = attachment.content_type
        if content_type and ";" in content_type:
            content_type = content_type.split(";")[0].strip()
            file_extension = MIME_TYPES.get(content_type, "ignore")
        elif not content_type:
            file_extension = attachment.filename.split(".")[-1].lower()
            content_type = next(
                (k for k, v in MIME_TYPES.items() if v == file_extension),
                "application/octet-stream",
            )
            logger.warning(
                f"Attachment {attachment.filename} has no content type; inferred as {content_type} based on file extension."
            )

        if file_extension == "ignore":
            logger.warning(
                f"Attachment {attachment.filename} has unsupported content type {content_type}; ignoring."
            )
            return None, None

        return content_type, file_extension

    def _collect_file_attachments(
        self,
        message: Message,
        content_type: str,
        file_extension: str,
        att_filename: str,
        attachment_contents: bytes,
    ) -> dict[str, tuple[str, bytes, str]]:
        """
        Collects file attachments from a Discord message and returns a list of tuples containing
        the filename, file content as bytes, and the content type.
        """

        time_of_upload = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        store_filename = f"{time_of_upload}_{hash_user_id(message.author.id)}_attachment.{file_extension}"
        store_temp_file_path = os.path.join(self.persistent_files_dir, store_filename)
        with open(store_temp_file_path, "wb") as f:
            f.write(attachment_contents)
        self._persistent_files.add(store_temp_file_path)

        # include as a file in the multipart/form-data
        files = {
            "file": (
                att_filename or store_filename,
                attachment_contents,
                content_type,
            )
        }

        return files
