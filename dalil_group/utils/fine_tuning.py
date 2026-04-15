#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model Fine-Tuning Backend
==========================

Handles model fine-tuning integration with multiple LLM providers.
Manages fine-tuning jobs, monitoring, and deployment.
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class FineTuningProvider(str, Enum):
    """Supported fine-tuning providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    AZURE = "azure"


class FineTuningStatus(str, Enum):
    """Status of fine-tuning jobs."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FineTuningConfig:
    """Configuration for a fine-tuning job."""
    model_name: str  # Base model to fine-tune
    provider: FineTuningProvider
    training_dataset: List[Dict[str, str]]  # List of {prompt, completion}
    validation_split: float = 0.1
    learning_rate: float = 0.01
    epochs: int = 3
    batch_size: int = 8
    max_tokens: Optional[int] = None
    suffix: Optional[str] = None  # Model name suffix for fine-tuned model
    description: Optional[str] = None


@dataclass
class FineTuningJob:
    """Represents a fine-tuning job."""
    job_id: str
    model_name: str
    provider: FineTuningProvider
    status: FineTuningStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    fine_tuned_model: Optional[str] = None
    error_message: Optional[str] = None
    training_tokens: int = 0
    validation_loss: Optional[float] = None
    training_loss: Optional[float] = None


