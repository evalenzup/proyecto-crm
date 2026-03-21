import json
import os
import sys
import pytest
from fastapi.testclient import TestClient

# ── PYTHONPATH al root del backend ─────────────────────────────
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ───────────────────────────────────────────────────────────────
# Tests


@pytest.mark.skip(reason="Requiere certificados .cer/.key válidos de prueba SAT")
def test_empresa_crud_completo(auth_client: TestClient, usuario_admin):
    """
    Prueba el ciclo de vida completo de una empresa:
    1. Crear empresa con certificados.
    2. Listar y verificar que existe.
    3. Obtener por ID.
    4. Actualizar datos y certificados.
    5. Eliminar y verificar que ya no existe.
    """
    # --- 1. Crear Empresa ---
    payload = {
        "nombre": "EMPRESA TEST CRUD",
        "nombre_comercial": "TEST CRUD",
        "ruc": "RUC-CRUD",
        "rfc": "AAA010101AAA",
        "regimen_fiscal": "601",
        "codigo_postal": "01000",
        "direccion": "CALLE FALSA 123",
        "telefono": "5551234567",
        "email": "crud@test.com",
        "contrasena": "12345678a",
    }

    cer_path = os.path.join(os.path.dirname(__file__), "fixtures", "demo.cer")
    key_path = os.path.join(os.path.dirname(__file__), "fixtures", "demo.key")

    with open(cer_path, "rb") as f_cer, open(key_path, "rb") as f_key:
        r = auth_client.post(
            "/api/empresas/",
            data={"empresa_data": json.dumps(payload)},
            files={
                "archivo_cer": ("test.cer", f_cer, "application/x-x509-ca-cert"),
                "archivo_key": ("test.key", f_key, "application/octet-stream"),
            },
        )

    assert r.status_code == 201, r.text
    empresa = r.json()
    empresa_id = empresa["id"]
    assert empresa["nombre"] == payload["nombre"]
    assert empresa["archivo_cer"] is not None
    assert empresa["archivo_key"] is not None

    # --- 2. Listar Empresas ---
    r = auth_client.get("/api/empresas/")
    assert r.status_code == 200
    lista = r.json() if isinstance(r.json(), list) else r.json().get("items", r.json())
    assert any(e["id"] == empresa_id for e in lista)

    # --- 3. Obtener por ID ---
    r = auth_client.get(f"/api/empresas/{empresa_id}")
    assert r.status_code == 200
    assert r.json()["id"] == empresa_id

    # --- 4. Actualizar Empresa ---
    update_payload = {
        "nombre_comercial": "TEST CRUD (ACTUALIZADO)",
        "telefono": "5557654321",
    }
    with open(cer_path, "rb") as f_cer, open(key_path, "rb") as f_key:
        r = auth_client.put(
            f"/api/empresas/{empresa_id}",
            data={"empresa_data": json.dumps(update_payload)},
            files={
                "archivo_cer": ("new.cer", f_cer, "application/x-x509-ca-cert"),
                "archivo_key": ("new.key", f_key, "application/octet-stream"),
            },
        )

    assert r.status_code == 200, r.text
    empresa_updated = r.json()
    assert empresa_updated["nombre_comercial"] == "TEST CRUD (ACTUALIZADO)"
    assert empresa_updated["telefono"] == "5557654321"

    # --- 5. Eliminar Empresa ---
    r = auth_client.delete(f"/api/empresas/{empresa_id}")
    assert r.status_code == 204

    # Verificar que ya no existe
    r = auth_client.get(f"/api/empresas/{empresa_id}")
    assert r.status_code == 404


@pytest.mark.skip(reason="Requiere certificados .cer/.key válidos de prueba SAT")
def test_crear_empresa_rfc_invalido(auth_client: TestClient, usuario_admin):
    """
    Verifica que la API rechace un RFC inválido para el régimen fiscal.
    """
    payload = {
        "nombre": "EMPRESA RFC INVÁLIDO",
        "rfc": "PERSONAFISICA",  # RFC de persona física
        "regimen_fiscal": "601",  # Régimen de persona moral
        "nombre_comercial": "TEST",
        "ruc": "RUC",
        "codigo_postal": "01000",
        "direccion": "C",
        "telefono": "1234567",
        "email": "a@b.com",
        "contrasena": "12345678a",
    }

    cer_path = os.path.join(os.path.dirname(__file__), "fixtures", "demo.cer")
    key_path = os.path.join(os.path.dirname(__file__), "fixtures", "demo.key")

    with open(cer_path, "rb") as f_cer, open(key_path, "rb") as f_key:
        r = auth_client.post(
            "/api/empresas/",
            data={"empresa_data": json.dumps(payload)},
            files={
                "archivo_cer": ("c.cer", f_cer, "application/x-x509-ca-cert"),
                "archivo_key": ("k.key", f_key, "application/octet-stream"),
            },
        )

    assert r.status_code == 422  # Unprocessable Entity
    body = r.json()
    detail = body.get("error", {}).get("detail") or body.get("detail") or ""
    detail_str = str(detail).lower()
    assert "rfc" in detail_str


def test_get_schema_empresa(client: TestClient):
    """
    Verifica que el endpoint del schema funcione y contenga las opciones de regimenes.
    """
    r = client.get("/api/empresas/form-schema")
    assert r.status_code == 200
    schema = r.json()
    assert "properties" in schema
    assert "regimen_fiscal" in schema["properties"]
    assert "x-options" in schema["properties"]["regimen_fiscal"]
    assert len(schema["properties"]["regimen_fiscal"]["x-options"]) > 0
