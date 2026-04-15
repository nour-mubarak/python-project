#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Tool for RAG Management
============================

Command-line interface for RAG document ingestion and querying.
"""

import argparse
import json
import os
from pathlib import Path


def ingest_documents_cli(args):
    """Ingest documents into RAG vector store."""

    from rag.document_loader import (
        FileDocumentLoader,
        URLDocumentLoader,
        DocumentChunker,
    )
    from rag.vector_store import VectorStore

    print("RAG Document Ingestion")
    print("=" * 70)

    # Load documents
    all_docs = []

    if args.files:
        print(f"Loading files from: {args.files}")
        file_loader = FileDocumentLoader()
        docs = file_loader.load(args.files)
        all_docs.extend(docs)
        print(f"  ✓ Loaded {len(docs)} documents")

    if args.urls:
        print(f"Loading URLs...")
        url_loader = URLDocumentLoader()
        for url in args.urls:
            docs = url_loader.load(url)
            all_docs.extend(docs)
        print(f"  ✓ Loaded {len(all_docs)} documents total")

    if not all_docs:
        print("❌ No documents loaded")
        return

    # Chunk documents
    print(f"\nChunking {len(all_docs)} documents...")
    chunker = DocumentChunker()
    chunks = []

    for doc in all_docs:
        if args.chunking_method == "tokens":
            doc_chunks = chunker.chunk_by_tokens(
                doc,
                chunk_size=args.chunk_size or 512,
                overlap=args.chunk_overlap or 50,
            )
        else:  # paragraphs
            doc_chunks = chunker.chunk_by_paragraphs(
                doc,
                max_chunk_size=args.chunk_size or 512,
            )
        chunks.extend(doc_chunks)

    print(f"  ✓ Created {len(chunks)} chunks")

    # Add to vector store
    print(f"\nAdding to vector store...")
    vector_store = VectorStore(
        name=args.collection,
        embedding_model=args.embedding_model,
        persist_dir=args.persist_dir,
    )

    added = vector_store.add_documents(chunks, batch_size=args.batch_size)

    # Save metadata
    vector_store.save_metadata(
        os.path.join(args.persist_dir or "vector_store", "metadata.json")
    )

    print(f"\n✅ Ingestion complete!")
    print(f"   Documents added: {added}")

    info = vector_store.get_collection_info()
    print(f"   Collection size: {info['count']}")


def query_rag_cli(args):
    """Query RAG system."""

    from rag.vector_store import VectorStore
    from rag.generation import RAGGenerator, RAGPipeline

    print("RAG Query")
    print("=" * 70)

    # Load vector store
    vector_store = VectorStore(
        name=args.collection,
        embedding_model=args.embedding_model,
        persist_dir=args.persist_dir,
    )

    # Create generator
    generator = RAGGenerator(
        llm_provider=args.llm_provider,
        model_id=args.model,
        temperature=args.temperature,
    )

    # Create pipeline
    pipeline = RAGPipeline(vector_store, generator)

    # Query
    print(f"Query: {args.query}\n")
    result = pipeline.query(
        query=args.query,
        k=args.top_k,
        language=args.language,
    )

    # Display results
    print("ANSWER:")
    print("-" * 70)
    print(result["answer"])

    print("\n\nSOURCES:")
    print("-" * 70)
    for match in result["retrieval"]["matches"]:
        print(f"[{match['rank']}] {match['title']} (score: {match['score']:.2f})")


def update_collection_cli(args):
    """Update vector store collection."""

    from rag.vector_store import VectorStore

    vector_store = VectorStore(
        name=args.collection,
        persist_dir=args.persist_dir,
    )

    info = vector_store.get_collection_info()

    print(f"Collection: {info['name']}")
    print(f"Documents: {info['count']}")

    if args.delete:
        print(f"\nDeleting documents: {args.delete}")
        deleted = vector_store.delete_documents(args.delete)
        print(f"✅ Deleted {deleted} documents")

    # Show updated count
    info = vector_store.get_collection_info()
    print(f"New count: {info['count']}")


def search_documents_cli(args):
    """Search for documents in RAG vector store."""

    from rag.vector_store import VectorStore, HybridRetriever

    vector_store = VectorStore(
        name=args.collection,
        persist_dir=args.persist_dir,
    )

    print("Document Search")
    print("=" * 70)
    print(f"Query: {args.query}\n")

    # Semantic search
    results = vector_store.search(args.query, k=args.top_k)

    print("Semantic Search Results:")
    print("-" * 70)

    for i, (doc_id, score, metadata) in enumerate(results, 1):
        print(f"[{i}] {metadata.get('title', doc_id)}")
        print(f"    Source: {metadata.get('source')}")
        print(f"    Score: {score:.4f}")
        print()


def export_collection_cli(args):
    """Export vector store to file."""

    from rag.vector_store import VectorStore
    import json

    vector_store = VectorStore(
        name=args.collection,
        persist_dir=args.persist_dir,
    )

    info = vector_store.get_collection_info()

    export_data = {
        "collection_name": info["name"],
        "document_count": info["count"],
        "metadata": info["metadata"],
        "export_timestamp": str(datetime.now()),
    }

    with open(args.output, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"✅ Collection exported to: {args.output}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="RAG Management CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # ════════════════════════════════════════════════════════════════════════
    # ingest: Add documents to RAG
    # ════════════════════════════════════════════════════════════════════════
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents")
    ingest_parser.add_argument("--files", help="Directory or file path")
    ingest_parser.add_argument("--urls", nargs="+", help="List of URLs")
    ingest_parser.add_argument(
        "--collection", default="dalil_rag", help="Collection name"
    )
    ingest_parser.add_argument(
        "--embedding-model", default="all-MiniLM-L6-v2", help="Embedding model"
    )
    ingest_parser.add_argument(
        "--persist-dir", default="vector_store", help="Vector store directory"
    )
    ingest_parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size")
    ingest_parser.add_argument(
        "--chunk-overlap", type=int, default=50, help="Chunk overlap"
    )
    ingest_parser.add_argument(
        "--chunking-method",
        choices=["tokens", "paragraphs"],
        default="tokens",
        help="Chunking method",
    )
    ingest_parser.add_argument(
        "--batch-size", type=int, default=100, help="Batch size for embedding"
    )
    ingest_parser.set_defaults(func=ingest_documents_cli)

    # ════════════════════════════════════════════════════════════════════════
    # query: Ask question to RAG
    # ════════════════════════════════════════════════════════════════════════
    query_parser = subparsers.add_parser("query", help="Query RAG system")
    query_parser.add_argument("--query", required=True, help="Query text")
    query_parser.add_argument(
        "--collection", default="dalil_rag", help="Collection name"
    )
    query_parser.add_argument(
        "--persist-dir", default="vector_store", help="Vector store directory"
    )
    query_parser.add_argument(
        "--embedding-model", default="all-MiniLM-L6-v2", help="Embedding model"
    )
    query_parser.add_argument("--llm-provider", default="openai", help="LLM provider")
    query_parser.add_argument("--model", default="gpt-3.5-turbo", help="Model ID")
    query_parser.add_argument(
        "--temperature", type=float, default=0.3, help="Generation temperature"
    )
    query_parser.add_argument(
        "--top-k", type=int, default=5, help="Number of documents to retrieve"
    )
    query_parser.add_argument(
        "--language", choices=["en", "ar"], default="en", help="Response language"
    )
    query_parser.set_defaults(func=query_rag_cli)

    # ════════════════════════════════════════════════════════════════════════
    # search: Search documents
    # ════════════════════════════════════════════════════════════════════════
    search_parser = subparsers.add_parser("search", help="Search documents")
    search_parser.add_argument("--query", required=True, help="Search query")
    search_parser.add_argument(
        "--collection", default="dalil_rag", help="Collection name"
    )
    search_parser.add_argument(
        "--persist-dir", default="vector_store", help="Vector store directory"
    )
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    search_parser.set_defaults(func=search_documents_cli)

    # ════════════════════════════════════════════════════════════════════════
    # update: Update collection
    # ════════════════════════════════════════════════════════════════════════
    update_parser = subparsers.add_parser("update", help="Update collection")
    update_parser.add_argument(
        "--collection", default="dalil_rag", help="Collection name"
    )
    update_parser.add_argument(
        "--persist-dir", default="vector_store", help="Vector store directory"
    )
    update_parser.add_argument("--delete", nargs="+", help="Document IDs to delete")
    update_parser.set_defaults(func=update_collection_cli)

    # ════════════════════════════════════════════════════════════════════════
    # export: Export collection
    # ════════════════════════════════════════════════════════════════════════
    export_parser = subparsers.add_parser("export", help="Export collection")
    export_parser.add_argument(
        "--collection", default="dalil_rag", help="Collection name"
    )
    export_parser.add_argument(
        "--persist-dir", default="vector_store", help="Vector store directory"
    )
    export_parser.add_argument(
        "--output", default="collection_export.json", help="Output file"
    )
    export_parser.set_defaults(func=export_collection_cli)

    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    from datetime import datetime

    main()
