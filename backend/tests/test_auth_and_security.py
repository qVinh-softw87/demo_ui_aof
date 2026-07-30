from __future__ import annotations

from fastapi.testclient import TestClient

import backend.app.db.repository as advisory_repository
from backend.app.core.auth import hash_password, verify_password
from backend.app.core.config import get_settings
from backend.app.db.sqlite import initialize_database
from backend.app.main import app


def test_password_hash_is_salted_and_verifiable() -> None:
    first_hash, first_salt = hash_password("correct-horse-battery")
    second_hash, second_salt = hash_password("correct-horse-battery")

    assert first_hash != second_hash
    assert first_salt != second_salt
    assert verify_password("correct-horse-battery", first_hash, first_salt)
    assert not verify_password("wrong-password", first_hash, first_salt)


def test_register_login_and_protected_api(tmp_path) -> None:
    settings = get_settings()
    original = (
        settings.db_path,
        settings.auth_required,
        settings.auth_secret,
        settings.allow_registration,
    )
    settings.db_path = tmp_path / "auth-test.sqlite3"
    settings.auth_required = True
    settings.auth_secret = "test-secret-with-enough-entropy-for-signing"
    settings.allow_registration = True
    initialize_database()

    try:
        with TestClient(app) as client:
            unauthenticated = client.get("/api/v1/me/recommendations")
            assert unauthenticated.status_code == 401
            assert unauthenticated.headers["x-content-type-options"] == "nosniff"
            assert unauthenticated.headers["x-request-id"]

            registered = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "owner@example.com",
                    "password": "long-secure-password",
                    "display_name": "Portfolio Owner",
                },
            )
            assert registered.status_code == 201
            payload = registered.json()
            assert payload["user"]["role"] == "admin"

            token = payload["access_token"]
            authenticated = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert authenticated.status_code == 200
            assert authenticated.json()["email"] == "owner@example.com"

            profile = client.get(
                "/api/v1/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert profile.status_code == 200
            profile_payload = profile.json()
            profile_payload["age"] = 41
            profile_payload["occupation"] = "Kỹ sư phần mềm"
            profile_payload["max_product_count"] = 5
            profile_payload["goals"].append(
                {
                    "goal_id": "education",
                    "name": "Quỹ giáo dục",
                    "target_amount": 600_000_000,
                    "horizon_months": 120,
                    "priority": "HIGH",
                    "flexibility": "ADJUSTABLE",
                }
            )
            saved_profile = client.put(
                "/api/v1/me/profile",
                headers={"Authorization": f"Bearer {token}"},
                json=profile_payload,
            )
            assert saved_profile.status_code == 200
            assert saved_profile.json()["age"] == 41
            assert saved_profile.json()["max_product_count"] == 5
            assert len(saved_profile.json()["goals"]) == 2

            persisted_profile = client.get(
                "/api/v1/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert persisted_profile.json()["occupation"] == "Kỹ sư phần mềm"

            conversational_chat = client.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "recommendation_id": None,
                    "message": "Xin chào, hệ thống hoạt động như thế nào?",
                },
            )
            assert conversational_chat.status_code == 200
            assert conversational_chat.json()["sections"]
            assert conversational_chat.json()["suggested_questions"]

            logged_in = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "owner@example.com",
                    "password": "long-secure-password",
                },
            )
            assert logged_in.status_code == 200
            assert logged_in.json()["access_token"]
    finally:
        (
            settings.db_path,
            settings.auth_required,
            settings.auth_secret,
            settings.allow_registration,
        ) = original


