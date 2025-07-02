from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base  # Asegúrate de tener Base centralizado

cliente_empresa = Table(
    'cliente_empresa',
    Base.metadata,
    Column('cliente_id', UUID(as_uuid=True), ForeignKey('clientes.id'), primary_key=True),
    Column('empresa_id', UUID(as_uuid=True), ForeignKey('empresas.id'), primary_key=True),
)
