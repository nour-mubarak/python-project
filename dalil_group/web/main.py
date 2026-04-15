#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinguaEval Web Dashboard
========================

FastAPI-based web interface for multilingual AI evaluation.

Usage:
    uvicorn web.main:app --reload --port 8000
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import json
import uuid

from fastapi import (
    FastAPI,
    Request,
    Form,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.routers import evaluations, reports, knowledge_agent, chat, auth

# ═══════════════════════════════════════════════════════════════
# APP CONFIGURATION
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="Dalīl Group",
    description="""
## Multilingual AI Assurance Platform

Dalīl Group — Evidence-Led AI. Guided by Rigour.

A comprehensive platform for evaluating multilingual AI systems, 
with a focus on Arabic-English bilingual performance and cultural integrity.

### Features

- **Evaluation Pipeline** — Automated testing across 6 quality dimensions
- **Web Dashboard** — 10-screen UI for managing evaluations
- **Knowledge Agent** — RAG-based bilingual assistant
- **Real-time Chat** — Side-by-side model comparison

### Scoring Dimensions

| Dimension | Description |
|-----------|-------------|
| Factual Accuracy | Ground-truth comparison |
| Gender Bias | Lexicon matching + pattern detection |
| Hallucination | Claim extraction + verification |
| Cross-Lingual Consistency | Embedding similarity |
| Cultural Sensitivity | Pattern matching |
| Fluency & Coherence | Perplexity + judge model |

### Prompt Packs

- Government (36 prompts)
- University (20 prompts)  
- Healthcare (25 prompts)
- Legal (25 prompts)
- Customer Support (30 prompts)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "evaluations", "description": "Evaluation management"},
        {"name": "reports", "description": "Report generation (DOCX, PDF, PPTX)"},
        {"name": "knowledge_agent", "description": "RAG-based bilingual assistant"},
        {"name": "chat", "description": "Real-time model comparison"},
        {"name": "settings", "description": "Platform configuration"},
    ],
)

# Static files and templates
BASE_DIR = Path(__file__).parent
# Static files and templates
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR.parent / "data"
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(knowledge_agent.router, prefix="/agent", tags=["knowledge_agent"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


# ═══════════════════════════════════════════════════════════════
# TEMPLATE RENDERING HELPER
# ═══════════════════════════════════════════════════════════════


def render_template(name: str, context: dict) -> str:
    """Render a template with the given context."""
    template = templates.get_template(name)
    return template.render(context)


# ═══════════════════════════════════════════════════════════════
_settings = {
    "ollama_host": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
    "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
    "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
    "azure_openai_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    "azure_openai_key": os.environ.get("AZURE_OPENAI_KEY", ""),
    "default_model": "llama3.1:latest",
    "judge_model": "llama3.1:latest",
    # Email notification settings
    "email_enabled": os.environ.get("EMAIL_ENABLED", "").lower() == "true",
    "smtp_host": os.environ.get("SMTP_HOST", ""),
    "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
    "smtp_user": os.environ.get("SMTP_USER", ""),
    "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
    "notification_email": os.environ.get("NOTIFICATION_EMAIL", ""),
    "notify_evaluation_complete": True,
    "notify_evaluation_failed": True,
    "notify_new_user": False,
    "notify_daily_summary": False,
}


@app.get("/health", tags=["health"], summary="Health check")
async def health_check():
    """
    Check the health status of the LinguaEval platform.

    Returns:
        Health status including Ollama connectivity.
    """
    import httpx

    ollama_status = "unknown"
    ollama_models = []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_settings['ollama_host']}/api/tags")
            if resp.status_code == 200:
                ollama_status = "healthy"
                data = resp.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
            else:
                ollama_status = "unhealthy"
    except Exception:
        ollama_status = "unreachable"

    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ollama": {
                "status": ollama_status,
                "host": _settings["ollama_host"],
                "models": ollama_models,
            },
            "openai": {
                "configured": bool(_settings["openai_api_key"]),
            },
            "anthropic": {
                "configured": bool(_settings["anthropic_api_key"]),
            },
        },
    }


@app.get("/settings", response_class=HTMLResponse, tags=["settings"])
async def settings_page(request: Request):
    """Settings configuration page."""
    import httpx

    # Check Ollama status
    ollama_status = "unknown"
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_settings['ollama_host']}/api/tags")
            if resp.status_code == 200:
                ollama_status = "connected"
                data = resp.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
            else:
                ollama_status = "error"
    except Exception:
        ollama_status = "disconnected"

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "page_title": "Settings",
            "settings": _settings,
            "ollama_status": ollama_status,
            "ollama_models": ollama_models,
        },
    )


@app.post("/settings/save", tags=["settings"], summary="Save settings")
async def save_settings(
    request: Request,
    ollama_host: str = Form(...),
    openai_api_key: str = Form(""),
    anthropic_api_key: str = Form(""),
    azure_openai_endpoint: str = Form(""),
    azure_openai_key: str = Form(""),
    default_model: str = Form("llama3.1:latest"),
    judge_model: str = Form("llama3.1:latest"),
    # Email notification settings
    email_enabled: bool = Form(False),
    smtp_host: str = Form(""),
    smtp_port: int = Form(587),
    smtp_user: str = Form(""),
    smtp_password: str = Form(""),
    notification_email: str = Form(""),
    notify_evaluation_complete: bool = Form(False),
    notify_evaluation_failed: bool = Form(False),
    notify_new_user: bool = Form(False),
    notify_daily_summary: bool = Form(False),
):
    """
    Save platform settings.

    Updates configuration for Ollama host, API keys, and email notifications.
    """
    global _settings

    _settings["ollama_host"] = ollama_host.rstrip("/")
    _settings["openai_api_key"] = openai_api_key
    _settings["anthropic_api_key"] = anthropic_api_key
    _settings["azure_openai_endpoint"] = azure_openai_endpoint
    _settings["azure_openai_key"] = azure_openai_key
    _settings["default_model"] = default_model
    _settings["judge_model"] = judge_model

    # Email settings
    _settings["email_enabled"] = email_enabled
    _settings["smtp_host"] = smtp_host
    _settings["smtp_port"] = smtp_port
    _settings["smtp_user"] = smtp_user
    _settings["smtp_password"] = smtp_password
    _settings["notification_email"] = notification_email
    _settings["notify_evaluation_complete"] = notify_evaluation_complete
    _settings["notify_evaluation_failed"] = notify_evaluation_failed
    _settings["notify_new_user"] = notify_new_user
    _settings["notify_daily_summary"] = notify_daily_summary

    # Update environment variables for other modules
    os.environ["OLLAMA_HOST"] = _settings["ollama_host"]
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    if anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

    # Email environment variables
    if smtp_host:
        os.environ["SMTP_HOST"] = smtp_host
        os.environ["SMTP_PORT"] = str(smtp_port)
        os.environ["SMTP_USER"] = smtp_user
        os.environ["SMTP_PASSWORD"] = smtp_password

    return RedirectResponse(url="/settings?saved=1", status_code=303)


@app.get("/settings/test-ollama", tags=["settings"], summary="Test Ollama connection")
async def test_ollama_connection(host: str = None):
    """
    Test connection to Ollama server.

    Args:
        host: Optional host URL to test. Uses saved settings if not provided.
    """
    import httpx

    test_host = host or _settings["ollama_host"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{test_host}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "status": "success",
                    "host": test_host,
                    "models": models,
                    "model_count": len(models),
                }
            else:
                return {
                    "status": "error",
                    "host": test_host,
                    "message": f"HTTP {resp.status_code}",
                }
    except httpx.TimeoutException:
        return {"status": "error", "host": test_host, "message": "Connection timeout"}
    except Exception as e:
        return {"status": "error", "host": test_host, "message": str(e)}


@app.post("/settings/test-email", tags=["settings"], summary="Test email configuration")
async def test_email_configuration(
    smtp_host: str = Form(""),
    smtp_port: int = Form(587),
    smtp_user: str = Form(""),
    smtp_password: str = Form(""),
    notification_email: str = Form(""),
):
    """
    Send a test email to verify SMTP configuration.
    """
    if not smtp_host or not smtp_user or not smtp_password:
        return {"status": "error", "message": "SMTP settings incomplete"}

    if not notification_email:
        return {"status": "error", "message": "No recipient email specified"}

    try:
        from notifications import EmailNotifier

        notifier = EmailNotifier(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
        )

        # Send test email to first recipient
        recipient = notification_email.split(",")[0].strip()

        result = notifier.send_email(
            to=recipient,
            subject="LinguaEval - Test Email",
            body_html="""
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #2563eb;">Test Email Successful!</h2>
                <p>Your email configuration is working correctly.</p>
                <p style="color: #6b7280; font-size: 12px;">
                    This is a test email from LinguaEval.
                </p>
            </div>
            """,
            body_text="Test Email Successful! Your email configuration is working correctly.",
        )

        if result:
            return {"status": "success", "message": f"Test email sent to {recipient}"}
        else:
            return {
                "status": "error",
                "message": "Failed to send email - check SMTP settings",
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/settings", tags=["settings"], summary="Get current settings")
async def get_settings():
    """
    Get current platform settings (API keys are masked).
    """
    return {
        "ollama_host": _settings["ollama_host"],
        "default_model": _settings["default_model"],
        "judge_model": _settings["judge_model"],
        "openai_configured": bool(_settings["openai_api_key"]),
        "anthropic_configured": bool(_settings["anthropic_api_key"]),
        "azure_configured": bool(
            _settings["azure_openai_endpoint"] and _settings["azure_openai_key"]
        ),
        "email_enabled": _settings.get("email_enabled", False),
        "email_configured": bool(
            _settings.get("smtp_host") and _settings.get("smtp_user")
        ),
    }


# ═══════════════════════════════════════════════════════════════
# BATCH EVALUATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

from batch_queue import batch_queue, BatchJob, JobStatus, process_batch_queue


@app.get("/batch", response_class=HTMLResponse, tags=["batch"])
async def batch_page(request: Request):
    """Batch evaluations management page."""
    import httpx

    # Get available models from Ollama
    models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_settings['ollama_host']}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
    except Exception:
        models = ["llama3.1:latest"]

    # Get available prompt packs
    prompts_dir = BASE_DIR.parent / "prompts"
    prompt_packs = (
        [f.stem for f in prompts_dir.glob("*.json")] if prompts_dir.exists() else []
    )

    return templates.TemplateResponse(
        "batch.html",
        {
            "request": request,
            "page_title": "Batch Evaluations",
            "jobs": batch_queue.get_all_jobs(),
            "status": batch_queue.get_queue_status(),
            "models": models,
            "prompt_packs": prompt_packs,
        },
    )


@app.post("/batch/add", tags=["batch"], summary="Add job to batch queue")
async def add_batch_job(
    request: Request,
    name: str = Form(...),
    model: str = Form(...),
    prompt_pack: str = Form(...),
    languages: List[str] = Form(...),
):
    """Add a new evaluation job to the batch queue."""
    job = batch_queue.add_job(
        name=name,
        config_id=str(uuid.uuid4())[:8],
        model=model,
        prompt_pack=prompt_pack,
        languages=languages,
    )
    return RedirectResponse(url="/batch", status_code=303)


@app.get("/batch/status", tags=["batch"], summary="Get batch queue status")
async def get_batch_status():
    """Get current batch queue status."""
    return {
        "status": batch_queue.get_queue_status(),
        "jobs": [j.to_dict() for j in batch_queue.get_all_jobs()[:10]],
    }


@app.post("/batch/start", tags=["batch"], summary="Start processing batch queue")
async def start_batch_processing(background_tasks: BackgroundTasks):
    """Start processing the batch queue in the background."""
    if batch_queue._running:
        return {"status": "already_running"}

    async def run_evaluation(model, prompt_pack, languages, progress_callback):
        """Run a single evaluation (simplified for demo)."""
        import asyncio

        # Simulate evaluation progress
        total = 20
        for i in range(total):
            await asyncio.sleep(0.5)  # Simulated work
            progress_callback(int((i + 1) / total * 100), i + 1, total)

        # In production, actually run the evaluation
        result_file = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_results.json"
        return result_file

    # Start processing in background
    background_tasks.add_task(process_batch_queue, run_evaluation)
    return {"status": "started"}


@app.post("/batch/{job_id}/cancel", tags=["batch"], summary="Cancel a batch job")
async def cancel_batch_job(job_id: str):
    """Cancel a queued batch job."""
    if batch_queue.cancel_job(job_id):
        return {"status": "cancelled"}
    raise HTTPException(status_code=400, detail="Cannot cancel job")


@app.delete("/batch/{job_id}", tags=["batch"], summary="Delete a batch job")
async def delete_batch_job(job_id: str):
    """Delete a batch job from the queue."""
    if batch_queue.delete_job(job_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=400, detail="Cannot delete job")


@app.post("/batch/clear", tags=["batch"], summary="Clear completed jobs")
async def clear_completed_jobs():
    """Clear all completed and failed jobs from the queue."""
    batch_queue.clear_completed()
    return {"status": "cleared"}


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION PRESETS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

PRESETS_FILE = DATA_DIR / "presets.json"


def load_presets() -> List[dict]:
    """Load saved presets from disk."""
    try:
        if PRESETS_FILE.exists():
            with open(PRESETS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_presets(presets: List[dict]):
    """Save presets to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)


