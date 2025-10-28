from fastapi import APIRouter, status
from app.services import utils_service

router = APIRouter()


@router.post("/geocode", status_code=status.HTTP_200_OK, summary="Obtener coordenadas de una dirección")
def get_coordinates_from_address(address: str):
    """
    Convierte una dirección de texto a coordenadas de latitud y longitud usando una API de geocodificación.
    """
    return utils_service.get_coordinates_from_address(address)