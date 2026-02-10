
import sys
import os
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime

# Adjust path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_path)

# --- MOCKING ---

# Mock app.config
mock_config = MagicMock()
mock_settings = MagicMock()
mock_config.settings = mock_settings
sys.modules['app.config'] = mock_config
sys.modules['app.core.logger'] = MagicMock()

# Mock app.services.cfdi40_xml
mock_cfdi = MagicMock()

def real_money2(v):
    return f"{Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

def real_tasa6(v):
    return f"{Decimal(str(v)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)}"

def real_fmt_date(dt):
    return dt.isoformat() if dt else datetime.now().isoformat()

mock_cfdi.money2 = real_money2
mock_cfdi.tasa6 = real_tasa6
mock_cfdi._fmt_cfdi_fecha_local = real_fmt_date
mock_cfdi._load_csd_cert_for_empresa.return_value = (None, "CERT", None)
mock_cfdi._load_csd_key_for_empresa.return_value = "KEY"
mock_cfdi._sign_cadena_sha256_pkcs1v15.return_value = "SELLO"
mock_cfdi._build_cadena_original_40.return_value = "OriginalString"

sys.modules['app.services.cfdi40_xml'] = mock_cfdi

# Now import pago20_xml
from app.services.pago20_xml import build_pago20_xml_sin_timbrar
from app.models.pago import Pago, PagoDocumentoRelacionado
from app.models.empresa import Empresa
from app.models.cliente import Cliente
from xml.etree import ElementTree as ET

def test_decimal_precision():
    print("--- Testing 3 Decimal Precision ---")
    
    # Mock DB Session
    db = MagicMock()
    
    pago_id = uuid4()
    empresa = Empresa(id=uuid4(), rfc="AAA010101AAA", nombre="Empresa Test", codigo_postal="22000", regimen_fiscal="601")
    cliente = Cliente(id=uuid4(), rfc="XAXX010101000", nombre_razon_social="Publico General", codigo_postal="22000", regimen_fiscal="616")
    
    # Scenario: Payment of 100.00, split into 3 parts of 33.333
    # Total = 99.999. If header is 100, we have mismatch.
    # Let's test just precision first: Header 33.333, Doc 33.333
    
    pago = Pago(
        id=pago_id,
        empresa_id=empresa.id,
        cliente_id=cliente.id,
        fecha_pago=datetime.now(),
        fecha_emision=datetime.now(),
        forma_pago_p="03",
        moneda_p="MXN",
        monto=Decimal("33.333"),
        tipo_cambio_p=Decimal("1"),
        estatus="BORRADOR",
        serie="P",
        folio="123",
    )
    pago.empresa = empresa
    pago.cliente = cliente
    
    doc1 = PagoDocumentoRelacionado(
        id=uuid4(),
        id_documento=str(uuid4()),
        moneda_dr="MXN",
        num_parcialidad=1,
        imp_saldo_ant=Decimal("100.00"),
        imp_pagado=Decimal("33.333"), # 3 decimals
        imp_saldo_insoluto=Decimal("66.667"),
        impuestos_dr={}
    )
    pago.documentos_relacionados = [doc1]
    
    # Mock Query
    db.query.return_value.options.return_value.filter.return_value.first.return_value = pago
    
    try:
        xml_bytes = build_pago20_xml_sin_timbrar(db, pago_id)
        root = ET.fromstring(xml_bytes)
        ns = {'pago20': 'http://www.sat.gob.mx/Pagos20'}
        
        totales = root.find(".//pago20:Totales", ns)
        monto_total_pagos = totales.get("MontoTotalPagos")
        print(f"Totales.MontoTotalPagos: {monto_total_pagos}")
        
        pago_node = root.find(".//pago20:Pago", ns)
        monto_pago = pago_node.get("Monto")
        print(f"Pago.Monto: {monto_pago}")
        
        # Verify 3 decimals
        if "33.333" not in monto_total_pagos:
            print(f"FAIL: Expected '33.333' in Totals, got '{monto_total_pagos}'")
        else:
             print("SUCCESS: Totals preserves 3 decimals.")

        if "33.333" not in monto_pago:
             print(f"FAIL: Expected '33.333' in Pago.Monto, got '{monto_pago}'")
        else:
             print("SUCCESS: Pago.Monto preserves 3 decimals.")
             
        # Check Doc
        doc_node = pago_node.find(".//pago20:DoctoRelacionado", ns)
        imp_pagado = doc_node.get("ImpPagado")
        if "33.333" not in imp_pagado:
             print(f"FAIL: Expected '33.333' in ImpPagado, got '{imp_pagado}'")
        else:
             print("SUCCESS: ImpPagado preserves 3 decimals.")

            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_decimal_precision()
