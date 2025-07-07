# -*- coding: utf-8 -*-

# app/catalogos_sat/__init__.py

from .regimenes_fiscales import REGIMENES_FISCALES_SAT, validar_regimen_fiscal, obtener_descripcion_regimen

__all__ = [
    "REGIMENES_FISCALES_SAT",
    "validar_regimen_fiscal",
    "obtener_descripcion_regimen",
]