def test_advisor_authorization_is_admin_controlled_and_server_owned(tmp_path) -> None:
    settings = get_settings()
    original = (
        settings.db_path,
        settings.auth_required,
        settings.auth_secret,
        settings.allow_registration,
        settings.llm_provider,
    )
    settings.db_path = tmp_path / "advisor-auth-test.sqlite3"
    settings.auth_required = True
    settings.auth_secret = "test-secret-with-enough-entropy-for-signing"
    settings.allow_registration = True
    settings.llm_provider = "deterministic"
    initialize_database()

    try:
        with TestClient(app) as client:
            admin_registration = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "advisor-admin@example.com",
                    "password": "long-secure-password",
                    "display_name": "Advisor Admin",
                },
            )
            assert admin_registration.status_code == 201
            assert admin_registration.json()["user"]["role"] == "admin"
            admin_headers = {
                "Authorization": (
                    f"Bearer {admin_registration.json()['access_token']}"
                )
            }

            initial_status = client.get(
                "/api/v1/advisory/status",
                headers=admin_headers,
            )
            assert initial_status.status_code == 200
            assert initial_status.json()["can_manage"] is True
            assert initial_status.json()["authorized"] is False

            verified_status = client.put(
                "/api/v1/admin/advisory/status",
                headers=admin_headers,
                json={
                    "licensed_entity_verified": True,
                    "advisory_contract_verified": True,
                    "responsible_advisor_verified": True,
                },
            )
            assert verified_status.status_code == 200
            assert verified_status.json()["authorized"] is True
            assert verified_status.json()["verified_at"]

            admin_request = client.get(
                "/api/v1/demo/default-request",
                headers=admin_headers,
            ).json()
            admin_request["requested_mode"] = "LICENSED_ADVISORY"
            admin_request["legal_evidence"] = {
                "licensed_entity_verified": False,
                "advisory_contract_verified": False,
                "responsible_advisor_verified": False,
            }
            advisory_result = client.post(
                "/api/v1/recommendations",
                headers=admin_headers,
                json=admin_request,
            )
            assert advisory_result.status_code == 200
            released = advisory_result.json()["released_output"]
            assert released["output_release_type"] == "ADVISORY_SELECTED"
            assert len(released["scenarios"]) == 3
            assert released["scenarios"][0]["recommendation_role"] == "RECOMMENDED"
            assert all(
                scenario["allocation_granularity"] == "PRODUCT"
                for scenario in released["scenarios"]
            )

            user_registration = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "regular-user@example.com",
                    "password": "long-secure-password",
                    "display_name": "Regular User",
                },
            )
            assert user_registration.status_code == 201
            assert user_registration.json()["user"]["role"] == "user"
            user_headers = {
                "Authorization": f"Bearer {user_registration.json()['access_token']}"
            }

            user_status = client.get(
                "/api/v1/advisory/status",
                headers=user_headers,
            )
            assert user_status.status_code == 200
            assert user_status.json()["can_manage"] is False
            assert user_status.json()["authorized"] is False

            forbidden_update = client.put(
                "/api/v1/admin/advisory/status",
                headers=user_headers,
                json={
                    "licensed_entity_verified": True,
                    "advisory_contract_verified": True,
                    "responsible_advisor_verified": True,
                },
            )
            assert forbidden_update.status_code == 403

            user_request = client.get(
                "/api/v1/demo/default-request",
                headers=user_headers,
            ).json()
            user_request["requested_mode"] = "LICENSED_ADVISORY"
            user_request["legal_evidence"] = {
                "licensed_entity_verified": True,
                "advisory_contract_verified": True,
                "responsible_advisor_verified": True,
            }
            spoofed_result = client.post(
                "/api/v1/recommendations",
                headers=user_headers,
                json=user_request,
            )
            assert spoofed_result.status_code == 200
            assert (
                spoofed_result.json()["released_output"]["output_release_type"]
                == "BLOCKED"
            )
    finally:
        (
            settings.db_path,
            settings.auth_required,
            settings.auth_secret,
            settings.allow_registration,
            settings.llm_provider,
        ) = original


def test_advisor_upsert_uses_boolean_case_conditions_for_postgres(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params

        def commit(self):
            return None

    monkeypatch.setattr(advisory_repository, "initialize_database", lambda: None)
    monkeypatch.setattr(
        advisory_repository,
        "get_connection",
        lambda: FakeConnection(),
    )
    monkeypatch.setattr(
        advisory_repository,
        "fetch_advisory_authorization",
        lambda user_id: {
            "user_id": user_id,
            "licensed_entity_verified": True,
            "advisory_contract_verified": True,
            "responsible_advisor_verified": True,
            "verified_by": "admin-user",
            "verified_at": "2026-07-30T00:00:00Z",
        },
    )

    advisory_repository.upsert_advisory_authorization(
        user_id="advisor-user",
        licensed_entity_verified=True,
        advisory_contract_verified=True,
        responsible_advisor_verified=True,
        verified_by="admin-user",
    )

    params = captured["params"]
    assert isinstance(params, tuple)
    assert params[-2:] == (True, True)
    assert all(isinstance(value, bool) for value in params[-2:])
