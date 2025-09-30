from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base

class EmailConfig(Base):
    __tablename__ = "email_configs"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), unique=True, nullable=False, index=True)
    smtp_server = Column(String, nullable=False)
    smtp_port = Column(Integer, nullable=False)
    smtp_user = Column(String, nullable=False)
    smtp_password = Column(String, nullable=False)  # Se almacenará cifrada
    from_address = Column(String, nullable=False)
    from_name = Column(String, nullable=True)
    use_tls = Column(Boolean, default=True)

    empresa = relationship("Empresa", back_populates="email_config")
