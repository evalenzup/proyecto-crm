import sys
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4
from decimal import Decimal
from datetime import datetime

# Setup path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.models.factura import Factura
from app.models.empresa import Empresa
from app.models.cliente import Cliente
from app.models.factura_detalle import FacturaDetalle

def test_generate_pdf():
    # Mock Objects
    empresa = Empresa(
        id=uuid4(),
        nombre="Empresa Demo S.A. de C.V.",
        rfc="DEMO8001019A1",
        regimen_fiscal="601",
        codigo_postal="01000",
        direccion="Av. Reforma 123",
        nombre_banco="BBVA Bancomer",
        numero_cuenta="0123456789",
        clabe="012345678901234567",
        beneficiario="Empresa Demo S.A."
    )
    
    cliente = Cliente(
        id=uuid4(),
        nombre_razon_social="Cliente Prueba S.A.",
        rfc="CLI000101000",
        regimen_fiscal="603",
        codigo_postal="02000"
    )
    
    concepto = FacturaDetalle(
        cantidad=1,
        valor_unitario=1000,
        clave_producto="84111506",
        descripcion="Servicios de facturación",
        clave_unidad="E48",
        importe=1000,
        descuento=0,
        iva_tasa=0.16,
        iva_importe=160
    )
    
    factura = Factura(
        id=uuid4(),
        empresa=empresa,
        cliente=cliente,
        conceptos=[concepto],
        fecha_emision=datetime.now(),
        folio="100",
        serie="A",
        subtotal=1000,
        total=1160,
        moneda="MXN",
        metodo_pago="PUE",
        forma_pago="03",
        uso_cfdi="G03",
        estatus="TIMBRADO",
        cfdi_uuid=str(uuid4()),
        fecha_timbrado=datetime.now(),
        sello_cfdi="SELLO_MOCK",
        sello_sat="SELLO_SAT_MOCK",
        rfc_proveedor_sat="SAT970701NN3",
        no_certificado_sat="00001000000500000001",
        observaciones="Estas son observaciones de prueba."
    )

    # Patch load_factura_full to return our mock
    with patch("app.services.pdf_factura.load_factura_full", return_value=factura):
        from app.services.pdf_factura import render_factura_pdf_bytes_from_model
        
        # Mock Session
        db = MagicMock()
        
        print("Generating PDF...")
        pdf_bytes = render_factura_pdf_bytes_from_model(db, factura.id)
        
        output_path = "test_factura_banco_centro.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
            
        print(f"PDF generated successfully at {output_path}")
        print(f"Size: {len(pdf_bytes)} bytes")

if __name__ == "__main__":
    test_generate_pdf()
