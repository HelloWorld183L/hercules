# Hercules

AI agent for creating training programs and reviewing progress.

## Quick Start - Discord Bot

### Prerequisites

- Python 3.12+
- Discord Bot Token
- OpenAI token

### Setup

1. **Install dependencies:**
```bash
pip install -e .
```

2. **Set your Discord bot token:**
```bash
export DISCORD_BOT_TOKEN=your_token_here
export OPENAI_API_KEY=your_token_here
```

3. **Run the bot:**
```bash
python -m hercules.agent
```

### Usage

- Mention the bot in a channel: `@Hercules your question here`
- Send a direct message to the bot

The bot uses Strands Agents with OpenAI to respond to user queries.
