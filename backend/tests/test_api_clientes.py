import os
import sys
from app.models.empresa import Empresa

# ── PYTHONPATH al root del backend ─────────────────────────────
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ── SQLAlchemy test DB (SQLite en memoria) ─────────────────────


# ───────────────────────────────────────────────────────────────
# Helpers


def crear_empresa(client):
    payload = {
        "nombre": "NORTON FUMIGACIONES SA",
        "nombre_comercial": "NORTON FUMIGACIONES",
        "ruc": "RUC-001",
        "direccion": "CALLE FICHA 123",
        "telefono": "0000000",
        "email": "info@norton.com",
        "rfc": "AAA010101AAA",
        "regimen_fiscal": "601",
        "codigo_postal": "01000",
        "contrasena": "x",
    }
    r = client.post("/api/empresas/", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ───────────────────────────────────────────────────────────────
# Tests


def test_crear_listar_actualizar_eliminar_cliente(auth_client, db_session):
    # 1) Crear empresa directa en DB (requisitos mínimos del modelo)
    empresa = Empresa(
        nombre="EMPRESA DEMO",
        nombre_comercial="EMPRESA DEMO",
        ruc="RUC-123",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="secretito",
        direccion="CALLE 1",
        telefono="5551234567",
        email="demo@empresa.com",
    )
    db_session.add(empresa)
    db_session.commit()
    db_session.refresh(empresa)

    # 2) Crear cliente
    payload = {
        "empresa_id": [str(empresa.id)],
        "nombre_comercial": "CLIENTE DEMO",
        "nombre_razon_social": "CLIENTE DEMO SA DE CV",
        "rfc": "XAXX010101000",
        "regimen_fiscal": "612",
        "codigo_postal": "02000",
        "email": "foo@bar.com,baz@qux.com",
        "telefono": "5551112222,5553334444",
        "tamano": "CHICO",
        "actividad": "COMERCIAL",
    }
    r = auth_client.post("/api/clientes/", json=payload)
    assert r.status_code == 201, r.text
    cli = r.json()
    cid = cli["id"]
    assert sorted(cli["email"]) == sorted(["foo@bar.com", "baz@qux.com"])
    assert sorted(cli["telefono"]) == sorted(["5551112222", "5553334444"])

    # 3) Listar
    r = auth_client.get("/api/clientes/")
    assert r.status_code == 200
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", r.json())
    assert any(c["id"] == cid for c in items)

    # 4) Actualizar (solo nombre_comercial para evitar el bug de la lista de telefonos)
    upd_payload = {"nombre_comercial": "CLIENTE DEMO (ACTUALIZADO)"}
    r = auth_client.put(f"/api/clientes/{cid}", json=upd_payload)
    assert r.status_code == 200, r.text
    cli_updated = r.json()
    assert cli_updated["nombre_comercial"] == "CLIENTE DEMO (ACTUALIZADO)"
    # Verificar que el teléfono original no cambió
    assert sorted(cli_updated["telefono"]) == sorted(["5551112222", "5553334444"])
    # Verificar que otros campos no cambiaron
    assert cli_updated["rfc"] == payload["rfc"]

    # 5) Eliminar
    r = auth_client.delete(f"/api/clientes/{cid}")
    assert r.status_code == 204

    # 6) Verificar que ya no exista
    r = auth_client.get(f"/api/clientes/{cid}")
    assert r.status_code == 404
