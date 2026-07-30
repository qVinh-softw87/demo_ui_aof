from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from backend.app.db import get_connection, initialize_database
from backend.app.models import (
    ConfirmationRequest,
    FullCalculationOutput,
    PlanningRequest,
    RecommendationResponse,
    UserFinancialProfile,
)


def _json(value: BaseModel | dict[str, Any] | list[Any] | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    return json.dumps(value, ensure_ascii=False, default=str)


def upsert_user_profile(request: PlanningRequest) -> None:
    profile = request.profile
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles (
                user_id, display_name, total_assets, emergency_reserve,
                near_term_liabilities, risk_capacity, liquidity_need_months,
                profile_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name=excluded.display_name,
                total_assets=excluded.total_assets,
                emergency_reserve=excluded.emergency_reserve,
                near_term_liabilities=excluded.near_term_liabilities,
                risk_capacity=excluded.risk_capacity,
                liquidity_need_months=excluded.liquidity_need_months,
                profile_json=excluded.profile_json,
                updated_at=datetime('now')
            """,
            (
                profile.user_id,
                profile.display_name,
                profile.total_assets,
                profile.emergency_reserve,
                profile.near_term_liabilities,
                profile.risk_capacity,
                profile.liquidity_need_months,
                profile.model_dump_json(),
            ),
        )
        conn.commit()


def fetch_user_profile(user_id: str) -> UserFinancialProfile | None:
    initialize_database()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT profile_json FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None or not row["profile_json"]:
        return None
    return UserFinancialProfile.model_validate_json(row["profile_json"])


def append_audit(
    *,
    module_name: str,
    event_type: str,
    recommendation_id: str,
    user_id: str,
    input_data: BaseModel | dict[str, Any] | None = None,
    output_data: BaseModel | dict[str, Any] | None = None,
) -> None:
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (
                audit_id, user_id, module_name, event_type, input_json,
                output_json, recommendation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user_id,
                module_name,
                event_type,
                _json(input_data),
                _json(output_data),
                recommendation_id,
            ),
        )
        conn.commit()


def save_recommendation(
    request: PlanningRequest,
    full_output: FullCalculationOutput,
    response: RecommendationResponse,
) -> None:
    upsert_user_profile(request)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO recommendation_runs (
                recommendation_id, user_id, request_json, full_output_json,
                released_output_json, explanation_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recommendation_id) DO UPDATE SET
                request_json=excluded.request_json,
                full_output_json=excluded.full_output_json,
                released_output_json=excluded.released_output_json,
                explanation_json=excluded.explanation_json,
                status=excluded.status
            """,
            (
                full_output.recommendation_id,
                request.profile.user_id,
                request.model_dump_json(),
                full_output.model_dump_json(),
                response.released_output.model_dump_json(),
                response.explanation.model_dump_json(),
                response.released_output.output_release_type,
            ),
        )
        conn.commit()


def fetch_recommendation(recommendation_id: str) -> dict[str, Any] | None:
    initialize_database()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT user_id, request_json, full_output_json, released_output_json,
                   explanation_json, status, created_at
            FROM recommendation_runs WHERE recommendation_id = ?
            """,
            (recommendation_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "user_id": row["user_id"],
        "request": json.loads(row["request_json"]),
        "full_output": json.loads(row["full_output_json"]),
        "released_output": json.loads(row["released_output_json"]),
        "explanation": json.loads(row["explanation_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
    }


def list_audit_logs(recommendation_id: str) -> list[dict[str, Any]]:
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT audit_id, user_id, module_name, event_type, input_json,
                   output_json, recommendation_id, created_at
            FROM audit_logs WHERE recommendation_id = ? ORDER BY created_at, rowid
            """,
            (recommendation_id,),
        ).fetchall()
    return [
        {
            **dict(row),
            "input": json.loads(row["input_json"]) if row["input_json"] else None,
            "output": json.loads(row["output_json"]) if row["output_json"] else None,
        }
        for row in rows
    ]


def save_chat_message(
    recommendation_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (
                message_id, recommendation_id, role, content, metadata_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid4()), recommendation_id, role, content, _json(metadata)),
        )
        conn.commit()


def save_confirmation(
    recommendation_id: str,
    confirmation: ConfirmationRequest,
) -> str:
    confirmation_id = str(uuid4())
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO confirmations (
                confirmation_id, recommendation_id, scenario_id, confirmed, note
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                confirmation_id,
                recommendation_id,
                confirmation.scenario_id,
                int(confirmation.confirmed),
                confirmation.note,
            ),
        )
        conn.execute(
            """
            INSERT INTO transactions (
                transaction_id, user_id, portfolio_id, status, payload_json,
                human_confirmed_at
            )
            SELECT ?, user_id, NULL, ?, ?, CASE WHEN ? THEN datetime('now') ELSE NULL END
            FROM recommendation_runs WHERE recommendation_id = ?
            """,
            (
                str(uuid4()),
                "HUMAN_CONFIRMED_DEMO" if confirmation.confirmed else "DECLINED",
                confirmation.model_dump_json(),
                int(confirmation.confirmed),
                recommendation_id,
            ),
        )
        conn.commit()
    return confirmation_id


