#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bias Detection Dashboard Routes
================================

REST API endpoints for bias pattern visualization and analytics.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import (
    SessionLocal,
    get_evaluation,
    get_model_responses_for_evaluation,
    get_prompt_results_for_evaluation
)
from scoring.bias_dashboard import bias_dashboard, BiasStatistics, BiasPattern

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bias-dashboard", tags=["bias_dashboard"])


# Pydantic models for responses
class BiasPatternResponse(BaseModel):
    """Single bias pattern response."""
    pattern_type: str
    severity: str
    count: int
    percentage: float
    examples: List[str]
    affected_dimensions: List[str]
    
    class Config:
        from_attributes = True


class BiasStatisticsResponse(BaseModel):
    """Bias statistics response."""
    evaluation_id: int
    model_name: str
    total_responses: int
    biased_responses: int
    bias_rate: float
    gender_bias_rate: float
    age_bias_rate: float
    ethnicity_bias_rate: float
    disability_bias_rate: float
    socioeconomic_bias_rate: float
    top_patterns: List[BiasPatternResponse]
    english_bias_rate: float
    arabic_bias_rate: float
    consistency_score: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        from_attributes = True


class BiasHeatmapPoint(BaseModel):
    """Single point in heatmap."""
    model: str
    dimension: str
    bias_score: float  # 0-100
    count: int


class BiasHeatmapResponse(BaseModel):
    """Heatmap data for visualization."""
    evaluation_id: int
    data_points: List[BiasHeatmapPoint]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class BiasTrendPoint(BaseModel):
    """Single point in trend graph."""
    date: str
    bias_rate: float
    response_count: int


class BiasTrendResponse(BaseModel):
    """Trend data over time."""
    model_name: str
    timeframe: str  # "week", "month", "quarter"
    trend_points: List[BiasTrendPoint]


