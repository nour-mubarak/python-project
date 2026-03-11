#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluations Router
==================

API routes for evaluation management.
"""

import os
import json
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# Get base directory
BASE_DIR = Path(__file__).parent.parent


def get_templates():
    from fastapi.templating import Jinja2Templates

    return Jinja2Templates(directory=BASE_DIR / "templates")


# In-memory storage for running evaluations
running_evaluations = {}


@router.get("/new", response_class=HTMLResponse)
async def new_evaluation(request: Request):
    """Create Evaluation Wizard (Screen 2)"""
    templates = get_templates()

    # Available prompt packs
    prompts_dir = BASE_DIR.parent / "prompts"
    prompt_packs = []
    if prompts_dir.exists():
        for f in prompts_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    prompt_packs.append(
                        {
                            "id": f.stem,
                            "name": data.get("name", f.stem),
                            "description": data.get("description", ""),
                            "version": data.get("version", "1.0"),
                            "count": len(data.get("prompts", [])),
                        }
                    )
            except:
                pass

    return templates.TemplateResponse(
        "wizard.html",
        {
            "request": request,
            "page_title": "Create New Evaluation",
            "prompt_packs": prompt_packs,
            "available_models": [
                {
                    "id": "llama3.1:latest",
                    "name": "Llama 3.1 (Ollama)",
                    "provider": "ollama",
                },
                {
                    "id": "gemma3:27b",
                    "name": "Gemma 3 27B (Ollama)",
                    "provider": "ollama",
                },
                {"id": "gpt-4o", "name": "GPT-4o (OpenAI)", "provider": "openai"},
                {
                    "id": "gpt-4o-mini",
                    "name": "GPT-4o Mini (OpenAI)",
                    "provider": "openai",
                },
                {
                    "id": "claude-3-opus",
                    "name": "Claude 3 Opus (Anthropic)",
                    "provider": "anthropic",
                },
            ],
        },
    )


@router.post("/create")
async def create_evaluation(
    request: Request,
    background_tasks: BackgroundTasks,
    client_name: str = Form(...),
    prompt_pack: str = Form(...),
    models: list = Form(...),
    use_judge: bool = Form(False),
):
    """Start a new evaluation"""
    eval_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Store evaluation info
    running_evaluations[eval_id] = {
        "id": eval_id,
        "client_name": client_name,
        "prompt_pack": prompt_pack,
        "models": models,
        "use_judge": use_judge,
        "status": "pending",
        "progress": 0,
        "started_at": datetime.now().isoformat(),
    }

    # Run evaluation in background
    background_tasks.add_task(
        run_evaluation_task,
        eval_id,
        client_name,
        prompt_pack,
        models,
        use_judge,
    )

    return RedirectResponse(url=f"/evaluations/run/{eval_id}", status_code=303)


async def run_evaluation_task(
    eval_id: str,
    client_name: str,
    prompt_pack: str,
    models: list,
    use_judge: bool,
):
    """Background task to run evaluation"""
    running_evaluations[eval_id]["status"] = "running"

    try:
        # Build command
        cmd = [
            "python",
            str(BASE_DIR.parent / "run_evaluation.py"),
            "--client",
            client_name,
            "--prompt-pack",
            prompt_pack,
        ]

        if use_judge:
            cmd.append("--use-judge")

        for model in models:
            cmd.extend(["--model", model])

        # Run process
        result = subprocess.run(
            cmd,
            cwd=str(BASE_DIR.parent),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            running_evaluations[eval_id]["status"] = "completed"
            running_evaluations[eval_id]["progress"] = 100
        else:
            running_evaluations[eval_id]["status"] = "failed"
            running_evaluations[eval_id]["error"] = result.stderr

    except Exception as e:
        running_evaluations[eval_id]["status"] = "failed"
        running_evaluations[eval_id]["error"] = str(e)


@router.get("/run/{eval_id}", response_class=HTMLResponse)
async def evaluation_run(request: Request, eval_id: str):
    """Evaluation Run Screen (Screen 3)"""
    templates = get_templates()

    eval_data = running_evaluations.get(eval_id)
    if not eval_data:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return templates.TemplateResponse(
        "run.html",
        {
            "request": request,
            "page_title": f"Running Evaluation - {eval_data['client_name']}",
            "evaluation": eval_data,
        },
    )


@router.get("/status/{eval_id}")
async def evaluation_status(eval_id: str):
    """Get evaluation status (for polling)"""
    eval_data = running_evaluations.get(eval_id)
    if not eval_data:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return {
        "id": eval_id,
        "status": eval_data["status"],
        "progress": eval_data.get("progress", 0),
        "error": eval_data.get("error"),
    }


@router.get("/list", response_class=HTMLResponse)
async def list_evaluations(request: Request):
    """List all evaluations"""
    templates = get_templates()

    # Get completed evaluations from results
    results_dir = BASE_DIR.parent / "results"
    completed = []

    if results_dir.exists():
        for f in sorted(results_dir.glob("*_results.json"), reverse=True):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    completed.append(
                        {
                            "id": f.stem,
                            "client": data.get("metadata", {}).get(
                                "client_name", "Unknown"
                            ),
                            "models": data.get("metadata", {}).get("models", []),
                            "timestamp": data.get("metadata", {}).get("timestamp", ""),
                        }
                    )
            except:
                pass

    return templates.TemplateResponse(
        "evaluations_list.html",
        {
            "request": request,
            "page_title": "All Evaluations",
            "completed": completed,
            "running": list(running_evaluations.values()),
        },
    )
