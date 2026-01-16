# app/services/egreso_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import date

from app.models.egreso import Egreso as EgresoModel
from app.schemas.egreso import EgresoCreate, EgresoUpdate
from app.repository.base import BaseRepository


class EgresoRepository(BaseRepository[EgresoModel, EgresoCreate, EgresoUpdate]):
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        empresa_id: Optional[UUID] = None,
        proveedor: Optional[str] = None,
        categoria: Optional[str] = None,
        estatus: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ) -> Tuple[List[EgresoModel], int]:
        query = db.query(self.model)

        if empresa_id:
            query = query.filter(self.model.empresa_id == empresa_id)
        if proveedor:
            query = query.filter(self.model.proveedor.ilike(f"%{proveedor}%"))
        if categoria:
            query = query.filter(self.model.categoria == categoria)
        if estatus:
            query = query.filter(self.model.estatus == estatus)
        if fecha_desde:
            query = query.filter(self.model.fecha_egreso >= fecha_desde)
        if fecha_hasta:
            query = query.filter(self.model.fecha_egreso <= fecha_hasta)

        total = query.count()
        items = query.order_by(self.model.fecha_egreso.desc()).offset(skip).limit(limit).all()
        return items, total

    def search_proveedores(
        self,
        db: Session,
        mpresa_id: Optional[UUID] = None,
        q: str = ""
    ) -> List[str]:
        query = db.query(self.model.proveedor).distinct()
        if mpresa_id:
            query = query.filter(self.model.empresa_id == mpresa_id)
        if q:
            query = query.filter(self.model.proveedor.ilike(f"%{q}%"))
        
        # Limit to 20 suggestions
        results = query.limit(20).all()
        # results is a list of tuples like [('Prov A',), ('Prov B',)]
        return [r[0] for r in results if r[0]]


egreso_repo = EgresoRepository(EgresoModel)


def parse_egreso_xml(file_content: bytes) -> dict:
    """
    Parsea un archivo XML (CFDI 3.3 o 4.0) y extrae datos relevantes para el Egreso.
    Retorna un diccionario con: fecha, monto, moneda, proveedor, metodo_pago.
    Si falla, retorna dict vacío o lanza excepción.
    """
    import xml.etree.ElementTree as ET
    
    try:
        root = ET.fromstring(file_content)
        # Namespaces SAT
        ns = {'cfdi': 'http://www.sat.gob.mx/cfd/3', 'cfdi4': 'http://www.sat.gob.mx/cfd/4'}
        
        # Detectar versión (comprobando si root tag incluye el namespace o atributos)
        # Generalmente root.tag es '{http://www.sat.gob.mx/cfd/3}Comprobante' o cfd/4
        
        # Extraer atributos principales del nodo raiz
        # Comprobante: Fecha, Total, Moneda, MetodoPago, FormaPago
        fecha_raw = root.get('Fecha') or root.get('fecha')
        total_raw = root.get('Total') or root.get('total')
        moneda_raw = root.get('Moneda') or root.get('moneda') or "MXN"
        metodo_pago_sat = root.get('MetodoPago') or root.get('metodoPago') # PUE/PPD
        forma_pago_sat = root.get('FormaPago') or root.get('formaPago') # 01, 02, etc.
        
        # Emisor
        emisor = None
        # Buscar namespace correcto
        for key in ['cfdi', 'cfdi4']:
            # Intentar encontrar Emisor con namespaces
            # Nota: ET a veces requiere el namespace completo en find
            # {http://www.sat.gob.mx/cfd/X}Emisor
            
            # Estrategia agnóstica de namespace para hijos directos si es posible,
            # o buscar con el namespace URI explícito.
            # El namespace map 'ns' ayuda en find('cfdi:Emisor', ns)
            
            # Intentamos buscar con prefix si el XML usa prefix 'cfdi'
            # Pero a veces no tienen prefix, es default namespace.
            # Lo más seguro es iterar hijos y buscar 'Emisor'
            pass
            
        # Búsqueda manual de Emisor en hijos directos
        nombre_emisor = ""
        rfc_emisor = ""
        for child in root:
            if 'Emisor' in child.tag:
                nombre_emisor = child.get('Nombre') or child.get('nombre') or ""
                rfc_emisor = child.get('Rfc') or child.get('rfc') or ""
                break
        
        # Formatear fecha (ISO 8601 YYYY-MM-DD)
        # La fecha en CFDI suele ser "YYYY-MM-DDTHH:MM:SS"
        fecha_iso = None
        if fecha_raw:
            fecha_iso = fecha_raw.split('T')[0]
            
        return {
            "fecha_egreso": fecha_iso,
            "monto": float(total_raw) if total_raw else 0.0,
            "moneda": moneda_raw,
            "proveedor": nombre_emisor or rfc_emisor, # Preferir Nombre, fallback RFC
            "metodo_pago": forma_pago_sat, # Mapear FormaPago (01, 02...) al campo metodo_pago
            "rfc_proveedor": rfc_emisor,
            "metodo_pago_sat": metodo_pago_sat # PUE/PPD
        }
        
    except Exception as e:
        print(f"Error parseando XML: {e}")
        return {}
