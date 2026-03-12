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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

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


# Initialize database on import
init_db()
