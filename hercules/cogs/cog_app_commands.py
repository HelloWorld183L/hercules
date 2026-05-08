import hashlib
import io
import logging

import discord

from hercules.client import HerculesBot
from discord import app_commands
from discord.ext import commands


class HerculesCog(commands.Cog):
    def __init__(self, bot: HerculesBot):
        super().__init__()
        self.bot = bot

    @app_commands.command(description="Creates a workout program.")
    @app_commands.describe(
        workout_split="Workout split that the user prefers (e.g. full body, push pull legs)"
    )
    async def create_program(
        self, interaction: discord.Interaction, workout_split: str
    ):
        """Create a workout program using the same logic as the message handler.

        The slash command provides `workout_split` as extra context.
        """
        await interaction.response.defer()

        # TODO: De-duplicate this code
        try:
            # Get the message content, removing the bot mention if present
            hashed_user_id = hashlib.sha256(
                str(interaction.user.id).encode()
            ).hexdigest()
            result = await self.bot.agent.invoke_async(
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
                file=discord.File(file_bytes, filename="workout_program.md"),
            )

        except Exception as e:
            logging.exception(f"Error in /create_program: {e}")
            await interaction.followup.send(
                "Hercules failed to create the program. Contact the developer."
            )


async def setup(bot):
    await bot.add_cog(HerculesCog(bot))
