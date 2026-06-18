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


# Claves que se resuelven automáticamente desde los datos del sistema (no las
# captura el usuario). El resto de placeholders de la plantilla son manuales.
def _auto_context(db: Session, contrato: Contrato) -> dict:
    empresa: Empresa = contrato.empresa
    cliente: Cliente = contrato.cliente
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
        # Metadatos del contrato
        "numero_contrato": contrato.numero_contrato or "",
    }


# Conjunto de claves auto-resueltas (para filtrar los campos manuales del form)
AUTO_KEYS = {
    "prestador_representante", "prestador_propietario", "prestador_rfc",
    "prestador_registro_patronal", "prestador_repse_aviso", "prestador_repse_registro",
    "prestador_licencia", "prestador_banco", "prestador_clabe", "prestador_cuenta",
    "cliente_razon_social", "cliente_representante", "cliente_rfc", "cliente_email",
    "numero_contrato", "personal",
}


def _build_context(db: Session, contrato: Contrato) -> dict:
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
            "salario": f"${_money(tec.salario_base_cotizable)}" if tec.salario_base_cotizable else "",
            "puesto": tec.puesto or "",
        })

    ctx = _auto_context(db, contrato)
    # Valores manuales (keyed por placeholder); formatea números de precio
    for k, v in (contrato.datos or {}).items():
        if v is None:
            ctx[k] = ""
        elif _es_campo_numerico(k):
            ctx[k] = _money(v)
        else:
            ctx[k] = v
    ctx["personal"] = personal
    return ctx


def _es_campo_numerico(nombre: str) -> bool:
    n = nombre.lower()
    return any(p in n for p in ("precio", "monto", "importe", "costo", "total"))


def _placeholders_en_docx(path: str) -> list[str]:
    """Extrae los nombres de placeholders {{ ... }} del docx, uniendo runs.
    No usa jinja (evita el conflicto con los tags {%tr%} del loop)."""
    import re
    import zipfile

    textos = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                xml = z.read(name).decode("utf-8", errors="ignore")
                # unir el texto de todos los <w:t> para reconstruir placeholders partidos
                textos.append("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml, re.DOTALL)))
    full = "".join(textos)
    # raíz de cada {{ expr }} (ignora miembros de loop como p.nombre)
    nombres = []
    for expr in re.findall(r"\{\{\s*([a-zA-Z0-9_\.]+)", full):
        raiz = expr.split(".")[0]
        if "." in expr:
            continue  # miembro de objeto del loop (p.nombre)
        nombres.append(raiz)
    # preservar orden de aparición, sin duplicados
    vistos, orden = set(), []
    for n in nombres:
        if n not in vistos:
            vistos.add(n)
            orden.append(n)
    return orden


def variables_plantilla(empresa: Empresa) -> list[dict]:
    """Introspecciona los placeholders de la plantilla de la empresa y devuelve
    los campos MANUALES (los que el usuario debe capturar), con tipo sugerido."""
    plantilla = _resolver_plantilla(empresa)
    campos = []
    for v in _placeholders_en_docx(plantilla):
        if v in AUTO_KEYS or v == "personal":
            continue
        campos.append({
            "name": v,
            "label": v.replace("_", " ").capitalize(),
            "tipo": "numero" if _es_campo_numerico(v) else "texto",
        })
    return campos


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
