#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Fine-tuning Integration
===============================

Fine-tune OpenAI models (GPT-3.5-turbo, GPT-4) on custom datasets.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import asdict


class OpenAIFinetuner:
    """
    Fine-tune OpenAI models using the OpenAI API.

    Features:
    - Upload training/validation datasets
    - Create fine-tuning jobs
    - Monitor training progress
    - Deploy fine-tuned models
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI fine-tuner."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        try:
            import openai

            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package required: pip install openai")

    def upload_training_file(self, file_path: str) -> str:
        """
        Upload training dataset to OpenAI.

        Args:
            file_path: Path to JSONL file

        Returns:
            File ID
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"Uploading training file: {file_path}")

        with open(file_path, "rb") as f:
            response = self.client.files.create(file=f, purpose="fine-tune")

        file_id = response.id
        print(f"✅ File uploaded: {file_id}")
        return file_id

    def create_finetuning_job(
        self,
        training_file_id: str,
        model: str = "gpt-3.5-turbo",
        hyperparameters: Optional[Dict[str, Any]] = None,
        validation_file_id: Optional[str] = None,
        suffix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a fine-tuning job.

        Args:
            training_file_id: File ID from upload_training_file()
            model: Base model (gpt-3.5-turbo, gpt-4, etc.)
            hyperparameters: Optional training hyperparameters
            validation_file_id: Optional validation dataset file ID
            suffix: Suffix for fine-tuned model name (max 40 chars)

        Returns:
            Fine-tuning job details
        """
        print(f"\nCreating fine-tuning job for {model}")

        params = {
            "training_file": training_file_id,
            "model": model,
        }

        if hyperparameters:
            params["hyperparameters"] = hyperparameters

        if validation_file_id:
            params["validation_file"] = validation_file_id

        if suffix:
            params["suffix"] = suffix[:40]  # Max 40 chars

        job = self.client.fine_tuning.jobs.create(**params)

        print(f"✅ Fine-tuning job created: {job.id}")
        print(f"   Status: {job.status}")
        print(f"   Model: {job.model}")

        return asdict(job) if hasattr(job, "__dict__") else job.model_dump()

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a fine-tuning job."""
        job = self.client.fine_tuning.jobs.retrieve(job_id)

        status_info = {
            "job_id": job.id,
            "status": job.status,
            "model": job.model,
            "created_at": job.created_at,
            "fine_tuned_model": getattr(job, "fine_tuned_model", None),
        }

        # Add training details if available
        if hasattr(job, "result_files"):
            status_info["result_files"] = job.result_files

        if hasattr(job, "training_file"):
            status_info["training_file"] = job.training_file

        return status_info

    def wait_for_completion(
        self,
        job_id: str,
        max_wait_seconds: int = 3600,
        poll_interval_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Wait for fine-tuning job to complete.

        Args:
            job_id: Fine-tuning job ID
            max_wait_seconds: Maximum time to wait
            poll_interval_seconds: How often to check status

        Returns:
            Final job status
        """
        print(f"\nWaiting for job {job_id} to complete...")
        start_time = time.time()

        while True:
            status = self.get_job_status(job_id)

            if status["status"] == "succeeded":
                print(f"✅ Job completed!")
                print(f"   Fine-tuned model: {status['fine_tuned_model']}")
                return status

            elif status["status"] == "failed":
                print(f"❌ Job failed!")
                return status

            elif status["status"] == "cancelled":
                print(f"⚠️  Job cancelled!")
                return status

            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                print(f"⚠️  Timeout waiting for job")
                return status

            print(f"   Status: {status['status']} (elapsed: {elapsed:.0f}s)")
            time.sleep(poll_interval_seconds)

    def list_jobs(self, limit: int = 10) -> list:
        """List recent fine-tuning jobs."""
        jobs = self.client.fine_tuning.jobs.list(limit=limit)

        result = []
        for job in jobs.data:
            result.append(
                {
                    "id": job.id,
                    "status": job.status,
                    "model": job.model,
                    "fine_tuned_model": getattr(job, "fine_tuned_model", None),
                    "created_at": job.created_at,
                }
            )

        return result

    def get_training_results(
        self, job_id: str, output_file: Optional[str] = None
    ) -> dict:
        """
        Download and parse training results.

        Args:
            job_id: Fine-tuning job ID
            output_file: Optional path to save results

        Returns:
            Training results (loss, accuracy, etc.)
        """
        status = self.get_job_status(job_id)

        if not status.get("result_files"):
            print(f"⚠️  No results available yet for job {job_id}")
            return {}

        result_file_id = status["result_files"][0] if status["result_files"] else None
        if not result_file_id:
            return {}

        print(f"Downloading results for job {job_id}...")

        file_response = self.client.files.content(result_file_id)
        content = file_response.text

        # Parse CSV/JSONL results
        results = {
            "raw_content": content,
        }

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Results saved to: {output_file}")

        return results

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a fine-tuning job."""
        job = self.client.fine_tuning.jobs.cancel(job_id)

        print(f"✅ Job {job_id} cancelled")
        return {
            "job_id": job.id,
            "status": job.status,
        }

    def delete_file(self, file_id: str) -> bool:
        """Delete an uploaded file."""
        result = self.client.files.delete(file_id)
        print(f"✅ File {file_id} deleted")
        return True
