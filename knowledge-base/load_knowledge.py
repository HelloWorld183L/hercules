import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, PointStruct
import openai


def embed(chunks: list[str], embedding_model: str) -> list[list[float]]:
    """Embed a list of texts using OpenAI Embeddings API."""
    # OpenAI can accept a list of inputs and returns embeddings in the same order
    # Use batching if chunks is large to avoid very large requests
    embeddings: list[list[float]] = []
    batch_size = 32
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        resp = openai.Embedding.create(model=embedding_model, input=batch)
        embeddings.extend([d["embedding"] for d in resp["data"]])
    return embeddings

def ingest(folder_path: str, client: QdrantClient):
    """Ingest markdown files from the specified folder into Qdrant."""
    docs = load_markdown_file(folder_path)
    point_id = 0

    for doc in docs:
        chunks = chunk_text(doc["text"])
        vectors = embed(chunks, OPENAI_EMBEDDING_MODEL)

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload={"text": chunk, "source": doc["path"], "chunk": i}
            )
            points.append(point)
            point_id += 1

        client.upsert(collection_name=COLLECTION, points=points)

def load_markdown_file(folder_path: str) -> list[dict[str, str]]:
    """Load the contents of markdown files under `folder_path`."""
    docs = []
    for file in Path(folder_path).rglob("*.md"):
        text = file.read_text(encoding="utf-8")
        docs.append({"path": str(file), "text": text})
    return docs

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into chunks with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # Move back by overlap for the next chunk
    return chunks

load_dotenv()

COLLECTION = "hercules_knowledge_base"
DISTANCE = "Cosine"

KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

qdrant_host_url = os.getenv("QDRANT_HOST_URL", "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable must be set for embeddings")

openai.api_key = OPENAI_API_KEY

client = QdrantClient(url=qdrant_host_url)

# Infer embedding size by requesting an embedding for a small sample
sample = ["This is a sample embedding to infer vector dimensionality."]
sample_embedding = openai.Embedding.create(model=OPENAI_EMBEDDING_MODEL, input=sample)["data"][0]["embedding"]
embedding_dim = len(sample_embedding)

client.recreate_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(size=embedding_dim, distance=DISTANCE),
)

ingest(KNOWLEDGE_BASE_DIR, client)