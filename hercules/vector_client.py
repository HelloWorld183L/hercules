"""
Module for building the Hercules vector store client and related utilities for 
embedding and ingesting documents into Qdrant.
"""

from pathlib import Path
from typing import List

from dotenv import load_dotenv
import openai
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, PointStruct
from qdrant_client.conversions import common_types as types

load_dotenv()

class VectorStoreClient:
    """Wrapper client for interacting with the Qdrant vector store through OpenAI embeddings."""

    def __init__(self, host_url: str, openai_api_key: str, embedding_model_name: str, collection_name: str):
        self.client = QdrantClient(url=host_url)
        self.openai_client = openai.OpenAI(api_key=openai_api_key)

        self.embedding_model_name = embedding_model_name
        self.collection_name = collection_name

    def search(self, query: str, limit: int = 5) -> types.QueryResponse:
        query_vector = self.create_embedding([query])
        return self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit
        )

    def create_collection(self, distance: str = "Cosine"):
        """Create a Qdrant collection with the specified embedding dimensionality and distance metric."""
        embedding = self.create_embedding(["This is a sample embedding to infer vector dimensionality."])
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=len(embedding), distance=distance),
        )
    
    def ingest(self, folder_path: str):
        """Ingest markdown files from the specified folder into Qdrant."""
        docs = self._load_markdown_file(folder_path)
        point_id = 0

        for doc in docs:
            chunks = self._chunk_text(doc["text"])
            vectors = self._embed(chunks)

            points = []
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"text": chunk, "source": doc["path"], "chunk": i}
                )
                points.append(point)
                point_id += 1

            self.client.upsert(collection_name=self.collection_name, points=points)

    def create_embedding(self, input: List[str]) -> List[float]:
        """Create a sample embedding to infer the dimensionality required for the Qdrant collection."""
        sample_embedding = self.openai_client.embeddings.create(model=self.embedding_model_name, input=input).data[0].embedding
        return sample_embedding

    def _load_markdown_file(self, folder_path: str) -> list[dict[str, str]]:
        """Load the contents of markdown files under `folder_path`."""
        docs = []
        for file in Path(folder_path).rglob("*.md"):
            text = file.read_text(encoding="utf-8")
            docs.append({"path": str(file), "text": text})
        return docs

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into chunks with overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap  # Move back by overlap for the next chunk
        return chunks    

    def _embed(self, chunks: list[str]) -> list[list[float]]:
        """Embed a list of texts using OpenAI Embeddings API."""
        # OpenAI can accept a list of inputs and returns embeddings in the same order
        # Use batching if chunks is large to avoid very large requests
        embeddings: list[list[float]] = []
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            resp = self.openai_client.embeddings.create(model=self.embedding_model_name, input=batch)
            embeddings.extend([d.embedding for d in resp.data])
        return embeddings