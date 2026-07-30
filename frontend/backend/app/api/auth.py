from __future__ import annotations

import sqlite3
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import (
    UserContext,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.app.core.config import get_settings
from backend.app.db.repository import (
    count_auth_users,
    create_auth_user,
    fetch_auth_user_by_email,
)
from backend.app.models import AuthToken, AuthUser, LoginRequest, RegisterRequest


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _public_user(row: dict) -> AuthUser:
    return AuthUser(
        user_id=row["user_id"],
        email=row["email"],
        display_name=row["display_name"],
        role=row["role"],
    )


@router.post("/register", response_model=AuthToken, status_code=201)
def register(payload: RegisterRequest) -> AuthToken:
    settings = get_settings()
    existing_count = count_auth_users()
    if existing_count and not settings.allow_registration:
        raise HTTPException(status_code=403, detail="Đăng ký tài khoản đang bị tắt.")
    password_hash, password_salt = hash_password(payload.password)
    try:
        row = create_auth_user(
            user_id=str(uuid4()),
            email=str(payload.email),
            display_name=payload.display_name,
            password_hash=password_hash,
            password_salt=password_salt,
            role="admin" if existing_count == 0 else "user",
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email đã được sử dụng.") from exc
    user = _public_user(row)
    context = UserContext(**user.model_dump())
    return AuthToken(
        access_token=create_access_token(context),
        expires_in=settings.auth_token_ttl_seconds,
        user=user,
    )


@router.post("/login", response_model=AuthToken)
def login(payload: LoginRequest) -> AuthToken:
    settings = get_settings()
    row = fetch_auth_user_by_email(str(payload.email))
    if (
        row is None
        or row["disabled"]
        or not verify_password(
            payload.password,
            row["password_hash"],
            row["password_salt"],
        )
    ):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")
    user = _public_user(row)
    context = UserContext(**user.model_dump())
    return AuthToken(
        access_token=create_access_token(context),
        expires_in=settings.auth_token_ttl_seconds,
        user=user,
    )


@router.get("/me", response_model=AuthUser)
def me(user: UserContext = Depends(get_current_user)) -> AuthUser:
    return AuthUser(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
    )
