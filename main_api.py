"""Run the Hercules FastAPI ASGI app with Uvicorn."""

import logging
import os
import sys

import uvicorn
from dotenv import load_dotenv

from hercules.vector_client import get_vector_client

load_dotenv()

COLLECTION = os.getenv("COLLECTION_NAME")
DISTANCE = "Cosine"

KNOWLEDGE_BASE_DIR = os.path.join("knowledge-base", "knowledge")

vector_client = get_vector_client()

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
