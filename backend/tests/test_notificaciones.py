# tests/test_notificaciones.py
"""Tests para el sistema de notificaciones in-app."""
import pytest
from app.services import notificacion_service as svc


# ── Helpers ─────────────────────────────────────────────────────

def crear_empresa_y_usuario(db_session):
    from app.models.empresa import Empresa
    from app.models.usuario import Usuario
    from app.core.security import get_password_hash

    empresa = Empresa(
        nombre="EMP NOTIF",
        nombre_comercial="EMP NOTIF",
        ruc="RUC-NOTIF",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="x",
    )
    db_session.add(empresa)
    db_session.flush()

    usuario = Usuario(
        email="user@notif.com",
        hashed_password=get_password_hash("pass"),
        nombre_completo="Usuario Notif",
        rol="supervisor",
        is_active=True,
        empresa_id=empresa.id,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(empresa)
    db_session.refresh(usuario)
    return empresa, usuario


# ── Tests unitarios del service ──────────────────────────────────

def test_crear_notificacion(db_session):
    empresa, _ = crear_empresa_y_usuario(db_session)

    notif = svc.crear_notificacion(
        db=db_session,
        empresa_id=empresa.id,
        tipo=svc.EXITO,
        titulo="Prueba",
        mensaje="Notificación de prueba",
    )

    assert notif.id is not None
    assert notif.tipo == svc.EXITO
    assert notif.titulo == "Prueba"
    assert notif.leida is False
    assert notif.empresa_id == empresa.id
    assert notif.usuario_id is None  # global de empresa


def test_crear_notificacion_para_usuario_especifico(db_session):
    empresa, usuario = crear_empresa_y_usuario(db_session)

    notif = svc.crear_notificacion(
        db=db_session,
        empresa_id=empresa.id,
        tipo=svc.INFO,
        titulo="Solo para ti",
        mensaje="Mensaje específico",
        usuario_id=usuario.id,
    )

    assert notif.usuario_id == usuario.id


def test_crear_notificacion_con_metadata(db_session):
    empresa, _ = crear_empresa_y_usuario(db_session)

    notif = svc.crear_notificacion(
        db=db_session,
        empresa_id=empresa.id,
        tipo=svc.EXITO,
        titulo="Con metadata",
        mensaje="Tiene datos extra",
        metadata={"factura_id": "abc-123", "folio": 42},
    )

    assert notif.metadata_["factura_id"] == "abc-123"
    assert notif.metadata_["folio"] == 42


def test_listar_notificaciones_vacio(db_session):
    empresa, usuario = crear_empresa_y_usuario(db_session)

    items, total, no_leidas = svc.listar_notificaciones(
        db=db_session,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
    )

    assert items == []
    assert total == 0
    assert no_leidas == 0


def test_listar_notificaciones_incluye_globales_y_propias(db_session):
    empresa, usuario = crear_empresa_y_usuario(db_session)

    # Notificación global (sin usuario_id)
    svc.crear_notificacion(db_session, empresa.id, svc.INFO, "Global", "Para todos")
    # Notificación específica del usuario
    svc.crear_notificacion(db_session, empresa.id, svc.EXITO, "Personal", "Solo para ti", usuario_id=usuario.id)

    items, total, no_leidas = svc.listar_notificaciones(
        db=db_session, empresa_id=empresa.id, usuario_id=usuario.id
    )

    assert total == 2
    assert no_leidas == 2
    titulos = {n.titulo for n in items}
    assert "Global" in titulos
    assert "Personal" in titulos


def test_listar_solo_no_leidas(db_session):
    empresa, usuario = crear_empresa_y_usuario(db_session)

    n1 = svc.crear_notificacion(db_session, empresa.id, svc.INFO, "N1", "msg1")
    n2 = svc.crear_notificacion(db_session, empresa.id, svc.INFO, "N2", "msg2")

    # Marcar la primera como leída
    svc.marcar_leida(db_session, n1.id, empresa.id)

    items, total, no_leidas = svc.listar_notificaciones(
        db=db_session, empresa_id=empresa.id, solo_no_leidas=True
    )

    assert total == 1
    assert items[0].titulo == "N2"


def test_marcar_leida(db_session):
    empresa, _ = crear_empresa_y_usuario(db_session)

    notif = svc.crear_notificacion(db_session, empresa.id, svc.INFO, "T", "M")
    assert notif.leida is False

    actualizada = svc.marcar_leida(db_session, notif.id, empresa.id)
    assert actualizada.leida is True


def test_marcar_leida_notificacion_inexistente(db_session):
    import uuid
    empresa, _ = crear_empresa_y_usuario(db_session)

    resultado = svc.marcar_leida(db_session, uuid.uuid4(), empresa.id)
    assert resultado is None


def test_marcar_todas_leidas(db_session):
    empresa, usuario = crear_empresa_y_usuario(db_session)

    svc.crear_notificacion(db_session, empresa.id, svc.INFO, "A", "msg")
    svc.crear_notificacion(db_session, empresa.id, svc.EXITO, "B", "msg")
    svc.crear_notificacion(db_session, empresa.id, svc.ADVERTENCIA, "C", "msg")

    count = svc.marcar_todas_leidas(db_session, empresa.id, usuario.id)
    assert count == 3

    _, _, no_leidas = svc.listar_notificaciones(db_session, empresa.id)
    assert no_leidas == 0


# ── Tests de API ─────────────────────────────────────────────────

def test_api_listar_notificaciones(auth_client, db_session, usuario_admin):
    usuario, token = usuario_admin

    r = auth_client.get("/api/notificaciones/")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "no_leidas" in body


def test_api_listar_solo_no_leidas(auth_client, db_session, usuario_admin):
    usuario, _ = usuario_admin

    r = auth_client.get("/api/notificaciones/", params={"solo_no_leidas": True})
    assert r.status_code == 200
    body = r.json()
    # Todas deben ser no leídas
    assert all(not n["leida"] for n in body["items"])


def test_api_marcar_leida(auth_client, db_session, usuario_admin):
    usuario, _ = usuario_admin

    # Crear notificación directamente en BD
    notif = svc.crear_notificacion(
        db=db_session,
        empresa_id=usuario.empresa_id,
        tipo=svc.INFO,
        titulo="Para marcar",
        mensaje="msg",
    )

    r = auth_client.patch(f"/api/notificaciones/{notif.id}/leer")
    assert r.status_code == 200
    assert r.json()["leida"] is True


def test_api_marcar_leida_no_existente(auth_client):
    import uuid
    r = auth_client.patch(f"/api/notificaciones/{uuid.uuid4()}/leer")
    assert r.status_code == 404


def test_api_marcar_todas_leidas(auth_client, db_session, usuario_admin):
    usuario, _ = usuario_admin

    svc.crear_notificacion(db_session, usuario.empresa_id, svc.INFO, "X", "msg")
    svc.crear_notificacion(db_session, usuario.empresa_id, svc.EXITO, "Y", "msg")

    r = auth_client.patch("/api/notificaciones/leer-todas")
    assert r.status_code == 200
    assert "marcadas" in r.json()["message"]
