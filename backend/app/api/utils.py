from fastapi import APIRouter, Depends, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.api import deps
from app.services import utils_service

router = APIRouter()


@router.post("/geocode", status_code=status.HTTP_200_OK, summary="Obtener coordenadas de una dirección")
def get_coordinates_from_address(
    address: str,
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Convierte una dirección de texto a coordenadas de latitud y longitud usando una API de geocodificación.
    """
    return utils_service.get_coordinates_from_address(address)


@router.post("/parse-csf", status_code=status.HTTP_200_OK, summary="Extraer datos de Constancia de Situación Fiscal (PDF)")
async def parse_csf_document(
    file: UploadFile = File(...),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Recibe un archivo PDF (Constancia de Situación Fiscal), lo procesa y devuelve:
    - RFC
    - Razón Social
    - Código Postal
    - Régimen Fiscal (si es posible extraerlo)
    """
    content = await file.read()
    return utils_service.parse_csf_pdf(content)