class FineTuningBackend:
    """
    Backend for managing model fine-tuning across multiple providers.
    
    Supports:
    - OpenAI Fine-tuning API
    - Anthropic Fine-tuning (when available)
    - Ollama fine-tuning via LoRA
    - Azure OpenAI Fine-tuning
    """
    
    def __init__(self):
        """Initialize the fine-tuning backend."""
        self.jobs: Dict[str, FineTuningJob] = {}
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.azure_key = os.environ.get("AZURE_OPENAI_KEY")
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    def create_fine_tuning_job(
        self,
        job_id: str,
        config: FineTuningConfig
    ) -> FineTuningJob:
        """
        Create a fine-tuning job.
        
        Args:
            job_id: Unique job identifier
            config: Fine-tuning configuration
            
        Returns:
            Created FineTuningJob
        """
        job = FineTuningJob(
            job_id=job_id,
            model_name=config.model_name,
            provider=config.provider,
            status=FineTuningStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        
        self.jobs[job_id] = job
        logger.info(f"Created fine-tuning job {job_id} for model {config.model_name}")
        
        return job
    
    def submit_job(
        self,
        job_id: str,
        config: FineTuningConfig
    ) -> bool:
        """
        Submit a fine-tuning job to the provider.
        
        Args:
            job_id: Job identifier
            config: Fine-tuning configuration
            
        Returns:
            True if successful
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        try:
            if config.provider == FineTuningProvider.OPENAI:
                return self._submit_openai_job(job_id, config, job)
            elif config.provider == FineTuningProvider.ANTHROPIC:
                return self._submit_anthropic_job(job_id, config, job)
            elif config.provider == FineTuningProvider.OLLAMA:
                return self._submit_ollama_job(job_id, config, job)
            elif config.provider == FineTuningProvider.AZURE:
                return self._submit_azure_job(job_id, config, job)
            else:
                logger.error(f"Unknown provider: {config.provider}")
                job.status = FineTuningStatus.FAILED
                job.error_message = f"Unknown provider: {config.provider}"
                return False
        except Exception as e:
            logger.error(f"Error submitting job {job_id}: {e}", exc_info=True)
            job.status = FineTuningStatus.FAILED
            job.error_message = str(e)
            return False
    
    def _submit_openai_job(
        self,
        job_id: str,
        config: FineTuningConfig,
        job: FineTuningJob
    ) -> bool:
        """Submit a fine-tuning job to OpenAI."""
        if not self.openai_api_key:
            logger.error("OpenAI API key not set")
            job.status = FineTuningStatus.FAILED
            job.error_message = "OpenAI API key not configured"
            return False
        
        try:
            import openai
            openai.api_key = self.openai_api_key
            
            # Prepare training data in OpenAI format
            training_data = []
            for item in config.training_dataset:
                training_data.append({
                    "prompt": item.get("prompt", ""),
                    "completion": item.get("completion", "")
                })
            
            # Create training file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
                for item in training_data:
                    f.write(json.dumps(item) + '\n')
                training_file = f.name
            
            # Upload file
            with open(training_file, 'rb') as f:
                files_response = openai.File.create(
                    file=f,
                    purpose="fine-tune"
                )
            
            # Submit fine-tuning job
            response = openai.FineTune.create(
                training_file=files_response['id'],
                model=config.model_name,
                n_epochs=config.epochs,
                batch_size=config.batch_size,
                learning_rate_multiplier=config.learning_rate,
                suffix=config.suffix,
            )
            
            job.status = FineTuningStatus.QUEUED
            job.started_at = datetime.utcnow()
            
            # Store OpenAI job ID in job metadata
            job.job_id = f"{job_id}:openai:{response['id']}"
            
            logger.info(f"Submitted OpenAI fine-tuning job: {response['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error with OpenAI fine-tuning: {e}", exc_info=True)
            job.status = FineTuningStatus.FAILED
            job.error_message = str(e)
            return False
    
    def _submit_anthropic_job(
        self,
        job_id: str,
        config: FineTuningConfig,
        job: FineTuningJob
    ) -> bool:
        """Submit a fine-tuning job to Anthropic."""
        logger.warning("Anthropic fine-tuning not yet implemented")
        job.status = FineTuningStatus.FAILED
        job.error_message = "Anthropic fine-tuning not yet available"
        return False
    
    def _submit_ollama_job(
        self,
        job_id: str,
        config: FineTuningConfig,
        job: FineTuningJob
    ) -> bool:
        """Submit a fine-tuning job to Ollama (via LoRA)."""
        logger.warning("Ollama fine-tuning not yet implemented")
        job.status = FineTuningStatus.FAILED
        job.error_message = "Ollama fine-tuning not yet available"
        return False
    
    def _submit_azure_job(
        self,
        job_id: str,
        config: FineTuningConfig,
        job: FineTuningJob
    ) -> bool:
        """Submit a fine-tuning job to Azure OpenAI."""
        logger.warning("Azure fine-tuning not yet implemented")
        job.status = FineTuningStatus.FAILED
        job.error_message = "Azure fine-tuning not yet available"
        return False
    
    def get_job_status(self, job_id: str) -> Optional[FineTuningJob]:
        """
        Get the status of a fine-tuning job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            FineTuningJob or None if not found
        """
        return self.jobs.get(job_id)
    
    def list_jobs(self, status: Optional[FineTuningStatus] = None) -> List[FineTuningJob]:
        """
        List fine-tuning jobs.
        
        Args:
            status: Optional filter by status
            
        Returns:
            List of FineTuningJobs
        """
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return jobs
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a fine-tuning job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if successful
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        if job.status in (FineTuningStatus.COMPLETED, FineTuningStatus.FAILED, FineTuningStatus.CANCELLED):
            logger.warning(f"Cannot cancel job in {job.status} status")
            return False
        
        job.status = FineTuningStatus.CANCELLED
        logger.info(f"Cancelled fine-tuning job {job_id}")
        return True
    
    def validate_training_data(
        self,
        training_data: List[Dict[str, str]]
    ) -> tuple[bool, List[str]]:
        """
        Validate training data format.
        
        Args:
            training_data: List of training examples
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if not training_data:
            errors.append("Training data is empty")
            return False, errors
        
        if len(training_data) < 10:
            errors.append("At least 10 training examples recommended")
        
        for i, item in enumerate(training_data):
            if not isinstance(item, dict):
                errors.append(f"Item {i} is not a dict")
                continue
            
            if "prompt" not in item or "completion" not in item:
                errors.append(f"Item {i} missing 'prompt' or 'completion' fields")
                continue
            
            if not item["prompt"] or not item["completion"]:
                errors.append(f"Item {i} has empty prompt or completion")
                continue
        
        return len(errors) == 0, errors


# Singleton instance
fine_tuning_backend = FineTuningBackend()
