# app/api/clientes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.utils.excel import generate_excel
# Catálogos
from app.catalogos_sat.regimenes_fiscales import REGIMENES_FISCALES_SAT

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteOut, ClienteCreate, ClienteUpdate, ClienteVincular
from app.services.cliente_service import cliente_repo
from app.api import deps
from app.models.usuario import Usuario, RolUsuario
from pydantic import BaseModel


class ClientePageOut(BaseModel):
    items: List[ClienteOut]
    total: int
    limit: int
    offset: int


router = APIRouter()


# El schema dinámico se mantiene por ahora, ya que está muy acoplado a la vista.
@router.get("/schema")
def get_form_schema(db: Session = Depends(get_db)):
    # Pydantic v2
    try:
        schema = ClienteCreate.model_json_schema()
    except Exception:
        schema = ClienteCreate.schema()

    props = schema["properties"]

    props["empresa_id"]["type"] = "array"
    props["empresa_id"]["items"] = {"type": "string", "format": "uuid"}
    empresas = db.query(Empresa).all()
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
        None, description="Texto a buscar en nombre_comercial (min 3 chars)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    empresa_id: Optional[UUID] = Query(None, description="Filtrar por empresa"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Busca clientes por nombre comercial para autocompletado; admite filtro por empresa."""
    # Si es supervisor, forzar empresa_id
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    return cliente_repo.search_by_name(db, name_query=q, limit=limit, empresa_id=empresa_id)


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
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Obtiene una lista paginada y filtrada de todos los clientes."""
    # Si es supervisor, forzar empresa_id
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    items, total = cliente_repo.get_multi(
        db,
        skip=offset,
        limit=limit,
        empresa_id=empresa_id,
        rfc=rfc,
        nombre_comercial=nombre_comercial,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/export-excel")
def exportar_clientes_excel(
    db: Session = Depends(get_db),
    empresa_id: Optional[UUID] = Query(None),
    rfc: Optional[str] = Query(None),
    nombre_comercial: Optional[str] = Query(None),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
        
    items, _ = cliente_repo.get_multi(
        db,
        skip=0,
        limit=5000,
        empresa_id=empresa_id,
        rfc=rfc,
        nombre_comercial=nombre_comercial,
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
        
    return cliente_repo.create(db, obj_in=payload)


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

    return cliente_repo.update(db, db_obj=db_cliente, obj_in=payload)


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

