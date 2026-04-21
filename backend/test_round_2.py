from decimal import Decimal, ROUND_HALF_UP

imp_pagado = Decimal("6613.79")
factura_total = Decimal("6613.79")

# Supongamos una factura de prueba que da este problema:
# Subtotal = 6000.00
# IVA 16% = 960.00
# Ret. IVA 10.6666% = 640.00 // Wait, what if they have ISR + Ret IVA?
# Let's say:
# Base = 6123.88
# IVA 16% = 979.82
# Retencion IVA (e.g., 8%) = 489.91
# Total = 6123.88 + 979.82 - 489.91 = 6613.79

sum_base_iva_ret = Decimal("6123.88") + Decimal("979.82") - Decimal("489.91")
print(sum_base_iva_ret)
