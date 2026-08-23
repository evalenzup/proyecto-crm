# tests/test_historial_documento.py
"""
Historial de un comprobante: el diff de las modificaciones y la línea de tiempo.

El diff existe porque las modificaciones no se auditaban: en producción había
UN registro de ACTUALIZAR_FACTURA contra 478 de CREAR_FACTURA y 1792 de
TIMBRAR_FACTURA. Se podía cambiar el receptor o los importes de una factura sin
que quedara rastro de qué había antes.
"""
import json
from datetime import datetime, timedelta

import pytest

from app.services import historial_documento_service as hist


@pytest.fixture
def factura_borrador(db_session):
    """Factura con un concepto, que es lo mínimo para comparar renglones."""
    from app.models.cliente import Cliente
    from app.models.empresa import Empresa
    from app.models.factura import Factura
    from app.models.factura_detalle import FacturaDetalle

    emp = Empresa(
        nombre="NORTON", nombre_comercial="NORTON", ruc="RUC-H",
        rfc="GAOA611225II9", regimen_fiscal="612", codigo_postal="22000",
        contrasena="x",
    )
    cli = Cliente(
        nombre_comercial="CLI", nombre_razon_social="CLI SA DE CV",
        rfc="PME140722QM7", regimen_fiscal="601", codigo_postal="22000",
    )
    cli.empresas.append(emp)
    db_session.add_all([emp, cli])
    db_session.commit()

    f = Factura(
        serie="A", folio=9001, empresa_id=emp.id, cliente_id=cli.id,
        estatus="BORRADOR", uso_cfdi="G03", subtotal=100, total=116,
    )
    f.conceptos.append(
        FacturaDetalle(
            descripcion="SERVICIO DE PRUEBA", cantidad=1, valor_unitario=100,
            importe=116, clave_producto="01010101", clave_unidad="E48",
        )
    )
    db_session.add(f)
    db_session.commit()
    return f


# ─────────────────────────────────────────────────────────────────────────────
# snapshot / diff
# ─────────────────────────────────────────────────────────────────────────────

def test_detecta_el_campo_que_cambio_y_lo_agrupa():
    antes = {"uso_cfdi": "G03", "observaciones": "nota vieja"}
    despues = {"uso_cfdi": "G01", "observaciones": "nota vieja"}

    cambios = hist.diff(antes, despues)

    assert len(cambios) == 1
    assert cambios[0] == {
        "campo": "uso_cfdi", "antes": "G03", "despues": "G01", "grupo": "fiscal",
    }


def test_separa_lo_fiscal_de_lo_de_cobranza_y_lo_interno():
    antes = {"total": "100.00", "status_pago": "NO_PAGADA", "observaciones": "a"}
    despues = {"total": "200.00", "status_pago": "PAGADA", "observaciones": "b"}

    grupos = {c["campo"]: c["grupo"] for c in hist.diff(antes, despues)}

    assert grupos == {
        "total": "fiscal",
        "status_pago": "cobranza",
        "observaciones": "interno",
    }


def test_sin_cambios_no_hay_nada_que_registrar():
    igual = {"total": "100.00", "conceptos": [{"descripcion": "x"}]}
    assert hist.diff(igual, dict(igual)) == []


def test_los_conceptos_se_comparan_como_un_bloque(db_session, factura_borrador):
    """
    Partir los renglones uno por uno sería adivinar cuál corresponde a cuál
    cuando se reordenan. Para leer el historial basta ver qué había y qué quedó.
    """
    antes = hist.snapshot(factura_borrador)
    factura_borrador.conceptos[0].descripcion = "SERVICIO CORREGIDO"
    db_session.flush()

    cambios = hist.diff(antes, hist.snapshot(factura_borrador))

    assert [c["campo"] for c in cambios] == ["conceptos"]
    assert cambios[0]["antes"][0]["descripcion"] == "SERVICIO DE PRUEBA"
    assert cambios[0]["despues"][0]["descripcion"] == "SERVICIO CORREGIDO"


def test_el_ruido_del_timbrado_no_ensucia_el_historial(db_session, factura_borrador):
    """
    Sellos, rutas de archivo y fechas automáticas cambian solos y ya tienen su
    propio evento en la línea de tiempo. Registrarlos aquí escondería los
    cambios que sí hizo una persona.
    """
    antes = hist.snapshot(factura_borrador)
    factura_borrador.sello_cfdi = "SELLO NUEVO"
    factura_borrador.xml_path = "/data/otro.xml"
    factura_borrador.fecha_timbrado = datetime.utcnow()
    factura_borrador.cfdi_uuid = "89697BD3-2F34-4997-8978-A32B28187197"
    db_session.flush()

    assert hist.diff(antes, hist.snapshot(factura_borrador)) == []


