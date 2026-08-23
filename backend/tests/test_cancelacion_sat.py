# tests/test_cancelacion_sat.py
"""
Pruebas de la máquina de estados de cancelación ante el SAT.

Es la lógica más re-trabajada del proyecto y la que más veces cambió de
conclusión (ver el historial de commits sobre "No cancelable", el motivo 01 y
los acuses del PAC). Hasta ahora no tenía ninguna prueba: el único test que la
tocaba estaba `skip` y afirmaba cosas de un modelo que ya no existe.

Todo lo de aquí corre sin red: `aplicar_acuse_sat` y
`_clasificar_respuesta_cancelacion` son funciones puras, y la bitácora se
prueba contra la base SQLite de los tests.
"""
import json
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.sat_cfdi_service import (
    DIAS_CANCELACION_VENCIDA,
    MINUTOS_GRACIA_SOLICITUD,
    AcuseSAT,
    aplicar_acuse_sat,
    aplicar_acuse_sat_pago,
)
from app.services.timbrado_factmoderna import _clasificar_respuesta_cancelacion

OK = "S - Comprobante obtenido satisfactoriamente."
AHORA = datetime(2026, 8, 19, 12, 0, 0)


def acuse(estado="Vigente", cancelacion="", cancelable="Cancelable con aceptación",
          codigo=OK) -> AcuseSAT:
    return AcuseSAT(
        codigo_estatus=codigo,
        estado=estado,
        es_cancelable=cancelable,
        estatus_cancelacion=cancelacion,
    )


