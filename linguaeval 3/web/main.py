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
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.routers import evaluations, reports, knowledge_agent

# ═══════════════════════════════════════════════════════════════
# APP CONFIGURATION
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="LinguaEval",
    description="Multilingual AI Evaluation & Deployment Studio",
    version="1.0.0",
)

# Static files and templates
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Include routers
app.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(knowledge_agent.router, prefix="/agent", tags=["knowledge_agent"])


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

    return templates.TemplateResponse(
        "home.html",
        {
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
        },
    )


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
