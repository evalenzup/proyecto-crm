# tests/test_exception_handlers.py
"""Tests para los manejadores globales de excepciones."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError, OperationalError, DataError


def test_404_devuelve_formato_estandar(client):
    r = client.get("/api/ruta-que-no-existe-jamás")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert "type" in body["error"]
    assert "detail" in body["error"]


def test_422_validacion_devuelve_formato_estandar(auth_client):
    # Enviar JSON inválido a un endpoint que espera datos estructurados
    r = auth_client.post("/api/clientes/", json={"campo_invalido": 999})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["type"] == "ValidationError"
    assert isinstance(body["error"]["detail"], list)


def test_integrity_error_unique_devuelve_409(auth_client, db_session):
    """Un IntegrityError por unicidad debe devolver 409, no 500."""
    from app.models.empresa import Empresa

    empresa = Empresa(
        nombre="EMP ÚNICA",
        nombre_comercial="EMP ÚNICA",
        ruc="RUC-UNICA",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="x",
    )
    db_session.add(empresa)
    db_session.commit()

    # Crear cliente con empresa_id válido
    from app.models.cliente import Cliente
    cli = Cliente(
        nombre_comercial="CLI",
        nombre_razon_social="CLI SA",
        rfc="XAXX010101000",
        regimen_fiscal="612",
        codigo_postal="01000",
    )
    cli.empresas.append(empresa)
    db_session.add(cli)
    db_session.commit()

    # Simular que el servicio lanza IntegrityError de unicidad
    orig = MagicMock()
    orig.__str__ = lambda self: "duplicate key value violates unique constraint"
    exc = IntegrityError("", {}, orig)

    from app.exception_handlers import sqlalchemy_exception_handler
    from fastapi import Request
    from unittest.mock import AsyncMock
    import asyncio

    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url = "http://test/api/clientes/"

    response = asyncio.get_event_loop().run_until_complete(
        sqlalchemy_exception_handler(request, exc)
    )
    assert response.status_code == 409
    import json
    body = json.loads(response.body)
    assert body["error"]["type"] == "DatabaseError"
    assert "Ya existe" in body["error"]["detail"]


def test_integrity_error_fk_devuelve_409():
    from app.exception_handlers import sqlalchemy_exception_handler
    from fastapi import Request
    import asyncio, json
    from unittest.mock import MagicMock

    orig = MagicMock()
    orig.__str__ = lambda self: "violates foreign key constraint"
    exc = IntegrityError("", {}, orig)

    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url = "http://test"

    response = asyncio.get_event_loop().run_until_complete(
        sqlalchemy_exception_handler(request, exc)
    )
    assert response.status_code == 409
    body = json.loads(response.body)
    assert "no existe" in body["error"]["detail"]


def test_operational_error_devuelve_503():
    from app.exception_handlers import sqlalchemy_exception_handler
    from fastapi import Request
    import asyncio, json
    from unittest.mock import MagicMock

    orig = MagicMock()
    orig.__str__ = lambda self: "connection refused"
    exc = OperationalError("", {}, orig)

    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url = "http://test"

    response = asyncio.get_event_loop().run_until_complete(
        sqlalchemy_exception_handler(request, exc)
    )
    assert response.status_code == 503
    body = json.loads(response.body)
    assert "no está disponible" in body["error"]["detail"]


def test_data_error_devuelve_400():
    from app.exception_handlers import sqlalchemy_exception_handler
    from fastapi import Request
    import asyncio, json
    from unittest.mock import MagicMock

    orig = MagicMock()
    orig.__str__ = lambda self: "value too long"
    exc = DataError("", {}, orig)

    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url = "http://test"

    response = asyncio.get_event_loop().run_until_complete(
        sqlalchemy_exception_handler(request, exc)
    )
    assert response.status_code == 400
    body = json.loads(response.body)
    assert "no son válidos" in body["error"]["detail"]
