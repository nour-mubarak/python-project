#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinguaEval — Main Evaluation Runner
====================================

Usage:
    python run_evaluation.py --config config/durham_eval.yaml
    python run_evaluation.py --preset university --client "Durham University"
    python run_evaluation.py --config config/eval.yaml --use-judge
    python run_evaluation.py --config config/eval.yaml --dry-run

This script:
1. Loads the evaluation config
2. Loads the appropriate prompt pack
3. Queries all specified models in both languages
4. Scores all responses across evaluation dimensions
5. Calculates cross-lingual gaps
6. Saves complete results to JSON
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.builder import (
    EvaluationConfig,
    preset_university,
    preset_government,
    preset_finance,
)
from utils.model_runner import ModelRunner, print_progress
from scoring.scorer import ScoringEngine


def load_prompt_pack(sector: str) -> list:
    """Load the prompt pack for the given sector."""
    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"{sector}.json")

    if not os.path.exists(prompt_file):
        print(f"[!] Prompt pack not found: {prompt_file}")
        print(
            f"    Available packs: {', '.join(f.replace('.json','') for f in os.listdir(os.path.join(os.path.dirname(__file__), 'prompts')) if f.endswith('.json'))}"
        )
        sys.exit(1)

    with open(prompt_file, encoding="utf-8") as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    print(f"[+] Loaded {len(prompts)} prompts from {sector} pack")
    print(f"    Categories: {', '.join(set(p['category'] for p in prompts))}")
    return prompts


