# app/api/catalogos.py

from fastapi import APIRouter
from app.catalogos_sat import REGIMENES_FISCALES_SAT

router = APIRouter(prefix="/api/catalogos", tags=["Catalogos"])

@router.get("/regimen-fiscal", summary="Obtener catálogo de régimen fiscal SAT")
def obtener_regimenes_fiscales():
    """
    Devuelve el catálogo de regímenes fiscales del SAT con clave y descripción
    para ser utilizado en formularios del CRM y validaciones CFDI.
    """
    return REGIMENES_FISCALES_SAT
