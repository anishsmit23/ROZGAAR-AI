"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
def test_health_check(client):
    """Test GET /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
def test_openapi_docs(client):
    """Test OpenAPI documentation is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()