@app.get("/presets", response_class=HTMLResponse, tags=["presets"])
async def presets_page(request: Request):
    """Configuration presets management page."""
    presets = load_presets()

    # Get current config
    current_config = {
        "model": _settings.get("default_model", "llama3.1:latest"),
        "judge_model": _settings.get("judge_model", "llama3.1:latest"),
        "ollama_host": _settings.get("ollama_host", "http://localhost:11434"),
        "languages": ["EN", "AR"],
        "prompt_packs": (
            list((BASE_DIR.parent / "prompts").glob("*.json"))
            if (BASE_DIR.parent / "prompts").exists()
            else []
        ),
    }

    return templates.TemplateResponse(
        "presets.html",
        {
            "request": request,
            "page_title": "Configuration Presets",
            "presets": presets,
            "current_config": current_config,
        },
    )


@app.post("/presets/save", tags=["presets"], summary="Save configuration preset")
async def save_preset(
    name: str = Form(...),
    description: str = Form(""),
    include_model: bool = Form(False),
    include_api_keys: bool = Form(False),
    include_email: bool = Form(False),
):
    """Save current configuration as a preset."""
    presets = load_presets()

    config = {}

    if include_model:
        config["model"] = _settings.get("default_model")
        config["judge_model"] = _settings.get("judge_model")
        config["ollama_host"] = _settings.get("ollama_host")

    if include_api_keys:
        config["openai_api_key"] = _settings.get("openai_api_key")
        config["anthropic_api_key"] = _settings.get("anthropic_api_key")
        config["azure_openai_endpoint"] = _settings.get("azure_openai_endpoint")
        config["azure_openai_key"] = _settings.get("azure_openai_key")

    if include_email:
        config["smtp_host"] = _settings.get("smtp_host")
        config["smtp_port"] = _settings.get("smtp_port")
        config["smtp_user"] = _settings.get("smtp_user")
        config["notification_email"] = _settings.get("notification_email")

    preset = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "description": description,
        "config": config,
        "created_at": datetime.now().isoformat(),
    }

    presets.append(preset)
    save_presets(presets)

    return RedirectResponse(url="/presets", status_code=303)