def test_la_foto_incluye_los_totales_que_cambian_de_rebote(db_session, factura_borrador):
    """
    El snapshot se toma de las columnas, no del payload: así se ve también lo
    que el sistema recalcula solo, no únicamente lo que el usuario tecleó.
    """
    foto = hist.snapshot(factura_borrador)
    assert "total" in foto and "subtotal" in foto
    assert "conceptos" in foto


# ─────────────────────────────────────────────────────────────────────────────
# Línea de tiempo
# ─────────────────────────────────────────────────────────────────────────────

def _auditar(db, factura, accion, entidad="factura", detalle=None, cuando=None):
    from app.models.auditoria import AuditoriaLog

    reg = AuditoriaLog(
        empresa_id=factura.empresa_id,
        usuario_email="mara@norton.mx",
        accion=accion,
        entidad=entidad,
        entidad_id=str(factura.id),
        detalle=json.dumps(detalle or {}),
        creado_en=cuando or datetime.utcnow(),
    )
    db.add(reg)
    db.flush()
    return reg


def test_junta_la_auditoria_con_la_bitacora_del_pac(db_session, factura_borrador):
    """
    Los dos rastros conviven a propósito: la auditoría dice quién apretó el
    botón y la bitácora qué contestó el PAC. Cuando una cancelación sale mal,
    la diferencia entre esas dos cosas es justo lo que hay que ver.
    """
    from app.services import cancelacion_intento_service as bitacora

    _auditar(db_session, factura_borrador, "TIMBRAR_FACTURA",
             cuando=datetime.utcnow() - timedelta(hours=2))
    bitacora.registrar(
        db_session, factura_borrador,
        motivo="02", folio_sustitucion=None,
        pac_code="GT11", pac_message="Solicitud de cancelación recibida.",
    )

    eventos = hist.linea_de_tiempo(db_session, factura_borrador)

    fuentes = [e["fuente"] for e in eventos]
    assert "auditoria" in fuentes and "cancelacion" in fuentes
    # Más reciente primero: la solicitud es de ahora, el timbrado de hace 2 h.
    assert eventos[0]["fuente"] == "cancelacion"
    assert eventos[0]["detalle"]["pac_code"] == "GT11"
    assert eventos[-1]["titulo"] == "Timbrada ante el SAT"


def test_no_se_pierden_los_eventos_con_entidad_en_mayuscula(db_session, factura_borrador):
    """
    `entidad` se escribió inconsistente: 'factura' en casi todo y 'Factura' en
    VERIFICAR_SAT. En producción son 211 eventos que se perderían al comparar
    con distinción de mayúsculas.
    """
    _auditar(db_session, factura_borrador, "VERIFICAR_SAT", entidad="Factura")

    eventos = hist.linea_de_tiempo(db_session, factura_borrador)

    assert [e["titulo"] for e in eventos] == ["Consulta al SAT"]


def test_el_detalle_json_llega_como_objeto_no_como_texto(db_session, factura_borrador):
    _auditar(db_session, factura_borrador, "ACTUALIZAR_FACTURA",
             detalle={"cambios": [{"campo": "uso_cfdi", "antes": "G03", "despues": "G01"}]})

    evento = hist.linea_de_tiempo(db_session, factura_borrador)[0]

    assert evento["detalle"]["cambios"][0]["campo"] == "uso_cfdi"


def test_un_envio_sin_respuesta_se_cuenta_distinto_a_uno_rechazado(
    db_session, factura_borrador
):
    """El título tiene que distinguir 'nadie vio la respuesta' de 'el PAC dijo que no'."""
    from app.models.cancelacion_intento import SIN_RESPUESTA
    from app.services import cancelacion_intento_service as bitacora

    bitacora.registrar(
        db_session, factura_borrador,
        motivo="02", folio_sustitucion=None,
        pac_code=None, pac_message="Error de red",
        envio=SIN_RESPUESTA,
    )

    evento = hist.linea_de_tiempo(db_session, factura_borrador)[0]

    assert "no contestó" in evento["titulo"]
    assert "pudo haberla recibido" in evento["titulo"]


def test_el_endpoint_devuelve_la_linea_de_tiempo(auth_client, db_session, factura_borrador):
    _auditar(db_session, factura_borrador, "CREAR_FACTURA")
    db_session.commit()

    r = auth_client.get(f"/api/facturas/{factura_borrador.id}/historial")

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["documento"]["folio"] == factura_borrador.folio
    assert cuerpo["eventos"][0]["titulo"] == "Factura creada"


