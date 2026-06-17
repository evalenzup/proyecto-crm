from app.models.cliente import Base as BaseCliente
from app.models.cliente import Cliente, cliente_empresa
from app.models.cliente_documento import ClienteDocumento
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
from .usuario import Usuario, UsuarioEmpresa, UsuarioPermiso
from .cobranza import CobranzaNota
from .notificacion import Notificacion
from .auditoria import AuditoriaLog
from .refresh_token import RefreshToken
from .servicio_operativo import ServicioOperativo
from .tecnico import Tecnico
from .unidad import Unidad
from .mantenimiento_unidad import MantenimientoUnidad
from .poliza_seguro import PolizaSeguro
from .associations import tecnico_especialidades, unidad_servicios_compatibles
from .orden_servicio import OrdenServicio, HistorialEstadoOS

# Usar uno de los Base como referencia unificada
Base = BaseCliente

__all__ = [
    "Base",
    "Cliente",
    "ClienteDocumento",
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
    "UsuarioEmpresa",
    "UsuarioPermiso",
    "CobranzaNota",
    "Notificacion",
    "AuditoriaLog",
    "RefreshToken",
    "ServicioOperativo",
    "Tecnico",
    "Unidad",
    "MantenimientoUnidad",
    "PolizaSeguro",
    "tecnico_especialidades",
    "unidad_servicios_compatibles",
    "OrdenServicio",
    "HistorialEstadoOS",
]
