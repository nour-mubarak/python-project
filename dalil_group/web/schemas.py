#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Schema Documentation
========================

Comprehensive Pydantic schemas for API request/response documentation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
# HEALTH & STATUS SCHEMAS
# ═══════════════════════════════════════════════════════════════


class ServiceStatus(BaseModel):
    """Health status of a service."""
    
    status: str = Field(..., description="Service status: healthy, unhealthy, unreachable")
    models: Optional[List[str]] = Field(None, description="Available models")


class OllamaServiceStatus(BaseModel):
    """Ollama service status."""
    
    status: str = Field(..., description="Connection status")
    host: str = Field(..., description="Ollama host URL")
    models: List[str] = Field([], description="Available models")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field("healthy", description="Overall platform status")
    version: str = Field("1.0.0", description="API version")
    timestamp: datetime = Field(..., description="Response timestamp")
    services: Dict[str, Dict[str, Any]] = Field(..., description="Service status details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2026-04-15T10:30:00",
                "services": {
                    "ollama": {
                        "status": "healthy",
                        "host": "http://localhost:11434",
                        "models": ["llama3.1:latest", "gemma3:27b"]
                    },
                    "openai": {"configured": True},
                    "anthropic": {"configured": False}
                }
            }
        }


# ═══════════════════════════════════════════════════════════════
# BATCH JOB SCHEMAS
# ═══════════════════════════════════════════════════════════════


class BatchJobConfig(BaseModel):
    """Batch job configuration."""
    
    models: List[str] = Field(..., description="Model IDs to evaluate")
    languages: List[str] = Field(default=["en", "ar"], description="Languages to test")
    dimensions: List[str] = Field(
        default=["accuracy", "bias", "hallucination", "consistency", "cultural", "fluency"],
        description="Evaluation dimensions"
    )
    prompt_pack: str = Field(..., description="Prompt pack name (government, university, etc.)")
    total_items: int = Field(0, description="Total prompts to evaluate")


class BatchJobRequest(BaseModel):
    """Create batch job request."""
    
    name: str = Field(..., description="Job name", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Job description")
    config: BatchJobConfig = Field(..., description="Job configuration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Government Sector Assessment - Phase 1",
                "description": "Evaluation of GPT-4 vs Claude on government prompts",
                "config": {
                    "models": ["gpt-4o-mini", "claude-haiku-4-5-20251001"],
                    "languages": ["en", "ar"],
                    "dimensions": ["accuracy", "bias", "hallucination"],
                    "prompt_pack": "government",
                    "total_items": 36
                }
            }
        }


class BatchJobResponse(BaseModel):
    """Batch job response."""
    
    id: str = Field(..., description="Job ID (UUID)")
    name: str = Field(..., description="Job name")
    status: str = Field(..., description="Job status: queued, running, completed, failed, cancelled")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    completed_items: int = Field(0, description="Completed items")
    failed_items: int = Field(0, description="Failed items")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Government Sector Assessment - Phase 1",
                "status": "running",
                "progress": 65,
                "completed_items": 23,
                "failed_items": 1,
                "created_at": "2026-04-15T09:30:00",
                "started_at": "2026-04-15T09:31:00",
                "completed_at": None,
                "error": None
            }
        }


# ═══════════════════════════════════════════════════════════════
# EVALUATION SCHEMAS
# ═══════════════════════════════════════════════════════════════


class EvaluationCreateRequest(BaseModel):
    """Create evaluation request."""
    
    client_name: str = Field(..., description="Client name")
    sector: str = Field(..., description="Sector: government, university, healthcare, legal, finance")
    prompt_pack: str = Field(..., description="Prompt pack to use")
    models: List[str] = Field(..., description="Models to evaluate")
    languages: List[str] = Field(default=["en", "ar"], description="Languages")
    dimensions: List[str] = Field(
        default=["accuracy", "bias", "hallucination", "consistency", "cultural", "fluency"],
        description="Scoring dimensions"
    )


class DimensionScore(BaseModel):
    """Score for a single dimension."""
    
    dimension: str = Field(..., description="Dimension name")
    score: float = Field(..., ge=0, le=100, description="Score 0-100")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    flags: List[str] = Field(default=[], description="Issue flags")
    details: str = Field(default="", description="Detailed explanation")