def run_evaluation(
    config: EvaluationConfig, use_judge: bool = False, dry_run: bool = False
):
    """
    Execute a complete evaluation pipeline.

    Args:
        config: EvaluationConfig with all parameters
        use_judge: Whether to use a judge model for enhanced scoring
        dry_run: If True, only show what would be done without making API calls
    """
    print(config.summary())

    # ── Step 1: Load prompts ──
    prompts = load_prompt_pack(config.prompt_pack)

    # ── Step 2: Get model configs ──
    model_configs = config.get_model_configs()
    print(f"\n[+] Models to evaluate:")
    for mc in model_configs:
        print(f"    • {mc.display_name} ({mc.provider}) @ temp={mc.temperature}")

    total_queries = len(prompts) * len(model_configs) * 2  # 2 languages
    print(f"\n[+] Total API calls required: {total_queries}")

    if dry_run:
        print("\n[DRY RUN] Would execute the above evaluation. Exiting.")
        return None

    # ── Step 3: Query models ──
    print("\n" + "=" * 60)
    print("  PHASE 1: Querying models")
    print("=" * 60)

    runner = ModelRunner(model_configs)

    # Build system prompt for evaluation context
    system_prompt = (
        f"You are being evaluated for performance in a {config.sector} context. "
        f"Answer the following question accurately, concisely, and professionally. "
        f"If you are unsure about any facts, say so rather than guessing."
    )

    responses = runner.run_evaluation(
        prompts=prompts,
        model_configs=model_configs,
        system_prompt=system_prompt,
        runs_per_prompt=config.runs_per_prompt,
        progress_callback=print_progress,
    )

    stats = runner.get_stats()
    print(
        f"\n[+] Query complete: {stats['total_responses']} responses, {stats['errors']} errors"
    )
    print(f"    Total tokens: {stats['total_tokens']:,}")
    print(f"    Avg latency: {stats['avg_latency_ms']:.0f}ms")

    # Save raw responses
    os.makedirs(config.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = os.path.join(
        config.output_dir,
        f"{config.client_name.lower().replace(' ', '_')}_{timestamp}_raw.json",
    )
    runner.save_responses(raw_path)

    # ── Step 4: Score responses ──
    print("\n" + "=" * 60)
    print("  PHASE 2: Scoring responses")
    print("=" * 60)

    # Set up judge model if requested
    judge_runner = None
    judge_config = None
    if use_judge:
        from config.builder import ModelConfig

        # Detect provider from judge model name
        judge_model = config.judge_model
        if judge_model.startswith("ollama-"):
            provider = "ollama"
            judge_model = judge_model.replace("ollama-", "")
        elif "claude" in judge_model:
            provider = "anthropic"
        else:
            provider = "openai"

        judge_config = ModelConfig(
            model_id=judge_model,
            display_name="Judge",
            provider=provider,
            temperature=0.1,
            max_tokens=1000,
        )
        judge_runner = ModelRunner([judge_config])
        print(f"[+] Judge model: {judge_model} ({provider})")

    scorer = ScoringEngine(judge_runner, judge_config)

    # Organise responses by prompt and model for scoring
    # Structure: response_map[prompt_id][model_id][language] = response_text
    response_map = {}
    for resp in responses:
        if resp.error:
            continue
        pid = resp.prompt_id
        mid = resp.model_id
        lang = resp.language
        if pid not in response_map:
            response_map[pid] = {}
        if mid not in response_map[pid]:
            response_map[pid][mid] = {}
        response_map[pid][mid][lang] = resp.response_text

    # Build prompt lookup
    prompt_lookup = {p["id"]: p for p in prompts}

    # Score everything
    all_results = []
    total_scoring = len(response_map) * len(model_configs) * 2
    scoring_count = 0

    for prompt_id, models_data in response_map.items():
        prompt_data = prompt_lookup.get(prompt_id, {})
        prompt_result = {
            "prompt_id": prompt_id,
            "category": prompt_data.get("category", ""),
            "prompt_en": prompt_data.get("en", ""),
            "prompt_ar": prompt_data.get("ar", ""),
            "model_scores": {},
        }

        for model_id, lang_responses in models_data.items():
            prompt_result["model_scores"][model_id] = {}

            en_response = lang_responses.get("en", "")
            ar_response = lang_responses.get("ar", "")

            for lang, response_text in lang_responses.items():
                scoring_count += 1
                print(
                    f"\r  Scoring {scoring_count}/{total_scoring}: {model_id} | {lang.upper()} | {prompt_id}",
                    end="",
                    flush=True,
                )

                scores = scorer.score_response(
                    response_text=response_text,
                    language=lang,
                    prompt_data=prompt_data,
                    en_response=en_response if lang == "ar" else None,
                    use_judge=use_judge,
                )

                prompt_result["model_scores"][model_id][lang] = {
                    "response": response_text,
                    "scores": [
                        {
                            "dimension": s.dimension,
                            "score": s.score,
                            "severity": s.severity,
                            "flags": s.flags,
                            "details": s.details,
                        }
                        for s in scores
                    ],
                }

        all_results.append(prompt_result)

    print()  # newline after progress

    # ── Step 5: Calculate aggregates ──
    print("\n" + "=" * 60)
    print("  PHASE 3: Calculating aggregates")
    print("=" * 60)

    aggregates = calculate_aggregates(
        all_results, [mc.model_id for mc in model_configs]
    )

    # ── Step 6: Save results ──
    results_path = os.path.join(
        config.output_dir,
        f"{config.client_name.lower().replace(' ', '_')}_{timestamp}_results.json",
    )

    final_output = {
        "metadata": {
            "client_name": config.client_name,
            "sector": config.sector,
            "use_case": config.use_case,
            "models": config.models,
            "dimensions": config.dimensions,
            "prompt_pack": config.prompt_pack,
            "total_prompts": len(prompts),
            "judge_model": config.judge_model if use_judge else None,
            "timestamp": datetime.now().isoformat(),
            "version": config.version,
        },
        "aggregates": aggregates,
        "detailed_results": all_results,
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Results saved to {results_path}")
    print_summary(aggregates)

    return final_output


def calculate_aggregates(results: list, model_ids: list) -> dict:
    """Calculate aggregate scores across all prompts for each model and dimension."""
    agg = {}

    for model_id in model_ids:
        agg[model_id] = {"en": {}, "ar": {}, "cross_lingual_gap": {}}

        for lang in ["en", "ar"]:
            dimension_scores = {}  # dimension -> [scores]

            for result in results:
                model_data = result.get("model_scores", {}).get(model_id, {})
                lang_data = model_data.get(lang, {})

                for score_entry in lang_data.get("scores", []):
                    dim = score_entry["dimension"]
                    if dim not in dimension_scores:
                        dimension_scores[dim] = []
                    dimension_scores[dim].append(score_entry["score"])

            # Calculate averages
            for dim, scores_list in dimension_scores.items():
                if scores_list:
                    avg = round(sum(scores_list) / len(scores_list), 1)
                    agg[model_id][lang][dim] = {
                        "average": avg,
                        "min": min(scores_list),
                        "max": max(scores_list),
                        "count": len(scores_list),
                    }

        # Calculate cross-lingual gaps
        for dim in agg[model_id]["en"]:
            if dim in agg[model_id]["ar"]:
                en_avg = agg[model_id]["en"][dim]["average"]
                ar_avg = agg[model_id]["ar"][dim]["average"]
                gap = round(abs(en_avg - ar_avg), 1)
                agg[model_id]["cross_lingual_gap"][dim] = {
                    "gap": gap,
                    "en_avg": en_avg,
                    "ar_avg": ar_avg,
                    "severity": (
                        "critical"
                        if gap > 20
                        else "high" if gap > 12 else "medium" if gap > 6 else "low"
                    ),
                }

    return agg


def print_summary(aggregates: dict):
    """Print a formatted summary of evaluation results."""
    print("\n" + "=" * 60)
    print("  EVALUATION SUMMARY")
    print("=" * 60)

    for model_id, data in aggregates.items():
        print(f"\n  Model: {model_id}")
        print(f"  {'─' * 50}")

        for dim in data.get("en", {}):
            en_score = data["en"].get(dim, {}).get("average", "N/A")
            ar_score = data["ar"].get(dim, {}).get("average", "N/A")
            gap_data = data.get("cross_lingual_gap", {}).get(dim, {})
            gap = gap_data.get("gap", "N/A")
            severity = gap_data.get("severity", "")

            en_str = (
                f"{en_score:>5.1f}%"
                if isinstance(en_score, (int, float))
                else f"{en_score:>6}"
            )
            ar_str = (
                f"{ar_score:>5.1f}%"
                if isinstance(ar_score, (int, float))
                else f"{ar_score:>6}"
            )
            gap_str = f"{gap:>5.1f}%" if isinstance(gap, (int, float)) else f"{gap:>6}"

            print(
                f"    {dim:<25} EN: {en_str}  AR: {ar_str}  Gap: {gap_str}  [{severity}]"
            )

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="LinguaEval Evaluation Runner")
    parser.add_argument("--config", type=str, help="Path to evaluation config YAML")
    parser.add_argument(
        "--preset",
        type=str,
        choices=["university", "government", "finance"],
        help="Use a preset configuration",
    )
    parser.add_argument(
        "--client", type=str, default="Test Client", help="Client name (with --preset)"
    )
    parser.add_argument(
        "--prompt-pack",
        type=str,
        help="Prompt pack to use (e.g., university, government)",
    )
    parser.add_argument(
        "--model",
        type=str,
        action="append",
        dest="models",
        help="Model to evaluate (can be used multiple times)",
    )
    parser.add_argument(
        "--use-judge", action="store_true", help="Use judge model for enhanced scoring"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show plan without making API calls"
    )

    args = parser.parse_args()

    if args.config:
        config = EvaluationConfig.load(args.config)
    elif args.preset:
        presets = {
            "university": preset_university,
            "government": preset_government,
            "finance": preset_finance,
        }
        config = presets[args.preset]()
        config.client_name = args.client
    else:
        print("Usage: python run_evaluation.py --config <path> OR --preset <type>")
        print(
            "       python run_evaluation.py --preset government --client 'SDAIA' --dry-run"
        )
        print(
            "       python run_evaluation.py --preset university --prompt-pack university --model llama3.1:latest --model gemma3:27b"
        )
        sys.exit(1)

    # Override prompt pack if specified
    if args.prompt_pack:
        config.prompt_pack = args.prompt_pack

    # Override models if specified
    if args.models:
        config.models = args.models

    run_evaluation(config, use_judge=args.use_judge, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
