from fastapi import APIRouter, status
from app.services import utils_service

router = APIRouter()


@router.post("/geocode", status_code=status.HTTP_200_OK, summary="Obtener coordenadas de una dirección")
def get_coordinates_from_address(address: str):
    """
    Convierte una dirección de texto a coordenadas de latitud y longitud usando una API de geocodificación.
    """
    return utils_service.get_coordinates_from_address(address)


from fastapi import UploadFile, File

@router.post("/parse-csf", status_code=status.HTTP_200_OK, summary="Extraer datos de Constancia de Situación Fiscal (PDF)")
async def parse_csf_document(file: UploadFile = File(...)):
    """
    Recibe un archivo PDF (Constancia de Situación Fiscal), lo procesa y devuelve:
    - RFC
    - Razón Social
    - Código Postal
    - Régimen Fiscal (si es posible extraerlo)
    """
    content = await file.read()
    return utils_service.parse_csf_pdf(content)