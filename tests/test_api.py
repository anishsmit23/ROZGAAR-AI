"""API-level tests for health and route wiring."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    """Health endpoint should return ok."""

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
