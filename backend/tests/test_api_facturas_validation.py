
import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal

# ── PYTHONPATH al root del backend ─────────────────────────────
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.models.empresa import Empresa
from app.models.cliente import Cliente

# ───────────────────────────────────────────────────────────────
# Helpers

def construir_factura_payload_base(empresa_id, cliente_id):
    """Payload base para una factura válida."""
    return {
        "empresa_id": str(empresa_id),
        "cliente_id": str(cliente_id),
        "tipo_comprobante": "I",
        "moneda": "MXN",
        "uso_cfdi": "G03",
        "lugar_expedicion": "01000",
        "conceptos": [
            {
                "clave_producto": "01010101",
                "clave_unidad": "H87",
                "descripcion": "TEST PRODUCT",
                "cantidad": 1,
                "valor_unitario": 100.00,
            }
        ],
    }

# ───────────────────────────────────────────────────────────────
# Tests de Validación

def test_crear_factura_cliente_inexistente(client, db_session):
    """
    Prueba que la API devuelva un error si se intenta crear una factura
    con un cliente_id que no existe en la base de datos.

    Se espera un 500 Internal Server Error porque la base de datos
    arrojará un IntegrityError que no es manejado de forma específica
    en la capa de servicio/API.
    """
    # 1) Crear una empresa válida
    empresa = Empresa(nombre="EMPRESA VALIDA", nombre_comercial="EMPRESA VALIDA", ruc="RUC-VALIDA", rfc="AAA010101AAA", regimen_fiscal="601", codigo_postal="01000", contrasena="x")
    db_session.add(empresa)
    db_session.commit()
    db_session.refresh(empresa)

    # 2) Construir payload con un cliente_id aleatorio
    payload = construir_factura_payload_base(empresa.id, uuid.uuid4())

    # 3) Realizar la petición
    r = client.post("/api/facturas/", json=payload)

    # 4) Verificar que la respuesta es un error
    # NOTA: Idealmente, esto debería ser un 404 o 422. Un 500 indica
    # que una excepción no fue manejada de forma controlada.
    assert r.status_code == 500
    assert r.json()["error"]["detail"] == "Error al crear la factura"


def test_crear_factura_sin_conceptos(client, db_session):
    """
    Prueba que se pueda crear una factura con una lista de conceptos vacía.
    El resultado debe ser una factura con subtotal y total en 0.
    """
    # 1) Crear empresa y cliente válidos
    empresa = Empresa(nombre="EMPRESA CONCEPTOS", nombre_comercial="EMPRESA CONCEPTOS", ruc="RUC-CONCEPTOS", rfc="AAA010101AAA", regimen_fiscal="601", codigo_postal="01000", contrasena="x")
    cliente = Cliente(nombre_comercial="CLIENTE CONCEPTOS", nombre_razon_social="CLIENTE CONCEPTOS SA DE CV", rfc="XAXX010101000", regimen_fiscal="612", codigo_postal="02020")
    cliente.empresas.append(empresa)
    db_session.add_all([empresa, cliente])
    db_session.commit()
    db_session.refresh(empresa)
    db_session.refresh(cliente)

    # 2) Construir payload base y quitarle los conceptos
    payload = construir_factura_payload_base(empresa.id, cliente.id)
    payload["conceptos"] = []

    # 3) Realizar la petición
    r = client.post("/api/facturas/", json=payload)

    # 4) Verificar que la factura se creó correctamente con total 0
    assert r.status_code == 201, r.text
    factura_creada = r.json()
    assert Decimal(factura_creada["total"]) == Decimal("0")
    assert Decimal(factura_creada["subtotal"]) == Decimal("0")
    assert len(factura_creada["conceptos"]) == 0


def test_crear_factura_cliente_no_asociado_a_empresa(client, db_session):
    """
    Prueba que la API permite (incorrectamente) crear una factura para un cliente
    que no está asociado a la empresa facturadora.

    Este es un test que se espera que PASE, pero que documenta una
    potencial falla de lógica de negocio o de seguridad.
    """
    # 1) Crear dos empresas y un cliente asociado solo a la segunda
    empresa1 = Empresa(nombre="EMPRESA A", nombre_comercial="EMPRESA A", ruc="RUC-A", rfc="AAA010101AAA", regimen_fiscal="601", codigo_postal="01000", contrasena="x")
    empresa2 = Empresa(nombre="EMPRESA B", nombre_comercial="EMPRESA B", ruc="RUC-B", rfc="AAA010101AAA", regimen_fiscal="601", codigo_postal="01000", contrasena="x")
    cliente = Cliente(nombre_comercial="CLIENTE B", nombre_razon_social="CLIENTE B SA DE CV", rfc="XAXX010101000", regimen_fiscal="612", codigo_postal="02020")
    cliente.empresas.append(empresa2) # Asociado solo a empresa2
    db_session.add_all([empresa1, empresa2, cliente])
    db_session.commit()
    db_session.refresh(empresa1)
    db_session.refresh(cliente)

    # 2) Intentar crear factura con empresa1 pero para cliente de empresa2
    payload = construir_factura_payload_base(empresa1.id, cliente.id)

    # 3) Realizar la petición
    r = client.post("/api/facturas/", json=payload)

    # 4) Verificar que la factura se crea (comportamiento actual)
    # NOTA: En un sistema multi-tenant estricto, esto debería fallar con un 403 o 404.
    assert r.status_code == 201, r.text
    factura_creada = r.json()
    assert factura_creada["empresa_id"] == str(empresa1.id)
    assert factura_creada["cliente_id"] == str(cliente.id)
