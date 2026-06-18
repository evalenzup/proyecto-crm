# app/services/contrato_service.py
"""
Generación del documento de contrato a partir de la plantilla docxtpl del
machote NORTON. Arma el contexto desde Contrato + Empresa + Cliente + Técnicos,
rellena el .docx y lo convierte a PDF con LibreOffice (soffice).
"""
from __future__ import annotations

import os
import subprocess
import uuid as _uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from docxtpl import DocxTemplate
from sqlalchemy.orm import Session

from app.config import settings
from app.models.contrato import Contrato
from app.models.empresa import Empresa
from app.models.cliente import Cliente
from app.models.tecnico import Tecnico

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "contrato_plantilla.docx"
_CONTRATOS_DIR = os.path.join(settings.DATA_DIR, "contratos")
_PLANTILLAS_DIR = os.path.join(settings.DATA_DIR, "contratos_plantillas")


def _resolver_plantilla(empresa: Empresa) -> str:
    """Devuelve la ruta de la plantilla docxtpl de la empresa.
    Cada empresa tiene su propio formato — no hay fallback entre empresas."""
    if empresa.plantilla_contrato:
        path = os.path.join(_PLANTILLAS_DIR, empresa.plantilla_contrato)
        if os.path.isfile(path):
            return path
    raise ValueError(
        f"La empresa '{empresa.nombre_comercial or empresa.nombre}' no tiene plantilla de "
        "contrato configurada. Súbela en la configuración de la empresa."
    )

_MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _money(v) -> str:
    if v is None or v == "":
        return ""
    try:
        return f"{Decimal(str(v)):,.2f}"
    except Exception:
        return str(v)


def _primer(valor) -> str:
    """Primer elemento de un campo de texto separado por comas (email/teléfono)."""
    if not valor:
        return ""
    return str(valor).replace(";", ",").split(",")[0].strip()


def _vigencia_texto(c: Contrato) -> str:
    if c.vigencia_desde and c.vigencia_hasta:
        d, h = c.vigencia_desde, c.vigencia_hasta
        return f"{_MESES[d.month]} {d.year} al mes de {_MESES[h.month]} {h.year}"
    return ""


def _fecha_texto(d: Optional[date]) -> str:
    if not d:
        return ""
    return f"{d.day} de {_MESES[d.month]} de {d.year}"


def _build_context(db: Session, contrato: Contrato) -> dict:
    empresa: Empresa = contrato.empresa
    cliente: Cliente = contrato.cliente
    servicios = contrato.servicios or {}

    # Personal asignado: lista de tecnico_ids → datos del técnico
    personal = []
    for tid in (contrato.personal_asignado or []):
        tec = db.query(Tecnico).filter(Tecnico.id == tid).first()
        if not tec:
            continue
        personal.append({
            "nombre": tec.nombre_completo or "",
            "nss": tec.nss or "",
            "curp": tec.curp or "",
            "salario": _money(tec.salario_base_cotizable) and f"${_money(tec.salario_base_cotizable)}" or "",
            "puesto": tec.puesto or "TÉCNICO EN FUMIGACIÓN",
        })

    return {
        # Prestador (empresa)
        "prestador_representante": empresa.representante_legal or "",
        "prestador_propietario": empresa.beneficiario or empresa.nombre or "",
        "prestador_rfc": empresa.rfc or "",
        "prestador_registro_patronal": empresa.registro_patronal or "",
        "prestador_repse_aviso": empresa.repse_aviso or "",
        "prestador_repse_registro": empresa.repse_registro or "",
        "prestador_licencia": empresa.licencia_sanitaria or "",
        "prestador_banco": empresa.nombre_banco or "",
        "prestador_clabe": empresa.clabe or "",
        "prestador_cuenta": empresa.numero_cuenta or "",
        # Cliente
        "cliente_razon_social": cliente.nombre_razon_social or cliente.nombre_comercial or "",
        "cliente_representante": cliente.representante_legal or "",
        "cliente_rfc": cliente.rfc or "",
        "cliente_email": _primer(cliente.email),
        # Contrato
        "precio_fumigacion": _money(servicios.get("fumigacion")),
        "precio_sanitizacion": _money(servicios.get("sanitizacion")),
        "precio_combo": _money(servicios.get("combo")),
        "vigencia_texto": _vigencia_texto(contrato),
        "fecha_contrato_texto": _fecha_texto(contrato.fecha_contrato),
        "certificado_folio": contrato.certificado_folio or "",
        "personal": personal,
    }


def _docx_a_pdf(docx_path: str, out_dir: str) -> Optional[str]:
    """Convierte docx→pdf con LibreOffice headless. Devuelve la ruta del PDF o None."""
    profile = f"/tmp/lo_profile_{_uuid.uuid4().hex}"
    try:
        subprocess.run(
            [
                "soffice", "--headless",
                f"-env:UserInstallation=file://{profile}",
                "--convert-to", "pdf", "--outdir", out_dir, docx_path,
            ],
            check=True, capture_output=True, timeout=120,
        )
    except Exception:
        return None
    pdf_path = os.path.join(out_dir, Path(docx_path).stem + ".pdf")
    return pdf_path if os.path.exists(pdf_path) else None


def generar_documento(db: Session, contrato: Contrato) -> Contrato:
    """Rellena la plantilla de la empresa, genera docx y pdf, y actualiza el contrato."""
    plantilla = _resolver_plantilla(contrato.empresa)

    os.makedirs(_CONTRATOS_DIR, exist_ok=True)
    base = f"contrato_{contrato.id}"
    docx_path = os.path.join(_CONTRATOS_DIR, base + ".docx")

    tpl = DocxTemplate(plantilla)
    tpl.render(_build_context(db, contrato))
    tpl.save(docx_path)

    contrato.archivo_docx = base + ".docx"

    pdf_path = _docx_a_pdf(docx_path, _CONTRATOS_DIR)
    contrato.archivo_pdf = (base + ".pdf") if pdf_path else None

    contrato.estado = "GENERADO"
    db.add(contrato)
    db.commit()
    db.refresh(contrato)
    return contrato