def factura(estatus="EN_CANCELACION", hace=None, mensaje=None):
    """Objeto mínimo con los campos que muta aplicar_acuse_sat."""
    return SimpleNamespace(
        estatus=estatus,
        cfdi_uuid="81373179-8431-4B4B-8BB3-8AF0A126FB2E",
        fecha_solicitud_cancelacion=(AHORA - hace) if hace else None,
        cancelacion_message=mensaje,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Códigos de respuesta del PAC
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("code", ["201", "202", "GT05", "GT11", "GT12"])
def test_codigos_documentados_no_dependen_del_mensaje(code):
    """
    GT11 es el código que la documentación del PAC dice que devuelve para las
    cancelaciones con aceptación, y estuvo fuera de la lista: sólo llegaba a
    EN_CANCELACION porque su mensaje traía la palabra "recibida". Si el PAC
    cambia ese texto, la solicitud se perdía en silencio.
    """
    aceptada, conocido = _clasificar_respuesta_cancelacion(code, "")
    assert aceptada is True
    assert conocido is True


def test_codigo_en_minusculas_tambien_se_reconoce():
    assert _clasificar_respuesta_cancelacion("gt11", "") == (True, True)


def test_codigo_desconocido_cae_al_texto_y_se_marca_como_desconocido():
    aceptada, conocido = _clasificar_respuesta_cancelacion(
        "GT99", "Solicitud de cancelación recibida"
    )
    assert aceptada is True
    assert conocido is False  # queda registrado que hubo que adivinar


def test_codigo_desconocido_sin_señales_no_se_da_por_aceptado():
    assert _clasificar_respuesta_cancelacion("GT99", "Error de sellado") == (False, False)


# ─────────────────────────────────────────────────────────────────────────────
# aplicar_acuse_sat — el veredicto del SAT manda
# ─────────────────────────────────────────────────────────────────────────────

def test_cfdi_no_verificable_no_toca_el_estatus():
    """
    601/602: el SAT no reconoce el comprobante. Antes esto caía en la rama
    "Vigente" y podía revertir a TIMBRADA una factura sí cancelada.
    """
    for codigo in ("N - 601", "N - 602"):
        f = factura(estatus="CANCELADA")
        nuevo, cambio = aplicar_acuse_sat(f, acuse(codigo=codigo), AHORA)
        assert (nuevo, cambio) == ("CANCELADA", False)


def test_cancelado_en_sat_marca_cancelada_y_limpia_la_fecha():
    f = factura(hace=timedelta(hours=1))
    nuevo, cambio = aplicar_acuse_sat(f, acuse(estado="Cancelado", cancelacion="Plazo vencido"), AHORA)
    assert (nuevo, cambio) == ("CANCELADA", True)
    assert f.fecha_solicitud_cancelacion is None


def test_en_proceso_mantiene_en_cancelacion_y_ancla_la_fecha():
    f = factura(estatus="TIMBRADA")
    nuevo, cambio = aplicar_acuse_sat(f, acuse(cancelacion="En proceso"), AHORA)
    assert (nuevo, cambio) == ("EN_CANCELACION", True)
    assert f.fecha_solicitud_cancelacion == AHORA


def test_receptor_rechazo_revierte_de_inmediato():
    f = factura(hace=timedelta(minutes=1))
    nuevo, cambio = aplicar_acuse_sat(f, acuse(cancelacion="Solicitud rechazada"), AHORA)
    assert (nuevo, cambio) == ("TIMBRADA", True)
    assert f.fecha_solicitud_cancelacion is None


def test_sin_solicitud_registrada_dentro_de_la_gracia_no_revierte():
    """El SAT puede tardar en publicar una solicitud recién enviada."""
    f = factura(hace=timedelta(minutes=MINUTOS_GRACIA_SOLICITUD - 1))
    nuevo, cambio = aplicar_acuse_sat(f, acuse(), AHORA)
    assert (nuevo, cambio) == ("EN_CANCELACION", False)


def test_sin_solicitud_registrada_pasada_la_gracia_revierte():
    """
    EstatusCancelacion vacío sobre un CFDI vigente = el SAT no tiene registrada
    ninguna solicitud. Es el caso A-2202: el PAC acusó recibo sin transmitirla.
    """
    f = factura(hace=timedelta(minutes=MINUTOS_GRACIA_SOLICITUD + 1))
    nuevo, cambio = aplicar_acuse_sat(f, acuse(), AHORA)
    assert (nuevo, cambio) == ("TIMBRADA", True)
    assert f.fecha_solicitud_cancelacion is None


def test_no_cancelable_sin_solicitud_tambien_revierte():
    # Atado a la constante a propósito: con un valor en duro, subir el margen
    # de gracia dejaba la prueba midiendo otra cosa sin que nadie lo notara.
    f = factura(hace=timedelta(minutes=MINUTOS_GRACIA_SOLICITUD + 1))
    nuevo, _ = aplicar_acuse_sat(f, acuse(cancelable="No cancelable"), AHORA)
    assert nuevo == "TIMBRADA"


def test_sin_fecha_registrada_ancla_pero_no_revierte():
    f = factura(hace=None)
    nuevo, cambio = aplicar_acuse_sat(f, acuse(), AHORA)
    assert (nuevo, cambio) == ("EN_CANCELACION", False)
    assert f.fecha_solicitud_cancelacion == AHORA


def test_estatus_desconocido_revierte_solo_como_respaldo_tardio():
    """Un EstatusCancelacion que no sabemos interpretar no revierte enseguida."""
    raro = acuse(cancelacion="Situación no contemplada")
    reciente = factura(hace=timedelta(days=DIAS_CANCELACION_VENCIDA - 1))
    assert aplicar_acuse_sat(reciente, raro, AHORA) == ("EN_CANCELACION", False)

    viejo = factura(hace=timedelta(days=DIAS_CANCELACION_VENCIDA + 1))
    assert aplicar_acuse_sat(viejo, raro, AHORA) == ("TIMBRADA", True)


def test_cancelada_local_pero_vigente_en_sat_se_reconcilia():
    """El SAT es la fuente de verdad, aunque contradiga lo que guardamos."""
    f = factura(estatus="CANCELADA", hace=timedelta(days=1))
    nuevo, cambio = aplicar_acuse_sat(f, acuse(), AHORA)
    assert (nuevo, cambio) == ("TIMBRADA", True)


def test_timbrada_vigente_no_cambia():
    f = factura(estatus="TIMBRADA")
    assert aplicar_acuse_sat(f, acuse(), AHORA) == ("TIMBRADA", False)


# ─────────────────────────────────────────────────────────────────────────────
# Complementos de pago — misma lógica, otros nombres de estatus
# ─────────────────────────────────────────────────────────────────────────────

def pago_fake(estatus="EN_CANCELACION", hace=None):
    from app.models.pago import EstatusPago

    return SimpleNamespace(
        estatus=EstatusPago(estatus),
        uuid="81373179-8431-4B4B-8BB3-8AF0A126FB2E",
        fecha_solicitud_cancelacion=(AHORA - hace) if hace else None,
        cancelacion_message=None,
    )


def test_pago_cancelado_en_sat():
    p = pago_fake(hace=timedelta(hours=1))
    nuevo, cambio = aplicar_acuse_sat_pago(p, acuse(estado="Cancelado"), AHORA)
    assert (nuevo, cambio) == ("CANCELADO", True)


def test_pago_sin_solicitud_registrada_revierte_pasada_la_gracia():
    p = pago_fake(hace=timedelta(minutes=MINUTOS_GRACIA_SOLICITUD + 1))
    nuevo, cambio = aplicar_acuse_sat_pago(p, acuse(), AHORA)
    assert (nuevo, cambio) == ("TIMBRADO", True)


def test_pago_no_verificable_no_toca_el_estatus():
    p = pago_fake(estatus="CANCELADO")
    assert aplicar_acuse_sat_pago(p, acuse(codigo="N - 601"), AHORA) == ("CANCELADO", False)


# ─────────────────────────────────────────────────────────────────────────────
# Bitácora de intentos
# ─────────────────────────────────────────────────────────────────────────────

def _factura_persistida():
    """Factura suelta: la bitácora no tiene FK, así que basta con id y empresa."""
    from app.models.factura import Factura

    f = Factura()
    f.id = uuid.uuid4()
    f.empresa_id = uuid.uuid4()
    f.serie, f.folio = "A", 2291
    f.cfdi_uuid = "81373179-8431-4B4B-8BB3-8AF0A126FB2E"
    return f


def test_bitacora_registra_lo_que_dijeron_pac_y_sat(db_session):
    from app.services import cancelacion_intento_service as bitacora

    f = _factura_persistida()
    intento = bitacora.registrar(
        db_session, f,
        motivo="01", folio_sustitucion="5052E9F0-FEA8-4AA2-9E17-8ECDBBEBDEB2",
        pac_code="GT12", pac_message="Solicitud de cancelación recibida.",
        pac_codigo_conocido=True,
        acuse_sat=acuse(cancelable="No cancelable"),
        sat_registro_solicitud=False,
    )
    assert intento is not None
    assert intento.documento_tipo == "FACTURA"
    assert intento.documento_folio == "A-2291"
    assert intento.sat_registro_solicitud is False
    assert intento.sat_es_cancelable == "No cancelable"
    assert intento.resultado is None  # abierto


def test_bitacora_conserva_los_intentos_previos(db_session):
    """Es la razón de existir de la tabla: las columnas de Factura se pisan."""
    from app.services import cancelacion_intento_service as bitacora

    f = _factura_persistida()
    for code in ("GT12", "GT11"):
        bitacora.registrar(
            db_session, f, motivo="02", folio_sustitucion=None,
            pac_code=code, pac_message="x", sat_registro_solicitud=False,
        )
    intentos = bitacora.listar(db_session, documento_id=f.id)
    assert len(intentos) == 2
    assert {i.pac_code for i in intentos} == {"GT11", "GT12"}


def test_bitacora_registra_la_ausencia_del_acuse(db_session):
    """La ausencia es el hecho que desmiente al PAC cuando dice tenerlo."""
    from app.services import cancelacion_intento_service as bitacora

    f = _factura_persistida()
    bitacora.registrar(
        db_session, f, motivo="01", folio_sustitucion=None,
        pac_code="GT12", pac_message="x", sat_registro_solicitud=False,
    )
    bitacora.anotar_acuse(db_session, f, error="El PAC no devolvió el acuse.")
    intento = bitacora.ultimo_abierto(db_session, f)
    assert intento.acuse_path is None
    assert "no devolvió" in intento.acuse_error


def test_bitacora_cierra_el_intento_al_resolverse(db_session):
    from app.services import cancelacion_intento_service as bitacora

    f = _factura_persistida()
    bitacora.registrar(
        db_session, f, motivo="03", folio_sustitucion=None,
        pac_code="GT11", pac_message="x", sat_registro_solicitud=True,
    )
    bitacora.cerrar_si_resuelto(db_session, f, "EN_CANCELACION", "CANCELADA")
    intentos = bitacora.listar(db_session, documento_id=f.id)
    assert intentos[0].resultado == "CANCELADO"
    assert intentos[0].fecha_resultado is not None
    assert bitacora.ultimo_abierto(db_session, f) is None


def test_bitacora_marca_revertido_cuando_el_sat_no_aplico(db_session):
    from app.services import cancelacion_intento_service as bitacora

    f = _factura_persistida()
    bitacora.registrar(
        db_session, f, motivo="01", folio_sustitucion=None,
        pac_code="GT12", pac_message="x", sat_registro_solicitud=False,
    )
    bitacora.cerrar_si_resuelto(db_session, f, "EN_CANCELACION", "TIMBRADA")
    assert bitacora.listar(db_session, documento_id=f.id)[0].resultado == "REVERTIDO"


def test_bitacora_no_cierra_si_el_estatus_no_cambio(db_session):
    from app.services import cancelacion_intento_service as bitacora

    f = _factura_persistida()
    bitacora.registrar(
        db_session, f, motivo="01", folio_sustitucion=None,
        pac_code="GT12", pac_message="x", sat_registro_solicitud=None,
    )
    bitacora.cerrar_si_resuelto(db_session, f, "EN_CANCELACION", "EN_CANCELACION")
    assert bitacora.ultimo_abierto(db_session, f) is not None


def test_reporte_de_solicitudes_que_el_sat_nunca_registro(db_session):
    """La consulta que responde «¿el PAC falla de forma sistemática?»."""
    from app.services import cancelacion_intento_service as bitacora

    perdida = _factura_persistida()
    buena = _factura_persistida()
    bitacora.registrar(
        db_session, perdida, motivo="01", folio_sustitucion=None,
        pac_code="GT12", pac_message="x", sat_registro_solicitud=False,
    )
    bitacora.registrar(
        db_session, buena, motivo="01", folio_sustitucion=None,
        pac_code="GT12", pac_message="x", sat_registro_solicitud=True,
    )
    sin_registro = bitacora.listar(db_session, solo_no_registrados=True)
    assert [i.documento_id for i in sin_registro] == [perdida.id]


def test_resumen_solo_cuenta_envios_observados(db_session):
    """
    Los renglones RECONSTRUIDOS (sembrados desde las columnas del documento)
    quedan fuera del resumen: nadie observó qué decía el SAT al enviarlos, así
    que contarlos falsearía el porcentaje de solicitudes perdidas.
    """
    from app.models.cancelacion_intento import RECONSTRUIDO
    from app.services import cancelacion_intento_service as bitacora

    perdida, buena, vieja = (_factura_persistida() for _ in range(3))
    bitacora.registrar(
        db_session, perdida, motivo="01", folio_sustitucion=None,
        pac_code="GT12", pac_message="x", sat_registro_solicitud=False,
    )
    bitacora.registrar(
        db_session, buena, motivo="01", folio_sustitucion=None,
        pac_code="GT11", pac_message="x", sat_registro_solicitud=True,
    )
    bitacora.registrar(
        db_session, vieja, motivo="01", folio_sustitucion=None,
        pac_code="GT11", pac_message="x", sat_registro_solicitud=None,
        origen=RECONSTRUIDO,
    )

    r = bitacora.resumen(db_session)
    assert r["total_envios"] == 2
    assert r["sat_nunca_la_registro"] == 1
    assert r["sat_registro_la_solicitud"] == 1
    assert r["porcentaje_no_registradas"] == 50.0
    assert r["codigos_del_pac"] == {"GT12": 1, "GT11": 1}
    assert r["abiertas"] == 2


def test_resumen_cuenta_los_desenlaces(db_session):
    from app.services import cancelacion_intento_service as bitacora

    ok, mala = _factura_persistida(), _factura_persistida()
    for doc in (ok, mala):
        bitacora.registrar(
            db_session, doc, motivo="02", folio_sustitucion=None,
            pac_code="GT05", pac_message="x", sat_registro_solicitud=True,
        )
    bitacora.cerrar_si_resuelto(db_session, ok, "EN_CANCELACION", "CANCELADA")
    bitacora.cerrar_si_resuelto(db_session, mala, "EN_CANCELACION", "TIMBRADA")

    r = bitacora.resumen(db_session)
    assert (r["canceladas"], r["revertidas"], r["abiertas"]) == (1, 1, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Reintento de la consulta al SAT tras enviar la solicitud
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sat_falso(monkeypatch):
    """Sustituye la consulta al SAT y quita la espera entre reintentos."""
    from app.services import sat_cfdi_service, timbrado_factmoderna

    monkeypatch.setattr(timbrado_factmoderna, "ESPERA_ENTRE_CONSULTAS_SEG", 0)
    llamadas = []

    def instalar(respuestas):
        def fake(**kw):
            llamadas.append(kw)
            r = respuestas[min(len(llamadas) - 1, len(respuestas) - 1)]
            if isinstance(r, Exception):
                raise r
            return r

        monkeypatch.setattr(sat_cfdi_service, "consultar_cfdi", fake)
        return llamadas

    return instalar


def _consultar():
    from app.services.timbrado_factmoderna import _consultar_sat_tras_envio

    return _consultar_sat_tras_envio(
        rfc_emisor="GAOA611225II9", rfc_receptor="PME140722QM7",
        total=100.0, uuid="81373179-8431-4B4B-8BB3-8AF0A126FB2E",
    )


def test_sat_reporta_en_proceso_a_la_primera_no_reintenta(sat_falso):
    llamadas = sat_falso([acuse(cancelacion="En proceso")])
    _acuse, registro = _consultar()
    assert registro is True
    assert len(llamadas) == 1


def test_sat_vacio_reintenta_y_acaba_reportando_que_no_hay_registro(sat_falso):
    from app.services.timbrado_factmoderna import REINTENTOS_CONSULTA_SAT

    llamadas = sat_falso([acuse()])
    _acuse, registro = _consultar()
    assert registro is False
    assert len(llamadas) == REINTENTOS_CONSULTA_SAT + 1


def test_sat_tarda_pero_acaba_registrando_la_solicitud(sat_falso):
    """El caso que el reintento existe para no marcar como perdido."""
    llamadas = sat_falso([acuse(), acuse(cancelacion="En proceso")])
    _acuse, registro = _consultar()
    assert registro is True
    assert len(llamadas) == 2


def test_cancelacion_inmediata_se_detecta_sin_reintentos(sat_falso):
    llamadas = sat_falso([acuse(estado="Cancelado", cancelacion="Cancelado sin aceptación")])
    _acuse, registro = _consultar()
    assert registro is True
    assert len(llamadas) == 1


def test_sat_caido_devuelve_none_y_no_reintenta(sat_falso):
    llamadas = sat_falso([RuntimeError("timeout")])
    acuse_sat, registro = _consultar()
    assert (acuse_sat, registro) == (None, None)
    assert len(llamadas) == 1


def test_cfdi_no_encontrado_no_reintenta(sat_falso):
    llamadas = sat_falso([acuse(codigo="N - 601")])
    _acuse, registro = _consultar()
    assert registro is None
    assert len(llamadas) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Segunda opinión del PAC (consultarEstatusCFDI)
# ─────────────────────────────────────────────────────────────────────────────

def test_parseo_de_consultar_estatus_cfdi():
    from xml.etree.ElementTree import fromstring

    from app.services.timbrado_factmoderna import _parse_estatus_response

    respuesta = b"""<?xml version="1.0"?>
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
      <SOAP-ENV:Body><ns1:consultarEstatusCFDIResponse
          xmlns:ns1="https://t1demo.facturacionmoderna.com/timbrado/soap">
        <return>
          <http_code>200</http_code>
          <estado>Cancelado</estado>
          <esCancelable>Cancelable con aceptacion</esCancelable>
          <estatusCancelacion>Plazo vencido</estatusCancelacion>
        </return>
      </ns1:consultarEstatusCFDIResponse></SOAP-ENV:Body>
    </SOAP-ENV:Envelope>"""

    datos = _parse_estatus_response(fromstring(respuesta))
    assert datos == {
        "http_code": "200",
        "estado": "Cancelado",
        "es_cancelable": "Cancelable con aceptacion",
        "estatus_cancelacion": "Plazo vencido",
    }


def test_el_envelope_de_estatus_lleva_los_seis_parametros():
    from app.services.timbrado_factmoderna import _soap_consultar_estatus_envelope

    xml = _soap_consultar_estatus_envelope(
        user_id="u", user_pass="p", emisor_rfc="GAOA611225II9",
        receptor_rfc="PME140722QM7", total="1160.00", uuid="ABC",
    ).decode("utf-8")
    for campo in ("UserPass", "UserID", "emisorRFC", "receptorRFC", "total", "UUID"):
        assert f"<{campo}" in xml
    assert "consultarEstatusCFDI" in xml


def test_la_segunda_opinion_se_guarda_en_la_bitacora(db_session):
    from app.services import cancelacion_intento_service as bitacora

    f = _factura_persistida()
    intento = bitacora.registrar(
        db_session, f, motivo="01", folio_sustitucion=None,
        pac_code="GT12", pac_message="recibida", sat_registro_solicitud=False,
        pac_consulta={"estado": "Vigente", "estatus_cancelacion": ""},
    )
    assert intento.pac_consulta_estado == "Vigente"
    assert intento.pac_consulta_estatus_cancelacion == ""


def test_consultar_estatus_nunca_lanza(monkeypatch):
    """Es evidencia, no parte del trámite: si falla, devuelve {} y sigue."""
    from app.services import timbrado_factmoderna as t

    def explota(*a, **kw):
        raise RuntimeError("PAC caído")

    monkeypatch.setattr(t, "_soap_consultar_estatus_envelope", explota)
    pac = t.FacturacionModernaPAC()
    assert pac.consultar_estatus_cfdi(
        emisor_rfc="A", receptor_rfc="B", total=1.0, uuid="X"
    ) == {}


# ─────────────────────────────────────────────────────────────────────────────
# Registrar una cancelación hecha en el portal del SAT
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def factura_timbrada(db_session):
    from app.models.cliente import Cliente
    from app.models.empresa import Empresa
    from app.models.factura import Factura

    emp = Empresa(
        nombre="NORTON", nombre_comercial="NORTON", ruc="RUC-P",
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
        serie="A", folio=2202, empresa_id=emp.id, cliente_id=cli.id,
        estatus="TIMBRADA", total=1160,
        cfdi_uuid="89697BD3-2F34-4997-8978-A32B28187197",
        cfdi_rfc_emisor="GAOA611225II9", cfdi_rfc_receptor="PME140722QM7",
        cfdi_total=1160,
    )
    db_session.add(f)
    db_session.commit()
    return f


@pytest.fixture
def sat_dice(monkeypatch):
    from app.services import sat_cfdi_service

    def instalar(respuesta):
        monkeypatch.setattr(sat_cfdi_service, "consultar_cfdi", lambda **kw: respuesta)

    return instalar


def test_portal_rechaza_si_el_sat_no_ve_ninguna_cancelacion(db_session, factura_timbrada, sat_dice):
    """No se cree lo que diga el usuario: manda lo que el SAT reporte."""
    from fastapi import HTTPException

    from app.services.factura_service import registrar_cancelacion_portal

    sat_dice(acuse())  # Vigente, sin trámite
    with pytest.raises(HTTPException) as e:
        registrar_cancelacion_portal(db_session, factura_timbrada)
    assert e.value.status_code == 400
    assert "no tiene registrada ninguna cancelación" in e.value.detail
    assert factura_timbrada.estatus == "TIMBRADA"


def test_portal_rechaza_si_el_sat_no_reconoce_el_cfdi(db_session, factura_timbrada, sat_dice):
    from fastapi import HTTPException

    from app.services.factura_service import registrar_cancelacion_portal

    sat_dice(acuse(codigo="N - 602"))
    with pytest.raises(HTTPException) as e:
        registrar_cancelacion_portal(db_session, factura_timbrada)
    assert e.value.status_code == 404


def test_portal_registra_cancelacion_confirmada(db_session, factura_timbrada, sat_dice):
    from app.services import cancelacion_intento_service as bitacora
    from app.services.factura_service import registrar_cancelacion_portal

    sat_dice(acuse(estado="Cancelado", cancelacion="Plazo vencido"))
    r = registrar_cancelacion_portal(
        db_session, factura_timbrada,
        motivo="01", folio_sustitucion="5052E9F0-FEA8-4AA2-9E17-8ECDBBEBDEB2",
    )

    assert r["estatus_nuevo"] == "CANCELADA"
    assert factura_timbrada.estatus == "CANCELADA"
    assert factura_timbrada.cancelacion_code == "SAT-PORTAL"
    assert factura_timbrada.motivo_cancelacion == "01"
    assert factura_timbrada.fecha_solicitud_cancelacion is None

    intentos = bitacora.listar(db_session, documento_id=factura_timbrada.id)
    assert len(intentos) == 1
    assert intentos[0].origen == "PORTAL_SAT"
    assert intentos[0].resultado == "CANCELADO"


def test_portal_registra_cancelacion_en_proceso(db_session, factura_timbrada, sat_dice):
    from app.services import cancelacion_intento_service as bitacora
    from app.services.factura_service import registrar_cancelacion_portal

    sat_dice(acuse(cancelacion="En proceso"))
    r = registrar_cancelacion_portal(db_session, factura_timbrada, motivo="02")

    assert r["estatus_nuevo"] == "EN_CANCELACION"
    assert factura_timbrada.fecha_solicitud_cancelacion is not None
    # Queda abierto para que el cron lo cierre cuando el SAT resuelva.
    assert bitacora.ultimo_abierto(db_session, factura_timbrada) is not None


def test_portal_guarda_el_acuse_sellado(db_session, factura_timbrada, sat_dice, tmp_path, monkeypatch):
    from app.config import settings
    from app.services.factura_service import registrar_cancelacion_portal

    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    sat_dice(acuse(estado="Cancelado", cancelacion="Cancelado con aceptación"))

    xml = b'<?xml version="1.0"?><Acuse RfcEmisor="GAOA611225II9"/>'
    r = registrar_cancelacion_portal(db_session, factura_timbrada, acuse_xml=xml)

    assert r["acuse_guardado"] is True
    guardado = tmp_path / "acuses" / f"{factura_timbrada.cfdi_uuid}.portal.xml"
    assert guardado.read_bytes() == xml
    # No pisa el acuse que hubiera bajado del PAC: usa un nombre distinto.
    assert factura_timbrada.cancelacion_acuse_path.endswith(".portal.xml")


# ─────────────────────────────────────────────────────────────────────────────
# Margen de gracia y limpieza del aviso pegado
# ─────────────────────────────────────────────────────────────────────────────

def test_el_margen_de_gracia_es_de_seis_horas():
    """
    Subido de 30 min a 6 h el 20-ago-2026: el SAT tardó ~16 minutos reales en
    reflejar solicitudes que sí habían entrado, contra los "2 a 3 minutos" que
    promete el PAC. Revertir a TIMBRADA algo que sí está en curso lo saca del
    radar del cron, así que el margen debe sobrar, no faltar.
    """
    assert MINUTOS_GRACIA_SOLICITUD == 360


def test_el_retraso_real_observado_no_revierte():
    """Los 16 minutos que tardó el SAT con A-961 no deben tocar el estatus."""
    f = factura(hace=timedelta(minutes=16))
    assert aplicar_acuse_sat(f, acuse(), AHORA) == ("EN_CANCELACION", False)


def test_a_las_cinco_horas_todavia_espera():
    f = factura(hace=timedelta(hours=5))
    assert aplicar_acuse_sat(f, acuse(), AHORA) == ("EN_CANCELACION", False)


def test_pasadas_las_seis_horas_si_revierte():
    f = factura(hace=timedelta(hours=6, minutes=1))
    assert aplicar_acuse_sat(f, acuse(), AHORA) == ("TIMBRADA", True)


AVISO = ("Solicitud de cancelación recibida. ⚠ El SAT todavía no registra esta "
         "solicitud (EstatusCancelacion vacío).")


def test_el_aviso_se_limpia_cuando_el_sat_reporta_en_proceso():
    """Es lo que le pasó a A-22130: seguía mostrando el aviso ya estando en proceso."""
    f = factura(hace=timedelta(minutes=20), mensaje=AVISO)
    aplicar_acuse_sat(f, acuse(cancelacion="En proceso"), AHORA)
    assert "todavía no registra" not in (f.cancelacion_message or "")
    assert f.cancelacion_message == "Solicitud de cancelación recibida."


def test_el_aviso_se_limpia_cuando_el_sat_confirma_la_cancelacion():
    f = factura(hace=timedelta(minutes=20), mensaje=AVISO)
    aplicar_acuse_sat(f, acuse(estado="Cancelado"), AHORA)
    assert "todavía no registra" not in (f.cancelacion_message or "")


def test_el_aviso_sigue_mientras_el_sat_no_reporte_nada():
    f = factura(hace=timedelta(minutes=20), mensaje=AVISO)
    aplicar_acuse_sat(f, acuse(), AHORA)
    assert "todavía no registra" in f.cancelacion_message


def test_no_toca_mensajes_que_no_traen_la_marca():
    f = factura(hace=timedelta(minutes=20), mensaje="Solicitud recibida.")
    aplicar_acuse_sat(f, acuse(cancelacion="En proceso"), AHORA)
    assert f.cancelacion_message == "Solicitud recibida."


# ─────────────────────────────────────────────────────────────────────────────
# "Solicitud previa": el PAC bloquea el reenvío
# ─────────────────────────────────────────────────────────────────────────────

FAULT_PREVIA = b"""<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Body><SOAP-ENV:Fault>
   <faultcode>SOAP-ENV:Server</faultcode>
   <faultstring>El UUID tiene una solicitud de cancelacion previa.</faultstring>
 </SOAP-ENV:Fault></SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


def test_extrae_el_faultstring_real_del_pac():
    """Antes se inventaba el código '202', que el PAC nunca devuelve."""
    from app.services.timbrado_factmoderna import _faultstring

    assert _faultstring(FAULT_PREVIA) == "El UUID tiene una solicitud de cancelacion previa."
    assert _faultstring(b"no es xml") is None


@pytest.fixture
def pac_responde_previa(monkeypatch):
    """El PAC contesta HTTP 500 con el fault de 'solicitud previa'."""
    import httpx

    from app.services import timbrado_factmoderna as t

    class RespFalsa:
        status_code = 500
        content = FAULT_PREVIA
        text = FAULT_PREVIA.decode()

    class ClienteFalso:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **kw): return RespFalsa()

    monkeypatch.setattr(httpx, "Client", ClienteFalso)
    # Sin esto, cada prueba que no encuentra la solicitud en el SAT duerme de
    # verdad los reintentos y la suite completa se va de 6 a 30 segundos.
    monkeypatch.setattr(t, "ESPERA_ENTRE_CONSULTAS_SEG", 0)
    monkeypatch.setattr(t, "_fm_user_id", lambda: "u")
    monkeypatch.setattr(t, "_fm_user_pass", lambda: "p")
    monkeypatch.setattr(t, "_fm_url", lambda: "http://pac.invalido")


def _cancelar(db, doc):
    from app.services.timbrado_factmoderna import FacturacionModernaPAC

    return FacturacionModernaPAC().solicitar_cancelacion_cfdi(
        db=db, factura_id=doc.id, motivo="02", folio_sustitucion=None
    )


def test_previa_sin_registro_en_sat_deja_rastro_y_avisa(
    db_session, factura_timbrada, pac_responde_previa, sat_dice
):
    """
    El caso A-22069: el PAC bloquea el reenvío por una solicitud previa que el
    SAT nunca recibió. Antes esto salía sin escribir bitácora, sin guardar
    código ni mensaje, y con un '202' inventado.
    """
    from app.services import cancelacion_intento_service as bitacora

    sat_dice(acuse())  # Vigente, sin trámite alguno
    out = _cancelar(db_session, factura_timbrada)

    assert out["code"] == "PAC-PREVIA"
    assert out["sat_registro_solicitud"] is False
    assert factura_timbrada.estatus == "EN_CANCELACION"
    assert factura_timbrada.cancelacion_code == "PAC-PREVIA"
    assert "portal del SAT" in factura_timbrada.cancelacion_message
    assert "no registra" in factura_timbrada.cancelacion_message

    intentos = bitacora.listar(db_session, documento_id=factura_timbrada.id)
    assert len(intentos) == 1
    assert intentos[0].pac_code == "PAC-PREVIA"
    assert intentos[0].pac_codigo_conocido is None
    assert "previa" in intentos[0].pac_message


def test_previa_con_solicitud_viva_en_sat_no_alarma(
    db_session, factura_timbrada, pac_responde_previa, sat_dice
):
    """Si el SAT sí confirma la solicitud previa, no hay nada que reportar."""
    sat_dice(acuse(cancelacion="En proceso"))
    out = _cancelar(db_session, factura_timbrada)

    assert out["sat_registro_solicitud"] is True
    assert factura_timbrada.estatus == "EN_CANCELACION"
    assert "sigue en curso" in factura_timbrada.cancelacion_message
    assert "portal del SAT" not in factura_timbrada.cancelacion_message


def test_previa_con_cfdi_ya_cancelado_se_sincroniza(
    db_session, factura_timbrada, pac_responde_previa, sat_dice
):
    """La solicitud previa ya prosperó: el estatus debe reflejarlo."""
    sat_dice(acuse(estado="Cancelado", cancelacion="Plazo vencido"))
    out = _cancelar(db_session, factura_timbrada)

    assert out["estatus"] == "CANCELADA"
    assert factura_timbrada.fecha_solicitud_cancelacion is None


def test_previa_reinicia_la_fecha_de_solicitud(
    db_session, factura_timbrada, pac_responde_previa, sat_dice
):
    """
    Antes sólo la fijaba si estaba vacía, así que un reintento heredaba la fecha
    del intento anterior y el margen de gracia se contaba desde entonces.
    """
    vieja = datetime(2026, 1, 1, 0, 0, 0)
    factura_timbrada.estatus = "EN_CANCELACION"
    factura_timbrada.fecha_solicitud_cancelacion = vieja
    db_session.commit()

    sat_dice(acuse())
    _cancelar(db_session, factura_timbrada)
    assert factura_timbrada.fecha_solicitud_cancelacion > vieja


# ─────────────────────────────────────────────────────────────────────────────
# Las dos ventanas del cron
# ─────────────────────────────────────────────────────────────────────────────

def test_cada_ventana_tiene_su_propio_candado():
    """
    Con un candado compartido, los dos jobs se registran en el mismo instante,
    sus intervalos quedan en fase y cada 2 h el de seguimiento dispara en el
    mismo segundo que la ventana caliente: como ésta toma el candado primero, el
    seguimiento se salta siempre. Pasó 45 horas sin correr ni una vez.
    Las dos ventanas procesan conjuntos disjuntos, así que correr a la vez es
    seguro y cada una necesita su propia clave.
    """
    from app.main import _SAT_SYNC_LOCK_KEYS

    assert _SAT_SYNC_LOCK_KEYS[True] != _SAT_SYNC_LOCK_KEYS[False]
    assert len(set(_SAT_SYNC_LOCK_KEYS.values())) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Validación del sustituto en motivo 01
# ─────────────────────────────────────────────────────────────────────────────

def _sustituta(db_session, original, *, estatus="TIMBRADA", tipo="04", apunta_a=None):
    """Factura que dice sustituir a `original`."""
    from app.models.factura import Factura

    f = Factura()
    f.id = uuid.uuid4()
    f.empresa_id = original.empresa_id
    f.cliente_id = original.cliente_id
    f.serie, f.folio = "A", 9001
    f.cfdi_uuid = str(uuid.uuid4()).upper()
    f.estatus = estatus
    f.total = original.total
    f.cfdi_relacionados_tipo = tipo
    f.cfdi_relacionados = (apunta_a or original.cfdi_uuid).upper()
    db_session.add(f)
    db_session.commit()
    return f


def _validar(db_session, original, sustituta_uuid):
    from app.services.factura_service import _validar_sustitucion_motivo_01

    _validar_sustitucion_motivo_01(db_session, original, sustituta_uuid)


def test_sustituta_cancelada_bloquea_el_motivo_01(db_session, factura_timbrada):
    """
    Caso A-785: declaraba a A-1202 como sustituta estando A-1202 cancelada. El
    SAT descartó la solicitud sin avisar y el trámite se perdió dos días.
    """
    from fastapi import HTTPException

    sus = _sustituta(db_session, factura_timbrada, estatus="CANCELADA")
    with pytest.raises(HTTPException) as e:
        _validar(db_session, factura_timbrada, sus.cfdi_uuid)
    assert e.value.status_code == 400
    assert "está CANCELADA" in e.value.detail      # concuerda con «la factura»
    assert "la factura A-9001" in e.value.detail   # dice qué es y cuál


def test_el_mensaje_distingue_un_complemento_de_pago(db_session, factura_timbrada):
    """El sustituto puede ser un complemento; hay que nombrarlo como tal."""
    from fastapi import HTTPException

    from app.models.pago import EstatusPago, Pago

    p = Pago()
    p.id = uuid.uuid4()
    p.empresa_id = factura_timbrada.empresa_id
    p.cliente_id = factura_timbrada.cliente_id
    p.serie, p.folio = "P", "312"
    p.uuid = str(uuid.uuid4()).upper()
    p.estatus = EstatusPago.CANCELADO
    p.fecha_pago = AHORA
    p.forma_pago_p, p.moneda_p, p.monto = "03", "MXN", 100
    db_session.add(p)
    db_session.commit()

    with pytest.raises(HTTPException) as e:
        _validar(db_session, factura_timbrada, p.uuid)
    assert "el complemento de pago P-312" in e.value.detail
    assert "está CANCELADO" in e.value.detail      # concuerda con «el complemento»


def test_sustituta_vigente_y_bien_relacionada_pasa(db_session, factura_timbrada):
    sus = _sustituta(db_session, factura_timbrada)
    _validar(db_session, factura_timbrada, sus.cfdi_uuid)  # no lanza


def test_sustituta_vigente_pero_apuntando_a_otro_cfdi_bloquea(db_session, factura_timbrada):
    from fastapi import HTTPException

    otro = str(uuid.uuid4()).upper()
    sus = _sustituta(db_session, factura_timbrada, apunta_a=otro)
    with pytest.raises(HTTPException) as e:
        _validar(db_session, factura_timbrada, sus.cfdi_uuid)
    assert "apunta a otro CFDI" in e.value.detail
    assert "la factura A-9001" in e.value.detail


def test_sustituta_con_tipo_equivocado_bloquea(db_session, factura_timbrada):
    from fastapi import HTTPException

    sus = _sustituta(db_session, factura_timbrada, tipo="01")
    with pytest.raises(HTTPException) as e:
        _validar(db_session, factura_timbrada, sus.cfdi_uuid)
    assert "'01' en lugar de '04'" in e.value.detail


def test_sustituto_que_no_esta_en_la_base_no_bloquea(db_session, factura_timbrada):
    """No se puede validar lo que no se tiene; se deja pasar como antes."""
    _validar(db_session, factura_timbrada, str(uuid.uuid4()).upper())


# ─────────────────────────────────────────────────────────────────────────────
# «No cancelable»: distinguir quién lo traba
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def diag_dice(monkeypatch):
    """Sustituye el diagnóstico del SAT por uno controlado."""
    from app.services import factura_service

    def instalar(*, complementos=None, relacionadas=None):
        d = {
            "puede_cancelar": True,
            "motivo": None,
            "advertencia": "El SAT reporta esta factura como «No cancelable»…",
            "estado_sat": "Vigente",
            "es_cancelable": "No cancelable",
            "complementos": complementos or [],
            "relacionadas": relacionadas or [],
        }
        if complementos:
            d["advertencia"] = (
                "El SAT reporta esta factura como «No cancelable» porque tiene "
                f"relacionado el complemento de pago {complementos[0]['folio']}. "
                "Debe cancelarse primero ese complemento y después la factura."
            )
        monkeypatch.setattr(factura_service, "diagnostico_cancelacion", lambda db, doc: d)

    return instalar


def _cancelar_servicio(db_session, factura, motivo, sustituto=None):
    from app.services.factura_service import solicitar_cancelacion_cfdi

    return solicitar_cancelacion_cfdi(db_session, factura.id, motivo, sustituto)


@pytest.mark.parametrize("motivo", ["01", "02", "03"])
def test_trabada_por_complemento_manda_a_cancelar_el_complemento(
    db_session, factura_timbrada, diag_dice, motivo
):
    """
    Con cualquier motivo. El error de esta mañana fue mandar a usar motivo 01 a
    facturas trabadas por un complemento (A-783 y A-787, detenidas por P-299).
    """
    from fastapi import HTTPException

    diag_dice(complementos=[{"id": "x", "folio": "P-299", "estatus": "TIMBRADO"}])
    with pytest.raises(HTTPException) as e:
        _cancelar_servicio(db_session, factura_timbrada, motivo, "algo")
    assert "P-299" in e.value.detail
    assert "cancelarse primero ese complemento" in e.value.detail
    assert "motivo 01" not in e.value.detail  # ya no manda por ahí


def test_trabada_por_sustituta_sigue_exigiendo_motivo_01(
    db_session, factura_timbrada, diag_dice
):
    from fastapi import HTTPException

    diag_dice(relacionadas=[{"id": "y", "folio": "A-1207", "tipo_relacion": "04"}])
    with pytest.raises(HTTPException) as e:
        _cancelar_servicio(db_session, factura_timbrada, "02", None)
    assert "motivo 01" in e.value.detail


def test_trabada_por_sustituta_con_motivo_01_no_la_detiene_la_guarda(
    db_session, factura_timbrada, diag_dice, monkeypatch
):
    """Es el caso de A-888: la guarda debe dejarla pasar hacia el PAC."""
    from app.services import factura_service

    diag_dice(relacionadas=[{"id": "y", "folio": "A-1207", "tipo_relacion": "04"}])
    llamadas = []
    monkeypatch.setattr(
        factura_service._pac, "solicitar_cancelacion_cfdi",
        lambda **kw: llamadas.append(kw) or {"estatus": "EN_CANCELACION", "code": "GT12"},
    )
    monkeypatch.setattr(factura_service, "_archivar_acuse_cancelacion", lambda db, d: None)
    monkeypatch.setattr(factura_service, "_validar_sustitucion_motivo_01",
                        lambda db, f, folio: None)

    _cancelar_servicio(db_session, factura_timbrada, "01", str(uuid.uuid4()))
    assert len(llamadas) == 1  # llegó al PAC


# ─────────────────────────────────────────────────────────────────────────────
# Reintento del acuse: sólo cuando el trámite pasó por el PAC
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def acuse_espia(monkeypatch):
    """Cuenta cuántas veces se intenta bajar el acuse."""
    from app.services import factura_service

    intentos = []
    monkeypatch.setattr(factura_service, "_archivar_acuse_cancelacion",
                        lambda db, doc: intentos.append(doc))
    return intentos


def _doc(code=None, acuse=None):
    return SimpleNamespace(id="x", cancelacion_code=code, cancelacion_acuse_path=acuse)


def test_no_reintenta_el_acuse_si_ya_lo_tiene(acuse_espia):
    from app.main import _reintentar_acuse

    _reintentar_acuse(None, _doc(code="GT12", acuse="acuses/x.xml"))
    assert acuse_espia == []


def test_no_reintenta_si_el_tramite_no_paso_por_el_pac(acuse_espia):
    """
    A-130, A-784 y A-926 se cancelaron en el portal del SAT: el PAC no va a
    tener acuse nunca. Antes se les pedía cada 15 minutos, para siempre.
    """
    from app.main import _reintentar_acuse

    _reintentar_acuse(None, _doc(code=None))
    _reintentar_acuse(None, _doc(code=""))
    assert acuse_espia == []


def test_no_reintenta_las_registradas_del_portal(acuse_espia):
    from app.main import _reintentar_acuse
    from app.services.factura_service import CODIGO_SAT_PORTAL

    _reintentar_acuse(None, _doc(code=CODIGO_SAT_PORTAL))
    assert acuse_espia == []


@pytest.mark.parametrize("code", ["GT12", "GT11", "GT05", "PAC-PREVIA"])
def test_si_reintenta_cuando_salio_por_el_pac(acuse_espia, code):
    from app.main import _reintentar_acuse

    _reintentar_acuse(None, _doc(code=code))
    assert len(acuse_espia) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Write-ahead del envío y candado de un envío en vuelo
#
# El renglón de la bitácora se escribe ANTES del POST al PAC. Sin eso, una
# llamada que no vuelve —timeout, corte, reinicio— es indistinguible de una que
# nunca ocurrió, aunque el PAC la haya recibido: registra la solicitud al
# recibirla, no al contestar. Ese hueco es el que fabrica los "solicitud previa"
# que nadie puede explicar (A-22069, siete reintentos rebotando).
# ─────────────────────────────────────────────────────────────────────────────

EXITO_GT11 = b"""<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:ns1="https://t1demo.facturacionmoderna.com/timbrado/soap">
 <SOAP-ENV:Body><ns1:requestCancelarCFDIResponse>
   <return><Code>GT11</Code><Message>Solicitud de cancelacion recibida.</Message></return>
 </ns1:requestCancelarCFDIResponse></SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

FAULT_OTRO = b"""<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Body><SOAP-ENV:Fault>
   <faultcode>SOAP-ENV:Server</faultcode>
   <faultstring>Certificado de sello digital revocado.</faultstring>
 </SOAP-ENV:Fault></SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


@pytest.fixture
def pac(monkeypatch):
    """Instala una respuesta del PAC, o una excepción de red si se pide."""
    import httpx

    from app.services import timbrado_factmoderna as t

    monkeypatch.setattr(t, "ESPERA_ENTRE_CONSULTAS_SEG", 0)
    monkeypatch.setattr(t, "_fm_user_id", lambda: "u")
    monkeypatch.setattr(t, "_fm_user_pass", lambda: "p")
    monkeypatch.setattr(t, "_fm_url", lambda: "http://pac.invalido")

    def instalar(*, status=200, body=EXITO_GT11, revienta=None):
        class RespFalsa:
            status_code = status
            content = body
            text = body.decode()

        class ClienteFalso:
            def __init__(self, *a, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False

            def post(self, *a, **kw):
                if revienta is not None:
                    raise revienta
                return RespFalsa()

        monkeypatch.setattr(httpx, "Client", ClienteFalso)

    return instalar


def _intentos(db, doc):
    from app.services import cancelacion_intento_service as bitacora

    return bitacora.listar(db, documento_id=doc.id)


def test_una_llamada_que_no_vuelve_deja_rastro_igual(
    db_session, factura_timbrada, pac, sat_dice
):
    """
    El write-ahead en su caso puro: el POST truena y aun así queda constancia.

    Antes no quedaba ninguna, y esa es justamente la situación en la que el PAC
    sí pudo haber recibido la solicitud.
    """
    import httpx

    sat_dice(acuse())
    pac(revienta=httpx.ReadTimeout("se acabó el tiempo"))

    with pytest.raises(RuntimeError, match="Error de red"):
        _cancelar(db_session, factura_timbrada)

    intentos = _intentos(db_session, factura_timbrada)
    assert len(intentos) == 1
    assert intentos[0].envio == "SIN_RESPUESTA"
    assert "se acabó el tiempo" in intentos[0].pac_message
    # El comprobante no se mueve: nadie sabe todavía si la solicitud llegó.
    assert factura_timbrada.estatus == "TIMBRADA"


def test_un_error_del_pac_no_deja_nada_que_reconciliar(
    db_session, factura_timbrada, pac, sat_dice
):
    """
    Si el PAC contestó —aunque sea con un error— sí se sabe qué pasó: no hubo
    solicitud. El renglón se cierra RESPONDIDO y el reconciliador no lo toca.
    """
    sat_dice(acuse())
    pac(status=500, body=FAULT_OTRO)

    with pytest.raises(RuntimeError):
        _cancelar(db_session, factura_timbrada)

    intentos = _intentos(db_session, factura_timbrada)
    assert len(intentos) == 1
    assert intentos[0].envio == "RESPONDIDO"
    assert "HTTP 500" in intentos[0].pac_message


def test_el_envio_normal_completa_el_renglon_que_abrio(
    db_session, factura_timbrada, pac, sat_dice
):
    """Un solo renglón por envío: se abre antes del POST y se completa después."""
    sat_dice(acuse(cancelacion="En proceso"))
    pac()

    out = _cancelar(db_session, factura_timbrada)

    assert out["code"] == "GT11"
    intentos = _intentos(db_session, factura_timbrada)
    assert len(intentos) == 1
    assert intentos[0].envio == "RESPONDIDO"
    assert intentos[0].pac_code == "GT11"
    assert intentos[0].sat_registro_solicitud is True
    assert factura_timbrada.estatus == "EN_CANCELACION"


def test_la_base_impide_dos_envios_en_vuelo_a_la_vez(db_session, factura_timbrada):
    """
    El candado de último recurso: un índice único parcial, no la buena voluntad
    del código. Dos solicitudes simultáneas son lo que fabrica la "previa".
    """
    from fastapi import HTTPException

    from app.services import cancelacion_intento_service as bitacora

    primero = bitacora.abrir(
        db_session, factura_timbrada, motivo="02", folio_sustitucion=None
    )
    assert primero is not None
    db_session.commit()

    with pytest.raises(HTTPException) as e:
        bitacora.abrir(
            db_session, factura_timbrada, motivo="02", folio_sustitucion=None
        )
    assert e.value.status_code == 409
    assert "en curso" in e.value.detail


def test_un_envio_recien_salido_rechaza_el_segundo(db_session, factura_timbrada):
    """El doble clic, o el usuario y el cron al mismo tiempo."""
    from fastapi import HTTPException

    from app.services import cancelacion_intento_service as bitacora

    bitacora.abrir(db_session, factura_timbrada, motivo="02", folio_sustitucion=None)
    db_session.commit()

    with pytest.raises(HTTPException) as e:
        bitacora.tomar_candado(db_session, factura_timbrada)
    assert e.value.status_code == 409
    assert "hace unos segundos" in e.value.detail


def test_un_envio_huerfano_no_bloquea_para_siempre(
    db_session, factura_timbrada, sat_dice
):
    """
    Un envío viejo en ENVIANDO ya no es una llamada viva: es un huérfano. Se
    resuelve contra el SAT y se deja pasar el reintento.

    Mantener el candado puesto ahí sería bloquear un trámite legal por una falla
    nuestra, que es el error que ya se cometió dos veces con los "No cancelable".
    """
    from app.models.cancelacion_intento import CancelacionIntento
    from app.services import cancelacion_intento_service as bitacora

    intento_id = bitacora.abrir(
        db_session, factura_timbrada, motivo="02", folio_sustitucion=None
    )
    huerfano = db_session.get(CancelacionIntento, intento_id)
    huerfano.fecha_envio = datetime.utcnow() - timedelta(minutes=45)
    db_session.commit()

    # El SAT sí tenía la solicitud: la llamada llegó aunque nadie viera la respuesta.
    sat_dice(acuse(cancelacion="En proceso"))
    bitacora.tomar_candado(db_session, factura_timbrada)

    db_session.refresh(huerfano)
    assert huerfano.envio == "RECONCILIADO"
    assert huerfano.sat_registro_solicitud is True
    assert factura_timbrada.estatus == "EN_CANCELACION"


def test_el_huerfano_se_cierra_aunque_el_sat_no_conteste(
    db_session, factura_timbrada, monkeypatch
):
    """
    Si ni el SAT se deja consultar, el renglón se cierra igual y queda escrito
    por qué. Dejarlo en ENVIANDO conservaría el candado sobre un comprobante
    cuya llamada murió hace rato.
    """
    from app.models.cancelacion_intento import CancelacionIntento
    from app.services import cancelacion_intento_service as bitacora
    from app.services import sat_cfdi_service

    intento_id = bitacora.abrir(
        db_session, factura_timbrada, motivo="02", folio_sustitucion=None
    )
    huerfano = db_session.get(CancelacionIntento, intento_id)
    huerfano.fecha_envio = datetime.utcnow() - timedelta(minutes=45)
    db_session.commit()

    def truena(**kw):
        raise RuntimeError("el WS del SAT no responde")

    monkeypatch.setattr(sat_cfdi_service, "consultar_cfdi", truena)
    bitacora.tomar_candado(db_session, factura_timbrada)

    db_session.refresh(huerfano)
    assert huerfano.envio == "RECONCILIADO"
    assert "tampoco se pudo consultar al SAT" in huerfano.pac_message
    assert factura_timbrada.estatus == "TIMBRADA"  # no se inventa nada


def test_el_barrido_del_cron_aplica_el_veredicto_del_sat(
    db_session, factura_timbrada, sat_dice
):
    """
    El huérfano que nadie reintenta lo resuelve el cron: si el SAT tiene la
    solicitud, el comprobante entra a EN_CANCELACION y vuelve al radar.
    """
    from app.models.cancelacion_intento import CancelacionIntento
    from app.services import cancelacion_intento_service as bitacora

    intento_id = bitacora.abrir(
        db_session, factura_timbrada, motivo="02", folio_sustitucion=None
    )
    huerfano = db_session.get(CancelacionIntento, intento_id)
    huerfano.fecha_envio = datetime.utcnow() - timedelta(minutes=45)
    db_session.commit()

    sat_dice(acuse(cancelacion="En proceso"))
    assert bitacora.reconciliar_huerfanos(db_session) == 1

    db_session.refresh(huerfano)
    db_session.refresh(factura_timbrada)
    assert huerfano.envio == "RECONCILIADO"
    assert factura_timbrada.estatus == "EN_CANCELACION"


def test_el_barrido_no_toca_los_envios_recientes(db_session, factura_timbrada):
    """Uno de hace segundos puede ser una llamada viva; no se toca."""
    from app.services import cancelacion_intento_service as bitacora

    bitacora.abrir(db_session, factura_timbrada, motivo="02", folio_sustitucion=None)
    db_session.commit()

    assert bitacora.reconciliar_huerfanos(db_session) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Filtro de solicitudes en el listado de facturas
#
# El estado del TRÁMITE no es el estatus del documento. Una factura puede
# acumular solicitudes fallidas y seguir TIMBRADA: A-785 y A-22069 vivieron días
# así sin aparecer en ninguna pantalla.
# ─────────────────────────────────────────────────────────────────────────────

def _factura_extra(db, factura_timbrada, folio, estatus):
    """Otra factura de la misma empresa, para que el filtro tenga qué descartar."""
    from app.models.factura import Factura

    f = Factura(
        serie="A", folio=folio,
        empresa_id=factura_timbrada.empresa_id,
        cliente_id=factura_timbrada.cliente_id,
        estatus=estatus, total=500,
        cfdi_uuid=f"00000000-0000-0000-0000-{folio:012d}",
    )
    db.add(f)
    db.commit()
    return f


def _listar(db, filtro):
    from app.services.factura_service import listar_facturas

    items, total = listar_facturas(db, cancelacion=filtro, limit=50)
    return {f"{i.serie}-{i.folio}" for i in items}, total


def test_atorada_encuentra_la_que_se_pidio_cancelar_y_sigue_vigente(
    db_session, factura_timbrada
):
    from app.services import cancelacion_intento_service as bitacora

    limpia = _factura_extra(db_session, factura_timbrada, 7001, "TIMBRADA")
    bitacora.registrar(
        db_session, factura_timbrada,
        motivo="02", folio_sustitucion=None,
        pac_code="GT12", pac_message="recibida", sat_registro_solicitud=False,
    )
    db_session.commit()

    folios, total = _listar(db_session, "atorada")

    assert folios == {"A-2202"}
    assert f"A-{limpia.folio}" not in folios
    assert total == 1


def test_sin_registro_sat_ignora_las_que_ya_se_cancelaron(db_session, factura_timbrada):
    """Una vez cancelada da igual cómo llegó ahí; lo urgente es lo no resuelto."""
    from app.services import cancelacion_intento_service as bitacora

    ya_cancelada = _factura_extra(db_session, factura_timbrada, 7002, "CANCELADA")
    for doc in (factura_timbrada, ya_cancelada):
        bitacora.registrar(
            db_session, doc,
            motivo="02", folio_sustitucion=None,
            pac_code="GT12", pac_message="recibida", sat_registro_solicitud=False,
        )
    db_session.commit()

    folios, _ = _listar(db_session, "sin_registro_sat")

    assert folios == {"A-2202"}


def test_con_solicitud_no_repite_la_factura_con_varios_intentos(
    db_session, factura_timbrada
):
    """
    Es un EXISTS y no un join: con join, una factura con tres intentos saldría
    tres veces en el listado.
    """
    from app.services import cancelacion_intento_service as bitacora

    for _ in range(3):
        bitacora.registrar(
            db_session, factura_timbrada,
            motivo="02", folio_sustitucion=None,
            pac_code="GT12", pac_message="recibida",
        )
    db_session.commit()

    folios, total = _listar(db_session, "con_solicitud")

    assert folios == {"A-2202"}
    assert total == 1


def test_en_tramite_no_depende_de_la_bitacora(db_session, factura_timbrada):
    """
    Las de antes de la bitácora también están en trámite: el filtro va por el
    estatus, no por si alcanzó a quedar registro del envío.
    """
    _factura_extra(db_session, factura_timbrada, 7003, "EN_CANCELACION")

    folios, _ = _listar(db_session, "en_tramite")

    assert folios == {"A-7003"}


# ─────────────────────────────────────────────────────────────────────────────
# «Verificar con SAT»: avance se aplica, retroceso se pregunta
#
# Lo que el SAT ya consumó no admite discusión: la factura ya está así ante
# Hacienda, y no reflejarlo sólo logra que siga contando en cobranza algo que
# fiscalmente no existe. Lo que REVIVE una factura sí se pregunta: el cliente
# vuelve a deberla y puede haber una sustituta ya timbrada.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "anterior,nuevo,esperado",
    [
        ("TIMBRADA", "CANCELADA", "avance"),
        ("TIMBRADA", "EN_CANCELACION", "avance"),
        ("EN_CANCELACION", "CANCELADA", "avance"),
        ("EN_CANCELACION", "EN_CANCELACION", "concuerda"),
        ("EN_CANCELACION", "TIMBRADA", "retroceso"),
        ("CANCELADA", "TIMBRADA", "retroceso"),
        ("CANCELADA", "EN_CANCELACION", "retroceso"),
        # Los complementos usan el género masculino y se ordenan igual.
        ("TIMBRADO", "CANCELADO", "avance"),
        ("CANCELADO", "TIMBRADO", "retroceso"),
    ],
)
def test_clasificacion_del_cambio(anterior, nuevo, esperado):
    from app.services.sat_cfdi_service import clasificar_cambio

    assert clasificar_cambio(anterior, nuevo) == esperado


def test_un_estatus_que_no_sabemos_ordenar_se_trata_como_retroceso():
    """Ante la duda, que decida una persona."""
    from app.services.sat_cfdi_service import clasificar_cambio

    assert clasificar_cambio("TIMBRADA", "LO_QUE_SEA") == "retroceso"


def test_el_boton_aplica_solo_lo_que_el_sat_ya_consumo(
    auth_client, db_session, factura_timbrada, sat_dice
):
    sat_dice(acuse(estado="Cancelado", cancelacion="Plazo vencido"))

    r = auth_client.post(f"/api/facturas/{factura_timbrada.id}/verificar-sat")

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["clasificacion"] == "avance"
    assert cuerpo["requiere_confirmacion"] is False
    assert cuerpo["estatus_nuevo"] == "CANCELADA"
    db_session.refresh(factura_timbrada)
    assert factura_timbrada.estatus == "CANCELADA"


def test_el_boton_no_revive_una_factura_sin_permiso(
    auth_client, db_session, factura_timbrada, sat_dice
):
    """El caso peligroso: el sistema la daba por cancelada y el SAT la ve viva."""
    factura_timbrada.estatus = "CANCELADA"
    db_session.commit()
    sat_dice(acuse())  # Vigente, sin trámite

    r = auth_client.post(f"/api/facturas/{factura_timbrada.id}/verificar-sat")

    cuerpo = r.json()
    assert cuerpo["requiere_confirmacion"] is True
    assert cuerpo["clasificacion"] == "retroceso"
    assert cuerpo["estatus_propuesto"] == "TIMBRADA"
    assert cuerpo["actualizado"] is False
    assert "revive" in cuerpo["advertencia"]
    # Y sobre todo: la factura no se movió.
    db_session.expire_all()
    assert factura_timbrada.estatus == "CANCELADA"


def test_la_propuesta_rechazada_queda_auditada(
    auth_client, db_session, factura_timbrada, sat_dice
):
    """
    Que alguien viera la advertencia y no confirmara también es un hecho: es lo
    que explica por qué el sistema y el SAT siguen distintos.
    """
    from app.models.auditoria import AuditoriaLog

    factura_timbrada.estatus = "CANCELADA"
    db_session.commit()
    sat_dice(acuse())

    auth_client.post(f"/api/facturas/{factura_timbrada.id}/verificar-sat")

    reg = (
        db_session.query(AuditoriaLog)
        .filter(AuditoriaLog.entidad_id == str(factura_timbrada.id))
        .order_by(AuditoriaLog.creado_en.desc())
        .first()
    )
    detalle = json.loads(reg.detalle)
    assert detalle["clasificacion"] == "retroceso"
    assert detalle["actualizado"] is False
    assert detalle["estatus_propuesto"] == "TIMBRADA"


def test_con_confirmacion_explicita_si_se_aplica(
    auth_client, db_session, factura_timbrada, sat_dice
):
    factura_timbrada.estatus = "CANCELADA"
    db_session.commit()
    sat_dice(acuse())

    r = auth_client.post(
        f"/api/facturas/{factura_timbrada.id}/verificar-sat",
        params={"confirmar_retroceso": True},
    )

    cuerpo = r.json()
    assert cuerpo["requiere_confirmacion"] is False
    assert cuerpo["estatus_nuevo"] == "TIMBRADA"
    db_session.refresh(factura_timbrada)
    assert factura_timbrada.estatus == "TIMBRADA"
