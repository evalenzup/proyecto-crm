from decimal import Decimal, ROUND_HALF_UP

# Simulando la factura de NORTON
factura_total_dec = Decimal("1232.04")
imp_pagado_dec = Decimal("1232.04")

payment_ratio = imp_pagado_dec / factura_total_dec

c_cantidad = Decimal("1")
c_vunit = Decimal("1200.00")
c_desc = Decimal("0")

base_concepto = (c_cantidad * c_vunit) - c_desc
base_proporcional = base_concepto * payment_ratio

# IVA 8%
importe_iva_orig = Decimal("96.00")
importe_iva_prop = importe_iva_orig * payment_ratio

# Retención IVA 5.33%
importe_ret_orig = Decimal("63.96")
importe_ret_prop = importe_ret_orig * payment_ratio

print("TOTAL Factura:", factura_total_dec)
print("Base:", base_proporcional)
print("IVA:", importe_iva_prop)
print("Retencion:", importe_ret_prop)

base_dr_rounded = base_proporcional.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
iva_dr_rounded = importe_iva_prop.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
ret_dr_rounded = importe_ret_prop.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

print("Base rounded:", base_dr_rounded)
print("IVA rounded:", iva_dr_rounded)
print("Ret rounded:", ret_dr_rounded)

sum_calc = base_dr_rounded + iva_dr_rounded - ret_dr_rounded
print("Sum calculated:", sum_calc)

if sum_calc != imp_pagado_dec:
    print("MISMATCH!")
