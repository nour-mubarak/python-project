#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Store Management for RAG
================================

Manage embeddings and vector database operations.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
import numpy as np


class EmbeddingEngine:
    """Generate embeddings for documents."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding engine.

        Args:
            model_name: HuggingFace sentence-transformers model
        """
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        """Load sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Loaded embedding model: {self.model_name}")
        except ImportError:
            raise ImportError(
                "sentence-transformers required: pip install sentence-transformers"
            )

    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=True)
        return [e.tolist() for e in embeddings]


class VectorStore:
    """
    Manage document embeddings and similarity search.

    Features:
    - Store embeddings (ChromaDB by default)
    - Semantic similarity search
    - Metadata filtering
    - Batch operations
    """

    def __init__(
        self,
        name: str = "dalil_rag",
        embedding_model: str = "all-MiniLM-L6-v2",
        persist_dir: Optional[str] = None,
    ):
        """
        Initialize vector store.

        Args:
            name: Collection name
            embedding_model: Model for embeddings
            persist_dir: Directory for persistent storage
        """
        self.name = name
        self.embedding_engine = EmbeddingEngine(embedding_model)
        self.persist_dir = persist_dir or "./vector_store"

        self._init_chroma()

    def _init_chroma(self):
        """Initialize ChromaDB."""
        try:
            import chromadb

            if self.persist_dir:
                self.client = chromadb.PersistentClient(path=self.persist_dir)
            else:
                self.client = chromadb.EphemeralClient()

            self.collection = self.client.get_or_create_collection(
                name=self.name, metadata={"hnsw:space": "cosine"}
            )

            print(f"✅ ChromaDB initialized: {self.name}")
        except ImportError:
            raise ImportError("chromadb required: pip install chromadb")

    def add_documents(self, documents: List, batch_size: int = 100) -> int:
        """
        Add documents to vector store.

        Args:
            documents: List of Document objects
            batch_size: Batch size for processing

        Returns:
            Number of documents added
        """
        print(f"Adding {len(documents)} documents to vector store...")

        added = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]

            ids = []
            embeddings = []
            documents_data = []
            metadatas = []

            for doc in batch:
                ids.append(doc.id)
                embeddings.append(self.embedding_engine.embed(doc.content))
                documents_data.append(doc.content)
                metadatas.append(
                    {"title": doc.title, "source": doc.source, **doc.metadata}
                )

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents_data,
                metadatas=metadatas,
            )

            added += len(batch)
            print(f"  Added {added}/{len(documents)}")

        print(f"✅ {added} documents added to vector store")
        return added

    def search(
        self,
        query: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar documents.

        Args:
            query: Search query
            k: Number of results to return
            where: Optional metadata filter

        Returns:
            List of (document_id, score, metadata) tuples
        """
        query_embedding = self.embedding_engine.embed(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "distances", "metadatas"],
        )

        # Convert distances to similarity scores (0-1)
        # ChromaDB returns cosine distances
        search_results = []

        if results["ids"] and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # Convert cosine distance to similarity (1 - distance)
                similarity = 1 - distance
                metadata = results["metadatas"][0][i]

                search_results.append((doc_id, similarity, metadata))

        return search_results

    def delete_documents(self, doc_ids: List[str]) -> int:
        """Delete documents from vector store."""
        self.collection.delete(ids=doc_ids)
        return len(doc_ids)

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        return {
            "name": self.collection.name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata,
        }

    def save_metadata(self, path: str) -> None:
        """Save collection metadata."""
        info = self.get_collection_info()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)


class HybridRetriever:
    """
    Hybrid retrieval combining semantic + keyword search.
    """

    def __init__(self, vector_store: VectorStore):
        """Initialize hybrid retriever."""
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        k: int = 5,
        alpha: float = 0.7,  # Weight for semantic search vs keyword
    ) -> List[Tuple[str, float, Dict, str]]:
        """
        Retrieve documents using hybrid search.

        Args:
            query: Search query
            k: Number of results
            alpha: Weight for semantic search (1-alpha for keyword)

        Returns:
            List of (doc_id, score, metadata, content) tuples
        """
        # Semantic search
        semantic_results = self.vector_store.search(query, k=k * 2)

        # Keyword search (simple TF matching)
        keyword_results = self._keyword_search(query, k=k * 2)

        # Combine and rank
        combined = self._combine_results(
            semantic_results, keyword_results, alpha=alpha, k=k
        )

        return combined

    def _keyword_search(self, query: str, k: int) -> List[Tuple[str, float]]:
        """Simple keyword search."""
        # This is a placeholder - in production, use Elasticsearch or similar
        query_terms = set(query.lower().split())

        # Get all documents from collection
        results = []

        # Simple scoring: count matching terms
        # In production, implement proper BM25 scoring

        return results

    def _combine_results(
        self,
        semantic_results: List[Tuple[str, float, Dict]],
        keyword_results: List[Tuple[str, float]],
        alpha: float,
        k: int,
    ) -> List[Tuple[str, float, Dict, str]]:
        """Combine semantic and keyword results."""
        # Normalize and combine scores
        combined = {}

        for doc_id, score, metadata in semantic_results:
            combined[doc_id] = {
                "semantic_score": score,
                "metadata": metadata,
            }

        for doc_id, score in keyword_results:
            if doc_id in combined:
                combined[doc_id]["keyword_score"] = score
            else:
                combined[doc_id] = {"keyword_score": score, "metadata": {}}

        # Calculate composite score
        results = []
        for doc_id, scores_dict in combined.items():
            semantic = scores_dict.get("semantic_score", 0)
            keyword = scores_dict.get("keyword_score", 0)

            composite = alpha * semantic + (1 - alpha) * keyword

            results.append(
                (
                    doc_id,
                    composite,
                    scores_dict["metadata"],
                    "",  # Content would be fetched from vector store
                )
            )

        # Sort by score and return top k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
