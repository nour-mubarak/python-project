#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Module
===============

SQLite database for LinguaEval persistence.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import json

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON

# Database path
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATA_DIR}/linguaeval.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    evaluations = relationship("Evaluation", back_populates="user")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Evaluation(Base):
    """Evaluation model."""

    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(100), unique=True, index=True, nullable=False)
    client_name = Column(String(200), nullable=False)
    sector = Column(String(50))
    prompt_pack = Column(String(50))
    status = Column(
        String(20), default="pending"
    )  # pending, running, completed, failed

    # Evaluation configuration
    models = Column(Text)  # JSON list of models
    languages = Column(Text)  # JSON list of languages
    dimensions = Column(Text)  # JSON list of dimensions

    # Results summary
    total_prompts = Column(Integer, default=0)
    total_responses = Column(Integer, default=0)
    overall_score = Column(Float)

    # File paths
    raw_results_path = Column(String(500))
    results_path = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="evaluations")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "client_name": self.client_name,
            "sector": self.sector,
            "prompt_pack": self.prompt_pack,
            "status": self.status,
            "models": json.loads(self.models) if self.models else [],
            "languages": json.loads(self.languages) if self.languages else [],
            "dimensions": json.loads(self.dimensions) if self.dimensions else [],
            "total_prompts": self.total_prompts,
            "total_responses": self.total_responses,
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class Setting(Base):
    """Settings model for key-value storage."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit log for tracking actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(Text)  # JSON
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class BatchJob(Base):
    """Batch evaluation job."""

    __tablename__ = "batch_jobs"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"))
    
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    status = Column(String(20), default="queued", index=True)  # queued, running, completed, failed, cancelled
    
    # Job configuration
    config_json = Column(Text)  # JSON: models, prompt_pack, languages, dimensions
    
    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Results
    result_json = Column(Text)  # JSON: summary results
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User")
    evaluation = relationship("Evaluation")


class ModelResponse(Base):
    """Individual model response to a prompt."""

    __tablename__ = "model_responses"

    id = Column(Integer, primary_key=True, index=True)
    batch_job_id = Column(String(36), ForeignKey("batch_jobs.id"), index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), index=True)
    
    # Prompt info
    prompt_id = Column(String(100), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    
    # Model info
    model_id = Column(String(100), nullable=False, index=True)
    provider = Column(String(50))  # openai, anthropic, azure, ollama
    language = Column(String(10))  # en, ar
    
    # Response
    response_text = Column(Text, nullable=False)
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    latency_ms = Column(Float)
    temperature = Column(Float)
    
    # Error tracking
    error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PromptResult(Base):
    """Aggregated evaluation result for a prompt across models."""

    __tablename__ = "prompt_results"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), index=True, nullable=False)
    prompt_id = Column(String(100), nullable=False, index=True)
    category = Column(String(50))
    
    # Scores JSON: {model_id: {language: [DimensionScore, ...]}}
    scores_json = Column(Text)
    
    # Cross-lingual gap JSON: {model_id: gap_percentage}
    cross_lingual_gap_json = Column(Text)
    
    # Summary scores
    avg_accuracy = Column(Float)
    avg_bias = Column(Float)
    avg_hallucination = Column(Float)
    avg_consistency = Column(Float)
    avg_cultural = Column(Float)
    avg_fluency = Column(Float)
    overall_score = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ConfigPreset(Base):
    """Saved evaluation configuration presets."""

    __tablename__ = "config_presets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text)
    sector = Column(String(50))
    
    # Configuration JSON
    models = Column(Text)  # JSON list
    languages = Column(Text)  # JSON list
    dimensions = Column(Text)  # JSON list
    prompt_pack = Column(String(50))
    
    # Metadata
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")


class RecommendationResult(Base):
    """AI recommendations from evaluation results."""

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), index=True, nullable=False)
    
    # Recommendation categories
    recommendation_type = Column(String(50))  # accuracy, bias, hallucination, cultural, etc.
    severity = Column(String(20))  # low, medium, high, critical
    
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Action items
    action_items_json = Column(Text)  # JSON list
    estimated_effort = Column(String(20))  # low, medium, high
    
    # References
    related_prompts_json = Column(Text)  # JSON list of prompt IDs
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════
# DATABASE FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

    # Create default admin user if not exists
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            import hashlib

            salt = "linguaeval_salt_2026"
            password_hash = hashlib.sha256(f"{salt}admin123".encode()).hexdigest()
            admin = User(
                username="admin",
                email="admin@linguaeval.local",
                password_hash=password_hash,
                role="admin",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# USER OPERATIONS
# ═══════════════════════════════════════════════════════════════


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session, username: str, email: str, password_hash: str, role: str = "user"
) -> User:
    """Create a new user."""
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_password(db: Session, user_id: int, password_hash: str):
    """Update user password."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.password_hash = password_hash
        db.commit()


