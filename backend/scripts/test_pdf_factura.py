import sys
import os
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.models.empresa import Empresa
from app.models.cliente import Cliente
from app.services.pdf_factura import render_factura_pdf_bytes_from_model

# Mock objects to avoid DB dependency for pure layout testing
class MockSession:
    def query(self, *args):
        return self
    def options(self, *args):
        return self
    def filter(self, *args):
        return self
    def first(self):
        # Mock Empresa
        empresa = Empresa(
            id=uuid4(),
            nombre="EMPRESA DE PRUEBA SA DE CV (FACTURA)",
            rfc="EMP123456789",
            regimen_fiscal="601",
            codigo_postal="22000"
        )
        # Mock Cliente
        cliente = Cliente(
            id=uuid4(),
            nombre_razon_social="CLIENTE DE PRUEBA SA DE CV",
            rfc="CLI123456789",
            regimen_fiscal="601",
            codigo_postal="22000"
        )
        
        conceptos = []
        for i in range(60): # 60 lines to force likely 2-3 pages
            det = FacturaDetalle(
                clave_producto="01010101",
                descripcion=f"Producto de prueba larga descripción linea {i+1} para verificar que el texto se ajuste y salte de página correctamente si es necesario.",
                clave_unidad="H87",
                cantidad=Decimal("1.0"),
                valor_unitario=Decimal("100.00"),
                importe=Decimal("100.00"),
                iva_tasa=Decimal("0.16"),
                factura_id=uuid4()
            )
            # Assign dynamic attributes expected by reportlab logic
            det.unidad_descripcion = "Pieza"
            conceptos.append(det)

        factura = Factura(
            id=uuid4(),
            empresa=empresa,
            cliente=cliente,
            serie="F",
            folio="555",
            fecha_emision=datetime.now(),
            forma_pago="99",
            metodo_pago="PPD",
            moneda="MXN",
            tipo_cambio=Decimal("1.0"),
            subtotal=Decimal("6000.00"),
            impuestos_trasladados=Decimal("960.00"),
            total=Decimal("6960.00"),
            estatus="TIMBRADO",
            cfdi_uuid=str(uuid4()),
            fecha_timbrado=datetime.now(),
            sello_cfdi="SelloCFDIfakeFactura" * 5,
            sello_sat="SelloSATfakeFactura" * 5,
            rfc_proveedor_sat="SAT970701NN3",
            lugar_expedicion="22000",
            conceptos=conceptos,
            uso_cfdi="G03"
        )
        # Add attributes expected by _compute_tax_breakdown
        factura.conceptos = conceptos
        
        return factura

def test_pagination_factura():
    db = MockSession()
    try:
        pdf_bytes = render_factura_pdf_bytes_from_model(db, uuid4())
        output_path = "test_pagination_factura.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"Generated {output_path} with 60 header rows. Check for overlap.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pagination_factura()
