# Hercules

AI agent for creating training programs, reviewing training programs and reviewing training progress.

## Quick Start - Discord Bot

### Prerequisites

- Python 3.12+
- Discord Bot Token
- OpenAI token

### Setup (dev)

1. **Install dev dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set your Discord bot token:**
```bash
export DISCORD_BOT_TOKEN=your_token_here
export OPENAI_API_KEY=your_token_here
```

3. **Run the bot:**
```bash
docker compose up -d
```

This Docker Compose sets up:

- Discord bot (`bot`)
- Hercules API (`api`)
- Valkey(`valkey`)

### Usage

- Mention the bot in a channel: `@Hercules your question here`
- Send a direct message to the bot