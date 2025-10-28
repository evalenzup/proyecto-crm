# app/services/email_config_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.models import EmailConfig, Empresa
from app.schemas.email_config import EmailConfigCreate, EmailConfigUpdate, EmailConfigTest
from app.repository.base import BaseRepository
from app.core.security import encrypt_data, decrypt_data
from app.services import email_sender


class EmailConfigRepository(BaseRepository[EmailConfig, EmailConfigCreate, EmailConfigUpdate]):
    def get_by_empresa(self, db: Session, *, empresa_id: UUID) -> Optional[EmailConfig]:
        return db.query(self.model).filter(self.model.empresa_id == empresa_id).first()

    def create_for_empresa(
        self, db: Session, *, empresa_id: UUID, obj_in: EmailConfigCreate
    ) -> EmailConfig:
        db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not db_empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        if db_empresa.email_config:
            raise HTTPException(
                status_code=400, detail="La empresa ya tiene una configuración de email"
            )

        encrypted_password = encrypt_data(obj_in.smtp_password)
        db_obj = self.model(
            **obj_in.model_dump(exclude={"smtp_password"}),
            empresa_id=empresa_id,
            smtp_password=encrypted_password,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_for_empresa(
        self, db: Session, *, empresa_id: UUID, obj_in: EmailConfigUpdate
    ) -> EmailConfig:
        db_email_config = self.get_by_empresa(db, empresa_id=empresa_id)
        if not db_email_config:
            raise HTTPException(
                status_code=404, detail="Configuración de email no encontrada"
            )

        update_data = obj_in.model_dump(exclude_unset=True)
        if "smtp_password" in update_data and update_data["smtp_password"]:
            update_data["smtp_password"] = encrypt_data(update_data["smtp_password"])

        return super().update(db, db_obj=db_email_config, obj_in=update_data)

    def remove_for_empresa(self, db: Session, *, empresa_id: UUID) -> Optional[EmailConfig]:
        db_email_config = self.get_by_empresa(db, empresa_id=empresa_id)
        if not db_email_config:
            return None
        db.delete(db_email_config)
        db.commit()
        return db_email_config

    def test_connection(
        self, db: Session, *, empresa_id: UUID, email_config_test: EmailConfigTest
    ):
        smtp_password = email_config_test.smtp_password
        if not smtp_password:
            db_email_cfg = self.get_by_empresa(db, empresa_id=empresa_id)
            if not db_email_cfg:
                raise HTTPException(
                    status_code=404,
                    detail="Configuración de email no encontrada para la empresa",
                )
            try:
                smtp_password = decrypt_data(db_email_cfg.smtp_password)
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo descifrar la contraseña almacenada",
                )

        try:
            email_sender.test_smtp_connection(
                smtp_server=email_config_test.smtp_server,
                smtp_port=email_config_test.smtp_port,
                smtp_user=email_config_test.smtp_user,
                smtp_password=smtp_password,
                use_tls=email_config_test.use_tls,
            )
        except email_sender.EmailSendingError as e:
            raise HTTPException(status_code=400, detail=str(e))


email_config_repo = EmailConfigRepository(EmailConfig)
