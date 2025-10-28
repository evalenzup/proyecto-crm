# app/services/utils_service.py
import os
import requests
from fastapi import HTTPException, status

def get_coordinates_from_address(address: str):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La API key de Google Maps no está configurada en el servidor.",
        )

    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al contactar el servicio de geocodificación: {e}",
        )

    data = response.json()
    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        return {"latitud": location["lat"], "longitud": location["lng"]}
    elif data["status"] == "ZERO_RESULTS":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se pudo encontrar la ubicación para la dirección proporcionada.",
        )
    else:
        error_message = data.get(
            "error_message", "Error desconocido de la API de geocodificación."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de geocodificación: {data['status']} - {error_message}",
        )
