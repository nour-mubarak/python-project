#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Evaluation Module
=======================

Queue system for running multiple evaluations.
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

logger = logging.getLogger(__name__)

# Store jobs in data directory
DATA_DIR = Path(__file__).parent / "data"
JOBS_FILE = DATA_DIR / "batch_jobs.json"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """A single evaluation job in the batch queue."""

    id: str
    name: str
    config_id: str  # Reference to evaluation config
    model: str
    prompt_pack: str
    languages: List[str]
    status: JobStatus = JobStatus.QUEUED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0  # 0-100
    total_prompts: int = 0
    completed_prompts: int = 0
    result_file: Optional[str] = None
    error: Optional[str] = None
    created_by: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BatchJob":
        # Handle status enum
        if "status" in data and isinstance(data["status"], str):
            data["status"] = JobStatus(data["status"])
        return cls(**data)


class BatchQueue:
    """
    Batch evaluation queue manager.

    Manages a queue of evaluation jobs that run sequentially.
    """

    def __init__(self):
        self.jobs: Dict[str, BatchJob] = {}
        self.queue: List[str] = []  # Job IDs in queue order
        self._lock = threading.Lock()
        self._running = False
        self._current_job: Optional[str] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._load_jobs()

    def _load_jobs(self):
        """Load jobs from disk."""
        try:
            if JOBS_FILE.exists():
                with open(JOBS_FILE, "r") as f:
                    data = json.load(f)
                    for job_data in data.get("jobs", []):
                        job = BatchJob.from_dict(job_data)
                        self.jobs[job.id] = job
                    self.queue = data.get("queue", [])
        except Exception as e:
            logger.error(f"Error loading batch jobs: {e}")

    def _save_jobs(self):
        """Save jobs to disk."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(JOBS_FILE, "w") as f:
                json.dump(
                    {
                        "jobs": [job.to_dict() for job in self.jobs.values()],
                        "queue": self.queue,
                    },
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as e:
            logger.error(f"Error saving batch jobs: {e}")

    def add_job(
        self,
        name: str,
        config_id: str,
        model: str,
        prompt_pack: str,
        languages: List[str],
        created_by: Optional[str] = None,
    ) -> BatchJob:
        """Add a new job to the queue."""
        with self._lock:
            job = BatchJob(
                id=str(uuid.uuid4())[:8],
                name=name,
                config_id=config_id,
                model=model,
                prompt_pack=prompt_pack,
                languages=languages,
                created_by=created_by,
            )
            self.jobs[job.id] = job
            self.queue.append(job.id)
            self._save_jobs()
            return job

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[BatchJob]:
        """Get all jobs sorted by creation date (newest first)."""
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    def get_queued_jobs(self) -> List[BatchJob]:
        """Get jobs in queue order."""
        return [self.jobs[jid] for jid in self.queue if jid in self.jobs]

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                if job_id in self.queue:
                    self.queue.remove(job_id)
                self._save_jobs()
                return True
            return False

    def delete_job(self, job_id: str) -> bool:
        """Delete a job (only if not running)."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            if job.status == JobStatus.RUNNING:
                return False

            if job_id in self.queue:
                self.queue.remove(job_id)
            del self.jobs[job_id]
            self._save_jobs()
            return True

    def update_job_progress(
        self,
        job_id: str,
        progress: int = None,
        completed_prompts: int = None,
        total_prompts: int = None,
    ):
        """Update job progress."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                if progress is not None:
                    job.progress = progress
                if completed_prompts is not None:
                    job.completed_prompts = completed_prompts
                if total_prompts is not None:
                    job.total_prompts = total_prompts
                self._save_jobs()

    def complete_job(self, job_id: str, result_file: str = None, error: str = None):
        """Mark job as completed or failed."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                job.completed_at = datetime.now().isoformat()
                if error:
                    job.status = JobStatus.FAILED
                    job.error = error
                else:
                    job.status = JobStatus.COMPLETED
                    job.result_file = result_file
                    job.progress = 100
                self._save_jobs()

    def get_queue_status(self) -> dict:
        """Get current queue status."""
        queued = sum(1 for j in self.jobs.values() if j.status == JobStatus.QUEUED)
        running = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)
        completed = sum(
            1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED
        )
        failed = sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED)

        return {
            "total_jobs": len(self.jobs),
            "queued": queued,
            "running": running,
            "completed": completed,
            "failed": failed,
            "is_processing": self._running,
            "current_job": self._current_job,
        }

    def clear_completed(self):
        """Remove all completed and failed jobs."""
        with self._lock:
            to_remove = [
                jid
                for jid, job in self.jobs.items()
                if job.status
                in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            ]
            for jid in to_remove:
                del self.jobs[jid]
                if jid in self.queue:
                    self.queue.remove(jid)
            self._save_jobs()


# Global batch queue instance
batch_queue = BatchQueue()


async def run_batch_evaluation(job: BatchJob, runner_func) -> str:
    """
    Run a single batch evaluation job.

    Args:
        job: The batch job to run
        runner_func: Async function to run evaluation (model, prompt_pack, languages) -> result_file

    Returns:
        Path to result file
    """
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now().isoformat()

    try:
        result_file = await runner_func(
            model=job.model,
            prompt_pack=job.prompt_pack,
            languages=job.languages,
            progress_callback=lambda p, c, t: batch_queue.update_job_progress(
                job.id, p, c, t
            ),
        )

        batch_queue.complete_job(job.id, result_file=result_file)
        return result_file

    except Exception as e:
        batch_queue.complete_job(job.id, error=str(e))
        raise


async def process_batch_queue(runner_func):
    """
    Process all jobs in the batch queue.

    This runs as a background task, processing jobs one at a time.
    """
    batch_queue._running = True

    try:
        while batch_queue.queue:
            job_id = batch_queue.queue[0]
            job = batch_queue.get_job(job_id)

            if not job or job.status != JobStatus.QUEUED:
                batch_queue.queue.pop(0)
                continue

            batch_queue._current_job = job_id

            try:
                await run_batch_evaluation(job, runner_func)
            except Exception as e:
                logger.error(f"Batch job {job_id} failed: {e}")

            # Remove from queue after processing
            if batch_queue.queue and batch_queue.queue[0] == job_id:
                batch_queue.queue.pop(0)

            batch_queue._current_job = None
            batch_queue._save_jobs()

    finally:
        batch_queue._running = False
        batch_queue._current_job = None
