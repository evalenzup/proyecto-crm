# app/api/mapa.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.api import deps
from app.database import get_db
from app.models.usuario import RolUsuario, Usuario
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.factura import Factura

router = APIRouter()


@router.get("/clientes-servicio", summary="Clientes geolocalizados con servicio")
def clientes_con_servicio(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Retorna los clientes que tienen coordenadas registradas y al menos
    una factura emitida. Exclusivo para usuarios con rol ADMIN.
    """
    if current_user.rol not in (RolUsuario.SUPERADMIN, RolUsuario.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este módulo.",
        )

    # Subquery: clientes que tienen al menos una factura
    clientes_con_factura = (
        db.query(Factura.cliente_id)
        .filter(Factura.cliente_id.isnot(None))
        .distinct()
        .subquery()
    )

    # Contar facturas por cliente
    conteo_facturas = (
        db.query(
            Factura.cliente_id,
            func.count(Factura.id).label("total_facturas"),
        )
        .group_by(Factura.cliente_id)
        .subquery()
    )

    # Cargar clientes con sus empresas en una sola consulta (selectinload evita N+1)
    clientes = (
        db.query(Cliente)
        .join(clientes_con_factura, Cliente.id == clientes_con_factura.c.cliente_id)
        .filter(
            Cliente.latitud.isnot(None),
            Cliente.longitud.isnot(None),
        )
        .options(selectinload(Cliente.empresas))
        .order_by(Cliente.nombre_comercial)
        .all()
    )

    # Mapa de conteo de facturas por cliente
    conteos = {
        str(r.cliente_id): r.total_facturas
        for r in db.query(conteo_facturas).all()
    }

    # Empresas únicas para el catálogo de filtros
    ids_clientes = [c.id for c in clientes]
    empresas_unicas: dict[str, str] = {}
    for c in clientes:
        for e in c.empresas:
            empresas_unicas[str(e.id)] = e.nombre_comercial

    return {
        "total": len(clientes),
        "empresas": [
            {"id": eid, "nombre": nombre}
            for eid, nombre in sorted(empresas_unicas.items(), key=lambda x: x[1])
        ],
        "clientes": [
            {
                "id": str(c.id),
                "nombre_comercial": c.nombre_comercial,
                "latitud": c.latitud,
                "longitud": c.longitud,
                "telefono": c.telefono,
                "email": c.email,
                "actividad": c.actividad,
                "total_facturas": conteos.get(str(c.id), 0),
                "empresas": [
                    {"id": str(e.id), "nombre": e.nombre_comercial}
                    for e in c.empresas
                ],
            }
            for c in clientes
        ],
    }
