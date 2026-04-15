#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest Configuration & Shared Fixtures
=======================================

Common fixtures and configuration for test suite.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, Base, engine


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create a test API client."""
    from fastapi.testclient import TestClient
    from web.main import app
    
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authorization headers for testing."""
    return {
        "Authorization": "Bearer test_token_12345",
        "Content-Type": "application/json"
    }


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    from database import create_user
    import hashlib
    
    salt = "test_salt"
    password_hash = hashlib.sha256(f"{salt}testpass".encode()).hexdigest()
    
    user = create_user(
        db_session,
        username="testuser",
        email="test@example.com",
        password_hash=password_hash,
        role="user"
    )
    return user


@pytest.fixture
def sample_evaluation(db_session, sample_user):
    """Create a sample evaluation for testing."""
    from database import create_evaluation
    
    eval_obj = create_evaluation(
        db_session,
        project_id="test_001",
        client_name="Test Client",
        sector="government",
        prompt_pack="government",
        models=["gpt-4o-mini", "claude-haiku"],
        languages=["en", "ar"],
        dimensions=["accuracy", "bias"],
        user_id=sample_user.id
    )
    return eval_obj


@pytest.fixture
def sample_batch_job(db_session, sample_user):
    """Create a sample batch job for testing."""
    from database import create_batch_job
    
    config = {
        "models": ["gpt-4o-mini"],
        "languages": ["en", "ar"],
        "prompt_pack": "government",
    }
    
    job = create_batch_job(
        db_session,
        job_id="test_job_001",
        user_id=sample_user.id,
        name="Test Batch Job",
        config=config
    )
    return job


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create a temporary directory for test data."""
    return tmp_path_factory.mktemp("test_data")


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
