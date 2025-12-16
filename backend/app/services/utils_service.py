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


import io
import re
from pypdf import PdfReader

def parse_csf_pdf(file_content: bytes):
    """
    Parsea una Constancia de Situación Fiscal (PDF) y extrae:
    - RFC
    - Razón Social (o Nombre)
    - Código Postal
    - Régimen Fiscal (primero encontrado)
    """
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo leer el archivo PDF: {e}"
        )

    # Limpieza básica
    text = text.replace('\n', ' ').strip()
    
    result = {
        "rfc": None,
        "razon_social": None,
        "codigo_postal": None,
        "regimen_fiscal": None,
        "direccion": None
    }

    # 1. RFC
    # Patrón genérico de RFC
    rfc_match = re.search(r'([A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3})', text)
    if rfc_match:
        result["rfc"] = rfc_match.group(1)

    # 2. Código Postal
    # Buscar "Código Postal" seguido de 5 dígitos
    # A veces aparece como "C.P.", "CP", "Código Postal:"
    cp_match = re.search(r'(?:Código Postal|C\.?P\.?):?\s*(\d{5})', text, re.IGNORECASE)
    if cp_match:
        result["codigo_postal"] = cp_match.group(1)

    # 3. Razón Social / Nombre
    # Prioridad: Persona Moral (una sola línea de Denominación)
    razon_match = re.search(r'Denominación/Razón Social:?\s*(.+?)(?=\s+(?:Régimen Capital|Fecha de inicio|Nombre Comercial))', text, re.IGNORECASE)
    
    if razon_match:
        result["razon_social"] = razon_match.group(1).strip()
    else:
        # Intento Persona Física (Nombre (s), Primer Apellido, Segundo Apellido)
        n_match = re.search(r'Nombre\s*\(s\):?\s*(.+?)(?=\s+Primer Apellido)', text, re.IGNORECASE)
        ap1_match = re.search(r'Primer Apellido:?\s*(.+?)(?=\s+Segundo Apellido)', text, re.IGNORECASE)
        ap2_match = re.search(r'Segundo Apellido:?\s*(.+?)(?=\s+Fecha)', text, re.IGNORECASE)
        
        parts = []
        if n_match: parts.append(n_match.group(1).strip())
        if ap1_match: parts.append(ap1_match.group(1).strip())
        if ap2_match: parts.append(ap2_match.group(1).strip())
        
        if parts:
            result["razon_social"] = " ".join(parts)
        else:
             # Fallback antiguo
             nombre_match = re.search(r'Nombre, Primer Apellido, Segundo Apellido:?\s*(.+?)(?=\s+Fecha de inicio)', text, re.IGNORECASE)
             if nombre_match:
                 result["razon_social"] = nombre_match.group(1).strip()

    # 4. Régimen Fiscal
    REGIMEN_MAP = {
        "General de Ley Personas Morales": "601",
        "Personas Morales con Fines no Lucrativos": "603",
        "Sueldos y Salarios": "605",
        "Arrendamiento": "606",
        "Enajenación o Adquisición de Bienes": "607",
        "Demás ingresos": "608",
        "Residentes en el Extranjero": "610",
        "Dividendos": "611",
        "Personas Físicas con Actividades Empresariales y Profesionales": "612",
        "Ingresos por intereses": "614",
        "Obtención de premios": "615",
        "Sin obligaciones fiscales": "616",
        "Incorporación Fiscal": "621",
        "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras": "622",
        "Opcional para Grupos de Sociedades": "623",
        "Coordinados": "624",
        "Plataformas Tecnológicas": "625",
        "Simplificado de Confianza": "626",
        "Hidrocarburos": "628",
        "De los Regímenes Fiscales Preferentes y de las Empresas Multinacionales": "629",
        "Enajenación de acciones en bolsa de valores": "630"
    }

    # Intentar extraer la TABLA de regímenes primero
    # El regex anterior fallaba porque "Fecha" aparece en el encabezado de la tabla ("Fecha Inicio")
    # Por lo tanto, buscaremos los nombres de regímenes conocidos en todo el texto,
    # dando prioridad a los más largos y específicos.
    
    text_normalized = text.lower()
    found_code = None
    
    # Ordenar por longitud de nombre descendente para priorizar coincidencias exactas largas
    sorted_regimenes = sorted(REGIMEN_MAP.items(), key=lambda x: len(x[0]), reverse=True)

    for name, code in sorted_regimenes:
        # Buscamos el nombre del régimen como palabra completa o frase exacta
        if name.lower() in text_normalized:
            found_code = code
            break 

    if found_code:
        result["regimen_fiscal"] = found_code
    else:
        # Fallback: RegExp directa para "Regimen: 601 - ..." (formato antiguo)
        regimen_code_match = re.search(r'Regimen:?\s*.*?\b(\d{3})\s*-\s*([^\n]+)', text, re.IGNORECASE)
        if regimen_code_match:
             result["regimen_fiscal"] = regimen_code_match.group(1)


    # 5. Domicilio (Vialidad + Ext + Int + Colonia)
    # Ajustamos lookaheads para ser más tolerantes a falata de espacios y evitar captura de etiquetas
    
    # Helper para limpiar etiquetas capturadas por error
    def clean_field(val: str, next_labels: list) -> str:
        if not val: return ""
        val = val.strip()
        for label in next_labels:
            # Si el valor contiene la etiqueta siguiente, cortamos ahí
            if label.lower() in val.lower():
                idx = val.lower().find(label.lower())
                val = val[:idx]
        return val.strip()

    vialidad_match = re.search(r'Nombre de Vialidad:?\s*(.*?)(?=\s*(?:Número Exterior|Número Interior|Nombre de la Colonia))', text, re.IGNORECASE | re.DOTALL)
    num_ext_match = re.search(r'Número Exterior:?\s*(.*?)(?=\s*(?:Número Interior|Nombre de la Colonia|Nombre de la Localidad))', text, re.IGNORECASE | re.DOTALL)
    num_int_match = re.search(r'Número Interior:?\s*(.*?)(?=\s*(?:Nombre de la Colonia|Nombre de la Localidad|Nombre del Municipio))', text, re.IGNORECASE | re.DOTALL)
    colonia_match = re.search(r'Nombre de la Colonia:?\s*(.*?)(?=\s*(?:Nombre de la Localidad|Nombre del Municipio|Nombre de la Entidad))', text, re.IGNORECASE | re.DOTALL)
    
    parts = []
    if vialidad_match:
        val = clean_field(vialidad_match.group(1), ["Número Exterior", "Número Interior", "Nombre de la Colonia"]) 
        if val:
            result["calle"] = val
            parts.append(val)
        
    if num_ext_match: 
        val = clean_field(num_ext_match.group(1), ["Número Interior", "Nombre de la Colonia", "Nombre de la Localidad"])
        if val:
            result["numero_exterior"] = val
            parts.append(val)
        
    if num_int_match: 
        val = clean_field(num_int_match.group(1), ["Nombre de la Colonia", "Nombre de la Localidad", "Nombre del Municipio"])
        if val: 
             result["numero_interior"] = val
             parts.append(f"Int {val}")
        
    if colonia_match: 
        val = clean_field(colonia_match.group(1), ["Nombre de la Localidad", "Nombre del Municipio", "Nombre de la Entidad"])
        if val:
            result["colonia"] = val
            parts.append(val)

    if parts:
        result["direccion"] = ", ".join(parts)

    return result
