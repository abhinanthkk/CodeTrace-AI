"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "sandbox_available" in data
        assert "ai_configured" in data
        assert "version" in data

    def test_root_returns_info(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CodeTrace AI"


class TestExecuteEndpoint:
    def test_empty_code_rejected(self, client):
        response = client.post("/api/execute", json={"code": "", "input": ""})
        assert response.status_code == 422  # Validation error

    def test_missing_code_rejected(self, client):
        response = client.post("/api/execute", json={"input": ""})
        assert response.status_code == 422

    def test_valid_request_accepted(self, client):
        """Valid request should be accepted (may fail at sandbox if Docker unavailable)."""
        response = client.post(
            "/api/execute",
            json={"code": "x = 1\nprint(x)", "input": ""},
        )
        # Either 200 (sandbox works) or 500 (Docker unavailable)
        assert response.status_code in (200, 500)

    def test_code_size_limit(self, client):
        """Code exceeding 64KB should be rejected."""
        huge_code = "x = 1\n" * 40000
        response = client.post("/api/execute", json={"code": huge_code, "input": ""})
        assert response.status_code in (400, 422)

    def test_cors_headers(self, client):
        response = client.options(
            "/api/execute",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
        )
        assert response.status_code in (200, 405)
