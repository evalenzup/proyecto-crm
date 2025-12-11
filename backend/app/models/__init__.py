from app.models.cliente import Base as BaseCliente
from app.models.cliente import Cliente, cliente_empresa
from app.models.empresa import Empresa
from .producto_servicio import ProductoServicio
from .email_config import EmailConfig
from .factura import Factura
from .factura_detalle import FacturaDetalle
from .pago import Pago, PagoDocumentoRelacionado
from .contacto import Contacto
from .egreso import Egreso
from .presupuestos import (
    Presupuesto,
    PresupuestoDetalle,
    PresupuestoAdjunto,
    PresupuestoEvento,
)
from .usuario import Usuario

# Usar uno de los Base como referencia unificada
Base = BaseCliente

__all__ = [
    "Base",
    "Cliente",
    "cliente_empresa",
    "Empresa",
    "ProductoServicio",
    "EmailConfig",
    "Factura",
    "FacturaDetalle",
    "Pago",
    "PagoDocumentoRelacionado",
    "Contacto",
    "Egreso",
    "Presupuesto",
    "PresupuestoDetalle",
    "PresupuestoAdjunto",
    "PresupuestoEvento",
    "Usuario",
]