# ─────────────────────────────────────────────────────────────────────────────
# Complementos de pago: el mismo historial, con sus propias diferencias
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def pago_timbrado(db_session):
    from app.models.cliente import Cliente
    from app.models.empresa import Empresa
    from app.models.pago import EstatusPago, Pago, PagoDocumentoRelacionado

    emp = Empresa(
        nombre="NORTON", nombre_comercial="NORTON", ruc="RUC-PG",
        rfc="GAOA611225II9", regimen_fiscal="612", codigo_postal="22000",
        contrasena="x",
    )
    cli = Cliente(
        nombre_comercial="CLI", nombre_razon_social="CLI SA DE CV",
        rfc="PME140722QM7", regimen_fiscal="601", codigo_postal="22000",
    )
    cli.empresas.append(emp)
    db_session.add_all([emp, cli])
    db_session.commit()

    p = Pago(
        serie="P", folio="927", empresa_id=emp.id, cliente_id=cli.id,
        estatus=EstatusPago.TIMBRADO, monto=1160,
        fecha_pago=datetime(2026, 8, 20, 12, 0),
        forma_pago_p="03", moneda_p="MXN",
        uuid="7C1E0A55-1111-4B4B-8BB3-8AF0A126FB2E",
    )
    from app.models.factura import Factura

    pagada = Factura(
        serie="A", folio=2202, empresa_id=emp.id, cliente_id=cli.id,
        estatus="TIMBRADA", total=1160,
    )
    db_session.add(pagada)
    db_session.commit()

    p.documentos_relacionados.append(
        PagoDocumentoRelacionado(
            factura_id=pagada.id,
            id_documento="0F6D3A11-9C3C-4A9E-9F1E-4A1C0D2E5B77",
            serie="A", folio="2202", moneda_dr="MXN",
            num_parcialidad=1, imp_pagado=1160, imp_saldo_ant=1160,
            imp_saldo_insoluto=0,
        )
    )
    db_session.add(p)
    db_session.commit()
    return p


def test_los_documentos_pagados_son_los_renglones_del_complemento(
    db_session, pago_timbrado
):
    """La factura compara conceptos; el complemento, lo que paga. Misma idea."""
    from app.services import historial_documento_service as h

    antes = h.snapshot(pago_timbrado)
    assert antes["documentos_relacionados"][0]["documento"] == "A-2202"

    pago_timbrado.documentos_relacionados[0].imp_pagado = 500
    db_session.flush()

    cambios = h.diff(antes, h.snapshot(pago_timbrado))
    assert [c["campo"] for c in cambios] == ["documentos_relacionados"]
    assert cambios[0]["grupo"] == "fiscal"


def test_fecha_pago_significa_cosas_distintas_en_cada_documento():
    """
    En una factura es la fecha programada de cobro —cobranza—; en un complemento
    es la fecha real del pago que va en el CFDI —fiscal—. Mismo nombre, dos
    cosas, y clasificarlas igual sería esconder un cambio fiscal.
    """
    from app.services import historial_documento_service as h

    de_factura = h.diff(
        {"fecha_pago": "2026-08-01", "conceptos": []},
        {"fecha_pago": "2026-09-01", "conceptos": []},
    )
    de_pago = h.diff(
        {"fecha_pago": "2026-08-01", "documentos_relacionados": []},
        {"fecha_pago": "2026-09-01", "documentos_relacionados": []},
    )

    assert de_factura[0]["grupo"] == "cobranza"
    assert de_pago[0]["grupo"] == "fiscal"


def test_el_historial_del_pago_lee_su_propia_entidad(db_session, pago_timbrado):
    """
    La auditoría de pagos se escribe con entidad 'pago'. Si el historial leyera
    'factura' saldría vacío y nadie lo notaría hasta necesitarlo.
    """
    from app.services import historial_documento_service as h

    _auditar(db_session, pago_timbrado, "TIMBRAR_PAGO", entidad="pago")

    eventos = h.linea_de_tiempo(db_session, pago_timbrado)

    assert [e["titulo"] for e in eventos] == ["Timbrado ante el SAT"]


def test_el_pago_no_se_lleva_los_eventos_de_una_factura(db_session, pago_timbrado, factura_borrador):
    """Los dos rastros comparten tabla; sólo los distingue el tipo de entidad."""
    from app.services import historial_documento_service as h

    _auditar(db_session, factura_borrador, "TIMBRAR_FACTURA")

    assert h.linea_de_tiempo(db_session, pago_timbrado) == []


def test_la_bitacora_del_pac_tambien_aparece_en_el_complemento(db_session, pago_timbrado):
    from app.services import cancelacion_intento_service as bitacora
    from app.services import historial_documento_service as h

    bitacora.registrar(
        db_session, pago_timbrado,
        motivo="02", folio_sustitucion=None,
        pac_code="GT05", pac_message="Solicitud recibida.",
        sat_registro_solicitud=False,
    )

    evento = h.linea_de_tiempo(db_session, pago_timbrado)[0]

    assert evento["fuente"] == "cancelacion"
    assert evento["detalle"]["sat_registro_solicitud"] is False


def test_el_endpoint_de_historial_del_pago_responde(auth_client, db_session, pago_timbrado):
    _auditar(db_session, pago_timbrado, "CREAR_PAGO", entidad="pago")
    db_session.commit()

    r = auth_client.get(f"/api/pagos/{pago_timbrado.id}/historial")

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["documento"]["folio"] == pago_timbrado.folio
    assert cuerpo["eventos"][0]["titulo"] == "Complemento creado"
