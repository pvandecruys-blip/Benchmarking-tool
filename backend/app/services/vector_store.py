"""
SourceLens — Vector Store
Manages document chunk embeddings using ChromaDB (with numpy fallback).
"""

import logging
import hashlib
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)

# Global store instance
_store = None


class VectorStore:
    """Abstraction over ChromaDB or fallback in-memory cosine similarity search."""

    def __init__(self):
        self.use_chromadb = False
        self.collection = None
        self.openai_client = None
        self._fallback_chunks: list[dict] = []
        self._fallback_embeddings: list[list[float]] = []
        self._init_store()

    def _init_store(self):
        """Initialize ChromaDB or fall back to in-memory store."""
        try:
            import chromadb
            settings = get_settings()
            persist_dir = f"{settings.data_dir}/chromadb"
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.use_chromadb = True
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.warning(f"ChromaDB not available ({e}), using in-memory fallback")
            self.use_chromadb = False

    def _get_openai_client(self):
        """Lazy-init OpenAI client."""
        if not self.openai_client:
            from openai import OpenAI
            settings = get_settings()
            self.openai_client = OpenAI(api_key=settings.openai_api_key)
        return self.openai_client

    def create_collection(self, project_id: str):
        """Create or get a collection for a project."""
        collection_name = f"sourcelens_{project_id[:8]}"
        if self.use_chromadb:
            try:
                self.client.delete_collection(collection_name)
            except Exception:
                pass
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            self._fallback_chunks = []
            self._fallback_embeddings = []
        logger.info(f"Created collection for project {project_id}")

    def add_chunks(self, chunks: list[dict]):
        """Embed and store document chunks."""
        if not chunks:
            return

        settings = get_settings()

        # Get embeddings from OpenAI
        texts = [c["text"] for c in chunks]
        embeddings = self._embed_texts(texts)

        if self.use_chromadb and self.collection:
            self.collection.add(
                ids=[c["chunk_id"] for c in chunks],
                documents=texts,
                embeddings=embeddings,
                metadatas=[{
                    "source_file_id": c["source_file_id"],
                    "page_number": str(c.get("page_number", "")),
                    "section_heading": c.get("section_heading", "") or "",
                    "chunk_index": str(c["chunk_index"]),
                } for c in chunks],
            )
        else:
            for chunk, emb in zip(chunks, embeddings):
                self._fallback_chunks.append(chunk)
                self._fallback_embeddings.append(emb)

        logger.info(f"Added {len(chunks)} chunks to vector store")

    def query(self, query_text: str, n_results: int = 8) -> list[dict]:
        """
        Search for relevant chunks.
        Returns list of {text, metadata, distance} dicts.
        """
        query_embedding = self._embed_texts([query_text])[0]

        if self.use_chromadb and self.collection:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
            output = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    output.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0.0,
                    })
            return output
        else:
            return self._fallback_query(query_embedding, n_results)

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings via unified LLM client."""
        import asyncio
        from app.services.llm_client import llm_embed, _pseudo_embedding, has_api_key

        if not has_api_key():
            logger.warning("No API key — using hash-based pseudo-embeddings")
            return [_pseudo_embedding(t) for t in texts]

        try:
            # Run async embed in sync context
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, llm_embed(texts))
                    return future.result()
            except RuntimeError:
                return asyncio.run(llm_embed(texts))
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return [_pseudo_embedding(t) for t in texts]

    def _fallback_query(self, query_embedding: list[float], n_results: int) -> list[dict]:
        """In-memory cosine similarity search."""
        if not self._fallback_embeddings:
            return []

        import numpy as np
        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        scores = []
        for i, emb in enumerate(self._fallback_embeddings):
            emb_vec = np.array(emb)
            emb_norm = np.linalg.norm(emb_vec)
            if emb_norm == 0:
                scores.append((i, 0.0))
            else:
                cos_sim = float(np.dot(query_vec, emb_vec) / (query_norm * emb_norm))
                scores.append((i, 1.0 - cos_sim))  # Distance = 1 - similarity

        scores.sort(key=lambda x: x[1])
        results = []
        for idx, distance in scores[:n_results]:
            chunk = self._fallback_chunks[idx]
            results.append({
                "text": chunk["text"],
                "metadata": {
                    "source_file_id": chunk["source_file_id"],
                    "page_number": str(chunk.get("page_number", "")),
                    "section_heading": chunk.get("section_heading", "") or "",
                    "chunk_index": str(chunk["chunk_index"]),
                },
                "distance": distance,
            })
        return results

    def clear(self):
        """Clear the store."""
        self._fallback_chunks = []
        self._fallback_embeddings = []
        if self.use_chromadb:
            try:
                collections = self.client.list_collections()
                for col in collections:
                    self.client.delete_collection(col.name)
            except Exception:
                pass


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
