#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recommendation Engine
====================

Generates AI-powered recommendations based on evaluation results.
Analyzes scores across dimensions to identify patterns and suggest improvements.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RecommendationSeverity(str, Enum):
    """Severity levels for recommendations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Recommendation:
    """A single recommendation with context."""
    recommendation_type: str
    title: str
    description: str
    severity: RecommendationSeverity
    action_items: List[str]
    affected_dimensions: List[str]
    metric_value: float  # Score/percentage related to this recommendation


class RecommendationEngine:
    """
    Generates recommendations based on evaluation results.
    
    Analyzes patterns across:
    - Accuracy issues
    - Bias detection
    - Hallucination frequency
    - Consistency problems
    - Cultural sensitivity gaps
    - Language fluency issues
    """
    
    def __init__(self):
        """Initialize the recommendation engine."""
        self.thresholds = {
            "accuracy": 70,
            "bias": 20,
            "hallucination": 15,
            "consistency": 75,
            "cultural": 65,
            "fluency": 70,
        }
    
    def generate_recommendations(
        self,
        scores: Dict[str, Dict[str, float]],
        model_name: str = "unknown",
        language: str = "en",
        context: Optional[Dict] = None,
    ) -> List[Recommendation]:
        """
        Generate recommendations based on evaluation scores.
        
        Args:
            scores: Dictionary with dimension -> {language -> score}
            model_name: Name of the model being evaluated
            language: Language code (en, ar, etc.)
            context: Additional context (sector, use case, etc.)
        
        Returns:
            List of recommendations sorted by severity
        """
        recommendations = []
        language_scores = self._extract_scores(scores, language)
        
        # Analyze each dimension
        if language_scores["accuracy"] < self.thresholds["accuracy"]:
            recommendations.extend(
                self._generate_accuracy_recommendations(
                    language_scores["accuracy"],
                    model_name,
                    context
                )
            )
        
        if language_scores["bias"] > self.thresholds["bias"]:
            recommendations.extend(
                self._generate_bias_recommendations(
                    language_scores["bias"],
                    model_name,
                    context
                )
            )
        
        if language_scores["hallucination"] > self.thresholds["hallucination"]:
            recommendations.extend(
                self._generate_hallucination_recommendations(
                    language_scores["hallucination"],
                    model_name,
                    context
                )
            )
        
        if language_scores["consistency"] < self.thresholds["consistency"]:
            recommendations.extend(
                self._generate_consistency_recommendations(
                    language_scores["consistency"],
                    model_name,
                    context
                )
            )
        
        if language_scores["cultural"] < self.thresholds["cultural"]:
            recommendations.extend(
                self._generate_cultural_recommendations(
                    language_scores["cultural"],
                    model_name,
                    context
                )
            )
        
        if language_scores["fluency"] < self.thresholds["fluency"]:
            recommendations.extend(
                self._generate_fluency_recommendations(
                    language_scores["fluency"],
                    model_name,
                    context
                )
            )
        
        # Cross-dimensional analysis
        recommendations.extend(
            self._generate_cross_dimensional_recommendations(
                language_scores,
                model_name,
                context
            )
        )
        
        # Sort by severity (critical -> low)
        severity_order = {
            RecommendationSeverity.CRITICAL: 0,
            RecommendationSeverity.HIGH: 1,
            RecommendationSeverity.MEDIUM: 2,
            RecommendationSeverity.LOW: 3,
        }
        
        recommendations.sort(
            key=lambda r: severity_order.get(r.severity, 4)
        )
        
        logger.info(f"Generated {len(recommendations)} recommendations for {model_name}")
        return recommendations
    
    def _extract_scores(self, scores: Dict, language: str) -> Dict[str, float]:
        """Extract scores for a specific language."""
        extracted = {}
        for dimension, lang_scores in scores.items():
            if isinstance(lang_scores, dict):
                extracted[dimension] = lang_scores.get(language, lang_scores.get("en", 50))
            else:
                extracted[dimension] = lang_scores
        
        # Ensure all dimensions exist
        for dim in self.thresholds.keys():
            if dim not in extracted:
                extracted[dim] = 50
        
        return extracted
    
    def _generate_accuracy_recommendations(
        self,
        score: float,
        model_name: str,
        context: Optional[Dict]
    ) -> List[Recommendation]:
        """Generate accuracy-related recommendations."""
        recommendations = []
        
        if score < 50:
            severity = RecommendationSeverity.CRITICAL
            action_items = [
                "Review model training data for quality and relevance",
                "Evaluate model against ground truth datasets",
                "Consider model retraining with higher quality data",
                "Test with domain-specific evaluation sets",
                "Compare performance with baseline models"
            ]
            title = "Critical Accuracy Issues Detected"
        elif score < 60:
            severity = RecommendationSeverity.HIGH
            action_items = [
                "Conduct error analysis to identify failure patterns",
                "Augment training data with hard examples",
                "Fine-tune model on domain-specific data",
                "Review preprocessing steps for data quality issues"
            ]
            title = "Significant Accuracy Gaps"
        elif score < self.thresholds["accuracy"]:
            severity = RecommendationSeverity.MEDIUM
            action_items = [
                "Analyze false positive/negative patterns",
                "Consider ensemble methods with other models",
                "Evaluate training set balance and representation"
            ]
            title = "Moderate Accuracy Improvement Needed"
        else:
            return recommendations
        
        recommendations.append(Recommendation(
            recommendation_type="accuracy",
            title=title,
            description=f"Model accuracy score: {score:.1f}%. Target: {self.thresholds['accuracy']}%",
            severity=severity,
            action_items=action_items,
            affected_dimensions=["accuracy"],
            metric_value=score
        ))
        
        return recommendations
    
    def _generate_bias_recommendations(
        self,
        score: float,
        model_name: str,
        context: Optional[Dict]
    ) -> List[Recommendation]:
        """Generate bias-related recommendations."""
        recommendations = []
        
        if score > 40:
            severity = RecommendationSeverity.CRITICAL
            action_items = [
                "Immediately audit for protected attributes (gender, race, age, etc.)",
                "Implement fairness constraints in model training",
                "Conduct intersectional bias analysis",
                "Establish bias monitoring in production",
                "Review training data for historical bias"
            ]
            title = "Critical Bias Issues Found"
        elif score > 30:
            severity = RecommendationSeverity.HIGH
            action_items = [
                "Perform comprehensive fairness evaluation",
                "Implement bias detection in preprocessing",
                "Use fairness-aware training techniques",
                "Establish demographic parity checks"
            ]
            title = "Significant Bias Detected"
        elif score > self.thresholds["bias"]:
            severity = RecommendationSeverity.MEDIUM
            action_items = [
                "Monitor specific demographic groups",
                "Consider debiasing techniques",
                "Increase diversity in training data"
            ]
            title = "Moderate Bias Concerns"
        else:
            return recommendations
        
        recommendations.append(Recommendation(
            recommendation_type="bias",
            title=title,
            description=f"Bias score: {score:.1f}%. Target: Below {self.thresholds['bias']}%",
            severity=severity,
            action_items=action_items,
            affected_dimensions=["bias"],
            metric_value=score
        ))
        
        return recommendations
    
    def _generate_hallucination_recommendations(
        self,
        score: float,
        model_name: str,
        context: Optional[Dict]
    ) -> List[Recommendation]:
        """Generate hallucination-related recommendations."""
        recommendations = []
        
        if score > 30:
            severity = RecommendationSeverity.CRITICAL
            action_items = [
                "Review model promptness and constraint handling",
                "Implement confidence scoring and uncertainty quantification",
                "Add retrieval-augmented generation (RAG) if applicable",
                "Reduce model temperature/creativity settings",
                "Add fact-checking and validation layers"
            ]
            title = "Severe Hallucination Problems"
        elif score > 20:
            severity = RecommendationSeverity.HIGH
            action_items = [
                "Add grounding mechanisms to model output",
                "Implement source attribution requirements",
                "Use prompt engineering to reduce false claims",
                "Add knowledge base validation"
            ]
            title = "Frequent Hallucinations Observed"
        elif score > self.thresholds["hallucination"]:
            severity = RecommendationSeverity.MEDIUM
            action_items = [
                "Monitor specific types of hallucinations",
                "Add optional verification steps",
                "Consider more conservative decoding parameters"
            ]
            title = "Occasional Hallucinations"
        else:
            return recommendations
        
        recommendations.append(Recommendation(
            recommendation_type="hallucination",
            title=title,
            description=f"Hallucination rate: {score:.1f}%. Target: Below {self.thresholds['hallucination']}%",
            severity=severity,
            action_items=action_items,
            affected_dimensions=["hallucination"],
            metric_value=score
        ))
        
        return recommendations
    
    def _generate_consistency_recommendations(
        self,
        score: float,
        model_name: str,
        context: Optional[Dict]
    ) -> List[Recommendation]:
        """Generate consistency-related recommendations."""
        recommendations = []
        
        if score < 50:
            severity = RecommendationSeverity.CRITICAL
            action_items = [
                "Review model training for data variability issues",
                "Implement version control for model consistency",
                "Test with repeated inputs to verify stability",
                "Consider ensemble methods for more stable outputs",
                "Investigate random seed and initialization effects"
            ]
            title = "Severe Inconsistency Issues"
        elif score < 65:
            severity = RecommendationSeverity.HIGH
            action_items = [
                "Standardize preprocessing and postprocessing",
                "Implement consistency checkpoints",
                "Review temperature/sampling parameters",
                "Test across input variations systematically"
            ]
            title = "Significant Consistency Problems"
        elif score < self.thresholds["consistency"]:
            severity = RecommendationSeverity.MEDIUM
            action_items = [
                "Monitor consistency metrics over time",
                "Standardize input formatting",
                "Consider additional regularization"
            ]
            title = "Minor Consistency Gaps"
        else:
            return recommendations
        
        recommendations.append(Recommendation(
            recommendation_type="consistency",
            title=title,
            description=f"Consistency score: {score:.1f}%. Target: {self.thresholds['consistency']}%",
            severity=severity,
            action_items=action_items,
            affected_dimensions=["consistency"],
            metric_value=score
        ))
        
        return recommendations
    
    def _generate_cultural_recommendations(
        self,
        score: float,
        model_name: str,
        context: Optional[Dict]
    ) -> List[Recommendation]:
        """Generate cultural sensitivity recommendations."""
        recommendations = []
        
        if score < 50:
            severity = RecommendationSeverity.HIGH
            action_items = [
                "Partner with cultural domain experts for review",
                "Audit for stereotypical or offensive content",
                "Expand training data with culturally diverse examples",
                "Establish cultural sensitivity guidelines",
                "Implement cultural bias detection in content filtering"
            ]
            title = "Critical Cultural Sensitivity Issues"
        elif score < 65:
            severity = RecommendationSeverity.MEDIUM
            action_items = [
                "Review content for cultural appropriateness",
                "Add cultural context to training examples",
                "Increase diversity in evaluation sets",
                "Consult with cultural advisors"
            ]
            title = "Cultural Sensitivity Needs Improvement"
        elif score < self.thresholds["cultural"]:
            severity = RecommendationSeverity.LOW
            action_items = [
                "Monitor for cultural sensitivity edge cases",
                "Continue expanding cultural representation in data"
            ]
            title = "Minor Cultural Adjustments Recommended"
        else:
            return recommendations
        
        recommendations.append(Recommendation(
            recommendation_type="cultural",
            title=title,
            description=f"Cultural sensitivity score: {score:.1f}%. Target: {self.thresholds['cultural']}%",
            severity=severity,
            action_items=action_items,
            affected_dimensions=["cultural"],
            metric_value=score
        ))
        
        return recommendations
    
    def _generate_fluency_recommendations(
        self,
        score: float,
        model_name: str,
        context: Optional[Dict]
    ) -> List[Recommendation]:
        """Generate fluency-related recommendations."""
        recommendations = []
        
        if score < 50:
            severity = RecommendationSeverity.HIGH
            action_items = [
                "Review language model for fluency training",
                "Increase exposure to well-formed text in training",
                "Tune decoding parameters for quality",
                "Implement post-processing for grammatical corrections",
                "Consider using a stronger base language model"
            ]
            title = "Severe Language Fluency Issues"
        elif score < 65:
            severity = RecommendationSeverity.MEDIUM
            action_items = [
                "Improve text generation quality scoring",
                "Add fluency constraints to decoding",
                "Review grammatical error patterns",
                "Enhance with language-specific models if needed"
            ]
            title = "Language Fluency Needs Work"
        elif score < self.thresholds["fluency"]:
            severity = RecommendationSeverity.LOW
            action_items = [
                "Monitor specific fluency issues",
                "Collect examples of non-fluent outputs for analysis"
            ]
            title = "Minor Fluency Adjustments"
        else:
            return recommendations
        
        recommendations.append(Recommendation(
            recommendation_type="fluency",
            title=title,
            description=f"Fluency score: {score:.1f}%. Target: {self.thresholds['fluency']}%",
            severity=severity,
            action_items=action_items,
            affected_dimensions=["fluency"],
            metric_value=score
        ))
        
        return recommendations
    
    def _generate_cross_dimensional_recommendations(
        self,
        scores: Dict[str, float],
        model_name: str,
        context: Optional[Dict]
    ) -> List[Recommendation]:
        """Generate recommendations based on cross-dimensional patterns."""
        recommendations = []
        
        # Check for systemic issues across multiple dimensions
        low_dimensions = [
            dim for dim, score in scores.items()
            if score < self.thresholds.get(dim, 70)
        ]
        
        if len(low_dimensions) >= 4:
            recommendations.append(Recommendation(
                recommendation_type="model_quality",
                title="Systemic Model Quality Issues",
                description=f"Poor performance across {len(low_dimensions)} dimensions suggests fundamental model issues",
                severity=RecommendationSeverity.CRITICAL,
                action_items=[
                    "Consider model retraining from scratch",
                    "Evaluate model architecture suitability for task",
                    "Review training data quality comprehensively",
                    "Compare against baseline and SOTA models",
                    "Consider using a completely different model approach"
                ],
                affected_dimensions=low_dimensions,
                metric_value=sum(scores.values()) / len(scores)
            ))
        elif len(low_dimensions) >= 2:
            recommendations.append(Recommendation(
                recommendation_type="model_improvement",
                title="Multiple Dimension Improvements Needed",
                description=f"Performance gaps in {', '.join(low_dimensions)}",
                severity=RecommendationSeverity.HIGH,
                action_items=[
                    "Prioritize improvements in weakest dimensions",
                    "Investigate if issues are related (shared root cause)",
                    "Consider targeted fine-tuning approaches",
                    "Implement comprehensive monitoring across dimensions"
                ],
                affected_dimensions=low_dimensions,
                metric_value=sum(scores.values()) / len(scores)
            ))
        
        # Identify strengths to leverage
        strong_dimensions = [
            dim for dim, score in scores.items()
            if score >= self.thresholds.get(dim, 70)
        ]
        
        if strong_dimensions:
            recommendations.append(Recommendation(
                recommendation_type="deployment_guidance",
                title="Deployment and Use Case Optimization",
                description=f"Model shows strength in {', '.join(strong_dimensions)}",
                severity=RecommendationSeverity.LOW,
                action_items=[
                    f"Focus deployment on use cases emphasizing: {', '.join(strong_dimensions)}",
                    "Establish monitoring for weaker dimensions in production",
                    "Consider ensemble approaches combining this model with others",
                    "Document model strengths and limitations in user documentation"
                ],
                affected_dimensions=strong_dimensions,
                metric_value=sum([scores[d] for d in strong_dimensions]) / len(strong_dimensions) if strong_dimensions else 0
            ))
        
        return recommendations


# Singleton instance
recommendation_engine = RecommendationEngine()
