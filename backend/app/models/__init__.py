from app.models.cliente import Cliente, cliente_empresa, Base as BaseCliente
from app.models.empresa import Empresa, Base as BaseEmpresa
from app.models.producto_servicio import ProductoServicio, Base as BaseProductoServicio

# Usar uno de los Base como referencia unificada
Base = BaseCliente
