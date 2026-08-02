"""Run the Hercules FastAPI ASGI app with Uvicorn."""

import logging
import os
import sys

import uvicorn
from dotenv import load_dotenv

from hercules.vector_client import VectorStoreClient

load_dotenv()

COLLECTION = os.getenv("COLLECTION_NAME")
DISTANCE = "Cosine"

KNOWLEDGE_BASE_DIR = os.path.join("knowledge-base", "knowledge")

QDRANT_HOST_URL = os.getenv("QDRANT_HOST_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable must be set for embeddings")

vector_client = VectorStoreClient(
    host_url=QDRANT_HOST_URL,
    openai_api_key=OPENAI_API_KEY,
    embedding_model_name=OPENAI_EMBEDDING_MODEL,
    collection_name=COLLECTION,
)

if __name__ == "__main__":
    vector_client.create_collection(distance=DISTANCE)
    vector_client.ingest(KNOWLEDGE_BASE_DIR)
    # Ensure Strands and Hercules logs go to stdout so container logs are
    # captured by `docker logs` and aggregators.
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    strands_logger = logging.getLogger("strands")
    strands_logger.setLevel(logging.DEBUG)
    strands_logger.addHandler(stream_handler)

    hercules_logger = logging.getLogger("hercules")
    hercules_logger.setLevel(logging.DEBUG)
    hercules_logger.addHandler(stream_handler)

    uvicorn.run("hercules.api_server:app", host="0.0.0.0", port=8000, reload=False)
