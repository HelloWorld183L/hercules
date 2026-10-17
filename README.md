# Hercules

Hercules is an AI agent for creating training programs, reviewing programs, and reviewing training progress. It runs as a Discord bot backed by a FastAPI service, with Valkey for session storage and Qdrant for the knowledge base.

## Requirements

For the Docker Compose setup, install Docker Engine or Docker Desktop with the Docker Compose v2 plugin. You will also need:

- A Discord application and bot token
- An OpenAI API key
- A Mem0 API key for the agent's memory store
- A Tavily API key if you want web search tools to work

Python 3.12 or newer is only needed if you want to run the Hercules Python processes directly on your machine instead of in Docker.

## Configure Environment

Run these commands from the repository root:

```bash
cp .env-example .env
```

Edit `.env` and set the credentials and values described below. `.env` is ignored by Git; keep credentials there and do not commit them.

| Variable | Required | Purpose and setup |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | OpenAI key used by the agent and for knowledge-base embeddings. |
| `STRANDS_MODEL_ID` | Yes | Model ID used by Strands, for example `gpt-4o`. Choose a model available to your OpenAI account. |
| `OPENAI_EMBEDDING_MODEL` | Yes | Embedding model used for Qdrant indexing and search; the template uses `text-embedding-3-small`. |
| `MEM0_API_KEY` | Yes | Mem0 key used by the agent's memory store. |
| `MEM0_LLM_PROVIDER` | No | Mem0 LLM provider; the template uses `openai`. |
| `MEM0_LLM_MODEL` | No | LLM model used by Mem0. Set this to a model supported by your Mem0 provider/account. |
| `MEM0_EMBEDDER_PROVIDER` | No | Mem0 embedding provider; the template uses `openai`. |
| `MEM0_EMBEDDER_MODEL` | No | Mem0 embedding model; the template uses `text-embedding-3-small`. |
| `DISCORD_BOT_TOKEN` | Yes | Token for the Discord bot. |
| `DISCORD_BOT_TIMEOUT` | No | API request timeout in seconds; defaults to `180`. |
| `DISCORD_DEV_GUILD_ID` | No | Discord server ID for faster development command synchronization. Leave unset for global command synchronization. |
| `TAVILY_API_KEY` | Recommended | Enables Tavily web search and extraction tools. |
| `QDRANT_HOST_URL` | Yes | Use `http://qdrant:6333` when running Hercules in Compose. Use `http://localhost:6333` when running the Python processes on your host. |
| `COLLECTION_NAME` | Yes | Qdrant collection name; the template uses `hercules_knowledge_base`. |
| `VALKEY_HOST` | Yes | Use `valkey` for the Compose setup or `localhost` for host-run Python processes. |
| `VALKEY_PORT` | Yes | Compose sets the internal port to `6379`; for host-run Python processes use the published port `6380`. |
| `VALKEY_PASSWORD` | No | Optional Valkey password. The supplied Compose service has no password configured, so leave this blank unless you configure Valkey authentication yourself. |
| `MAX_RESULT_TOKENS` | No | Maximum tool-result tokens before context offloading; defaults to `2000`. |
| `PREVIEW_TOKENS` | No | Preview size for offloaded tool results; defaults to `750`. |
| `HERCULES_API_HOST` | No | Not read by the current entry points. The bot uses `HERCULES_API_URL`; Compose sets it to `http://api:8000` for the bot automatically. |

The Compose setup passes `.env` to its containers, then overrides `VALKEY_HOST` and `VALKEY_PORT` with the container network values. Set `QDRANT_HOST_URL=http://qdrant:6333` in `.env` for Compose, because `localhost` inside the API container is not the Qdrant container.

## Create the Discord Bot

In the Discord Developer Portal, create an application and add a bot. Copy its bot token into `DISCORD_BOT_TOKEN`. Under the bot settings, enable the **Message Content Intent**; Hercules needs it to read messages that mention the bot and direct messages.

Generate an invite URL with the `bot` and `applications.commands` scopes. Grant the bot permission to view channels, send messages, read message history, and attach files. Invite it to the server where you want to use it. To sync slash commands to one development server quickly, set `DISCORD_DEV_GUILD_ID` to that server's ID.

## Run with Docker Compose

From the repository root, after configuring `.env`, build and start the services:

```bash
docker compose up --build -d
```

Compose starts the Hercules API (`api`), Discord bot (`bot`), Qdrant (`qdrant`), and Valkey (`valkey`). The API creates the configured Qdrant collection and indexes files under `knowledge-base/knowledge` when it starts. On the first run, wait for that indexing and startup to finish.

Check service state and API health:

```bash
docker compose ps
curl http://localhost:8000/health
```

The health endpoint should return `{"status":"ok"}`. Follow service logs when diagnosing startup problems:

```bash
docker compose logs -f api bot
```

Once the bot is online, mention it in a channel or send it a direct message. The bot only responds to direct messages and messages that mention it. It can also receive supported file attachments.

Stop the services while keeping their data volumes:

```bash
docker compose down
```

To also delete the Valkey and Qdrant data, use `docker compose down -v`. This permanently removes stored sessions and the local knowledge-base index.

## Run Python Processes Locally

Use this workflow for development when you want to run the API and bot outside Docker. Keep Valkey and Qdrant in Docker, and set `VALKEY_HOST=localhost`, `VALKEY_PORT=6380`, and `QDRANT_HOST_URL=http://localhost:6333` in `.env`.

Create a virtual environment and install the project dependencies:

```bash
uv venv
uv sync
```

Start the backing services:

```bash
docker compose up -d valkey qdrant
```

In one terminal, start the API. It initializes the Qdrant collection and indexes the knowledge-base files before serving requests:

```bash
python main_api.py
```

In a second terminal, activate the same virtual environment and start the bot:

```bash
source .venv/bin/activate
python main.py
```

For host-run processes, set `HERCULES_API_URL=http://localhost:8000` in `.env`; unlike the Compose bot, a locally run bot does not receive this setting automatically.

## Troubleshooting

- If the bot starts but does not respond to channel messages, confirm the Message Content Intent is enabled in the Developer Portal and that the message mentions the bot. Direct messages are also supported.
- If the API cannot connect to Qdrant in Compose, check that `.env` contains `QDRANT_HOST_URL=http://qdrant:6333`. For Python processes running on the host, use `http://localhost:6333` instead.
- If the bot cannot reach the API when running locally, confirm the API is running and `HERCULES_API_URL=http://localhost:8000` is set.
- Inspect startup errors with `docker compose logs -f api bot`; verify the OpenAI, Mem0, and Discord credentials are valid and that the required model IDs are available to your accounts.