#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Tool for Fine-tuning Management
====================================

Command-line interface for fine-tuning models.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Optional


def finetune_openai_cli(args):
    """Fine-tune OpenAI model from CLI."""

    from finetuning.openai_finetuner import OpenAIFinetuner

    tuner = OpenAIFinetuner(api_key=args.api_key or os.getenv("OPENAI_API_KEY"))

    print(f"OpenAI Fine-tuning Job")
    print("=" * 70)
    print(f"Training file: {args.training_file}")
    print(f"Model: {args.model}")

    # Upload file
    file_id = tuner.upload_training_file(args.training_file)

    if args.validation_file:
        val_file_id = tuner.upload_training_file(args.validation_file)
    else:
        val_file_id = None

    # Create job
    job = tuner.create_finetuning_job(
        training_file_id=file_id,
        model=args.model,
        validation_file_id=val_file_id,
        suffix=args.suffix,
        hyperparameters={
            "n_epochs": args.epochs,
            "learning_rate_multiplier": args.learning_rate,
        },
    )

    print(f"\n✅ Job created: {job['id']}")

    if args.wait:
        print("Waiting for job to complete...")
        final_status = tuner.wait_for_completion(job["id"])

        if final_status["status"] == "succeeded":
            print(f"\n✅ Job completed!")
            print(f"   Fine-tuned model: {final_status['fine_tuned_model']}")
        else:
            print(f"\n❌ Job {final_status['status']}")

    return job


def finetune_local_cli(args):
    """Fine-tune local model (Llama, Mistral) from CLI."""

    from finetuning.finetuner import Finetuner

    tuner = Finetuner(
        model_id=args.model, output_dir=args.output_dir, use_qlora=not args.full_lora
    )

    print(f"Local Model Fine-tuning")
    print("=" * 70)
    print(f"Model: {args.model}")
    print(f"Training file: {args.training_file}")
    print(f"QLoRA: {not args.full_lora}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")

    # Fine-tune
    result = tuner.finetune(
        dataset_file=args.training_file,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        num_gpus=args.num_gpus,
    )

    print(f"\n✅ Fine-tuning complete!")
    print(f"   Output: {result['output_dir']}")

    if args.merge:
        print("Merging LoRA weights...")
        merged = tuner.merge_lora_weights(result["output_dir"])
        print(f"   Merged model: {merged}")


def list_jobs_cli(args):
    """List fine-tuning jobs."""

    from finetuning.openai_finetuner import OpenAIFinetuner

    tuner = OpenAIFinetuner(api_key=args.api_key or os.getenv("OPENAI_API_KEY"))

    jobs = tuner.list_jobs(limit=args.limit)

    print(f"\nRecent Fine-tuning Jobs:\n")
    print(f"{'ID':<30} {'Status':<12} {'Model':<20} {'Fine-tuned Model':<30}")
    print("-" * 92)

    for job in jobs:
        print(
            f"{job['id']:<30} {job['status']:<12} {job['model']:<20} {job.get('fine_tuned_model', '-'):<30}"
        )


def job_status_cli(args):
    """Get status of a fine-tuning job."""

    from finetuning.openai_finetuner import OpenAIFinetuner

    tuner = OpenAIFinetuner(api_key=args.api_key or os.getenv("OPENAI_API_KEY"))

    status = tuner.get_job_status(args.job_id)

    print(f"\nJob Status: {args.job_id}")
    print("=" * 70)
    print(json.dumps(status, indent=2, default=str))

    if args.results and status.get("result_files"):
        output_file = f"job_{args.job_id}_results.csv"
        tuner.get_training_results(args.job_id, output_file)
        print(f"\n✅ Results saved: {output_file}")


def cancel_job_cli(args):
    """Cancel a fine-tuning job."""

    from finetuning.openai_finetuner import OpenAIFinetuner

    tuner = OpenAIFinetuner(api_key=args.api_key or os.getenv("OPENAI_API_KEY"))

    result = tuner.cancel_job(args.job_id)

    print(f"\n✅ Job cancelled: {result['job_id']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Fine-tuning Management CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # ════════════════════════════════════════════════════════════════════════
    # openai: Fine-tune OpenAI models
    # ════════════════════════════════════════════════════════════════════════
    openai_parser = subparsers.add_parser("openai", help="Fine-tune OpenAI models")
    openai_parser.add_argument(
        "--training-file", required=True, help="Training data (JSONL)"
    )
    openai_parser.add_argument("--validation-file", help="Validation data (JSONL)")
    openai_parser.add_argument("--model", default="gpt-3.5-turbo", help="Base model")
    openai_parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    openai_parser.add_argument(
        "--learning-rate", type=float, default=0.1, help="Learning rate multiplier"
    )
    openai_parser.add_argument("--suffix", default="v1", help="Model suffix")
    openai_parser.add_argument("--api-key", help="OpenAI API key")
    openai_parser.add_argument(
        "--wait", action="store_true", help="Wait for completion"
    )
    openai_parser.set_defaults(func=finetune_openai_cli)

    # ════════════════════════════════════════════════════════════════════════
    # local: Fine-tune local models
    # ════════════════════════════════════════════════════════════════════════
    local_parser = subparsers.add_parser("local", help="Fine-tune local models")
    local_parser.add_argument(
        "--model", required=True, help="Model ID (e.g., meta-llama/Llama-2-7b)"
    )
    local_parser.add_argument(
        "--training-file", required=True, help="Training data (JSONL)"
    )
    local_parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    local_parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    local_parser.add_argument(
        "--learning-rate", type=float, default=2e-4, help="Learning rate"
    )
    local_parser.add_argument("--num-gpus", type=int, default=1, help="Number of GPUs")
    local_parser.add_argument(
        "--full-lora", action="store_true", help="Use full LoRA (not QLoRA)"
    )
    local_parser.add_argument(
        "--output-dir", default="finetuned_models", help="Output directory"
    )
    local_parser.add_argument(
        "--merge", action="store_true", help="Merge LoRA weights after training"
    )
    local_parser.set_defaults(func=finetune_local_cli)

    # ════════════════════════════════════════════════════════════════════════
    # jobs: List jobs
    # ════════════════════════════════════════════════════════════════════════
    jobs_parser = subparsers.add_parser("jobs", help="List fine-tuning jobs")
    jobs_parser.add_argument("--api-key", help="OpenAI API key")
    jobs_parser.add_argument("--limit", type=int, default=10, help="Limit results")
    jobs_parser.set_defaults(func=list_jobs_cli)

    # ════════════════════════════════════════════════════════════════════════
    # status: Get job status
    # ════════════════════════════════════════════════════════════════════════
    status_parser = subparsers.add_parser("status", help="Get job status")
    status_parser.add_argument("--job-id", required=True, help="Job ID")
    status_parser.add_argument("--api-key", help="OpenAI API key")
    status_parser.add_argument(
        "--results", action="store_true", help="Download results"
    )
    status_parser.set_defaults(func=job_status_cli)

    # ════════════════════════════════════════════════════════════════════════
    # cancel: Cancel job
    # ════════════════════════════════════════════════════════════════════════
    cancel_parser = subparsers.add_parser("cancel", help="Cancel job")
    cancel_parser.add_argument("--job-id", required=True, help="Job ID")
    cancel_parser.add_argument("--api-key", help="OpenAI API key")
    cancel_parser.set_defaults(func=cancel_job_cli)

    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
