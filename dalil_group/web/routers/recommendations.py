#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recommendations Router
======================

API routes for recommendation generation and retrieval.
"""

import logging
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Depends
from sqlalchemy.orm import Session

from database import SessionLocal, get_evaluation, create_recommendation, get_recommendations_for_evaluation
from web.schemas import RecommendationResponse
from scoring.recommendations import recommendation_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/generate/{eval_id}", response_model=List[RecommendationResponse])
async def generate_recommendations(
    eval_id: int = Path(..., description="Evaluation ID"),
    language: str = Query("en", description="Language code (en, ar, etc.)"),
    db: Session = Depends(get_db)
) -> List[RecommendationResponse]:
    """
    Generate recommendations for an evaluation.
    
    Analyzes evaluation results across all dimensions and generates
    actionable recommendations based on the scores.
    
    Args:
        eval_id: ID of the evaluation
        language: Language to analyze (default: en)
        
    Returns:
        List of recommendations with action items and severity levels
    """
    try:
        # Get evaluation
        eval_record = get_evaluation(db, eval_id)
        if not eval_record:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Extract scores from prompt results
        from database import get_prompt_results_for_evaluation
        
        prompt_results = get_prompt_results_for_evaluation(db, eval_id)
        if not prompt_results:
            raise HTTPException(
                status_code=400,
                detail="No evaluation results found. Run evaluation first."
            )
        
        # Build scores dictionary
        scores = {}
        for result in prompt_results:
            scores_dict = result.scores if hasattr(result, 'scores') else {}
            for dimension, score_info in scores_dict.items():
                if dimension not in scores:
                    scores[dimension] = {}
                scores[dimension][language] = score_info.get("score", 0)
        
        # Generate recommendations
        model_name = eval_record.models[0] if eval_record.models else "unknown"
        context = {
            "sector": eval_record.sector if hasattr(eval_record, 'sector') else None,
            "prompt_pack": eval_record.prompt_pack if hasattr(eval_record, 'prompt_pack') else None,
        }
        
        recommendations = recommendation_engine.generate_recommendations(
            scores=scores,
            model_name=model_name,
            language=language,
            context=context
        )
        
        # Save recommendations to database
        saved_recommendations = []
        for rec in recommendations:
            db_rec = create_recommendation(
                db,
                evaluation_id=eval_id,
                recommendation_type=rec.recommendation_type,
                title=rec.title,
                description=rec.description,
                severity=rec.severity.value,
                action_items=rec.action_items,
                estimated_effort="medium",  # TODO: calculate based on recommendation
                related_prompts=[]
            )
            saved_recommendations.append(db_rec)
        
        logger.info(f"Generated {len(saved_recommendations)} recommendations for evaluation {eval_id}")
        
        # Convert to response models
        return [
            RecommendationResponse(
                id=rec.id,
                recommendation_type=rec.recommendation_type,
                title=rec.title,
                description=rec.description,
                severity=rec.severity,
                action_items=rec.action_items_json and json.loads(rec.action_items_json) or [],
                estimated_effort=rec.estimated_effort or "medium",
                related_prompts=rec.related_prompts_json and json.loads(rec.related_prompts_json) or []
            )
            for rec in saved_recommendations
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{eval_id}", response_model=List[RecommendationResponse])
async def get_recommendations(
    eval_id: int = Path(..., description="Evaluation ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    rec_type: Optional[str] = Query(None, description="Filter by recommendation type"),
    db: Session = Depends(get_db)
) -> List[RecommendationResponse]:
    """
    Get recommendations for an evaluation.
    
    Retrieves previously generated recommendations, with optional filtering
    by severity level or recommendation type.
    
    Args:
        eval_id: ID of the evaluation
        severity: Optional severity filter
        rec_type: Optional recommendation type filter
        
    Returns:
        List of recommendations
    """
    try:
        # Verify evaluation exists
        eval_record = get_evaluation(db, eval_id)
        if not eval_record:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Get recommendations
        recommendations = get_recommendations_for_evaluation(db, eval_id)
        
        # Apply filters
        if severity:
            recommendations = [r for r in recommendations if r.severity == severity]
        
        if rec_type:
            recommendations = [r for r in recommendations if r.recommendation_type == rec_type]
        
        logger.info(f"Retrieved {len(recommendations)} recommendations for evaluation {eval_id}")
        
        # Convert to response models
        return [
            RecommendationResponse(
                id=rec.id,
                recommendation_type=rec.recommendation_type,
                title=rec.title,
                description=rec.description,
                severity=rec.severity,
                action_items=rec.action_items_json and json.loads(rec.action_items_json) or [],
                estimated_effort=rec.estimated_effort or "medium",
                related_prompts=rec.related_prompts_json and json.loads(rec.related_prompts_json) or []
            )
            for rec in recommendations
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
