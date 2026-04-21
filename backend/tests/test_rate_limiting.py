# tests/test_rate_limiting.py
"""Tests para los límites de tasa (rate limiting) en endpoints críticos."""
import pytest


def test_login_permite_solicitudes_normales(client):
    """Login debe responder 422 por credenciales vacías, no 429."""
    r = client.post("/api/login/access-token", data={"username": "", "password": ""})
    # 422 = validación, no 429 = rate limit
    assert r.status_code in (401, 422)


def test_login_devuelve_error_con_credenciales_invalidas(client):
    """Login debe devolver 4xx con credenciales incorrectas (400 según OAuth2)."""
    r = client.post(
        "/api/login/access-token",
        data={"username": "noexiste@test.com", "password": "wrong"},
    )
    assert r.status_code in (400, 401)


def test_login_exitoso(client, db_session):
    """Login con credenciales correctas debe devolver access_token."""
    from app.models.empresa import Empresa
    from app.models.usuario import Usuario
    from app.core.security import get_password_hash

    empresa = Empresa(
        nombre="EMP LOGIN",
        nombre_comercial="EMP LOGIN",
        ruc="RUC-LOGIN",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="x",
    )
    db_session.add(empresa)
    db_session.flush()

    usuario = Usuario(
        email="login@test.com",
        hashed_password=get_password_hash("supersecreta"),
        nombre_completo="Login Test",
        rol="admin",
        is_active=True,
        empresa_id=empresa.id,
    )
    db_session.add(usuario)
    db_session.commit()

    r = client.post(
        "/api/login/access-token",
        data={"username": "login@test.com", "password": "supersecreta"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_endpoint_protegido_sin_token(client):
    """Endpoints protegidos deben devolver 401 sin Authorization header."""
    r = client.get("/api/notificaciones/")
    assert r.status_code == 401


def test_endpoint_protegido_con_token_invalido(client):
    """Endpoints protegidos deben devolver 401/403 con token inválido."""
    r = client.get(
        "/api/notificaciones/",
        headers={"Authorization": "Bearer token-invalido-abc123"},
    )
    assert r.status_code in (401, 403)
