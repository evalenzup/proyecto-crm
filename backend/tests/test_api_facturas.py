import os
import sys
from datetime import date

# ── PYTHONPATH al root del backend ─────────────────────────────
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Env mínimos (por si Settings los requiere)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from app.models.empresa import Empresa  # noqa: E402
from app.models.cliente import Cliente  # noqa: E402


def construir_factura_payload(empresa_id, cliente_id):
    return {
        "empresa_id": empresa_id,
        "cliente_id": cliente_id,
        "tipo_comprobante": "I",
        "moneda": "MXN",
        "uso_cfdi": "G03",
        "lugar_expedicion": "01000",
        "conceptos": [
            {
                "clave_producto": "01010101",
                "clave_unidad": "H87",
                "descripcion": "SERVICIO A",
                "cantidad": 1,
                "valor_unitario": 100.00,
                "descuento": 0,
                "iva_tasa": 0.16,
            },
            {
                "clave_producto": "01010101",
                "clave_unidad": "H87",
                "descripcion": "SERVICIO B",
                "cantidad": 2,
                "valor_unitario": 50.00,
                "descuento": 0,
                "iva_tasa": 0.16,
            },
        ],
    }


# ───────────────────────────────────────────────────────────────
# Tests


def test_crear_listar_y_folios_consecutivos(client, db_session):
    # Crear empresas y clientes directamente en la DB
    emp1 = Empresa(
        nombre="EMPRESA UNO",
        nombre_comercial="EMPRESA UNO",
        ruc="RUC-001",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="x",
    )
    emp2 = Empresa(
        nombre="EMPRESA DOS",
        nombre_comercial="EMPRESA DOS",
        ruc="RUC-002",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="x",
    )
    cli1 = Cliente(
        nombre_comercial="CLIENTE 1",
        nombre_razon_social="CLIENTE 1 SA DE CV",
        rfc="XAXX010101000",
        regimen_fiscal="612",
        codigo_postal="02020",
    )
    cli2 = Cliente(
        nombre_comercial="CLIENTE 2",
        nombre_razon_social="CLIENTE 2 SA DE CV",
        rfc="XAXX010101000",
        regimen_fiscal="612",
        codigo_postal="02020",
    )

    cli1.empresas.append(emp1)
    cli2.empresas.append(emp2)

    db_session.add_all([emp1, emp2, cli1, cli2])
    db_session.commit()
    db_session.refresh(emp1)
    db_session.refresh(emp2)
    db_session.refresh(cli1)
    db_session.refresh(cli2)

    # Crear primera factura de emp1 → folio 1
    payload = construir_factura_payload(str(emp1.id), str(cli1.id))
    r = client.post("/api/factura/", json=payload)
    assert r.status_code == 201, r.text
    f1 = r.json()
    assert f1["serie"] == "A"
    assert f1["folio"] == 1
    assert f1["estatus"] == "BORRADOR"
    assert f1["status_pago"] == "NO_PAGADA"
    assert f1["total"]  # > 0

    # Segunda factura de emp1 → folio 2
    r = client.post(
        "/api/factura/", json=construir_factura_payload(str(emp1.id), str(cli1.id))
    )
    assert r.status_code == 201
    f2 = r.json()
    assert f2["folio"] == 2

    # Primera factura de emp2 → folio 1 (consecutivo por empresa)
    r = client.post(
        "/api/factura/", json=construir_factura_payload(str(emp2.id), str(cli2.id))
    )
    assert r.status_code == 201
    f3 = r.json()
    assert f3["folio"] == 1

    # Listar facturas (sin filtros)
    r = client.get("/api/factura/")
    assert r.status_code == 200
    lista = r.json()
    assert len(lista["items"]) == 3


def test_timbrar_cancelar_y_pago(client, db_session):
    emp = Empresa(
        nombre="EMPRESA TIMBRE",
        nombre_comercial="EMPRESA TIMBRE",
        ruc="RUC-T",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="x",
    )
    cli = Cliente(
        nombre_comercial="CLIENTE T",
        nombre_razon_social="CLIENTE T SA DE CV",
        rfc="XAXX010101000",
        regimen_fiscal="612",
        codigo_postal="02020",
    )
    cli.empresas.append(emp)
    db_session.add_all([emp, cli])
    db_session.commit()
    db_session.refresh(emp)
    db_session.refresh(cli)

    r = client.post(
        "/api/factura/", json=construir_factura_payload(str(emp.id), str(cli.id))
    )
    assert r.status_code == 201
    fac = r.json()

    # Timbrar
    r = client.post(f"/api/factura/{fac['id']}/timbrar")
    assert r.status_code == 200, r.text
    fac_t = r.json()
    assert fac_t["estatus"] == "TIMBRADA"
    assert fac_t["cfdi_uuid"] is not None

    # Marcar pagada (requiere fecha_cobro)
    r = client.patch(
        f"/api/factura/{fac['id']}/pago",
        params={"status": "PAGADA", "fecha_cobro": date.today().isoformat()},
    )
    assert r.status_code == 200
    fac_p = r.json()
    assert fac_p["status_pago"] == "PAGADA"
    assert fac_p["fecha_cobro"] is not None

    # Quitar pago para poder cancelar
    r = client.patch(f"/api/factura/{fac['id']}/pago", params={"status": "NO_PAGADA"})
    assert r.status_code == 200
    fac_np = r.json()
    assert fac_np["status_pago"] == "NO_PAGADA"
    assert fac_np["fecha_cobro"] is None

    # Cancelar (ahora debería permitirlo)
    r = client.post(f"/api/factura/{fac['id']}/cancelar")
    assert r.status_code == 200, r.text

    fac_c = r.json()
    assert fac_c["estatus"] == "CANCELADA"
    assert fac_c["status_pago"] == "NO_APLICA"  # o lo que corresponda
    assert fac_c["fecha_cancelacion"] is not None