def get_all_users(db: Session) -> List[User]:
    """Get all users."""
    return db.query(User).all()


# ═══════════════════════════════════════════════════════════════
# EVALUATION OPERATIONS
# ═══════════════════════════════════════════════════════════════


def create_evaluation(
    db: Session,
    project_id: str,
    client_name: str,
    sector: str,
    prompt_pack: str,
    models: List[str],
    languages: List[str],
    dimensions: List[str],
    user_id: int = None,
) -> Evaluation:
    """Create a new evaluation."""
    evaluation = Evaluation(
        project_id=project_id,
        client_name=client_name,
        sector=sector,
        prompt_pack=prompt_pack,
        models=json.dumps(models),
        languages=json.dumps(languages),
        dimensions=json.dumps(dimensions),
        user_id=user_id,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


def get_evaluation(db: Session, project_id: str) -> Optional[Evaluation]:
    """Get evaluation by project_id."""
    return db.query(Evaluation).filter(Evaluation.project_id == project_id).first()


def get_all_evaluations(db: Session, user_id: int = None) -> List[Evaluation]:
    """Get all evaluations, optionally filtered by user."""
    query = db.query(Evaluation)
    if user_id:
        query = query.filter(Evaluation.user_id == user_id)
    return query.order_by(Evaluation.created_at.desc()).all()


def update_evaluation_status(
    db: Session,
    project_id: str,
    status: str,
    results_path: str = None,
    raw_results_path: str = None,
    total_prompts: int = None,
    total_responses: int = None,
    overall_score: float = None,
):
    """Update evaluation status and results."""
    evaluation = get_evaluation(db, project_id)
    if evaluation:
        evaluation.status = status
        if results_path:
            evaluation.results_path = results_path
        if raw_results_path:
            evaluation.raw_results_path = raw_results_path
        if total_prompts:
            evaluation.total_prompts = total_prompts
        if total_responses:
            evaluation.total_responses = total_responses
        if overall_score is not None:
            evaluation.overall_score = overall_score

        if status == "running":
            evaluation.started_at = datetime.utcnow()
        elif status in ("completed", "failed"):
            evaluation.completed_at = datetime.utcnow()

        db.commit()


# ═══════════════════════════════════════════════════════════════
# SETTINGS OPERATIONS
# ═══════════════════════════════════════════════════════════════


def get_setting(db: Session, key: str, default: str = None) -> Optional[str]:
    """Get a setting value."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    """Set a setting value."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()


def get_all_settings(db: Session) -> dict:
    """Get all settings as a dictionary."""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


# ═══════════════════════════════════════════════════════════════
# AUDIT LOG OPERATIONS
# ═══════════════════════════════════════════════════════════════


def log_action(
    db: Session,
    action: str,
    user_id: int = None,
    resource_type: str = None,
    resource_id: str = None,
    details: dict = None,
    ip_address: str = None,
):
    """Log an action to the audit log."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()


def get_recent_audit_logs(db: Session, limit: int = 50) -> List[AuditLog]:
    """Get recent audit logs."""
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


# ═══════════════════════════════════════════════════════════════
# BATCH JOB OPERATIONS
# ═══════════════════════════════════════════════════════════════


def create_batch_job(
    db: Session,
    job_id: str,
    user_id: int,
    name: str,
    config: dict,
    description: str = None,
    evaluation_id: int = None,
) -> "BatchJob":
    """Create a new batch job."""
    job = BatchJob(
        id=job_id,
        user_id=user_id,
        evaluation_id=evaluation_id,
        name=name,
        description=description,
        config_json=json.dumps(config),
        total_items=config.get("total_items", 0),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_batch_job(db: Session, job_id: str) -> Optional["BatchJob"]:
    """Get a batch job by ID."""
    return db.query(BatchJob).filter(BatchJob.id == job_id).first()


def get_batch_jobs_for_user(db: Session, user_id: int, limit: int = 50) -> List["BatchJob"]:
    """Get batch jobs for a user."""
    return (
        db.query(BatchJob)
        .filter(BatchJob.user_id == user_id)
        .order_by(BatchJob.created_at.desc())
        .limit(limit)
        .all()
    )


def get_running_batch_jobs(db: Session) -> List["BatchJob"]:
    """Get all currently running batch jobs."""
    return db.query(BatchJob).filter(BatchJob.status == "running").all()


def update_batch_job_progress(
    db: Session,
    job_id: str,
    progress: int = None,
    completed_items: int = None,
    failed_items: int = None,
    status: str = None,
    error_message: str = None,
    result_json: dict = None,
):
    """Update batch job progress."""
    job = get_batch_job(db, job_id)
    if job:
        if progress is not None:
            job.progress = min(100, max(0, progress))
        if completed_items is not None:
            job.completed_items = completed_items
        if failed_items is not None:
            job.failed_items = failed_items
        if status:
            job.status = status
            if status == "running" and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status in ("completed", "failed", "cancelled"):
                job.completed_at = datetime.utcnow()
        if error_message:
            job.error_message = error_message
        if result_json:
            job.result_json = json.dumps(result_json)
        
        db.commit()


# ═══════════════════════════════════════════════════════════════
# MODEL RESPONSE OPERATIONS
# ═══════════════════════════════════════════════════════════════


def create_model_response(
    db: Session,
    batch_job_id: str,
    evaluation_id: int,
    prompt_id: str,
    prompt_text: str,
    model_id: str,
    provider: str,
    language: str,
    response_text: str,
    tokens_input: int = None,
    tokens_output: int = None,
    latency_ms: float = None,
    temperature: float = None,
    error: str = None,
) -> "ModelResponse":
    """Create a model response record."""
    response = ModelResponse(
        batch_job_id=batch_job_id,
        evaluation_id=evaluation_id,
        prompt_id=prompt_id,
        prompt_text=prompt_text,
        model_id=model_id,
        provider=provider,
        language=language,
        response_text=response_text,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms,
        temperature=temperature,
        error=error,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return response


def get_model_responses_for_evaluation(
    db: Session, evaluation_id: int
) -> List["ModelResponse"]:
    """Get all model responses for an evaluation."""
    return (
        db.query(ModelResponse)
        .filter(ModelResponse.evaluation_id == evaluation_id)
        .order_by(ModelResponse.created_at.asc())
        .all()
    )


def get_model_responses_for_prompt(
    db: Session, evaluation_id: int, prompt_id: str
) -> List["ModelResponse"]:
    """Get all model responses for a specific prompt in an evaluation."""
    return (
        db.query(ModelResponse)
        .filter(
            ModelResponse.evaluation_id == evaluation_id,
            ModelResponse.prompt_id == prompt_id,
        )
        .all()
    )


# ═══════════════════════════════════════════════════════════════
# PROMPT RESULT OPERATIONS
# ═══════════════════════════════════════════════════════════════


def create_prompt_result(
    db: Session,
    evaluation_id: int,
    prompt_id: str,
    category: str,
    scores_json: dict,
    cross_lingual_gap_json: dict = None,
) -> "PromptResult":
    """Create a prompt result record."""
    result = PromptResult(
        evaluation_id=evaluation_id,
        prompt_id=prompt_id,
        category=category,
        scores_json=json.dumps(scores_json),
        cross_lingual_gap_json=json.dumps(cross_lingual_gap_json or {}),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_prompt_results_for_evaluation(
    db: Session, evaluation_id: int
) -> List["PromptResult"]:
    """Get all prompt results for an evaluation."""
    return (
        db.query(PromptResult)
        .filter(PromptResult.evaluation_id == evaluation_id)
        .order_by(PromptResult.created_at.asc())
        .all()
    )


def update_prompt_result_scores(
    db: Session,
    result_id: int,
    avg_accuracy: float = None,
    avg_bias: float = None,
    avg_hallucination: float = None,
    avg_consistency: float = None,
    avg_cultural: float = None,
    avg_fluency: float = None,
    overall_score: float = None,
):
    """Update aggregated scores for a prompt result."""
    result = db.query(PromptResult).filter(PromptResult.id == result_id).first()
    if result:
        if avg_accuracy is not None:
            result.avg_accuracy = avg_accuracy
        if avg_bias is not None:
            result.avg_bias = avg_bias
        if avg_hallucination is not None:
            result.avg_hallucination = avg_hallucination
        if avg_consistency is not None:
            result.avg_consistency = avg_consistency
        if avg_cultural is not None:
            result.avg_cultural = avg_cultural
        if avg_fluency is not None:
            result.avg_fluency = avg_fluency
        if overall_score is not None:
            result.overall_score = overall_score
        
        db.commit()


# ═══════════════════════════════════════════════════════════════
# CONFIG PRESET OPERATIONS
# ═══════════════════════════════════════════════════════════════


def create_config_preset(
    db: Session,
    user_id: int,
    name: str,
    sector: str,
    models: List[str],
    languages: List[str],
    dimensions: List[str],
    prompt_pack: str,
    description: str = None,
    is_public: bool = False,
) -> "ConfigPreset":
    """Create a new configuration preset."""
    preset = ConfigPreset(
        user_id=user_id,
        name=name,
        description=description,
        sector=sector,
        models=json.dumps(models),
        languages=json.dumps(languages),
        dimensions=json.dumps(dimensions),
        prompt_pack=prompt_pack,
        is_public=is_public,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


def get_config_preset(db: Session, preset_id: int) -> Optional["ConfigPreset"]:
    """Get a config preset by ID."""
    return db.query(ConfigPreset).filter(ConfigPreset.id == preset_id).first()


def get_config_presets_for_user(
    db: Session, user_id: int
) -> List["ConfigPreset"]:
    """Get all config presets for a user."""
    return (
        db.query(ConfigPreset)
        .filter(ConfigPreset.user_id == user_id)
        .order_by(ConfigPreset.created_at.desc())
        .all()
    )


def get_public_config_presets(db: Session) -> List["ConfigPreset"]:
    """Get all public config presets."""
    return (
        db.query(ConfigPreset)
        .filter(ConfigPreset.is_public == True)
        .order_by(ConfigPreset.created_at.desc())
        .all()
    )


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATION OPERATIONS
# ═══════════════════════════════════════════════════════════════


def create_recommendation(
    db: Session,
    evaluation_id: int,
    recommendation_type: str,
    severity: str,
    title: str,
    description: str,
    action_items: List[str] = None,
    estimated_effort: str = None,
    related_prompts: List[str] = None,
) -> "RecommendationResult":
    """Create a recommendation."""
    rec = RecommendationResult(
        evaluation_id=evaluation_id,
        recommendation_type=recommendation_type,
        severity=severity,
        title=title,
        description=description,
        action_items_json=json.dumps(action_items or []),
        estimated_effort=estimated_effort,
        related_prompts_json=json.dumps(related_prompts or []),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_recommendations_for_evaluation(
    db: Session, evaluation_id: int
) -> List["RecommendationResult"]:
    """Get all recommendations for an evaluation."""
    return (
        db.query(RecommendationResult)
        .filter(RecommendationResult.evaluation_id == evaluation_id)
        .order_by(RecommendationResult.severity.desc(), RecommendationResult.created_at.desc())
        .all()
    )


def get_recommendations_by_type(
    db: Session, evaluation_id: int, rec_type: str
) -> List["RecommendationResult"]:
    """Get recommendations of a specific type for an evaluation."""
    return (
        db.query(RecommendationResult)
        .filter(
            RecommendationResult.evaluation_id == evaluation_id,
            RecommendationResult.recommendation_type == rec_type,
        )
        .all()
    )


# Initialize database on import
init_db()
