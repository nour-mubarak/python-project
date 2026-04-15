#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Helper
==========================

CLI tool for managing database migrations and initialization.
"""

import sys
from pathlib import Path
from database import engine, SessionLocal, init_db, Base


def init_cmd():
    """Initialize database tables."""
    print("Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        init_db()
        print("[OK] Database initialized successfully!")
        print("[OK] Default admin user created (username: admin, password: admin123)")
    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)


def reset_cmd():
    """Reset database (drop all tables and reinitialize)."""
    response = input("WARNING: This will delete ALL data. Continue? (y/N): ")
    if response.lower() != "y":
        print("Cancelled.")
        return
    
    print("Resetting database...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("[OK] All tables dropped")
        
        Base.metadata.create_all(bind=engine)
        print("[OK] All tables recreated")
        
        init_db()
        print("[OK] Database reset successfully!")
    except Exception as e:
        print(f"[ERROR] Error resetting database: {e}", file=sys.stderr)
        sys.exit(1)


def status_cmd():
    """Check database status."""
    try:
        db = SessionLocal()
        result = db.execute("SELECT 1").fetchone()
        db.close()
        
        if result:
            print("[OK] Database connection: OK")
            print(f"[OK] Database URL: {engine.url}")
            
            # Count tables
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"[OK] Tables: {len(tables)}")
            for table in sorted(tables):
                print(f"  - {table}")
    except Exception as e:
        print(f"[ERROR] Database error: {e}", file=sys.stderr)
        sys.exit(1)


def seed_cmd():
    """Seed database with sample data."""
    print("Seeding database with sample data...")
    try:
        from database import (
            SessionLocal,
            create_user,
            create_config_preset,
        )
        import hashlib
        
        db = SessionLocal()
        
        # Create test user
        salt = "linguaeval_salt_2026"
        password_hash = hashlib.sha256(f"{salt}test123".encode()).hexdigest()
        user = create_user(
            db,
            username="testuser",
            email="test@linguaeval.local",
            password_hash=password_hash,
            role="user",
        )
        print(f"[OK] Created test user: {user.username}")
        
        # Create sample config preset
        preset = create_config_preset(
            db,
            user_id=user.id,
            name="Government Sector - Standard",
            sector="government",
            models=["gpt-4o-mini", "claude-haiku-4-5-20251001"],
            languages=["en", "ar"],
            dimensions=["accuracy", "bias", "hallucination", "consistency", "cultural", "fluency"],
            prompt_pack="government",
            description="Standard evaluation for government sector AI systems",
            is_public=True,
        )
        print(f"[OK] Created sample config preset: {preset.name}")
        
        print("[OK] Database seeding complete!")
    except Exception as e:
        print(f"[ERROR] Error seeding database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [init|reset|status|seed]")
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "init":
        init_cmd()
    elif command == "reset":
        reset_cmd()
    elif command == "status":
        status_cmd()
    elif command == "seed":
        seed_cmd()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: init, reset, status, seed")
        sys.exit(1)