class PromptEvaluationResult(BaseModel):
    """Evaluation result for a single prompt."""
    
    prompt_id: str = Field(..., description="Prompt ID")
    category: str = Field(..., description="Prompt category")
    model_scores: Dict[str, List[DimensionScore]] = Field(
        ..., description="Scores by model ID"
    )
    cross_lingual_gap: Dict[str, float] = Field(
        default={}, description="Cross-lingual consistency gap by model"
    )
    overall_score: float = Field(..., ge=0, le=100, description="Aggregate score")


class EvaluationResponse(BaseModel):
    """Evaluation response."""
    
    project_id: str = Field(..., description="Project ID")
    client_name: str = Field(..., description="Client name")
    sector: str = Field(..., description="Sector")
    status: str = Field(..., description="Status: pending, running, completed, failed")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    overall_score: Optional[float] = Field(None, description="Overall evaluation score")
    created_at: datetime = Field(..., description="Creation time")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")


# ═══════════════════════════════════════════════════════════════
# CONFIG PRESET SCHEMAS
# ═══════════════════════════════════════════════════════════════


class ConfigPresetCreate(BaseModel):
    """Create config preset request."""
    
    name: str = Field(..., description="Preset name", min_length=1, max_length=200)
    sector: str = Field(..., description="Sector")
    models: List[str] = Field(..., description="Model IDs")
    languages: List[str] = Field(..., description="Languages")
    dimensions: List[str] = Field(..., description="Evaluation dimensions")
    prompt_pack: str = Field(..., description="Prompt pack")
    description: Optional[str] = Field(None, description="Preset description")
    is_public: bool = Field(False, description="Make preset public")


class ConfigPresetResponse(BaseModel):
    """Config preset response."""
    
    id: int = Field(..., description="Preset ID")
    name: str = Field(..., description="Preset name")
    sector: str = Field(..., description="Sector")
    description: Optional[str] = Field(None, description="Description")
    models: List[str] = Field(..., description="Models")
    languages: List[str] = Field(..., description="Languages")
    is_public: bool = Field(..., description="Is public")
    created_at: datetime = Field(..., description="Creation time")


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATION SCHEMAS
# ═══════════════════════════════════════════════════════════════


class RecommendationResponse(BaseModel):
    """AI recommendation from evaluation."""
    
    id: int = Field(..., description="Recommendation ID")
    recommendation_type: str = Field(..., description="Type: accuracy, bias, hallucination, cultural, etc.")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    action_items: List[str] = Field(..., description="Actionable items")
    estimated_effort: str = Field(..., description="Effort: low, medium, high")
    related_prompts: List[str] = Field(..., description="Related prompt IDs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "recommendation_type": "bias",
                "severity": "high",
                "title": "Gender bias detected in government responses",
                "description": "The model shows consistent gender stereotyping in certain government service categories...",
                "action_items": [
                    "Review and augment training data with gender-neutral examples",
                    "Implement bias detection in deployment",
                    "Regular auditing of model outputs"
                ],
                "estimated_effort": "medium",
                "related_prompts": ["gov_001", "gov_015", "gov_023"]
            }
        }


# ═══════════════════════════════════════════════════════════════
# ERROR SCHEMAS
# ═══════════════════════════════════════════════════════════════


class ErrorResponse(BaseModel):
    """Error response."""
    
    detail: str = Field(..., description="Error detail message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(..., description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Evaluation not found",
                "status_code": 404,
                "timestamp": "2026-04-15T10:30:00"
            }
        }


# ═══════════════════════════════════════════════════════════════
# REPORT SCHEMAS
# ═══════════════════════════════════════════════════════════════


class ReportGenerateRequest(BaseModel):
    """Generate report request."""
    
    project_id: str = Field(..., description="Project ID")
    format: str = Field("docx", description="Report format: docx, pdf, pptx")
    include_sections: Optional[List[str]] = Field(
        None, description="Sections to include: summary, detailed, recommendations, appendix"
    )


class ReportResponse(BaseModel):
    """Report generation response."""
    
    project_id: str = Field(..., description="Project ID")
    format: str = Field(..., description="Report format")
    url: str = Field(..., description="Download URL")
    generated_at: datetime = Field(..., description="Generation time")
    file_size_mb: float = Field(..., description="File size in MB")
