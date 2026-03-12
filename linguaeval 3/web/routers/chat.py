#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time Chat Router
=====================

Demo 3: Side-by-side model comparison chat interface.
Compare Arabic vs English responses in real-time across multiple models.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import json

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent

# Lazy-loaded Ollama client
_ollama_client = None


def get_templates():
    from fastapi.templating import Jinja2Templates

    return Jinja2Templates(directory=BASE_DIR / "templates")


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


def detect_language(text: str) -> str:
    """Detect if text is primarily Arabic or English."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    ratio = arabic_chars / max(len(text), 1)
    return "ar" if ratio > 0.3 else "en"


# Available models for comparison
AVAILABLE_MODELS = [
    {"id": "llama3.1:latest", "name": "Llama 3.1", "provider": "ollama"},
    {"id": "gemma3:27b", "name": "Gemma 3 27B", "provider": "ollama"},
]

# Chat history (in-memory for demo)
chat_sessions: Dict[str, List[Dict]] = {}


@router.get("/", response_class=HTMLResponse)
async def chat_home(request: Request):
    """Real-time Chat Comparison Interface."""
    templates = get_templates()

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "page_title": "Real-time Chat Comparison",
            "models": AVAILABLE_MODELS,
        },
    )


@router.post("/send")
async def send_message(
    request: Request,
    message: str = Form(...),
    models: str = Form(...),  # Comma-separated model IDs
    language: str = Form("auto"),
    session_id: str = Form("default"),
):
    """Send message to multiple models and get responses."""
    model_list = [m.strip() for m in models.split(",") if m.strip()]

    if not model_list:
        raise HTTPException(status_code=400, detail="No models selected")

    # Detect language if auto
    if language == "auto":
        language = detect_language(message)

    # Initialize session if needed
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # Add user message to history
    user_msg = {
        "role": "user",
        "content": message,
        "language": language,
        "timestamp": datetime.now().isoformat(),
    }
    chat_sessions[session_id].append(user_msg)

    # Get responses from each model
    client = get_ollama_client()
    responses = {}

    # System prompts based on language
    system_prompts = {
        "en": """You are a helpful AI assistant. Provide clear, accurate, and professional responses.
Be concise but thorough. If you're unsure about something, acknowledge it.""",
        "ar": """أنت مساعد ذكاء اصطناعي مفيد. قدم إجابات واضحة ودقيقة ومهنية.
كن موجزاً ولكن شاملاً. إذا لم تكن متأكداً من شيء ما، اعترف بذلك.""",
    }

    # Build conversation history for context
    messages = [
        {
            "role": "system",
            "content": system_prompts.get(language, system_prompts["en"]),
        }
    ]

    # Add recent conversation history (last 10 messages)
    for msg in chat_sessions[session_id][-10:]:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg.get("content", "")})

    for model_id in model_list:
        start_time = time.time()
        try:
            response = client.chat(
                model=model_id,
                messages=messages,
            )

            elapsed = time.time() - start_time
            content = response["message"]["content"]

            # Basic quality scoring
            quality_score = score_response(content, language)

            responses[model_id] = {
                "content": content,
                "latency_ms": round(elapsed * 1000),
                "language": language,
                "quality_score": quality_score,
                "success": True,
            }

        except Exception as e:
            responses[model_id] = {
                "content": f"Error: {str(e)}",
                "latency_ms": 0,
                "language": language,
                "quality_score": 0,
                "success": False,
            }

    # Store assistant responses in history
    assistant_msg = {
        "role": "assistant",
        "responses": responses,
        "timestamp": datetime.now().isoformat(),
    }
    chat_sessions[session_id].append(assistant_msg)

    return JSONResponse(
        {
            "user_message": message,
            "language": language,
            "responses": responses,
            "session_id": session_id,
        }
    )


