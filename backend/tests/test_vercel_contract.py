from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_same_origin_api_health_alias() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app_version"]
    assert payload["llm_provider"]
