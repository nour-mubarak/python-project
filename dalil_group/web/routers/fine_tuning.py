#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fine-Tuning Router
==================

API routes for model fine-tuning management.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Path, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal
from utils.fine_tuning import (
    fine_tuning_backend,
    FineTuningConfig,
    FineTuningProvider,
    FineTuningStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fine-tuning", tags=["fine-tuning"])


class TrainingDataItem(BaseModel):
    """Training data item."""
    prompt: str = Field(..., description="Input prompt")
    completion: str = Field(..., description="Expected completion")


class FineTuningJobRequest(BaseModel):
    """Request to create a fine-tuning job."""
    model_name: str = Field(..., description="Base model to fine-tune")
    provider: str = Field(..., description="Provider: openai, anthropic, ollama, azure")
    training_dataset: List[TrainingDataItem] = Field(..., description="Training data")
    learning_rate: float = Field(0.01, description="Learning rate")
    epochs: int = Field(3, description="Number of epochs")
    batch_size: int = Field(8, description="Batch size")
    suffix: Optional[str] = Field(None, description="Suffix for fine-tuned model name")
    description: Optional[str] = Field(None, description="Job description")


class FineTuningJobResponse(BaseModel):
    """Response with fine-tuning job details."""
    job_id: str = Field(..., description="Job ID")
    model_name: str = Field(..., description="Base model")
    provider: str = Field(..., description="Provider")
    status: str = Field(..., description="Status")
    created_at: str = Field(..., description="Creation time")
    started_at: Optional[str] = Field(None, description="Start time")
    completed_at: Optional[str] = Field(None, description="Completion time")
    fine_tuned_model: Optional[str] = Field(None, description="Fine-tuned model name")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    training_loss: Optional[float] = Field(None, description="Final training loss")
    validation_loss: Optional[float] = Field(None, description="Validation loss")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/jobs", response_model=FineTuningJobResponse)
async def create_fine_tuning_job(
    request: FineTuningJobRequest,
    db: Session = Depends(get_db)
) -> FineTuningJobResponse:
    """
    Create a new fine-tuning job.
    
    Validates the training data and creates a fine-tuning job that can be
    submitted to the selected provider.
    
    Args:
        request: Fine-tuning job request
        
    Returns:
        FineTuningJobResponse
    """
    try:
        # Validate training data
        training_data = [item.dict() for item in request.training_dataset]
        is_valid, errors = fine_tuning_backend.validate_training_data(training_data)
        
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid training data: {', '.join(errors)}"
            )
        
        # Create config
        config = FineTuningConfig(
            model_name=request.model_name,
            provider=FineTuningProvider(request.provider),
            training_dataset=training_data,
            learning_rate=request.learning_rate,
            epochs=request.epochs,
            batch_size=request.batch_size,
            suffix=request.suffix,
            description=request.description
        )
        
        # Create job
        job_id = str(uuid.uuid4())
        job = fine_tuning_backend.create_fine_tuning_job(job_id, config)
        
        logger.info(f"Created fine-tuning job {job_id}")
        
        return FineTuningJobResponse(
            job_id=job.job_id,
            model_name=job.model_name,
            provider=job.provider.value,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            fine_tuned_model=job.fine_tuned_model,
            error_message=job.error_message,
            training_loss=job.training_loss,
            validation_loss=job.validation_loss
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fine-tuning job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/submit", response_model=FineTuningJobResponse)
async def submit_fine_tuning_job(
    job_id: str = Path(..., description="Job ID"),
    db: Session = Depends(get_db)
) -> FineTuningJobResponse:
    """
    Submit a fine-tuning job for processing.
    
    Submits the job to the configured provider's API for actual fine-tuning.
    
    Args:
        job_id: Job ID
        
    Returns:
        Updated FineTuningJobResponse
    """
    try:
        job = fine_tuning_backend.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # For now, just mark as submitted (actual submission would require config)
        # In production, we'd load the full config from the database
        job.status = FineTuningStatus.QUEUED
        logger.info(f"Submitted fine-tuning job {job_id}")
        
        return FineTuningJobResponse(
            job_id=job.job_id,
            model_name=job.model_name,
            provider=job.provider.value,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            fine_tuned_model=job.fine_tuned_model,
            error_message=job.error_message,
            training_loss=job.training_loss,
            validation_loss=job.validation_loss
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting fine-tuning job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=FineTuningJobResponse)
async def get_fine_tuning_job(
    job_id: str = Path(..., description="Job ID"),
    db: Session = Depends(get_db)
) -> FineTuningJobResponse:
    """
    Get fine-tuning job status.
    
    Retrieves the current status and details of a fine-tuning job.
    
    Args:
        job_id: Job ID
        
    Returns:
        FineTuningJobResponse
    """
    try:
        job = fine_tuning_backend.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return FineTuningJobResponse(
            job_id=job.job_id,
            model_name=job.model_name,
            provider=job.provider.value,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            fine_tuned_model=job.fine_tuned_model,
            error_message=job.error_message,
            training_loss=job.training_loss,
            validation_loss=job.validation_loss
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving fine-tuning job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=List[FineTuningJobResponse])
async def list_fine_tuning_jobs(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[FineTuningJobResponse]:
    """
    List fine-tuning jobs.
    
    Retrieves a list of all fine-tuning jobs, optionally filtered by status.
    
    Args:
        status: Optional status filter (pending, queued, running, completed, failed, cancelled)
        
    Returns:
        List of FineTuningJobResponse
    """
    try:
        filter_status = None
        if status:
            try:
                filter_status = FineTuningStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        jobs = fine_tuning_backend.list_jobs(filter_status)
        
        return [
            FineTuningJobResponse(
                job_id=job.job_id,
                model_name=job.model_name,
                provider=job.provider.value,
                status=job.status.value,
                created_at=job.created_at.isoformat(),
                started_at=job.started_at.isoformat() if job.started_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                fine_tuned_model=job.fine_tuned_model,
                error_message=job.error_message,
                training_loss=job.training_loss,
                validation_loss=job.validation_loss
            )
            for job in jobs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing fine-tuning jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def cancel_fine_tuning_job(
    job_id: str = Path(..., description="Job ID"),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Cancel a fine-tuning job.
    
    Cancels a fine-tuning job if it's still in progress.
    
    Args:
        job_id: Job ID
        
    Returns:
        Status message
    """
    try:
        success = fine_tuning_backend.cancel_job(job_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Could not cancel job")
        
        return {"status": "cancelled", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling fine-tuning job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
