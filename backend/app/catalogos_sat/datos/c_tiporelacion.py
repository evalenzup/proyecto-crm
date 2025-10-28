from typing import List, Dict

"""
Catálogo generado a partir de la hoja 'c_TipoRelacion'
"""

CATALOGO: List[Dict[str, str]] = [
    {"clave": "1", "descripcion": "Nota de crédito de los documentos relacionados"},
    {"clave": "2", "descripcion": "Nota de débito de los documentos relacionados"},
    {
        "clave": "3",
        "descripcion": "Devolución de mercancía sobre facturas o traslados previos",
    },
    {"clave": "4", "descripcion": "Sustitución de los CFDI previos"},
    {"clave": "5", "descripcion": "Traslados de mercancías facturados previamente"},
    {"clave": "6", "descripcion": "Factura generada por los traslados previos"},
    {"clave": "7", "descripcion": "CFDI por aplicación de anticipo"},
]
