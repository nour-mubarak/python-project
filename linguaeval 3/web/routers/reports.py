#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reports Router
==============

API routes for report generation and management.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent


def get_templates():
    from fastapi.templating import Jinja2Templates

    return Jinja2Templates(directory=BASE_DIR / "templates")


# In-memory storage for report generation status
report_jobs = {}


@router.get("/", response_class=HTMLResponse)
async def reports_list(request: Request):
    """Reports Screen (Screen 10)"""
    templates = get_templates()

    # Find all generated reports
    results_dir = BASE_DIR.parent / "results"
    reports = []

    if results_dir.exists():
        # Find DOCX reports
        for f in sorted(results_dir.glob("*.docx"), reverse=True):
            reports.append(
                {
                    "name": f.stem,
                    "format": "docx",
                    "path": str(f),
                    "size": f.stat().st_size // 1024,
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )

        # Find PDF reports
        for f in sorted(results_dir.glob("*.pdf"), reverse=True):
            reports.append(
                {
                    "name": f.stem,
                    "format": "pdf",
                    "path": str(f),
                    "size": f.stat().st_size // 1024,
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )

        # Find PPTX reports
        for f in sorted(results_dir.glob("*.pptx"), reverse=True):
            reports.append(
                {
                    "name": f.stem,
                    "format": "pptx",
                    "path": str(f),
                    "size": f.stat().st_size // 1024,
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )

    # Sort by date descending
    reports.sort(key=lambda x: x["date"], reverse=True)

    # Get available results for generation
    available_results = []
    if results_dir.exists():
        for f in sorted(results_dir.glob("*_results.json"), reverse=True):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    available_results.append(
                        {
                            "id": f.stem,
                            "name": data.get("metadata", {}).get(
                                "client_name", "Unknown"
                            ),
                            "timestamp": data.get("metadata", {}).get("timestamp", "")[
                                :10
                            ],
                        }
                    )
            except:
                pass

    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "page_title": "Reports",
            "reports": reports,
            "available_results": available_results,
        },
    )


@router.post("/generate")
async def generate_report(
    request: Request,
    background_tasks: BackgroundTasks,
    results_id: str = Form(...),
    format: str = Form("all"),
):
    """Generate report from results"""
    results_path = BASE_DIR.parent / "results" / f"{results_id}.json"

    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Results not found")

    # Run report generation
    cmd = [
        "python",
        str(BASE_DIR.parent / "generate_report.py"),
        str(results_path),
        "--format",
        format,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(BASE_DIR.parent),
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500, detail=f"Report generation failed: {result.stderr}"
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Report generation timed out")

    return RedirectResponse(url="/reports/", status_code=303)


@router.get("/download/{filename}")
async def download_report(filename: str):
    """Download a report file"""
    results_dir = BASE_DIR.parent / "results"

    # Security check - only allow files in results dir
    file_path = results_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    if not file_path.is_relative_to(results_dir):
        raise HTTPException(status_code=403, detail="Access denied")

    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".json": "application/json",
    }

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_types.get(suffix, "application/octet-stream"),
    )
