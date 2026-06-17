# app/api/clientes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.utils.excel import generate_excel
# Catálogos
from app.catalogos_sat.regimenes_fiscales import REGIMENES_FISCALES_SAT

from app.database import get_db
from app.models.empresa import Empresa
from app.models.factura import Factura
from app.models.orden_servicio import OrdenServicio
from app.models.presupuestos import Presupuesto
from app.schemas.cliente import (
    ClienteOut,
    ClienteCreate,
    ClienteUpdate,
    ClienteVincular,
    ClienteDocumentoOut,
)
from app.services.cliente_service import cliente_repo
from app.models.cliente_documento import ClienteDocumento
from app.api import deps
from app.models.usuario import Usuario, RolUsuario
from app.services import auditoria_service as audit_svc
from pydantic import BaseModel


class ClientePageOut(BaseModel):
    items: List[ClienteOut]
    total: int
    limit: int
    offset: int


router = APIRouter()


# El schema dinámico se mantiene por ahora, ya que está muy acoplado a la vista.
@router.get("/schema")
def get_form_schema(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    # Pydantic v2
    try:
        schema = ClienteCreate.model_json_schema()
    except Exception:
        schema = ClienteCreate.schema()

    props = schema["properties"]

    props["empresa_id"]["type"] = "array"
    props["empresa_id"]["items"] = {"type": "string", "format": "uuid"}

    # ADMIN y SUPERADMIN ven todas las empresas; el resto solo la suya
    if current_user.rol in (RolUsuario.ADMIN, RolUsuario.SUPERADMIN):
        empresas = db.query(Empresa).all()
    else:
        empresas = db.query(Empresa).filter(
            Empresa.id == current_user.empresa_id
        ).all()

    props["empresa_id"]["x-options"] = [
        {"value": str(e.id), "label": e.nombre_comercial} for e in empresas
    ]

    props["telefono"]["type"] = "array"
    props["telefono"]["items"] = {"type": "string"}
    props["email"]["type"] = "array"
    props["email"]["items"] = {"type": "string", "format": "email"}

    return {"properties": props, "required": schema.get("required", [])}


@router.get("/busqueda", response_model=List[ClienteOut])
def buscar_clientes(
    q: Optional[str] = Query(
        None, description="Texto a buscar (min 3 chars)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    empresa_id: Optional[UUID] = Query(None, description="Filtrar por empresa"),
    search_field: str = Query("comercial", description="'comercial', 'fiscal' o 'both'"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Busca clientes por nombre comercial o razón social; admite filtro por empresa."""
    # Forzar empresa_id para cualquier rol que no sea ADMIN o SUPERADMIN
    if current_user.rol not in (RolUsuario.ADMIN, RolUsuario.SUPERADMIN):
        empresa_id = current_user.empresa_id

    return cliente_repo.search_by_name(
        db, name_query=q, limit=limit, empresa_id=empresa_id, search_field=search_field
    )


@router.get("/validar-rfc", response_model=List[str])
def validar_rfc_cliente(
    rfc: str = Query(..., min_length=12, max_length=13, description="RFC a validar"),
    exclude_id: Optional[UUID] = Query(None, description="ID del cliente a excluir (edición)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Verifica si un RFC ya existe en la base de datos de clientes.
    Retorna la lista de nombres de empresas donde está registrado.
    """
    return cliente_repo.validar_rfc_global(db, rfc=rfc.upper(), exclude_cliente_id=exclude_id)


    return cliente_repo.validar_rfc_global(db, rfc=rfc.upper(), exclude_cliente_id=exclude_id)


@router.get("/buscar-existente", response_model=Optional[ClienteOut])
def buscar_cliente_existente(
    rfc: str = Query(..., min_length=12, max_length=13),
    nombre_comercial: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Busca un cliente que coincida exactamente con RFC y Nombre Comercial.
    Retorna el cliente si existe, o null.
    """
    return cliente_repo.get_by_rfc_and_name(db, rfc=rfc.upper(), nombre_comercial=nombre_comercial)


@router.get("/", response_model=ClientePageOut)
def listar_clientes(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    empresa_id: Optional[UUID] = Query(None),
    rfc: Optional[str] = Query(None),
    nombre_comercial: Optional[str] = Query(None),
    nombre_razon_social: Optional[str] = Query(None),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Obtiene una lista paginada y filtrada de todos los clientes."""
    # Forzar empresa_id para cualquier rol que no sea ADMIN o SUPERADMIN
    if current_user.rol not in (RolUsuario.ADMIN, RolUsuario.SUPERADMIN):
        empresa_id = current_user.empresa_id

    items, total = cliente_repo.get_multi(
        db,
        skip=offset,
        limit=limit,
        empresa_id=empresa_id,
        rfc=rfc,
        nombre_comercial=nombre_comercial,
        nombre_razon_social=nombre_razon_social,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/export-excel")
def exportar_clientes_excel(
    db: Session = Depends(get_db),
    empresa_id: Optional[UUID] = Query(None),
    rfc: Optional[str] = Query(None),
    nombre_comercial: Optional[str] = Query(None),
    nombre_razon_social: Optional[str] = Query(None),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
        
    items, _ = cliente_repo.get_multi(
        db,
        skip=0,
        limit=1000000,
        empresa_id=empresa_id,
        rfc=rfc,
        nombre_comercial=nombre_comercial,
        nombre_razon_social=nombre_razon_social,
    )

    # Mapa de regimenes
    map_regimenes = {i["clave"]: i["descripcion"] for i in REGIMENES_FISCALES_SAT}

    data_list = []
    for c in items:
        # Manejo seguro de listas (email/telefono pueden ser None o List)
        emails = c.email if c.email else []
        if isinstance(emails, list):
            email_str = ", ".join(emails)
        else:
            email_str = str(emails)
            
        telefonos = c.telefono if c.telefono else []
        if isinstance(telefonos, list):
            telefono_str = ", ".join(telefonos)
        else:
            telefono_str = str(telefonos)

        # Regimen fiscal description
        regimen_desc = c.regimen_fiscal
        if c.regimen_fiscal and c.regimen_fiscal in map_regimenes:
            regimen_desc = f"{c.regimen_fiscal} - {map_regimenes[c.regimen_fiscal]}"

        data_list.append({
            "nombre_comercial": c.nombre_comercial,
            "nombre_razon_social": c.nombre_razon_social,
            "rfc": c.rfc,
            "regimen_fiscal": regimen_desc,
            "email": email_str,
            "telefono": telefono_str,
        })

    headers = {
        "nombre_comercial": "Nombre Comercial",
        "nombre_razon_social": "Razón Social",
        "rfc": "RFC",
        "regimen_fiscal": "Régimen Fiscal",
        "email": "Email",
        "telefono": "Teléfono",
    }

    excel_file = generate_excel(data_list, headers, sheet_name="Clientes")
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.EXPORTAR_EXCEL, entidad="cliente",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=empresa_id, detalle={"registros": len(data_list)},
        )
        db.commit()
    except Exception:
        pass
    headers_resp = {
        "Content-Disposition": 'attachment; filename="clientes.xlsx"'
    }
    return StreamingResponse(excel_file, headers=headers_resp, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")



@router.get("/{id}", response_model=ClienteOut)
def obtener_cliente(
    id: UUID = Path(...), 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Obtiene un cliente por su ID."""
    cliente = cliente_repo.get(db, id=id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Validar acceso por empresa
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresas_ids = [e.id for e in cliente.empresas]
        if current_user.empresa_id not in empresas_ids:
             raise HTTPException(status_code=404, detail="Cliente no encontrado")
             
    return cliente


@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(
    payload: ClienteCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Crea un nuevo cliente."""
    # Si es supervisor, forzar la empresa
    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="El usuario supervisor no tiene empresa asignada.")
        payload.empresa_id = [current_user.empresa_id]

    result = cliente_repo.create(db, obj_in=payload)
    try:
        _empresa_id = result.empresas[0].id if result.empresas else current_user.empresa_id
        audit_svc.registrar(
            db=db, accion=audit_svc.CREAR_CLIENTE, entidad="cliente",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=_empresa_id, entidad_id=str(result.id),
            detalle={"rfc": result.rfc, "nombre": result.nombre_comercial or result.nombre_razon_social},
        )
        db.commit()
    except Exception:
        pass
    return result


@router.put("/{id}", response_model=ClienteOut)
def actualizar_cliente(
    id: UUID, 
    payload: ClienteUpdate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Actualiza un cliente existente."""
    db_cliente = cliente_repo.get(db, id=id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    # Validar acceso
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresas_ids = [e.id for e in db_cliente.empresas]
        if current_user.empresa_id not in empresas_ids:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        # No permitir cambiar empresa_id a otra cosa (mantiene solo la suya)
        payload.empresa_id = [current_user.empresa_id]

    result = cliente_repo.update(db, db_obj=db_cliente, obj_in=payload)
    try:
        _empresa_id = db_cliente.empresas[0].id if db_cliente.empresas else current_user.empresa_id
        audit_svc.registrar(
            db=db, accion=audit_svc.ACTUALIZAR_CLIENTE, entidad="cliente",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=_empresa_id, entidad_id=str(id),
            detalle={"rfc": db_cliente.rfc, "nombre": db_cliente.nombre_comercial},
        )
        db.commit()
    except Exception:
        pass
    return result


@router.delete("/{id}", status_code=204)
def eliminar_cliente(
    id: UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Elimina un cliente."""
    cliente = cliente_repo.get(db, id=id) # Verificar existencia primero para validar auth
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if current_user.rol == RolUsuario.SUPERVISOR:
        empresas_ids = [e.id for e in cliente.empresas]
        if current_user.empresa_id not in empresas_ids:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

    _empresa_id = cliente.empresas[0].id if cliente.empresas else current_user.empresa_id

    # Verificar registros dependientes antes de intentar borrar
    n_ordenes     = db.query(OrdenServicio).filter(OrdenServicio.cliente_id == id).count()
    n_facturas    = db.query(Factura).filter(Factura.cliente_id == id).count()
    n_presupuestos = db.query(Presupuesto).filter(Presupuesto.cliente_id == id).count()

    bloqueantes = []
    if n_ordenes:     bloqueantes.append(f"{n_ordenes} orden(es) de servicio")
    if n_facturas:    bloqueantes.append(f"{n_facturas} factura(s)")
    if n_presupuestos: bloqueantes.append(f"{n_presupuestos} presupuesto(s)")

    if bloqueantes:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar el cliente porque tiene registros asociados: {', '.join(bloqueantes)}. "
                   "Elimina o reasigna esos registros primero.",
        )

    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.ELIMINAR_CLIENTE, entidad="cliente",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=_empresa_id, entidad_id=str(id),
            detalle={"rfc": cliente.rfc, "nombre": cliente.nombre_comercial},
        )
    except Exception:
        pass

    try:
        cliente_repo.remove(db, id=id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar el cliente porque tiene registros asociados en el sistema.",
        )

    return Response(status_code=204)

@router.post("/{id}/vincular", status_code=200)
def vincular_cliente(
    id: UUID,
    payload: ClienteVincular,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """
    Agrega asociaciones de empresas a un cliente existente sin eliminar las actuales.
    Permite a inspectores vincular clientes existentes a su empresa asignada.
    """
    cliente = cliente_repo.get(db, id=id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    ids_a_vincular = set(payload.empresa_ids)
    
    # Restricción Supervisor: Solo puede vincular A SU PROPIA empresa
    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="Supervisor sin empresa asignada")
        
        # Ignoramos lo que envíe en el payload y forzamos solo su empresa
        ids_a_vincular = {current_user.empresa_id}
        
    # Lógica de vinculación (append)
    empresas_existentes = {e.id for e in cliente.empresas}
    nuevas_empresas = []
    
    # Buscar entidades Empresa para agregar
    from app.models.empresa import Empresa
    empresas_db = db.query(Empresa).filter(Empresa.id.in_(list(ids_a_vincular))).all()
    
    cambios = False
    for emp in empresas_db:
        if emp.id not in empresas_existentes:
            cliente.empresas.append(emp)
            cambios = True
            
    if cambios:
        db.commit()
        db.refresh(cliente)

    return {"message": "Cliente vinculado correctamente", "cliente_id": cliente.id}


# ── Documentos del cliente (contrato firmado, adjuntos) ───────────────────────

import os
import uuid as _uuid
import mimetypes
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
from app.config import settings

_CLIENTES_DOCS_DIR = os.path.join(settings.DATA_DIR, "clientes_docs")
_CLIENTE_DOC_ALLOWED_EXTS = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx"})
_CLIENTE_DOC_MAX_BYTES = 15 * 1024 * 1024  # 15 MB


def _get_cliente_or_404(db: Session, id: UUID, current_user: Usuario):
    cliente = cliente_repo.get(db, id=id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresas_ids = [e.id for e in cliente.empresas]
        if current_user.empresa_id not in empresas_ids:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/{id}/documentos", response_model=List[ClienteDocumentoOut])
def listar_documentos_cliente(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    _get_cliente_or_404(db, id, current_user)
    return (
        db.query(ClienteDocumento)
        .filter(ClienteDocumento.cliente_id == id)
        .order_by(ClienteDocumento.creado_en.desc())
        .all()
    )


@router.post("/{id}/documentos", response_model=ClienteDocumentoOut, status_code=201)
def subir_documento_cliente(
    id: UUID,
    file: UploadFile = File(...),
    tipo: str = Form("OTRO"),
    nombre: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    _get_cliente_or_404(db, id, current_user)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if not ext or ext not in _CLIENTE_DOC_ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Válidos: {', '.join(sorted(_CLIENTE_DOC_ALLOWED_EXTS))}",
        )
    content = file.file.read()
    if len(content) > _CLIENTE_DOC_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo supera el tamaño máximo de {_CLIENTE_DOC_MAX_BYTES // (1024 * 1024)} MB.",
        )

    os.makedirs(_CLIENTES_DOCS_DIR, exist_ok=True)
    filename = f"{_uuid.uuid4()}{ext}"
    with open(os.path.join(_CLIENTES_DOCS_DIR, filename), "wb") as fh:
        fh.write(content)

    doc = ClienteDocumento(
        cliente_id=id,
        tipo=(tipo or "OTRO").upper(),
        nombre=nombre or file.filename or filename,
        archivo=filename,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{id}/documentos/{doc_id}/archivo")
def descargar_documento_cliente(
    id: UUID,
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    _get_cliente_or_404(db, id, current_user)
    doc = (
        db.query(ClienteDocumento)
        .filter(ClienteDocumento.id == doc_id, ClienteDocumento.cliente_id == id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    base = os.path.realpath(_CLIENTES_DOCS_DIR)
    resolved = os.path.realpath(os.path.join(base, doc.archivo))
    if not resolved.startswith(base + os.sep) or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    mime, _ = mimetypes.guess_type(resolved)
    return FileResponse(
        resolved,
        media_type=mime or "application/octet-stream",
        filename=doc.nombre,
    )


@router.delete("/{id}/documentos/{doc_id}", status_code=204)
def eliminar_documento_cliente(
    id: UUID,
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    _get_cliente_or_404(db, id, current_user)
    doc = (
        db.query(ClienteDocumento)
        .filter(ClienteDocumento.id == doc_id, ClienteDocumento.cliente_id == id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    path = os.path.join(_CLIENTES_DOCS_DIR, doc.archivo)
    if os.path.exists(path):
        os.remove(path)
    db.delete(doc)
    db.commit()
    return Response(status_code=204)

