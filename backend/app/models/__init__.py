from app.models.cliente import Cliente, cliente_empresa, Base as BaseCliente
from app.models.empresa import Empresa, Base as BaseEmpresa
from .producto_servicio import ProductoServicio
from .email_config import EmailConfig, Base as BaseProductoServicio
from .factura import Factura
from .factura_detalle import FacturaDetalle
from .pago import Pago, PagoDocumentoRelacionado
from .contacto import Contacto

# Usar uno de los Base como referencia unificada
Base = BaseCliente