def get_db():
    """Database dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/stats/{eval_id}", response_model=BiasStatisticsResponse)
async def get_bias_statistics(
    eval_id: int,
    language: Optional[str] = Query("en", description="Analysis language"),
    db: Session = Depends(get_db)
) -> BiasStatisticsResponse:
    """
    Get bias statistics for an evaluation.
    
    Args:
        eval_id: Evaluation ID
        language: Language for analysis (en, ar, etc.)
        db: Database session
        
    Returns:
        BiasStatistics with detected bias patterns
    """
    try:
        # Get evaluation
        evaluation = get_evaluation(db, eval_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Get model responses
        responses = get_model_responses_for_evaluation(db, eval_id)
        if not responses:
            raise HTTPException(status_code=404, detail="No responses found for evaluation")
        
        # Get scores
        results = get_prompt_results_for_evaluation(db, eval_id)
        scores_dict = {}
        for result in results:
            if hasattr(result, 'scores_json') and result.scores_json:
                scores_dict = result.scores_json
                break
        
        # Convert responses to dict format expected by analyzer
        response_dicts = [
            {
                "prompt_id": r.prompt_id,
                "response": r.response_text,
                "language": r.language or language,
                "model": r.model_name if hasattr(r, 'model_name') else evaluation.model_name
            }
            for r in responses
        ]
        
        # Analyze
        stats = bias_dashboard.analyze_evaluation(
            evaluation_id=eval_id,
            model_name=evaluation.model_name,
            model_responses=response_dicts,
            scores=scores_dict
        )
        
        # Convert to response
        return BiasStatisticsResponse(
            evaluation_id=stats.evaluation_id,
            model_name=stats.model_name,
            total_responses=stats.total_responses,
            biased_responses=stats.biased_responses,
            bias_rate=stats.bias_rate,
            gender_bias_rate=stats.gender_bias_rate,
            age_bias_rate=stats.age_bias_rate,
            ethnicity_bias_rate=stats.ethnicity_bias_rate,
            disability_bias_rate=stats.disability_bias_rate,
            socioeconomic_bias_rate=stats.socioeconomic_bias_rate,
            top_patterns=[
                BiasPatternResponse(
                    pattern_type=p.pattern_type,
                    severity=p.severity,
                    count=p.count,
                    percentage=p.percentage,
                    examples=p.examples,
                    affected_dimensions=p.affected_dimensions
                )
                for p in stats.top_patterns
            ],
            english_bias_rate=stats.english_bias_rate,
            arabic_bias_rate=stats.arabic_bias_rate,
            consistency_score=stats.consistency_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing bias for evaluation {eval_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap/{eval_id}", response_model=BiasHeatmapResponse)
async def get_bias_heatmap(
    eval_id: int,
    db: Session = Depends(get_db)
) -> BiasHeatmapResponse:
    """
    Get heatmap data showing bias across dimensions.
    
    Args:
        eval_id: Evaluation ID
        db: Database session
        
    Returns:
        Heatmap data with bias scores per dimension
    """
    try:
        # Get evaluation
        evaluation = get_evaluation(db, eval_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Get model responses
        responses = get_model_responses_for_evaluation(db, eval_id)
        if not responses:
            raise HTTPException(status_code=404, detail="No responses found")
        
        # Get scores
        results = get_prompt_results_for_evaluation(db, eval_id)
        scores_dict = {}
        for result in results:
            if hasattr(result, 'scores_json') and result.scores_json:
                scores_dict = result.scores_json
                break
        
        # Build heatmap data
        data_points = []
        dimensions = ["accuracy", "bias", "hallucination", "consistency", "cultural", "fluency"]
        
        response_count = len(responses)
        
        for dimension in dimensions:
            if dimension in scores_dict:
                scores = scores_dict[dimension]
                if isinstance(scores, dict):
                    # Multi-language scores
                    avg_score = sum(scores.values()) / len(scores) if scores else 0
                elif isinstance(scores, (int, float)):
                    avg_score = scores
                else:
                    avg_score = 0
                
                # Invert bias so high = bad (for red in heatmap)
                if dimension == "bias":
                    bias_visual_score = avg_score  # High bias = high visual score
                else:
                    bias_visual_score = 100 - avg_score  # Low scores in other dims = potential bias
                
                data_points.append(BiasHeatmapPoint(
                    model=evaluation.model_name,
                    dimension=dimension,
                    bias_score=bias_visual_score,
                    count=response_count
                ))
        
        return BiasHeatmapResponse(
            evaluation_id=eval_id,
            data_points=data_points
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating heatmap for {eval_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", response_model=List[BiasTrendResponse])
async def get_bias_trends(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    timeframe: str = Query("month", description="Time period: week, month, quarter"),
    limit: int = Query(30, description="Number of days to include"),
    db: Session = Depends(get_db)
) -> List[BiasTrendResponse]:
    """
    Get bias trends over time.
    
    Args:
        model_name: Optional model filter
        timeframe: Time period for grouping
        limit: Number of data points
        db: Database session
        
    Returns:
        List of trend data for visualization
    """
    try:
        from database import get_all_evaluations
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=limit)
        
        # Get all evaluations and filter by date range
        all_evaluations = get_all_evaluations(db)
        evaluations = [
            e for e in all_evaluations
            if hasattr(e, 'created_at') and start_date <= e.created_at <= end_date
            and (model_name is None or e.model_name == model_name)
        ]
        
        if not evaluations:
            raise HTTPException(status_code=404, detail="No evaluations found in timeframe")
        
        # Group by model and date
        trends_by_model = {}
        
        for evaluation in evaluations:
            model = evaluation.model_name
            
            if model not in trends_by_model:
                trends_by_model[model] = []
            
            # Get responses for this evaluation
            responses = get_model_responses_for_evaluation(db, evaluation.id)
            response_count = len(responses)
            biased_count = sum(1 for r in responses 
                             if bias_dashboard._is_biased({
                                 "response": r.response_text if hasattr(r, 'response_text') else ""
                             }))
            bias_rate = (biased_count / response_count * 100) if response_count > 0 else 0
            
            # Format date based on timeframe
            eval_date = evaluation.created_at if hasattr(evaluation, 'created_at') else datetime.utcnow()
            if timeframe == "week":
                date_key = eval_date.strftime("%Y-W%U")
            elif timeframe == "quarter":
                quarter = (eval_date.month - 1) // 3 + 1
                date_key = f"{eval_date.year}-Q{quarter}"
            else:  # month
                date_key = eval_date.strftime("%Y-%m")
            
            trends_by_model[model].append(BiasTrendPoint(
                date=date_key,
                bias_rate=bias_rate,
                response_count=response_count
            ))
        
        # Convert to response
        result = [
            BiasTrendResponse(
                model_name=model,
                timeframe=timeframe,
                trend_points=points
            )
            for model, points in trends_by_model.items()
        ]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving bias trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison")
async def compare_bias_across_models(
    eval_ids: List[int] = Query(..., description="List of evaluation IDs"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Compare bias patterns across multiple evaluations/models.
    
    Args:
        eval_ids: List of evaluation IDs to compare
        db: Database session
        
    Returns:
        Comparative analysis of bias patterns
    """
    try:
        comparison_results = {}
        
        for eval_id in eval_ids:
            evaluation = get_evaluation(db, eval_id)
            if not evaluation:
                continue
            
            responses = get_model_responses_for_evaluation(db, eval_id)
            results = get_prompt_results_for_evaluation(db, eval_id)
            scores_dict = {}
            for result in results:
                if hasattr(result, 'scores_json') and result.scores_json:
                    scores_dict = result.scores_json
                    break
            
            response_dicts = [
                {
                    "prompt_id": r.prompt_id,
                    "response": r.response_text if hasattr(r, 'response_text') else "",
                    "language": r.language if hasattr(r, 'language') else "en"
                }
                for r in responses
            ]
            
            stats = bias_dashboard.analyze_evaluation(
                evaluation_id=eval_id,
                model_name=evaluation.model_name,
                model_responses=response_dicts,
                scores=scores_dict
            )
            
            comparison_results[evaluation.model_name] = {
                "bias_rate": stats.bias_rate,
                "gender_bias": stats.gender_bias_rate,
                "age_bias": stats.age_bias_rate,
                "ethnicity_bias": stats.ethnicity_bias_rate,
                "consistency": stats.consistency_score
            }
        
        return {
            "comparison": comparison_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error comparing bias: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
