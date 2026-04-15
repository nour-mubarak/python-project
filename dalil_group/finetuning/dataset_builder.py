#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fine-tuning Dataset Builder
============================

Build training datasets for model fine-tuning from evaluation results.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TrainingExample:
    """Single training example for fine-tuning."""

    prompt: str
    completion: str
    language: str
    category: str
    quality_score: float  # 0-100
    metadata: Dict[str, Any]


class DatasetBuilder:
    """
    Build fine-tuning datasets from evaluation results.

    Features:
    - Extract high-quality responses from evaluations
    - Generate instruction-following examples
    - Balance dataset across languages/sectors
    - Export in multiple formats (JSONL, CSV, Parquet)
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()
        self.examples: List[TrainingExample] = []

    def add_example(
        self,
        prompt: str,
        completion: str,
        language: str = "en",
        category: str = "general",
        quality_score: float = 100.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a training example to the dataset."""
        example = TrainingExample(
            prompt=prompt,
            completion=completion,
            language=language,
            category=category,
            quality_score=quality_score,
            metadata=metadata or {},
        )
        self.examples.append(example)

    def add_from_evaluation_results(
        self,
        results_file: str,
        min_quality_score: float = 75.0,
    ) -> int:
        """
        Import training examples from evaluation results.

        Args:
            results_file: Path to evaluation results JSON file
            min_quality_score: Minimum quality score to include

        Returns:
            Number of examples added
        """
        if not os.path.exists(results_file):
            raise FileNotFoundError(f"Results file not found: {results_file}")

        with open(results_file, "r", encoding="utf-8") as f:
            results = json.load(f)

        added_count = 0

        for prompt_result in results.get("prompt_results", []):
            prompt_id = prompt_result.get("prompt_id")
            category = prompt_result.get("category", "general")

            # Extract responses by model and language
            responses = prompt_result.get("responses", {})

            for model_id, model_responses in responses.items():
                for language, response_data in model_responses.items():
                    if isinstance(response_data, dict):
                        response_text = response_data.get("text", "")
                        scores = response_data.get("scores", [])
                    else:
                        response_text = response_data
                        scores = []

                    # Calculate quality score from dimension scores
                    quality_score = self._calculate_quality_score(scores)

                    if quality_score >= min_quality_score:
                        prompt_text = prompt_result.get(language, "")
                        if prompt_text and response_text:
                            self.add_example(
                                prompt=prompt_text,
                                completion=response_text,
                                language=language,
                                category=category,
                                quality_score=quality_score,
                                metadata={
                                    "model": model_id,
                                    "prompt_id": prompt_id,
                                    "source": "evaluation_results",
                                },
                            )
                            added_count += 1

        return added_count

    def _calculate_quality_score(self, scores: List[Dict[str, Any]]) -> float:
        """Calculate average quality score from dimension scores."""
        if not scores:
            return 50.0

        score_values = [s.get("score", 50) for s in scores if isinstance(s, dict)]
        if not score_values:
            return 50.0

        return sum(score_values) / len(score_values)

    def filter_by_quality(self, min_score: float) -> int:
        """Remove examples below minimum quality score."""
        original_count = len(self.examples)
        self.examples = [e for e in self.examples if e.quality_score >= min_score]
        return original_count - len(self.examples)

    def balance_dataset(self, max_per_category: Optional[int] = None) -> Dict[str, int]:
        """
        Balance dataset across categories/languages.

        Returns:
            Dict mapping category to number of examples
        """
        if max_per_category is None:
            # Find category with fewest examples
            from collections import Counter

            categories = Counter(e.category for e in self.examples)
            max_per_category = min(categories.values()) if categories else 10

        balanced = []
        category_counts: Dict[str, int] = {}

        for example in self.examples:
            key = f"{example.category}_{example.language}"
            count = category_counts.get(key, 0)

            if count < max_per_category:
                balanced.append(example)
                category_counts[key] = count + 1

        self.examples = balanced

        # Return count per main category
        result = {}
        for example in self.examples:
            key = example.category
            result[key] = result.get(key, 0) + 1

        return result

    def export_jsonl(self, output_path: str) -> int:
        """
        Export dataset in OpenAI JSONL format.

        Format: {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for example in self.examples:
                record = {
                    "messages": [
                        {"role": "user", "content": example.prompt},
                        {"role": "assistant", "content": example.completion},
                    ]
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return len(self.examples)

    def export_csv(self, output_path: str) -> int:
        """Export dataset as CSV."""
        import csv

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "prompt",
                    "completion",
                    "language",
                    "category",
                    "quality_score",
                ],
            )
            writer.writeheader()

            for example in self.examples:
                writer.writerow(
                    {
                        "prompt": example.prompt,
                        "completion": example.completion,
                        "language": example.language,
                        "category": example.category,
                        "quality_score": example.quality_score,
                    }
                )

        return len(self.examples)

    def export_parquet(self, output_path: str) -> int:
        """Export dataset as Parquet for efficient storage."""
        try:
            import pandas as pd

            data = [asdict(e) for e in self.examples]
            df = pd.DataFrame(data)
            df.to_parquet(output_path, index=False)

            return len(self.examples)
        except ImportError:
            raise ImportError(
                "Pandas required for Parquet export: pip install pandas pyarrow"
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        from collections import Counter

        if not self.examples:
            return {"total": 0, "error": "No examples in dataset"}

        categories = Counter(e.category for e in self.examples)
        languages = Counter(e.language for e in self.examples)
        quality_scores = [e.quality_score for e in self.examples]

        return {
            "total_examples": len(self.examples),
            "by_category": dict(categories),
            "by_language": dict(languages),
            "quality_score_stats": {
                "min": min(quality_scores),
                "max": max(quality_scores),
                "avg": sum(quality_scores) / len(quality_scores),
                "median": sorted(quality_scores)[len(quality_scores) // 2],
            },
        }

    def save_metadata(self, output_path: str) -> None:
        """Save dataset metadata."""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "total_examples": len(self.examples),
            "statistics": self.get_statistics(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
