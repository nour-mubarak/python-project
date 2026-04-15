#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Evaluation Module
=======================

Queue system for running multiple evaluations with database persistence.
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field, asdict
import threading
import logging

from database import (
    SessionLocal,
    create_batch_job,
    get_batch_job,
    update_batch_job_progress,
    get_running_batch_jobs,
    get_batch_jobs_for_user,
)

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """A single evaluation job in the batch queue."""

    id: str
    user_id: int
    name: str
    config: dict  # {models, prompt_pack, languages, dimensions, etc.}
    status: JobStatus = JobStatus.QUEUED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0  # 0-100
    completed_items: int = 0
    failed_items: int = 0
    error: Optional[str] = None
    result: Optional[dict] = None

    def to_dict(self):
        """Convert to dictionary representation."""
        return asdict(self)


class BatchQueue:
    """Queue manager for batch evaluations with database persistence."""

    def __init__(self):
        """Initialize the batch queue."""
        self.queue: List[BatchJob] = []
        self.running: Dict[str, BatchJob] = {}
        self.lock = threading.Lock()
        self._load_pending_jobs()

    def _load_pending_jobs(self):
        """Load pending and running jobs from database on startup."""
        db = SessionLocal()
        try:
            running_jobs = get_running_batch_jobs(db)
            for job_record in running_jobs:
                config = json.loads(job_record.config_json)
                batch_job = BatchJob(
                    id=job_record.id,
                    user_id=job_record.user_id,
                    name=job_record.name,
                    config=config,
                    status=JobStatus(job_record.status),
                    created_at=job_record.created_at.isoformat(),
                    started_at=job_record.started_at.isoformat() if job_record.started_at else None,
                    completed_at=job_record.completed_at.isoformat() if job_record.completed_at else None,
                    progress=job_record.progress,
                    completed_items=job_record.completed_items,
                    failed_items=job_record.failed_items,
                    error=job_record.error_message,
                    result=json.loads(job_record.result_json) if job_record.result_json else None,
                )
                self.running[batch_job.id] = batch_job
        finally:
            db.close()

    def add_job(
        self,
        user_id: int,
        name: str,
        config: dict,
    ) -> str:
        """Add a new job to the queue."""
        job_id = str(uuid.uuid4())
        
        db = SessionLocal()
        try:
            create_batch_job(
                db,
                job_id=job_id,
                user_id=user_id,
                name=name,
                config=config,
            )
        finally:
            db.close()

        batch_job = BatchJob(
            id=job_id,
            user_id=user_id,
            name=name,
            config=config,
            status=JobStatus.QUEUED,
        )

        with self.lock:
            self.queue.append(batch_job)

        logger.info(f"Added batch job {job_id} to queue")
        return job_id

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get a job by ID."""
        with self.lock:
            if job_id in self.running:
                return self.running[job_id]
            for job in self.queue:
                if job.id == job_id:
                    return job
        return None

    def start_job(self, job_id: str):
        """Mark job as started."""
        db = SessionLocal()
        try:
            update_batch_job_progress(
                db,
                job_id,
                status=JobStatus.RUNNING.value,
            )
            with self.lock:
                self.running[job_id] = self.get_job(job_id)
        finally:
            db.close()

    def update_job_progress(
        self,
        job_id: str,
        progress: int = 0,
        completed_items: int = 0,
        failed_items: int = 0,
    ):
        """Update job progress."""
        db = SessionLocal()
        try:
            update_batch_job_progress(
                db,
                job_id,
                progress=progress,
                completed_items=completed_items,
                failed_items=failed_items,
            )
        finally:
            db.close()

    def complete_job(self, job_id: str, result: dict = None):
        """Mark job as completed."""
        db = SessionLocal()
        try:
            update_batch_job_progress(
                db,
                job_id,
                status=JobStatus.COMPLETED.value,
                result_json=result if result else None,
            )
            with self.lock:
                if job_id in self.running:
                    del self.running[job_id]
        finally:
            db.close()

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed."""
        db = SessionLocal()
        try:
            update_batch_job_progress(
                db,
                job_id,
                status=JobStatus.FAILED.value,
                error_message=error,
            )
            with self.lock:
                if job_id in self.running:
                    del self.running[job_id]
        finally:
            db.close()

    def cancel_job(self, job_id: str):
        """Cancel a job."""
        db = SessionLocal()
        try:
            update_batch_job_progress(
                db,
                job_id,
                status=JobStatus.CANCELLED.value,
            )
            with self.lock:
                if job_id in self.running:
                    del self.running[job_id]
        finally:
            db.close()

    def queue_size(self) -> int:
        """Get number of jobs in queue."""
        with self.lock:
            return len(self.queue)

    def running_jobs_count(self) -> int:
        """Get number of running jobs."""
        return len(self.running)


# Global batch queue instance
batch_queue = BatchQueue()


def process_batch_queue() -> None:
    """
    Process batch queue (placeholder for background task integration).
    
    In production, this would be coordinated with Celery or similar
    async task processing framework.
    """
    logger.info("Batch queue processor initialized")
