# tests/test_health.py
"""Tests para los endpoints de health check."""


def test_liveness(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_readiness(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_health_no_requiere_auth(client):
    """Los endpoints de health deben ser públicos."""
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
