from app.models.cliente import Cliente, cliente_empresa, Base as BaseCliente
from app.models.empresa import Empresa, Base as BaseEmpresa

# Usar uno de los Base como referencia unificada
Base = BaseCliente