def count_auth_users() -> int:
    initialize_database()
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM auth_users").fetchone()
    return int(row["total"])


def create_auth_user(
    *,
    user_id: str,
    email: str,
    display_name: str,
    password_hash: str,
    password_salt: str,
    role: str,
) -> dict[str, Any]:
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO auth_users (
                user_id, email, display_name, password_hash, password_salt, role
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                email.lower(),
                display_name,
                password_hash,
                password_salt,
                role,
            ),
        )
        conn.commit()
    return fetch_auth_user_by_id(user_id) or {}


def fetch_auth_user_by_email(email: str) -> dict[str, Any] | None:
    initialize_database()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM auth_users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
    return dict(row) if row else None


def fetch_auth_user_by_id(user_id: str) -> dict[str, Any] | None:
    initialize_database()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM auth_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def fetch_advisory_authorization(user_id: str) -> dict[str, Any]:
    initialize_database()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT user_id, licensed_entity_verified,
                   advisory_contract_verified, responsible_advisor_verified,
                   verified_by, verified_at
            FROM advisory_authorizations
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        return {
            "user_id": user_id,
            "licensed_entity_verified": False,
            "advisory_contract_verified": False,
            "responsible_advisor_verified": False,
            "verified_by": None,
            "verified_at": None,
        }
    payload = dict(row)
    for field in (
        "licensed_entity_verified",
        "advisory_contract_verified",
        "responsible_advisor_verified",
    ):
        payload[field] = bool(payload[field])
    return payload


def upsert_advisory_authorization(
    *,
    user_id: str,
    licensed_entity_verified: bool,
    advisory_contract_verified: bool,
    responsible_advisor_verified: bool,
    verified_by: str,
) -> dict[str, Any]:
    initialize_database()
    authorized = (
        licensed_entity_verified
        and advisory_contract_verified
        and responsible_advisor_verified
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO advisory_authorizations (
                user_id, licensed_entity_verified, advisory_contract_verified,
                responsible_advisor_verified, verified_by, verified_at
            ) VALUES (?, ?, ?, ?, ?, CASE WHEN ? THEN datetime('now') ELSE NULL END)
            ON CONFLICT(user_id) DO UPDATE SET
                licensed_entity_verified=excluded.licensed_entity_verified,
                advisory_contract_verified=excluded.advisory_contract_verified,
                responsible_advisor_verified=excluded.responsible_advisor_verified,
                verified_by=excluded.verified_by,
                verified_at=CASE WHEN ? THEN datetime('now') ELSE NULL END,
                updated_at=datetime('now')
            """,
            (
                user_id,
                int(licensed_entity_verified),
                int(advisory_contract_verified),
                int(responsible_advisor_verified),
                verified_by,
                int(authorized),
                int(authorized),
            ),
        )
        conn.commit()
    return fetch_advisory_authorization(user_id)


def list_user_recommendations(
    user_id: str,
    *,
    limit: int = 30,
) -> list[dict[str, Any]]:
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT recommendation_id, request_json, released_output_json,
                   status, created_at
            FROM recommendation_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    result = []
    for row in rows:
        request = json.loads(row["request_json"])
        released = json.loads(row["released_output_json"])
        result.append(
            {
                "recommendation_id": row["recommendation_id"],
                "status": row["status"],
                "created_at": row["created_at"],
                "goal": request["profile"]["goal"],
                "scenario_count": len(released.get("scenarios", [])),
            }
        )
    return result


def list_chat_messages(recommendation_id: str) -> list[dict[str, Any]]:
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT message_id, role, content, metadata_json, created_at
            FROM chat_messages
            WHERE recommendation_id = ?
            ORDER BY created_at, rowid
            """,
            (recommendation_id,),
        ).fetchall()
    return [
        {
            "message_id": row["message_id"],
            "role": row["role"],
            "content": row["content"],
            "metadata": json.loads(row["metadata_json"])
            if row["metadata_json"]
            else None,
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def append_api_event(
    *,
    request_id: str,
    user_id: str | None,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str | None,
) -> None:
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO api_events (
                event_id, request_id, user_id, method, path,
                status_code, duration_ms, client_ip
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                request_id,
                user_id,
                method,
                path,
                status_code,
                duration_ms,
                client_ip,
            ),
        )
        conn.commit()
