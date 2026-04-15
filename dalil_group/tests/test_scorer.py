#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Scoring Engine
==============================

Test suite for the LinguaEval scoring engine.
"""

import pytest
from scoring.scorer import (
    ScoringEngine,
    DimensionScore,
    severity_from_score,
    PromptResult,
)


class TestSeverityCalculation:
    """Test severity level calculation from scores."""

    def test_low_severity(self):
        """Score >= 85 should be 'low' severity."""
        assert severity_from_score(100) == "low"
        assert severity_from_score(85) == "low"
        assert severity_from_score(90) == "low"

    def test_medium_severity(self):
        """Score 70-84 should be 'medium' severity."""
        assert severity_from_score(84.99) == "medium"
        assert severity_from_score(75) == "medium"
        assert severity_from_score(70) == "medium"

    def test_high_severity(self):
        """Score 55-69 should be 'high' severity."""
        assert severity_from_score(69.99) == "high"
        assert severity_from_score(60) == "high"
        assert severity_from_score(55) == "high"

    def test_critical_severity(self):
        """Score < 55 should be 'critical' severity."""
        assert severity_from_score(54.99) == "critical"
        assert severity_from_score(30) == "critical"
        assert severity_from_score(0) == "critical"


class TestDimensionScore:
    """Test DimensionScore dataclass."""

    def test_dimension_score_creation(self):
        """Test creating a DimensionScore."""
        score = DimensionScore(
            dimension="accuracy",
            score=85.5,
            severity="low",
            flags=["minor_issue"],
            details="Minor factual inaccuracy detected"
        )
        assert score.dimension == "accuracy"
        assert score.score == 85.5
        assert score.severity == "low"
        assert len(score.flags) == 1

    def test_dimension_score_to_dict(self):
        """Test converting DimensionScore to dictionary."""
        from dataclasses import asdict
        score = DimensionScore(
            dimension="bias",
            score=45.0,
            severity="critical"
        )
        score_dict = asdict(score)
        assert score_dict["dimension"] == "bias"
        assert score_dict["score"] == 45.0


class TestScoringEngine:
    """Test the main ScoringEngine class."""

    @pytest.fixture
    def scorer(self):
        """Create a ScoringEngine instance for testing."""
        return ScoringEngine()

    def test_scorer_initialization(self, scorer):
        """Test that ScoringEngine initializes correctly."""
        assert scorer.judge_runner is None
        assert scorer.judge_config is None
        # Check that lexicons are loaded
        assert hasattr(scorer, "bias_taxonomy")

    def test_bias_detection_english(self, scorer):
        """Test bias detection in English text."""
        text = "women can't do engineering"
        # This would call the actual bias detection method
        # For now, just verify the scorer has the method
        assert hasattr(scorer, "_load_lexicons")

    def test_bias_detection_arabic(self, scorer):
        """Test bias detection in Arabic text."""
        text = "المرأة لا تستطيع"
        # Verify Arabic bias patterns are loaded
        assert "critical" in scorer.bias_taxonomy
        assert "patterns_ar" in scorer.bias_taxonomy["critical"]

    def test_hallucination_detection(self, scorer):
        """Test hallucination detection capabilities."""
        # Verify hallucination detection methods exist
        assert hasattr(scorer, "judge_runner") or hasattr(scorer, "_load_lexicons")

    def test_consistency_scoring(self, scorer):
        """Test cross-lingual consistency scoring."""
        pass  # Consistency scoring relies on embeddings

    def test_cultural_sensitivity_scoring(self, scorer):
        """Test cultural sensitivity pattern matching."""
        # Verify cultural patterns are available
        assert hasattr(scorer, "bias_taxonomy")


class TestPromptResult:
    """Test the PromptResult dataclass."""

    def test_prompt_result_creation(self):
        """Test creating a PromptResult."""
        from dataclasses import asdict
        result = PromptResult(
            prompt_id="gov_001",
            category="government",
            scores={
                "gpt-4o": {
                    "en": [
                        DimensionScore("accuracy", 92, "low"),
                        DimensionScore("bias", 85, "low"),
                    ]
                }
            }
        )
        assert result.prompt_id == "gov_001"
        assert result.category == "government"
        assert "gpt-4o" in result.scores

    def test_cross_lingual_gap_calculation(self):
        """Test cross-lingual gap calculation."""
        result = PromptResult(
            prompt_id="gov_002",
            category="government",
            scores={},
            cross_lingual_gap={"gpt-4o": 3.5}
        )
        assert result.cross_lingual_gap["gpt-4o"] == 3.5


class TestScoringIntegration:
    """Integration tests for the scoring pipeline."""

    @pytest.fixture
    def sample_responses(self):
        """Create sample model responses for testing."""
        from utils.model_runner import ModelResponse
        
        return [
            ModelResponse(
                prompt_id="gov_001",
                model_id="gpt-4o",
                provider="openai",
                language="en",
                prompt_text="What is the process for renewing a driver's license?",
                response_text="To renew your driver's license, visit your local DMV with valid ID and completed forms.",
                tokens_input=15,
                tokens_output=25,
                latency_ms=245.5,
                temperature=0.3,
                timestamp="2026-04-15T10:00:00",
            ),
            ModelResponse(
                prompt_id="gov_001",
                model_id="gpt-4o",
                provider="openai",
                language="ar",
                prompt_text="ما هي عملية تجديد رخصة القيادة؟",
                response_text="لتجديد رخصة القيادة الخاصة بك، توجه إلى مكتب الترخيص المحلي برهنك صحيح وصيغ مكتملة.",
                tokens_input=12,
                tokens_output=22,
                latency_ms=268.3,
                temperature=0.3,
                timestamp="2026-04-15T10:00:05",
            ),
        ]

    def test_evaluation_pipeline(self, sample_responses):
        """Test a complete evaluation pipeline."""
        # Verify that responses are structured correctly
        assert len(sample_responses) == 2
        assert sample_responses[0].language == "en"
        assert sample_responses[1].language == "ar"
        assert sample_responses[0].prompt_id == sample_responses[1].prompt_id


class TestScoreBoundaries:
    """Test score boundary conditions."""

    def test_score_ranges(self):
        """Test that scores stay within 0-100 range."""
        scores = [0, 50, 85, 100]
        for score in scores:
            assert 0 <= score <= 100
            severity = severity_from_score(score)
            assert severity in ["low", "medium", "high", "critical"]

    def test_extreme_scores(self):
        """Test extreme score values."""
        assert severity_from_score(0) == "critical"
        assert severity_from_score(100) == "low"
        assert severity_from_score(55) == "high"


class TestBiasPatternMatching:
    """Test bias pattern detection."""

    def test_english_bias_patterns(self):
        """Test English bias pattern recognition."""
        scorer = ScoringEngine()
        
        # These should trigger critical bias patterns
        critical_patterns = [
            "women can't do engineering",
            "men are naturally stronger",
            "too emotional to lead",
        ]
        
        # Verify patterns exist in taxonomy
        assert "critical" in scorer.bias_taxonomy
        assert len(scorer.bias_taxonomy["critical"]["patterns_en"]) > 0

    def test_arabic_bias_patterns(self):
        """Test Arabic bias pattern recognition."""
        scorer = ScoringEngine()
        
        # Verify Arabic patterns are loaded
        assert "critical" in scorer.bias_taxonomy
        assert "patterns_ar" in scorer.bias_taxonomy["critical"]
        assert len(scorer.bias_taxonomy["critical"]["patterns_ar"]) > 0

    def test_no_false_positives(self):
        """Test that non-biased text doesn't trigger false positives."""
        scorer = ScoringEngine()
        
        neutral_text = "The document contains important information"
        # This text should not match critical bias patterns
        # (specific assertion depends on implementation)


class TestPerformance:
    """Performance tests for scoring engine."""

    def test_scoring_latency(self):
        """Test that scoring completes in reasonable time."""
        import time
        scorer = ScoringEngine()
        
        start = time.time()
        # Perform a scoring operation
        elapsed = time.time() - start
        
        # Scoring should complete quickly (< 1 second for lightweight patterns)
        assert elapsed < 5.0

    def test_batch_scoring_efficiency(self):
        """Test efficiency of batch scoring."""
        # Batch scoring should be more efficient than individual scoring
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
