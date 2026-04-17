"""
Hercules - A Discord bot powered by Strands Agents
"""

import os
import asyncio
from discord import Client, DMChannel, Intents, Message
import discord
from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.tools import tool
from strands_tools import calculator, current_time
from strands_tools.tavily import tavily_search
from strands_tools import mem0_memory
import warnings
import hashlib

from hercules.steering import WorkoutProgramSteeringHandler

warnings.filterwarnings("ignore", category=DeprecationWarning, module="mem0_memory")

load_dotenv()

STRANDS_MODEL_ID = os.getenv(
    "STRANDS_MODEL_ID", "gpt-4o"
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DISCORD_RESPONSE_LIMIT = 2000

model = OpenAIModel(client_args={"api_key": OPENAI_API_KEY}, model_id=STRANDS_MODEL_ID)

# Load the Agent SOP
with open(os.path.join(os.path.dirname(__file__), "sop.md"), "r") as f:
    SYSTEM_PROMPT = f.read()

workout_program_steering_handler = WorkoutProgramSteeringHandler()

# Create the Strands Agent with the SOP
agent = Agent(
    model=model,
    tools=[calculator, current_time, tavily_search, mem0_memory],
    plugins=[workout_program_steering_handler],
    system_prompt=SYSTEM_PROMPT
)


# Discord Client
class HerculesClient(Client):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f"Hercules is online as {self.user}")

    async def on_message(self, message: Message):
        # Ignore messages from bots
        if message.author.bot:
            return

        mentioned_or_dmed = self.user.mentioned_in(message) or isinstance(message.channel, DMChannel)
        if mentioned_or_dmed:
            try:
                # Get the message content, removing the bot mention if present
                user_input = message.content.replace(f"<@{self.user.id}>", "").strip()

                discord_user_id = str(message.author.id)

                # For enhanced privacy we hash this since discord IDs can link back to users
                hashed_user_id = hashlib.sha256(discord_user_id.encode()).hexdigest()

                context_input = f"""
                [user_id: {hashed_user_id}], 
                [user_input: {user_input}]
                """

                # Call the Strands Agent
                result = agent(context_input)
                if isinstance(result.message, dict) and "content" in result.message:
                    response_text = result.message["content"][0]["text"]
                else:
                    response_text = str(result.message)

                if len(response_text) > DISCORD_RESPONSE_LIMIT:
                    temp_file = "hercules_response.txt"
                    with open(temp_file, "w") as f:
                        f.write(response_text)
                    await message.reply(
                        "Unfortunately, the response is too long for Discord. Here's a markdown file:",
                        file=discord.File(temp_file, filename="workout_program.md")
                    )
                else:
                    # Send the response
                    await message.reply(response_text)
            except Exception as e:
                await message.reply(f"Hercules discord bot has failed. Please contact the developer for support.")


# Run the bot
def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set")

    client = HerculesClient()
    client.run(token)


if __name__ == "__main__":
    main()
