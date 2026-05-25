# app/schemas/programacion_factura.py
from __future__ import annotations
import calendar
from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

PERIODICIDADES = Literal[
    "unica", "semanal", "quincenal", "mensual",
    "bimestral", "trimestral", "semestral", "anual"
]

PERIODICIDAD_LABELS = {
    "unica":      "Única vez",
    "semanal":    "Semanal",
    "quincenal":  "Quincenal",
    "mensual":    "Mensual",
    "bimestral":  "Bimestral",
    "trimestral": "Trimestral",
    "semestral":  "Semestral",
    "anual":      "Anual",
}


class ConceptoPlantilla(BaseModel):
    """Un concepto serializable para guardar en JSONB."""
    tipo:                   Optional[str]   = None
    producto_servicio_id:   Optional[UUID]  = None
    clave_producto:         str
    clave_unidad:           str
    descripcion:            str
    cantidad:               str = "1"        # str para preservar decimales exactos
    valor_unitario:         str = "0"
    descuento:              str = "0"
    iva_tasa:               Optional[str]   = None
    ret_iva_tasa:           Optional[str]   = None
    ret_isr_tasa:           Optional[str]   = None
    no_identificacion:      Optional[str]   = None
    unidad:                 Optional[str]   = None
    objeto_imp:             Optional[str]   = "02"

    @field_validator("descripcion")
    @classmethod
    def strip_desc(cls, v: str) -> str:
        return v.strip()


class ProgramacionFacturaBase(BaseModel):
    empresa_id:     UUID
    cliente_id:     UUID
    nombre:         Optional[str]   = Field(None, max_length=120, description="Etiqueta descriptiva")

    # Datos fiscales
    serie:              Optional[str]   = Field("A", max_length=10)
    tipo_comprobante:   Literal["I", "P"] = "I"
    forma_pago:         Optional[str]   = None
    metodo_pago:        Optional[Literal["PUE", "PPD"]] = None
    uso_cfdi:           Optional[str]   = None
    moneda:             Literal["MXN", "USD"] = "MXN"
    lugar_expedicion:   Optional[str]   = None
    condiciones_pago:   Optional[str]   = None
    observaciones:      Optional[str]   = None
    retencion_local_desc: Optional[str] = None
    retencion_local_tasa: Optional[str] = None

    # Conceptos
    conceptos: List[ConceptoPlantilla] = Field(default_factory=list, min_length=1)

    # Programación
    periodicidad:       PERIODICIDADES          = "mensual"
    proxima_ejecucion:  date
    fecha_fin:          Optional[date]          = None

    # Automatización
    auto_timbrar:   bool = False
    auto_enviar:    bool = False
    emails_destino: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_fechas_y_emails(self) -> "ProgramacionFacturaBase":
        if self.fecha_fin and self.fecha_fin < self.proxima_ejecucion:
            raise ValueError("fecha_fin debe ser posterior a proxima_ejecucion")
        if self.auto_enviar and not self.emails_destino:
            raise ValueError("Debes indicar al menos un email en emails_destino cuando auto_enviar=True")
        return self


class ProgramacionFacturaCreate(ProgramacionFacturaBase):
    pass


class ProgramacionFacturaUpdate(BaseModel):
    nombre:             Optional[str]           = None
    cliente_id:         Optional[UUID]          = None
    serie:              Optional[str]           = None
    tipo_comprobante:   Optional[str]           = None
    forma_pago:         Optional[str]           = None
    metodo_pago:        Optional[str]           = None
    uso_cfdi:           Optional[str]           = None
    moneda:             Optional[str]           = None
    lugar_expedicion:   Optional[str]           = None
    condiciones_pago:   Optional[str]           = None
    observaciones:      Optional[str]           = None
    retencion_local_desc: Optional[str]         = None
    retencion_local_tasa: Optional[str]         = None
    conceptos:          Optional[List[ConceptoPlantilla]] = None
    periodicidad:       Optional[PERIODICIDADES] = None
    proxima_ejecucion:  Optional[date]          = None
    fecha_fin:          Optional[date]          = None
    auto_timbrar:       Optional[bool]          = None
    auto_enviar:        Optional[bool]          = None
    emails_destino:     Optional[List[str]]     = None
    activo:             Optional[bool]          = None


class ProgramacionFacturaOut(ProgramacionFacturaBase):
    id:                 UUID
    activo:             bool
    ultima_ejecucion:   Optional[datetime]  = None
    facturas_generadas: int
    creado_en:          datetime
    actualizado_en:     datetime

    # Campos denormalizados para la UI
    cliente_nombre:     Optional[str]   = None
    empresa_nombre:     Optional[str]   = None

    class Config:
        from_attributes = True


class ProgramacionFacturaListOut(BaseModel):
    items: List[ProgramacionFacturaOut]
    total: int
