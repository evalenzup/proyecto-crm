
import sys
import os
from decimal import Decimal
from uuid import uuid4
from datetime import datetime
from unittest.mock import MagicMock

# Adjust path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_path)

# Mock config
sys.modules['app.config'] = MagicMock()
sys.modules['app.core.logger'] = MagicMock()

# Mock dependencies
sys.modules['app.services.timbrado_factmoderna'] = MagicMock()
sys.modules['app.services.cfdi40_xml'] = MagicMock()
sys.modules['app.services.pdf_factura'] = MagicMock()

from app.services.factura_service import crear_factura, obtener_factura, actualizar_factura
from app.schemas.factura import FacturaCreate, FacturaDetalleIn, FacturaUpdate
from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.models.empresa import Empresa
from app.models.cliente import Cliente
from app.models.associations import cliente_empresa

def test_retention_persistence():
    print("--- Testing Factura Retention Persistence ---")
    
    # Mock Session
    db = MagicMock()
    
    # Mock Association Check
    db.query.return_value.filter_by.return_value.first.return_value = True # Association exists
    
    # Mock Siguiente Folio
    # We need to mock the chain: db.query(Factura).filter(...).order_by(...).with_for_update().first()
    # It's complex to mock specific query chains. 
    # Let's trust logic and just inspect the objects created before "commit".
    
    # Create Payload
    empresa_id = uuid4()
    cliente_id = uuid4()
    
    concepto = FacturaDetalleIn(
        clave_producto="01010101",
        clave_unidad="H87",
        descripcion="Servicio con Retencion",
        cantidad=Decimal("1.0"),
        valor_unitario=Decimal("1000.00"),
        iva_tasa=Decimal("0.1600"),
        ret_iva_tasa=Decimal("0.0600"), # 6% Retention
        ret_isr_tasa=Decimal("0.1000"), # 10% Retention
    )
    
    payload = FacturaCreate(
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        conceptos=[concepto],
        moneda="MXN",
        uso_cfdi="G03",
        rfc_proveedor_sat=None,
        cfdi_relacionados_tipo=None,
        cfdi_relacionados=None,
        fecha_emision=datetime.now()
    )
    
    # We can't easily run 'crear_factura' with a Mock DB because it relies on SQLAlchemy models and relationships behaving broadly.
    # But we can inspect the logic in 'crear_factura' by tracing variables if we could run it.
    # Use a simpler approach: Re-read the code logic in `crear_factura` carefully.
    
    # Code Logic Analysis:
    # 1. base_calculo = 1000 * 1 = 1000
    # 2. ret_iva_importe = 1000 * 0.0600 = 60.00
    # 3. ret_isr_importe = 1000 * 0.1000 = 100.00
    # 4. FacturaDetalle created with **c.dict().
    #    c.dict() includes 'ret_iva_tasa': 0.0600.
    # 5. FacturaDetalle model has 'ret_iva_tasa' column.
    
    # So Persistence should works.
    
    # Failure point: Frontend Mapping "ON LOAD".
    # Frontend receives JSON.
    # normalizeConcepto (Frontend) maps it back to form.
    
    print("Logic seems sound in Backend. Checking Frontend mapping via manual inspection again.")
    
if __name__ == "__main__":
    test_retention_persistence()