@app.get("/presets/{preset_id}/load", tags=["presets"], summary="Load a preset")
async def load_preset(preset_id: str):
    """Load a saved preset into current settings."""
    global _settings

    presets = load_presets()
    preset = next((p for p in presets if p["id"] == preset_id), None)

    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    config = preset.get("config", {})

    for key, value in config.items():
        if key in _settings and value is not None:
            _settings[key] = value

    return RedirectResponse(url="/settings?saved=1", status_code=303)


@app.get(
    "/presets/{preset_id}/export", tags=["presets"], summary="Export preset as file"
)
async def export_preset(preset_id: str):
    """Export a preset as a downloadable JSON file."""
    presets = load_presets()
    preset = next((p for p in presets if p["id"] == preset_id), None)

    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    return JSONResponse(
        content=preset,
        headers={
            "Content-Disposition": f'attachment; filename="preset_{preset["name"].replace(" ", "_")}.json"'
        },
    )


@app.delete("/presets/{preset_id}", tags=["presets"], summary="Delete a preset")
async def delete_preset(preset_id: str):
    """Delete a saved preset."""
    presets = load_presets()
    presets = [p for p in presets if p["id"] != preset_id]
    save_presets(presets)
    return {"status": "deleted"}


@app.post("/presets/import", tags=["presets"], summary="Import preset from file")
async def import_preset(file: UploadFile = File(...)):
    """Import a preset from uploaded file."""
    try:
        content = await file.read()
        data = json.loads(content.decode())

        # Validate structure
        if "name" not in data:
            data["name"] = file.filename.replace(".json", "")
        if "config" not in data:
            data["config"] = data  # Assume whole file is config

        data["id"] = str(uuid.uuid4())[:8]
        data["created_at"] = datetime.now().isoformat()

        presets = load_presets()
        presets.append(data)
        save_presets(presets)

        return RedirectResponse(url="/presets", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid preset file: {str(e)}")


@app.get("/presets/export-current", tags=["presets"], summary="Export current config")
async def export_current_config():
    """Export current configuration as a JSON file."""
    export_config = {
        "name": "Current Configuration",
        "config": {
            "model": _settings.get("default_model"),
            "judge_model": _settings.get("judge_model"),
            "ollama_host": _settings.get("ollama_host"),
        },
        "exported_at": datetime.now().isoformat(),
    }

    return JSONResponse(
        content=export_config,
        headers={
            "Content-Disposition": 'attachment; filename="linguaeval_config.json"'
        },
    )


@app.get("/presets/export-all", tags=["presets"], summary="Export all presets")
async def export_all_presets():
    """Export all presets as a JSON file."""
    presets = load_presets()
    return JSONResponse(
        content={"presets": presets, "exported_at": datetime.now().isoformat()},
        headers={
            "Content-Disposition": 'attachment; filename="linguaeval_all_presets.json"'
        },
    )


@app.post("/presets/reset", tags=["presets"], summary="Reset to defaults")
async def reset_to_defaults():
    """Reset all settings to default values."""
    global _settings

    _settings.update(
        {
            "ollama_host": "http://localhost:11434",
            "default_model": "llama3.1:latest",
            "judge_model": "llama3.1:latest",
            "openai_api_key": "",
            "anthropic_api_key": "",
            "azure_openai_endpoint": "",
            "azure_openai_key": "",
        }
    )

    return {"status": "reset"}


# ═══════════════════════════════════════════════════════════════
# PROMPT EDITOR ENDPOINTS
# ═══════════════════════════════════════════════════════════════

PROMPTS_DIR = BASE_DIR.parent / "prompts"


def get_prompt_packs():
    """Get list of available prompt packs."""
    packs = []
    if PROMPTS_DIR.exists():
        for f in PROMPTS_DIR.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    packs.append(
                        {
                            "name": f.stem,
                            "file": f.name,
                            "prompt_count": len(data.get("prompts", [])),
                            "domain": data.get("domain", "General"),
                        }
                    )
            except Exception:
                packs.append({"name": f.stem, "file": f.name, "prompt_count": 0})
    return packs


@app.get("/prompts/editor", response_class=HTMLResponse, tags=["prompts"])
async def prompt_editor_page(request: Request, pack: str = None):
    """Prompt editor page."""
    packs = get_prompt_packs()
    prompts = []

    if pack:
        pack_file = PROMPTS_DIR / f"{pack}.json"
        if pack_file.exists():
            with open(pack_file) as f:
                data = json.load(f)
                prompts = data.get("prompts", [])

    return templates.TemplateResponse(
        "prompt_editor.html",
        {
            "request": request,
            "page_title": "Prompt Editor",
            "packs": packs,
            "selected_pack": pack,
            "prompts": prompts,
        },
    )


@app.post("/prompts/create-pack", tags=["prompts"], summary="Create new prompt pack")
async def create_prompt_pack(
    name: str = Form(...),
    description: str = Form(""),
    domain: str = Form(""),
):
    """Create a new empty prompt pack."""
    # Sanitize name
    name = name.lower().replace(" ", "_")

    pack_file = PROMPTS_DIR / f"{name}.json"
    if pack_file.exists():
        raise HTTPException(status_code=400, detail="Pack already exists")

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    pack_data = {
        "name": name,
        "description": description,
        "domain": domain,
        "version": "1.0",
        "prompts": [],
    }

    with open(pack_file, "w") as f:
        json.dump(pack_data, f, indent=2, ensure_ascii=False)

    return RedirectResponse(url=f"/prompts/editor?pack={name}", status_code=303)


@app.post("/prompts/save/{pack_name}", tags=["prompts"], summary="Save prompts")
async def save_prompts(pack_name: str, request: Request):
    """Save prompts to a pack."""
    data = await request.json()
    prompts = data.get("prompts", [])

    pack_file = PROMPTS_DIR / f"{pack_name}.json"

    # Load existing pack data or create new
    if pack_file.exists():
        with open(pack_file) as f:
            pack_data = json.load(f)
    else:
        pack_data = {"name": pack_name, "version": "1.0"}

    pack_data["prompts"] = prompts

    with open(pack_file, "w") as f:
        json.dump(pack_data, f, indent=2, ensure_ascii=False)

    return {"status": "saved", "count": len(prompts)}


@app.delete("/prompts/{pack_name}", tags=["prompts"], summary="Delete prompt pack")
async def delete_prompt_pack(pack_name: str):
    """Delete a prompt pack."""
    pack_file = PROMPTS_DIR / f"{pack_name}.json"

    if not pack_file.exists():
        raise HTTPException(status_code=404, detail="Pack not found")

    pack_file.unlink()
    return {"status": "deleted"}


@app.get("/prompts/{pack_name}/export", tags=["prompts"], summary="Export prompt pack")
async def export_prompt_pack(pack_name: str):
    """Export a prompt pack as JSON file."""
    pack_file = PROMPTS_DIR / f"{pack_name}.json"

    if not pack_file.exists():
        raise HTTPException(status_code=404, detail="Pack not found")

    return FileResponse(
        pack_file,
        media_type="application/json",
        filename=f"{pack_name}_prompts.json",
    )


# ═══════════════════════════════════════════════════════════════
# FINE-TUNING ENDPOINTS
# ═══════════════════════════════════════════════════════════════

FINETUNE_DIR = DATA_DIR / "finetune"
DATASETS_DIR = FINETUNE_DIR / "datasets"
FINETUNE_JOBS_FILE = FINETUNE_DIR / "jobs.json"


def load_finetune_jobs() -> List[dict]:
    """Load fine-tuning jobs from disk."""
    try:
        if FINETUNE_JOBS_FILE.exists():
            with open(FINETUNE_JOBS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_finetune_jobs(jobs: List[dict]):
    """Save fine-tuning jobs to disk."""
    FINETUNE_DIR.mkdir(parents=True, exist_ok=True)
    with open(FINETUNE_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def get_datasets():
    """Get available training datasets."""
    datasets = []
    if DATASETS_DIR.exists():
        for f in DATASETS_DIR.glob("*.jsonl"):
            try:
                with open(f) as fp:
                    lines = fp.readlines()
                    datasets.append(
                        {
                            "name": f.stem,
                            "file": f.name,
                            "samples": len(lines),
                            "format": "jsonl",
                            "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
                        }
                    )
            except Exception:
                pass
    return datasets


@app.get("/finetune", response_class=HTMLResponse, tags=["finetune"])
async def finetune_page(request: Request):
    """Fine-tuning management page."""
    import httpx

    # Get available Ollama models
    available_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_settings['ollama_host']}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                available_models = [m["name"] for m in data.get("models", [])]
    except Exception:
        available_models = ["llama3.1:latest"]

    jobs = load_finetune_jobs()
    datasets = get_datasets()

    # Get fine-tuned models (those ending with -ft or custom suffix)
    fine_tuned_models = [
        m for m in available_models if "-ft" in m or "fine" in m.lower()
    ]

    return templates.TemplateResponse(
        "finetune.html",
        {
            "request": request,
            "page_title": "Fine-tuning",
            "jobs": jobs,
            "datasets": datasets,
            "available_models": available_models,
            "fine_tuned_models": fine_tuned_models,
        },
    )


@app.post("/finetune/create", tags=["finetune"], summary="Create fine-tuning job")
async def create_finetune_job(
    base_model: str = Form(...),
    dataset: str = Form(...),
    output_name: str = Form(""),
    epochs: int = Form(3),
    learning_rate: float = Form(0.0001),
    batch_size: int = Form(4),
    max_seq_len: int = Form(2048),
    use_lora: bool = Form(True),
):
    """Create a new fine-tuning job."""
    jobs = load_finetune_jobs()

    job_id = str(uuid.uuid4())[:8]
    output_model = output_name or f"{base_model.split(':')[0]}-ft-{job_id}"

    job = {
        "id": job_id,
        "base_model": base_model,
        "dataset": dataset,
        "output_model": output_model,
        "status": "queued",
        "progress": 0,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "max_seq_len": max_seq_len,
        "use_lora": use_lora,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
    }

    jobs.append(job)
    save_finetune_jobs(jobs)

    # In production, this would start an actual fine-tuning process
    # For demo, we simulate the job

    return RedirectResponse(url="/finetune", status_code=303)


@app.post(
    "/finetune/{job_id}/cancel", tags=["finetune"], summary="Cancel fine-tuning job"
)
async def cancel_finetune_job(job_id: str):
    """Cancel a fine-tuning job."""
    jobs = load_finetune_jobs()

    for job in jobs:
        if job["id"] == job_id and job["status"] in ["queued", "running"]:
            job["status"] = "cancelled"
            save_finetune_jobs(jobs)
            return {"status": "cancelled"}

    raise HTTPException(status_code=400, detail="Cannot cancel job")


@app.delete("/finetune/{job_id}", tags=["finetune"], summary="Delete fine-tuning job")
async def delete_finetune_job(job_id: str):
    """Delete a fine-tuning job."""
    jobs = load_finetune_jobs()
    jobs = [j for j in jobs if j["id"] != job_id]
    save_finetune_jobs(jobs)
    return {"status": "deleted"}


@app.post(
    "/finetune/{job_id}/deploy", tags=["finetune"], summary="Deploy fine-tuned model"
)
async def deploy_finetune_model(job_id: str):
    """Deploy a fine-tuned model for use."""
    jobs = load_finetune_jobs()

    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job or job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")

    # In production, this would register the model with Ollama
    # For demo, we return success

    return {
        "status": "deployed",
        "message": f"Model {job['output_model']} is now available",
    }


@app.post(
    "/finetune/upload-dataset", tags=["finetune"], summary="Upload training dataset"
)
async def upload_dataset(
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
):
    """Upload a training dataset."""
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    # Validate and save
    content = await file.read()

    # Check if valid JSONL
    try:
        lines = content.decode().strip().split("\n")
        for line in lines[:5]:  # Validate first 5 lines
            json.loads(line)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSONL format: {str(e)}")

    # Save file
    dataset_path = DATASETS_DIR / f"{name}.jsonl"
    with open(dataset_path, "wb") as f:
        f.write(content)

    return RedirectResponse(url="/finetune", status_code=303)


@app.delete("/finetune/dataset/{name}", tags=["finetune"], summary="Delete dataset")
async def delete_dataset(name: str):
    """Delete a training dataset."""
    dataset_path = DATASETS_DIR / f"{name}.jsonl"

    if dataset_path.exists():
        dataset_path.unlink()
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Dataset not found")


@app.get(
    "/finetune/dataset/{name}/preview", response_class=HTMLResponse, tags=["finetune"]
)
async def preview_dataset(request: Request, name: str):
    """Preview a training dataset."""
    dataset_path = DATASETS_DIR / f"{name}.jsonl"

    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")

    samples = []
    with open(dataset_path) as f:
        for i, line in enumerate(f):
            if i >= 10:  # Show first 10 samples
                break
            samples.append(json.loads(line))

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dataset Preview: {name}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container py-4">
            <h2>Dataset: {name}</h2>
            <p class="text-muted">Showing first 10 samples</p>
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Content</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for i, sample in enumerate(samples, 1):
        html += f"<tr><td>{i}</td><td><pre class='mb-0'>{json.dumps(sample, indent=2, ensure_ascii=False)[:500]}</pre></td></tr>"

    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html)


# ═══════════════════════════════════════════════════════════════
# IN-MEMORY DATA STORE (for demo purposes)
# ═══════════════════════════════════════════════════════════════


# In production, use a proper database
class AppState:
    projects: dict = {}
    evaluations: dict = {}
    current_user: str = "demo_user"


state = AppState()


def get_recent_projects():
    """Get recent projects from results directory."""
    results_dir = BASE_DIR.parent / "results"
    projects = []

    if results_dir.exists():
        for f in sorted(results_dir.glob("*_results.json"), reverse=True)[:5]:
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    projects.append(
                        {
                            "id": f.stem,
                            "name": data.get("metadata", {}).get(
                                "client_name", "Unknown"
                            ),
                            "models": len(data.get("metadata", {}).get("models", [])),
                            "status": "Completed",
                            "date": data.get("metadata", {}).get("timestamp", "")[:10],
                        }
                    )
            except:
                pass

    return projects


def get_summary_stats():
    """Calculate summary statistics."""
    results_dir = BASE_DIR.parent / "results"
    total_evals = (
        len(list(results_dir.glob("*_results.json"))) if results_dir.exists() else 0
    )

    # Count high-risk findings from latest results
    high_risk = 0
    latest_score = None

    if results_dir.exists():
        results_files = sorted(results_dir.glob("*_results.json"), reverse=True)
        if results_files:
            try:
                with open(results_files[0]) as f:
                    data = json.load(f)
                    # Count critical gaps
                    for model_data in data.get("aggregates", {}).values():
                        for dim, gap_data in model_data.get(
                            "cross_lingual_gap", {}
                        ).items():
                            if gap_data.get("severity") in ["high", "critical"]:
                                high_risk += 1

                    # Calculate overall score
                    scores = []
                    for model_data in data.get("aggregates", {}).values():
                        for lang in ["en", "ar"]:
                            for dim_data in model_data.get(lang, {}).values():
                                if "average" in dim_data:
                                    scores.append(dim_data["average"])
                    if scores:
                        latest_score = sum(scores) / len(scores)
            except:
                pass

    return {
        "total_evaluations": total_evals,
        "models_compared": total_evals * 2,  # Approximate
        "high_risk_findings": high_risk,
        "latest_score": round(latest_score, 1) if latest_score else None,
    }


# ═══════════════════════════════════════════════════════════════
# MAIN ROUTES
# ═══════════════════════════════════════════════════════════════


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing / Workspace Home (Screen 1)"""
    projects = get_recent_projects()
    stats = get_summary_stats()

    template = templates.get_template("home.html")
    context = {
        "request": request,
        "page_title": "LinguaEval Dashboard",
        "projects": projects,
        "stats": stats,
        "templates": [
            {
                "name": "Government Service Delivery",
                "sector": "government",
                "icon": "🏛️",
            },
            {
                "name": "University Administration",
                "sector": "university",
                "icon": "🎓",
            },
            {"name": "Customer Support", "sector": "support", "icon": "💬"},
            {"name": "Policy & Legal", "sector": "legal", "icon": "⚖️"},
        ],
    }
    return template.render(context)


@app.get("/services", response_class=HTMLResponse)
async def services(request: Request):
    """Dalīl Group Services Overview"""
    context = {
        "request": request,
        "page_title": "Our Services",
    }
    return render_template("services.html", context)


@app.get("/sectors/government", response_class=HTMLResponse)
async def sector_government(request: Request):
    """Government & Public Sector Page"""
    context = {
        "request": request,
        "page_title": "Government & Public Sector",
    }
    return render_template("sector_government.html", context)


@app.get("/sectors/university", response_class=HTMLResponse)
async def sector_university(request: Request):
    """Higher Education Sector Page"""
    context = {
        "request": request,
        "page_title": "Higher Education",
    }
    return render_template("sector_university.html", context)


@app.get("/sectors/healthcare", response_class=HTMLResponse)
async def sector_healthcare(request: Request):
    """Healthcare & Life Sciences Sector Page"""
    context = {
        "request": request,
        "page_title": "Healthcare & Life Sciences",
    }
    return render_template("sector_healthcare.html", context)


@app.get("/sectors/finance", response_class=HTMLResponse)
async def sector_finance(request: Request):
    """Financial Services Sector Page"""
    context = {
        "request": request,
        "page_title": "Financial Services",
    }
    return render_template("sector_finance.html", context)


@app.get("/sectors/legal", response_class=HTMLResponse)
async def sector_legal(request: Request):
    """Legal & Regulatory Sector Page"""
    context = {
        "request": request,
        "page_title": "Legal & Regulatory Services",
    }
    return render_template("sector_legal.html", context)


@app.get("/sectors", response_class=HTMLResponse)
async def sectors(request: Request):
    """All Sectors Overview"""
    sectors_list = [
        {
            "name": "Government & Public Sector",
            "icon": "🏛️",
            "url": "/sectors/government",
            "description": "Trustworthy AI for citizen services",
        },
        {
            "name": "Higher Education",
            "icon": "🎓",
            "url": "/sectors/university",
            "description": "Fair AI for student services and research",
        },
        {
            "name": "Healthcare & Life Sciences",
            "icon": "⚕️",
            "url": "/sectors/healthcare",
            "description": "Safe, culturally competent medical AI",
        },
        {
            "name": "Financial Services",
            "icon": "💰",
            "url": "/sectors/finance",
            "description": "Fair, compliant AI for banking and fintech",
        },
        {
            "name": "Legal & Regulatory",
            "icon": "⚖️",
            "url": "/sectors/legal",
            "description": "Accurate AI for legal research and compliance",
        },
    ]
    context = {
        "request": request,
        "page_title": "Industries We Serve",
        "sectors": sectors_list,
    }
    return render_template("sectors.html", context)


@app.get("/dashboard/{project_id}", response_class=HTMLResponse)
async def dashboard(request: Request, project_id: str):
    """Overview Dashboard (Screen 4)"""
    results_path = BASE_DIR.parent / "results" / f"{project_id}.json"

    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    with open(results_path) as f:
        data = json.load(f)

    # Calculate overall scores
    overall = {}
    for model_id, model_data in data.get("aggregates", {}).items():
        en_scores = [v["average"] for v in model_data.get("en", {}).values()]
        ar_scores = [v["average"] for v in model_data.get("ar", {}).values()]
        gaps = [v["gap"] for v in model_data.get("cross_lingual_gap", {}).values()]

        en_avg = sum(en_scores) / len(en_scores) if en_scores else 0
        ar_avg = sum(ar_scores) / len(ar_scores) if ar_scores else 0
        combined = (en_avg + ar_avg) / 2
        avg_gap = sum(gaps) / len(gaps) if gaps else 0

        # Determine status
        if combined >= 80 and avg_gap < 10:
            status = "Ready for Pilot"
            status_class = "success"
        elif combined >= 65:
            status = "Restricted Pilot Only"
            status_class = "warning"
        else:
            status = "Not Ready"
            status_class = "danger"

        overall[model_id] = {
            "en_avg": round(en_avg, 1),
            "ar_avg": round(ar_avg, 1),
            "combined": round(combined, 1),
            "gap": round(avg_gap, 1),
            "status": status,
            "status_class": status_class,
        }

    # Find recommended model
    recommended = None
    best_score = 0
    for mid, scores in overall.items():
        score = scores["combined"] - scores["gap"]
        if score > best_score:
            best_score = score
            recommended = mid

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "page_title": f"Dashboard - {data['metadata']['client_name']}",
            "project_id": project_id,
            "metadata": data["metadata"],
            "overall": overall,
            "recommended": recommended,
            "aggregates": data.get("aggregates", {}),
        },
    )


@app.get("/comparison/{project_id}", response_class=HTMLResponse)
async def model_comparison(request: Request, project_id: str):
    """Model Comparison Screen (Screen 5)"""
    results_path = BASE_DIR.parent / "results" / f"{project_id}.json"

    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    with open(results_path) as f:
        data = json.load(f)

    # Get all dimensions
    all_dims = set()
    for model_data in data.get("aggregates", {}).values():
        all_dims.update(model_data.get("en", {}).keys())
        all_dims.update(model_data.get("ar", {}).keys())

    return templates.TemplateResponse(
        "comparison.html",
        {
            "request": request,
            "page_title": f"Model Comparison - {data['metadata']['client_name']}",
            "project_id": project_id,
            "metadata": data["metadata"],
            "aggregates": data.get("aggregates", {}),
            "dimensions": sorted(all_dims),
        },
    )


@app.get("/consistency/{project_id}", response_class=HTMLResponse)
async def consistency(request: Request, project_id: str):
    """Cross-Lingual Consistency Screen (Screen 6)"""
    results_path = BASE_DIR.parent / "results" / f"{project_id}.json"

    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    with open(results_path) as f:
        data = json.load(f)

    # Extract gap data
    gap_analysis = {}
    for model_id, model_data in data.get("aggregates", {}).items():
        gap_analysis[model_id] = model_data.get("cross_lingual_gap", {})

    return templates.TemplateResponse(
        "consistency.html",
        {
            "request": request,
            "page_title": f"Cross-Lingual Consistency - {data['metadata']['client_name']}",
            "project_id": project_id,
            "metadata": data["metadata"],
            "gap_analysis": gap_analysis,
            "detailed": data.get("detailed_results", [])[:10],  # First 10 for demo
        },
    )


@app.get("/bias/{project_id}", response_class=HTMLResponse)
async def bias_fairness(request: Request, project_id: str):
    """Bias & Fairness Screen (Screen 7)"""
    results_path = BASE_DIR.parent / "results" / f"{project_id}.json"

    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    with open(results_path) as f:
        data = json.load(f)

    # Extract bias flags
    bias_flags = {"en": [], "ar": []}
    for result in data.get("detailed_results", []):
        for model_id, model_scores in result.get("model_scores", {}).items():
            for lang in ["en", "ar"]:
                for score in model_scores.get(lang, {}).get("scores", []):
                    if score.get("dimension") == "bias" and score.get("flags"):
                        for flag in score["flags"]:
                            bias_flags[lang].append(
                                {
                                    "model": model_id,
                                    "prompt_id": result.get("prompt_id"),
                                    "flag": flag,
                                    "severity": score.get("severity", "medium"),
                                }
                            )

    return templates.TemplateResponse(
        "bias.html",
        {
            "request": request,
            "page_title": f"Bias & Fairness - {data['metadata']['client_name']}",
            "project_id": project_id,
            "metadata": data["metadata"],
            "bias_flags": bias_flags,
            "aggregates": data.get("aggregates", {}),
        },
    )


@app.get("/reliability/{project_id}", response_class=HTMLResponse)
async def reliability(request: Request, project_id: str):
    """Reliability Screen (Screen 8)"""
    results_path = BASE_DIR.parent / "results" / f"{project_id}.json"

    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    with open(results_path) as f:
        data = json.load(f)

    # Extract hallucination and accuracy data
    reliability_data = {}
    for model_id, model_data in data.get("aggregates", {}).items():
        reliability_data[model_id] = {
            "accuracy_en": model_data.get("en", {}).get("accuracy", {}).get("average"),
            "accuracy_ar": model_data.get("ar", {}).get("accuracy", {}).get("average"),
            "hallucination_en": model_data.get("en", {})
            .get("hallucination", {})
            .get("average"),
            "hallucination_ar": model_data.get("ar", {})
            .get("hallucination", {})
            .get("average"),
            "fluency_en": model_data.get("en", {}).get("fluency", {}).get("average"),
            "fluency_ar": model_data.get("ar", {}).get("fluency", {}).get("average"),
        }

    return templates.TemplateResponse(
        "reliability.html",
        {
            "request": request,
            "page_title": f"Reliability - {data['metadata']['client_name']}",
            "project_id": project_id,
            "metadata": data["metadata"],
            "reliability_data": reliability_data,
        },
    )


@app.get("/recommendation/{project_id}", response_class=HTMLResponse)
async def recommendation(request: Request, project_id: str):
    """Deployment Recommendation Screen (Screen 9)"""
    results_path = BASE_DIR.parent / "results" / f"{project_id}.json"

    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    with open(results_path) as f:
        data = json.load(f)

    # Generate recommendations
    recommendations = {}
    for model_id, model_data in data.get("aggregates", {}).items():
        en_scores = [v["average"] for v in model_data.get("en", {}).values()]
        ar_scores = [v["average"] for v in model_data.get("ar", {}).values()]
        gaps = [v["gap"] for v in model_data.get("cross_lingual_gap", {}).values()]

        en_avg = sum(en_scores) / len(en_scores) if en_scores else 0
        ar_avg = sum(ar_scores) / len(ar_scores) if ar_scores else 0
        combined = (en_avg + ar_avg) / 2
        avg_gap = sum(gaps) / len(gaps) if gaps else 0

        # Critical gaps
        critical = [
            (dim, gd["gap"])
            for dim, gd in model_data.get("cross_lingual_gap", {}).items()
            if gd.get("severity") in ["high", "critical"]
        ]

        if combined >= 80 and avg_gap < 10 and not critical:
            status = "Ready for Pilot"
            controls = [
                "Standard human review sampling (10-15%)",
                "Monthly performance monitoring",
                "Quarterly re-evaluation",
            ]
        elif combined >= 65:
            status = "Restricted Pilot Only"
            controls = [
                "Enhanced human review for Arabic outputs",
                "Restricted scope deployment",
                "Weekly monitoring during pilot",
                "Re-evaluation after 4 weeks",
            ]
        else:
            status = "Not Ready"
            controls = [
                "Consider alternative models",
                "Fine-tuning or prompt engineering required",
                "Re-evaluate after improvements",
            ]

        recommendations[model_id] = {
            "status": status,
            "score": round(combined, 1),
            "gap": round(avg_gap, 1),
            "critical_gaps": critical,
            "controls": controls,
        }

    return templates.TemplateResponse(
        "recommendation.html",
        {
            "request": request,
            "page_title": f"Deployment Recommendation - {data['metadata']['client_name']}",
            "project_id": project_id,
            "metadata": data["metadata"],
            "recommendations": recommendations,
        },
    )


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
