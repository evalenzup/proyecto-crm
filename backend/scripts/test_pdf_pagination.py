import sys
import os
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.models.pago import Pago, PagoDocumentoRelacionado, EstatusPago
from app.models.empresa import Empresa
from app.models.cliente import Cliente
from app.models.factura import Factura
from app.services.pdf_pago import render_pago_pdf_bytes_from_model

# Mock objects to avoid DB dependency for pure layout testing
class MockSession:
    def query(self, *args):
        return self
    def options(self, *args):
        return self
    def filter(self, *args):
        return self
    def first(self):
        # Return a mock Pago with many documents
        empresa = Empresa(
            id=uuid4(),
            nombre="EMPRESA DE PRUEBA SA DE CV",
            rfc="EMP123456789",
            regimen_fiscal="601",
            codigo_postal="22000"
        )
        cliente = Cliente(
            id=uuid4(),
            nombre_razon_social="CLIENTE DE PRUEBA SA DE CV",
            rfc="CLI123456789",
            regimen_fiscal="601",
            codigo_postal="22000"
        )
        
        docs = []
        for i in range(40): # 40 documents should trigger pagination/overflow
            f = Factura(
                serie="F",
                folio=str(1000 + i),
                moneda="MXN",
                total=Decimal("1000.00")
            )
            doc = PagoDocumentoRelacionado(
                id_documento=str(uuid4()),
                moneda_dr="MXN",
                num_parcialidad=1,
                imp_saldo_ant=Decimal("1000.00"),
                imp_pagado=Decimal("1000.00"),
                imp_saldo_insoluto=Decimal("0.00"),
                factura=f
            )
            docs.append(doc)

        pago = Pago(
            id=uuid4(),
            empresa=empresa,
            cliente=cliente,
            serie="P",
            folio="100",
            fecha_pago=datetime.now(),
            forma_pago_p="03",
            moneda_p="MXN",
            monto=Decimal("40000.00"),
            tipo_cambio_p=1,
            estatus=EstatusPago.TIMBRADO,
            uuid=str(uuid4()), # Timbrado
            fecha_timbrado=datetime.now(),
            sello_cfdi="SelloCFDIfake1234567890",
            sello_sat="SelloSATfake1234567890",
            rfc_proveedor_sat="SAT970701NN3",
            no_certificado="00001000000500000000",
            no_certificado_sat="00001000000500000000",
            documentos_relacionados=docs
        )
        return pago

def test_pagination():
    db = MockSession()
    try:
        pdf_bytes = render_pago_pdf_bytes_from_model(db, uuid4())
        output_path = "test_pagination.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"Generated {output_path} with 40 rows. Check for overlap.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pagination()
