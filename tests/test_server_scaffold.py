# tests/test_server_scaffold.py
import pytest
from fastapi.testclient import TestClient
from aede.server import app

def test_server_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_cors_headers_present():
    client = TestClient(app)
    # Origin that should be allowed (e.g. localhost for development)
    response = client.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    # SEC-02: No wildcard
    assert response.headers["access-control-allow-origin"] != "*"
