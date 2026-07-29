from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from backend.app.core.config import get_settings
from backend.app.db.repository import fetch_auth_user_by_id


@dataclass(frozen=True)
class UserContext:
    user_id: str
    email: str
    display_name: str
    role: str


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    resolved_salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=resolved_salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return _b64url(digest), _b64url(resolved_salt)


def verify_password(password: str, expected_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, _b64url_decode(salt))
    return hmac.compare_digest(candidate, expected_hash)


def create_access_token(user: UserContext) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": user.user_id,
        "email": user.email,
        "role": user.role,
        "iat": now,
        "exp": now + settings.auth_token_ttl_seconds,
        "jti": secrets.token_urlsafe(12),
    }
    encoded_payload = _b64url(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        settings.auth_secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_b64url(signature)}"


def parse_access_token(token: str) -> UserContext:
    settings = get_settings()
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected = hmac.new(
            settings.auth_secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected, _b64url_decode(encoded_signature)):
            raise ValueError("signature")
        payload = json.loads(_b64url_decode(encoded_payload))
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError("expired")
        row = fetch_auth_user_by_id(str(payload["sub"]))
        if row is None or row["disabled"]:
            raise ValueError("user")
        return UserContext(
            user_id=row["user_id"],
            email=row["email"],
            display_name=row["display_name"],
            role=row["role"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(authorization: str | None = Header(default=None)) -> UserContext:
    settings = get_settings()
    if not settings.auth_required:
        return UserContext(
            user_id="demo-user",
            email="demo@local.invalid",
            display_name="Nhà đầu tư demo",
            role="admin",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cần đăng nhập để sử dụng API này.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parse_access_token(authorization[7:].strip())


def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên được phép.")
    return user