@router.post("/compare")
async def compare_translation(
    request: Request,
    message: str = Form(...),
    models: str = Form(...),
):
    """
    Compare model responses in both English and Arabic.
    Tests cross-lingual consistency.
    """
    model_list = [m.strip() for m in models.split(",") if m.strip()]

    if not model_list:
        raise HTTPException(status_code=400, detail="No models selected")

    # Detect original language
    original_lang = detect_language(message)
    target_lang = "ar" if original_lang == "en" else "en"

    client = get_ollama_client()
    results = {}

    for model_id in model_list:
        model_results = {
            "original": {"lang": original_lang},
            "translated": {"lang": target_lang},
        }

        # Get response in original language
        try:
            start = time.time()
            resp_original = client.chat(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": f"Respond in {original_lang.upper()} only.",
                    },
                    {"role": "user", "content": message},
                ],
            )
            model_results["original"]["content"] = resp_original["message"]["content"]
            model_results["original"]["latency_ms"] = round(
                (time.time() - start) * 1000
            )
            model_results["original"]["quality"] = score_response(
                resp_original["message"]["content"], original_lang
            )
        except Exception as e:
            model_results["original"]["content"] = f"Error: {str(e)}"
            model_results["original"]["quality"] = 0

        # Get response in target language
        try:
            # Translate the prompt
            if target_lang == "ar":
                translated_prompt = f"Please respond in Arabic to: {message}"
            else:
                translated_prompt = f"الرجاء الرد بالإنجليزية على: {message}"

            start = time.time()
            resp_translated = client.chat(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": f"You must respond in {target_lang.upper()} only.",
                    },
                    {"role": "user", "content": translated_prompt},
                ],
            )
            model_results["translated"]["content"] = resp_translated["message"][
                "content"
            ]
            model_results["translated"]["latency_ms"] = round(
                (time.time() - start) * 1000
            )
            model_results["translated"]["quality"] = score_response(
                resp_translated["message"]["content"], target_lang
            )
        except Exception as e:
            model_results["translated"]["content"] = f"Error: {str(e)}"
            model_results["translated"]["quality"] = 0

        # Calculate consistency gap
        orig_q = model_results["original"].get("quality", 0)
        trans_q = model_results["translated"].get("quality", 0)
        model_results["consistency_gap"] = abs(orig_q - trans_q)

        results[model_id] = model_results

    return JSONResponse(
        {
            "original_message": message,
            "original_language": original_lang,
            "target_language": target_lang,
            "results": results,
        }
    )


def score_response(content: str, language: str) -> int:
    """
    Basic response quality scoring.
    Returns a score from 0-100.
    """
    if not content or content.startswith("Error:"):
        return 0

    score = 50  # Base score

    # Length checks
    word_count = len(content.split())
    if word_count >= 10:
        score += 10
    if word_count >= 50:
        score += 10
    if word_count > 500:
        score -= 10  # Too verbose

    # Language-specific checks
    if language == "ar":
        arabic_chars = sum(1 for c in content if "\u0600" <= c <= "\u06ff")
        arabic_ratio = arabic_chars / max(len(content), 1)
        if arabic_ratio > 0.5:
            score += 20  # Good Arabic content
        elif arabic_ratio < 0.2:
            score -= 30  # Responded in wrong language
    else:
        # English checks
        english_chars = sum(1 for c in content if c.isascii() and c.isalpha())
        english_ratio = english_chars / max(len(content), 1)
        if english_ratio > 0.5:
            score += 20

    # Professionalism indicators
    professional_markers = [
        "however",
        "therefore",
        "additionally",
        "furthermore",  # EN
        "لذلك",
        "بالإضافة",
        "علاوة على ذلك",
        "من ناحية أخرى",  # AR
    ]
    if any(marker in content.lower() for marker in professional_markers):
        score += 5

    # Safety checks
    unsafe_patterns = ["I cannot", "I'm unable", "I don't", "لا أستطيع", "لا يمكنني"]
    if any(pattern in content for pattern in unsafe_patterns):
        score -= 5  # Might be refusing valid requests

    return max(0, min(100, score))


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    history = chat_sessions.get(session_id, [])
    return {"session_id": session_id, "messages": history}


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return {"status": "cleared", "session_id": session_id}


@router.get("/models")
async def list_models():
    """List available models for chat."""
    # Try to get actual Ollama models
    try:
        client = get_ollama_client()
        ollama_models = client.list()

        models = []
        for model in ollama_models.get("models", []):
            models.append(
                {
                    "id": model["name"],
                    "name": model["name"].split(":")[0].title(),
                    "size": model.get("size", 0),
                    "provider": "ollama",
                }
            )
        return {"models": models}
    except:
        return {"models": AVAILABLE_MODELS}
