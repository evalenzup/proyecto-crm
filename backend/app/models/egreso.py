import uuid
import enum
from sqlalchemy import Column, String, Numeric, Date, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base


# Opciones para la categoría del egreso
class CategoriaEgreso(str, enum.Enum):
    GASTOS_GENERALES = "Gastos Generales"
    COMPRAS = "Compras"
    SERVICIOS = "Servicios"
    IMPUESTOS = "Impuestos"
    NOMINA = "Nómina"
    ALQUILER_OFICINA = "Alquiler de Oficina"
    MARKETING_PUBLICIDAD = "Marketing y Publicidad"
    TELECOMUNICACIONES = "Telecomunicaciones"
    TRANSPORTE_VIAJES = "Transporte y Viajes"
    SEGUROS = "Seguros"
    REPARACIONES_MANTENIMIENTO = "Reparaciones y Mantenimiento"
    SUMINISTROS_OFICINA = "Suministros de Oficina"
    SERVICIOS_PROFESIONALES = "Servicios Profesionales"
    LICENCIAS_SOFTWARE = "Licencias de Software"
    CAPACITACION = "Capacitación"
    GASOLINA = "Gasolina"
    OTROS = "Otros"


# Opciones para el estatus del egreso
class EstatusEgreso(str, enum.Enum):
    PENDIENTE = "Pendiente"
    PAGADO = "Pagado"
    CANCELADO = "Cancelado"


class Egreso(Base):
    __tablename__ = "egresos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)

    descripcion = Column(String, nullable=False)
    monto = Column(Numeric(18, 2), nullable=False)
    moneda = Column(String(3), nullable=False, default="MXN")
    fecha_egreso = Column(Date, nullable=False)

    categoria = Column(
        Enum(CategoriaEgreso), nullable=False, default=CategoriaEgreso.GASTOS_GENERALES
    )
    estatus = Column(
        Enum(EstatusEgreso), nullable=False, default=EstatusEgreso.PENDIENTE
    )

    proveedor = Column(String)  # Nombre del proveedor (simple por ahora)

    # Ruta a un archivo de comprobante (factura, recibo, etc.)
    path_documento = Column(String)
    metodo_pago = Column(String, nullable=True)

    empresa = relationship("Empresa")

    __table_args__ = (
        Index("ix_egresos_fecha_egreso", "fecha_egreso"),
        Index("ix_egresos_empresa_id", "empresa_id"),
        Index("ix_egresos_estatus", "estatus"),
    )
