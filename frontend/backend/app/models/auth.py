from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    email: EmailStr
    display_name: str
    role: Literal["admin", "user"]


class AuthToken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: AuthUser


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    role: Literal["user", "assistant"]
    content: str
    metadata: dict | None = None
    created_at: str


class RecommendationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    status: str
    created_at: str
    goal: str
    scenario_count: int


class AdvisoryAuthorizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    licensed_entity_verified: bool
    advisory_contract_verified: bool
    responsible_advisor_verified: bool


class AdvisoryAuthorizationStatus(AdvisoryAuthorizationUpdate):
    user_id: str
    authorized: bool
    can_manage: bool
    verified_by: str | None = None
    verified_at: str | None = None
