# app/catalogos_sat/facturacion.py
from typing import List, Dict, Optional
from app.catalogos_sat.datos.c_tipodecomprobante import CATALOGO as TIPO_COMPROBANTE
from app.catalogos_sat.datos.c_formapago import CATALOGO as FORMA_PAGO
from app.catalogos_sat.datos.c_metodopago import CATALOGO as METODO_PAGO
from app.catalogos_sat.datos.c_tiporelacion import CATALOGO as TIPO_RELACION
from app.catalogos_sat.datos.c_motivocancelacion import CATALOGO as MOTIVO_CANCELACION

from app.catalogos_sat.datos.c_usocfdi import CATALOGO as USO_CFDI 

# Para tipocomprobante
def obtener_todos_tipos_comprobante() -> list[dict]:
    """
    Devuelve la lista de tipos de comprobante disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return TIPO_COMPROBANTE

def validar_clave_tipo_comprobante(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in TIPO_COMPROBANTE)

# Para forma de pago
def obtener_todas_formas_pago() -> list[dict]:
    """
    Devuelve la lista de formas de pago disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return FORMA_PAGO

def validar_clave_forma_pago(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in FORMA_PAGO)

# Para metodo de pago
def obtener_todos_metodos_pago() -> list[dict]:
    """
    Devuelve la lista de métodos de pago disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return METODO_PAGO

def validar_clave_metodo_pago(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in METODO_PAGO)

# Para usocfdi
def obtener_todos_usos_cfdi() -> list[dict]:
    """
    Devuelve la lista de usos de CFDI disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return USO_CFDI

def validar_clave_usos_cfdi(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in USO_CFDI)

# Para tipo de relacion
def obtener_todas_tipos_relacion() -> list[dict]:
    """
    Devuelve la lista de tipos de relación disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return TIPO_RELACION

def validar_clave_tipo_relacion(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in TIPO_RELACION)


# Para tipo de relacion
def obtener_todas_tipos_relacion() -> list[dict]:
    """
    Devuelve la lista de tipos de relación disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return TIPO_RELACION

def validar_clave_tipo_relacion(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in TIPO_RELACION)

# Para motivos de cancelación
def obtener_todas_motivos_cancelacion() -> list[dict]:
    """
    Devuelve la lista de motivos de cancelación disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return MOTIVO_CANCELACION

def validar_clave_motivo_cancelacion(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in MOTIVO_CANCELACION)
