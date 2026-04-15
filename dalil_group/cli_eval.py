#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Tool for Evaluation Management
===================================

Command-line interface for running and managing evaluations.
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from config.builder import (
    EvaluationConfig,
    preset_government,
    preset_university,
    preset_healthcare,
    preset_finance,
)
from utils.model_runner import ModelRunner
from scoring.scorer import ScoringEngine
from generate_report import generate_report


def run_evaluation_cli(args):
    """Execute evaluation from CLI arguments."""

    if args.preset:
        if args.preset == "government":
            config = preset_government(client_name=args.client)
        elif args.preset == "university":
            config = preset_university(client_name=args.client)
        elif args.preset == "healthcare":
            config = preset_healthcare(client_name=args.client)
        elif args.preset == "finance":
            config = preset_finance(client_name=args.client)
        else:
            raise ValueError(f"Unknown preset: {args.preset}")
    elif args.config:
        with open(args.config, "r") as f:
            config_dict = json.load(f)
        config = EvaluationConfig(**config_dict)
    else:
        raise ValueError("Must specify either --preset or --config")

    print("=" * 70)
    print(f"EVALUATION: {config.client_name}")
    print("=" * 70)
    print(f"  Models: {config.models}")
    print(f"  Dimensions: {config.evaluation_dimensions}")
    print(f"  Output: {config.output_dir}")

    if args.dry_run:
        print("\n  🔍 DRY RUN - No API calls will be made\n")

    # Run evaluation
    runner = ModelRunner(config.models)
    responses = runner.run(dry_run=args.dry_run)

    # Score responses
    if args.use_judge:
        scorer = ScoringEngine()
        print("\nScoring with judge model...")

    # Save results
    os.makedirs(config.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(
        config.output_dir,
        f"{config.client_name.lower().replace(' ', '_')}_{timestamp}.json",
    )

    # Generate report if requested
    if args.report:
        print(f"\nGenerating report...")
        report_file = generate_report(
            results_file=results_file, output_dir=config.output_dir, format=args.report
        )
        print(f"✅ Report saved: {report_file}")

    print(f"\n✅ Evaluation complete!")
    print(f"   Results: {results_file}")


def list_evaluations_cli(args):
    """List recent evaluation results."""

    results_dir = Path(args.results_dir or "results")

    if not results_dir.exists():
        print(f"No results directory: {results_dir}")
        return

    results = []
    for json_file in sorted(results_dir.glob("*.json"), reverse=True):
        if args.limit and len(results) >= args.limit:
            break

        with open(json_file, "r") as f:
            data = json.load(f)

        results.append(
            {
                "filename": json_file.name,
                "client": data.get("client_name"),
                "date": json_file.stat().st_mtime,
                "size": json_file.stat().st_size,
            }
        )

    print(f"\nRecent Evaluations ({len(results)} results):\n")
    print(f"{'Filename':<40} {'Client':<20} {'Size':<10}")
    print("-" * 70)

    for r in results:
        size_kb = r["size"] / 1024
        date_str = datetime.fromtimestamp(r["date"]).strftime("%Y-%m-%d %H:%M")
        print(f"{r['filename']:<40} {r['client']:<20} {size_kb:>8.1f}KB")


def compare_evaluations_cli(args):
    """Compare two evaluation results."""

    if not args.file1 or not args.file2:
        print("Error: Must specify both --file1 and --file2")
        return

    with open(args.file1, "r") as f:
        results1 = json.load(f)

    with open(args.file2, "r") as f:
        results2 = json.load(f)

    print("\n" + "=" * 70)
    print("EVALUATION COMPARISON")
    print("=" * 70)
    print(f"File 1: {args.file1}")
    print(f"File 2: {args.file2}")
    print("=" * 70)

    # Compare metrics
    metrics1 = results1.get("summary", {})
    metrics2 = results2.get("summary", {})

    print(f"\n{'Metric':<30} {'Eval 1':>15} {'Eval 2':>15} {'Change':>15}")
    print("-" * 75)

    for key in metrics1.keys():
        val1 = metrics1.get(key)
        val2 = metrics2.get(key)

        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            change = val2 - val1
            change_pct = (change / val1 * 100) if val1 != 0 else 0

            change_str = f"{change:+.1f} ({change_pct:+.1f}%)"
            print(f"{key:<30} {val1:>15.2f} {val2:>15.2f} {change_str:>15}")


def export_dataset_cli(args):
    """Export evaluation results as training dataset."""

    from finetuning.dataset_builder import DatasetBuilder

    if not args.results_file:
        print("Error: Must specify --results-file")
        return

    builder = DatasetBuilder()

    print(f"Loading evaluation results: {args.results_file}")
    added = builder.add_from_evaluation_results(
        results_file=args.results_file, min_quality_score=args.min_quality or 75.0
    )

    print(f"✅ Added {added} examples")

    # Balance if requested
    if args.balance:
        balance_info = builder.balance_dataset(max_per_category=100)
        print(f"Balanced dataset: {balance_info}")

    # Export
    output_dir = Path(args.output_dir or "datasets")
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.format == "jsonl" or not args.format:
        output_file = output_dir / "training_data.jsonl"
        builder.export_jsonl(str(output_file))
        print(f"✅ Exported to: {output_file}")

    if args.format == "csv" or not args.format:
        output_file = output_dir / "training_data.csv"
        builder.export_csv(str(output_file))
        print(f"✅ Exported to: {output_file}")

    # Save metadata
    metadata_file = output_dir / "metadata.json"
    builder.save_metadata(str(metadata_file))
    print(f"✅ Metadata saved: {metadata_file}")

    # Print statistics
    stats = builder.get_statistics()
    print(f"\nDataset Statistics:")
    print(f"  Total examples: {stats['total_examples']}")
    print(f"  By category: {stats['by_category']}")
    print(f"  By language: {stats['by_language']}")
    print(f"  Quality score (avg): {stats['quality_score_stats']['avg']:.1f}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Dalīl Group Evaluation & Fine-tuning CLI"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # ════════════════════════════════════════════════════════════════════════
    # run: Execute evaluation
    # ════════════════════════════════════════════════════════════════════════
    run_parser = subparsers.add_parser("run", help="Run evaluation")
    run_parser.add_argument("--config", help="Config file (YAML/JSON)")
    run_parser.add_argument(
        "--preset",
        choices=["government", "university", "healthcare", "finance"],
        help="Preset configuration",
    )
    run_parser.add_argument("--client", default="Test Client", help="Client name")
    run_parser.add_argument("--use-judge", action="store_true", help="Use judge model")
    run_parser.add_argument(
        "--dry-run", action="store_true", help="Dry run (no API calls)"
    )
    run_parser.add_argument(
        "--report", choices=["pdf", "html", "json"], help="Generate report"
    )
    run_parser.set_defaults(func=run_evaluation_cli)

    # ════════════════════════════════════════════════════════════════════════
    # list: List recent evaluations
    # ════════════════════════════════════════════════════════════════════════
    list_parser = subparsers.add_parser("list", help="List evaluations")
    list_parser.add_argument(
        "--results-dir", default="results", help="Results directory"
    )
    list_parser.add_argument("--limit", type=int, default=10, help="Limit results")
    list_parser.set_defaults(func=list_evaluations_cli)

    # ════════════════════════════════════════════════════════════════════════
    # compare: Compare two evaluations
    # ════════════════════════════════════════════════════════════════════════
    compare_parser = subparsers.add_parser("compare", help="Compare evaluations")
    compare_parser.add_argument("--file1", required=True, help="First results file")
    compare_parser.add_argument("--file2", required=True, help="Second results file")
    compare_parser.set_defaults(func=compare_evaluations_cli)

    # ════════════════════════════════════════════════════════════════════════
    # export: Export dataset for fine-tuning
    # ════════════════════════════════════════════════════════════════════════
    export_parser = subparsers.add_parser(
        "export", help="Export dataset for fine-tuning"
    )
    export_parser.add_argument(
        "--results-file", required=True, help="Results JSON file"
    )
    export_parser.add_argument(
        "--min-quality", type=float, default=75.0, help="Minimum quality score"
    )
    export_parser.add_argument(
        "--balance", action="store_true", help="Balance across categories"
    )
    export_parser.add_argument(
        "--format", choices=["jsonl", "csv"], default="jsonl", help="Output format"
    )
    export_parser.add_argument(
        "--output-dir", default="datasets", help="Output directory"
    )
    export_parser.set_defaults(func=export_dataset_cli)

    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
