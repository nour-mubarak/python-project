#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knowledge Agent Router
======================

RAG-based bilingual knowledge assistant (Demo 2).
Handles document indexing and Q&A using ChromaDB + sentence-transformers.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
DOCUMENTS_DIR = BASE_DIR.parent / "knowledge_agent" / "documents"
CHROMA_PERSIST_DIR = BASE_DIR.parent / "knowledge_agent" / ".chromadb"

# Lazy-loaded components
_embedding_model = None
_chroma_client = None
_collection = None
_ollama_client = None


def get_templates():
    from fastapi.templating import Jinja2Templates

    return Jinja2Templates(directory=BASE_DIR / "templates")


def get_embedding_model():
    """Lazy load embedding model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            # Use multilingual model for Arabic + English
            _embedding_model = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
        except ImportError:
            raise HTTPException(
                status_code=500, detail="sentence-transformers not installed"
            )
    return _embedding_model


def get_chroma_collection():
    """Lazy load ChromaDB collection."""
    global _chroma_client, _collection
    if _collection is None:
        try:
            import chromadb
            from chromadb.config import Settings

            _chroma_client = chromadb.Client(
                Settings(
                    persist_directory=str(CHROMA_PERSIST_DIR),
                    anonymized_telemetry=False,
                )
            )

            # Get or create collection
            _collection = _chroma_client.get_or_create_collection(
                name="linguaeval_docs",
                metadata={"description": "LinguaEval knowledge base documents"},
            )
        except ImportError:
            raise HTTPException(status_code=500, detail="chromadb not installed")
    return _collection


def get_ollama_client():
    """Lazy load Ollama client."""
    global _ollama_client
    if _ollama_client is None:
        try:
            from ollama import Client

            _ollama_client = Client(host="http://localhost:11434")
        except ImportError:
            raise HTTPException(status_code=500, detail="ollama package not installed")
    return _ollama_client


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


def detect_language(text: str) -> str:
    """Simple language detection."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    ratio = arabic_chars / max(len(text), 1)
    return "ar" if ratio > 0.3 else "en"


@router.get("/", response_class=HTMLResponse)
async def knowledge_agent_home(request: Request):
    """Knowledge Agent main screen."""
    templates = get_templates()

    # Get indexed documents
    documents = []
    if DOCUMENTS_DIR.exists():
        for f in DOCUMENTS_DIR.iterdir():
            if f.is_file():
                documents.append(
                    {
                        "name": f.name,
                        "size": f.stat().st_size // 1024,
                        "date": datetime.fromtimestamp(f.stat().st_mtime).strftime(
                            "%Y-%m-%d"
                        ),
                    }
                )

    # Get collection stats
    try:
        collection = get_chroma_collection()
        doc_count = collection.count()
    except:
        doc_count = 0

    return templates.TemplateResponse(
        "knowledge_agent.html",
        {
            "request": request,
            "page_title": "Knowledge Agent",
            "documents": documents,
            "indexed_chunks": doc_count,
        },
    )


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload and index a document."""
    # Ensure documents directory exists
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = DOCUMENTS_DIR / file.filename
    content = await file.read()

    # Decode text
    try:
        text = content.decode("utf-8")
    except:
        try:
            text = content.decode("utf-8-sig")
        except:
            text = content.decode("latin-1")

    # Save to disk
    file_path.write_text(text, encoding="utf-8")

    # Index document
    await index_document(file_path.name, text)

    return JSONResponse(
        {
            "status": "success",
            "message": f"Document '{file.filename}' uploaded and indexed",
            "chunks": len(chunk_text(text)),
        }
    )


async def index_document(filename: str, text: str):
    """Index document in ChromaDB."""
    model = get_embedding_model()
    collection = get_chroma_collection()

    # Chunk the text
    chunks = chunk_text(text)

    # Generate embeddings
    embeddings = model.encode(chunks).tolist()

    # Generate unique IDs
    ids = [f"{filename}_{i}" for i in range(len(chunks))]

    # Detect language
    lang = detect_language(text)

    # Prepare metadata
    metadatas = [
        {
            "source": filename,
            "chunk_index": i,
            "language": lang,
        }
        for i in range(len(chunks))
    ]

    # Add to collection
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )


@router.post("/ask")
async def ask_question(
    request: Request,
    question: str = Form(...),
    language: str = Form("auto"),
    model: str = Form("llama3.1:latest"),
):
    """Answer a question using RAG."""
    # Detect language if auto
    if language == "auto":
        language = detect_language(question)

    # Get relevant context
    embed_model = get_embedding_model()
    collection = get_chroma_collection()

    # Embed question
    question_embedding = embed_model.encode([question]).tolist()

    # Query ChromaDB
    results = collection.query(
        query_embeddings=question_embedding,
        n_results=5,
        include=["documents", "metadatas"],
    )

    # Build context
    context_docs = results.get("documents", [[]])[0]
    context = "\n\n".join(context_docs)

    # Build prompt based on language
    if language == "ar":
        system_prompt = """أنت مساعد ذكي متخصص في تقييم الذكاء الاصطناعي متعدد اللغات.
استخدم السياق المقدم للإجابة على الأسئلة بدقة.
إذا لم تجد الإجابة في السياق، قل ذلك بوضوح."""

        prompt = f"""السياق المتوفر:
{context}

السؤال: {question}

الإجابة (بالعربية):"""
    else:
        system_prompt = """You are an intelligent assistant specialized in multilingual AI evaluation.
Use the provided context to answer questions accurately.
If the answer is not in the context, say so clearly."""

        prompt = f"""Available context:
{context}

Question: {question}

Answer:"""

    # Query Ollama
    client = get_ollama_client()

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        answer = response["message"]["content"]
    except Exception as e:
        answer = f"Error: {str(e)}"

    return JSONResponse(
        {
            "question": question,
            "answer": answer,
            "language": language,
            "sources": [m.get("source") for m in results.get("metadatas", [[]])[0]],
            "model": model,
        }
    )


@router.get("/documents")
async def list_documents():
    """List all indexed documents."""
    documents = []

    if DOCUMENTS_DIR.exists():
        for f in DOCUMENTS_DIR.iterdir():
            if f.is_file():
                documents.append(
                    {
                        "name": f.name,
                        "size_kb": f.stat().st_size // 1024,
                        "modified": datetime.fromtimestamp(
                            f.stat().st_mtime
                        ).isoformat(),
                    }
                )

    return {"documents": documents}


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document and its index."""
    file_path = DOCUMENTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from ChromaDB
    try:
        collection = get_chroma_collection()
        # Get all IDs for this document
        all_ids = [f"{filename}_{i}" for i in range(1000)]  # Assume max 1000 chunks
        # Delete silently (ChromaDB handles non-existent IDs)
        collection.delete(ids=all_ids)
    except:
        pass

    # Delete file
    file_path.unlink()

    return {"status": "deleted", "filename": filename}


@router.post("/reindex")
async def reindex_all():
    """Reindex all documents."""
    if not DOCUMENTS_DIR.exists():
        return {"status": "no documents"}

    count = 0
    for f in DOCUMENTS_DIR.iterdir():
        if f.is_file():
            text = f.read_text(encoding="utf-8")
            await index_document(f.name, text)
            count += 1

    return {"status": "success", "reindexed": count}
