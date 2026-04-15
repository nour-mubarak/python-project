#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Router
=====================

Simple session-based authentication for LinguaEval.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import json

from fastapi import APIRouter, Request, Form, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# Get base directory
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

# Session configuration
SESSION_COOKIE_NAME = "linguaeval_session"
SESSION_DURATION_HOURS = 24


# Import shared render_template helper from main.py
def render_template(name: str, context: dict):
    """Lazy import to avoid circular imports."""
    from web.main import render_template as shared_render

    return shared_render(name, context)


def hash_password(password: str) -> str:
    """Hash password with SHA-256 and salt."""
    salt = "linguaeval_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def load_users() -> dict:
    """Load users from JSON file."""
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            return json.load(f)
    # Create default admin user
    default_users = {
        "admin": {
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "email": "admin@linguaeval.local",
            "role": "admin",
            "created_at": datetime.now().isoformat(),
        }
    }
    save_users(default_users)
    return default_users


def save_users(users: dict):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def load_sessions() -> dict:
    """Load active sessions."""
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE) as f:
            sessions = json.load(f)
        # Clean expired sessions
        now = datetime.now()
        active = {}
        for token, data in sessions.items():
            expires = datetime.fromisoformat(data["expires_at"])
            if expires > now:
                active[token] = data
        if len(active) != len(sessions):
            save_sessions(active)
        return active
    return {}


def save_sessions(sessions: dict):
    """Save sessions to JSON file."""
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def create_session(username: str) -> str:
    """Create a new session for user."""
    token = secrets.token_urlsafe(32)
    sessions = load_sessions()
    sessions[token] = {
        "username": username,
        "created_at": datetime.now().isoformat(),
        "expires_at": (
            datetime.now() + timedelta(hours=SESSION_DURATION_HOURS)
        ).isoformat(),
    }
    save_sessions(sessions)
    return token


def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    sessions = load_sessions()
    session = sessions.get(token)
    if not session:
        return None

    # Check expiry
    expires = datetime.fromisoformat(session["expires_at"])
    if expires < datetime.now():
        return None

    users = load_users()
    user = users.get(session["username"])
    return user


def require_auth(request: Request) -> dict:
    """Dependency that requires authentication."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, next: str = "/"):
    """Login page."""

    # If already logged in, redirect
    user = get_current_user(request)
    if user:
        return RedirectResponse(url=next, status_code=303)

    return render_template(
        "login.html",
        {
            "request": request,
            "page_title": "Login",
            "error": error,
            "next": next,
        },
    )


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    """Process login."""
    users = load_users()
    user = users.get(username)

    if not user or user["password_hash"] != hash_password(password):
        return RedirectResponse(
            url=f"/auth/login?error=Invalid+credentials&next={next}",
            status_code=303,
        )

    # Create session
    token = create_session(username)

    response = RedirectResponse(url=next, status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_DURATION_HOURS * 3600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    """Logout and clear session."""
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if token:
        sessions = load_sessions()
        if token in sessions:
            del sessions[token]
            save_sessions(sessions)

    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None, success: str = None):
    """Registration page."""
    return render_template(
        "register.html",
        {
            "request": request,
            "page_title": "Register",
            "error": error,
            "success": success,
        },
    )


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Process registration."""
    # Validation
    if len(username) < 3:
        return RedirectResponse(
            url="/auth/register?error=Username+must+be+at+least+3+characters",
            status_code=303,
        )

    if password != confirm_password:
        return RedirectResponse(
            url="/auth/register?error=Passwords+do+not+match",
            status_code=303,
        )

    if len(password) < 6:
        return RedirectResponse(
            url="/auth/register?error=Password+must+be+at+least+6+characters",
            status_code=303,
        )

    users = load_users()

    if username in users:
        return RedirectResponse(
            url="/auth/register?error=Username+already+exists",
            status_code=303,
        )

    # Create user
    users[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "email": email,
        "role": "user",
        "created_at": datetime.now().isoformat(),
    }
    save_users(users)

    return RedirectResponse(
        url="/auth/login?success=Registration+successful.+Please+login.",
        status_code=303,
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login?next=/auth/profile", status_code=303)

        return render_template(
            "profile.html",
            {
                "request": request,
                "page_title": "Profile",
                "user": user,
            },
        )


@router.post("/profile/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Change user password."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    if user["password_hash"] != hash_password(current_password):
        return RedirectResponse(
            url="/auth/profile?error=Current+password+is+incorrect",
            status_code=303,
        )

    if new_password != confirm_password:
        return RedirectResponse(
            url="/auth/profile?error=Passwords+do+not+match",
            status_code=303,
        )

    if len(new_password) < 6:
        return RedirectResponse(
            url="/auth/profile?error=Password+must+be+at+least+6+characters",
            status_code=303,
        )

    users = load_users()
    users[user["username"]]["password_hash"] = hash_password(new_password)
    save_users(users)

    return RedirectResponse(
        url="/auth/profile?success=Password+changed+successfully",
        status_code=303,
    )
