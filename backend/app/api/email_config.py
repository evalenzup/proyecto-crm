# backend/app/api/email_config.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app import models
from app.schemas import email_config
from app.database import get_db
from app.core.security import encrypt_data, decrypt_data
from app.services import email_sender

router = APIRouter()


@router.post("/test-connection", status_code=status.HTTP_200_OK)
def test_email_config_connection(
    empresa_id: uuid.UUID,
    email_config_test: email_config.EmailConfigTest,
    db: Session = Depends(get_db),
):
    """Prueba la conexión a un servidor SMTP. Si no se envía `smtp_password`, usa la contraseña guardada en la empresa."""
    try:
        smtp_password = email_config_test.smtp_password
        if not smtp_password:
            # Buscar configuración almacenada y usar la contraseña cifrada
            db_email_cfg = db.query(models.EmailConfig).filter(models.EmailConfig.empresa_id == empresa_id).first()
            if not db_email_cfg:
                raise HTTPException(status_code=404, detail="Configuración de email no encontrada para la empresa")
            try:
                smtp_password = decrypt_data(db_email_cfg.smtp_password)
            except Exception:
                raise HTTPException(status_code=500, detail="No se pudo descifrar la contraseña almacenada")

        email_sender.test_smtp_connection(
            smtp_server=email_config_test.smtp_server,
            smtp_port=email_config_test.smtp_port,
            smtp_user=email_config_test.smtp_user,
            smtp_password=smtp_password,
            use_tls=email_config_test.use_tls,
        )
        return {"message": "Conexión SMTP exitosa."}
    except email_sender.EmailSendingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado al probar la conexión: {e}")

@router.post("/", response_model=email_config.EmailConfig, status_code=status.HTTP_201_CREATED)
def create_email_config(
    empresa_id: uuid.UUID,
    email_config_in: email_config.EmailConfigCreate,
    db: Session = Depends(get_db),
):
    """Crea una nueva configuración de email para una empresa."""
    db_empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if db_empresa.email_config:
        raise HTTPException(status_code=400, detail="La empresa ya tiene una configuración de email")

    encrypted_password = encrypt_data(email_config_in.smtp_password)
    
    db_email_config = models.EmailConfig(
        **email_config_in.model_dump(exclude={"smtp_password"}),
        empresa_id=empresa_id,
        smtp_password=encrypted_password
    )
    
    db.add(db_email_config)
    db.commit()
    db.refresh(db_email_config)
    return db_email_config

@router.get("/", response_model=email_config.EmailConfig)
def read_email_config(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtiene la configuración de email de una empresa."""
    db_email_config = db.query(models.EmailConfig).filter(models.EmailConfig.empresa_id == empresa_id).first()
    if not db_email_config:
        raise HTTPException(status_code=404, detail="Configuración de email no encontrada")
    return db_email_config

@router.put("/", response_model=email_config.EmailConfig)
def update_email_config(
    empresa_id: uuid.UUID,
    email_config_in: email_config.EmailConfigUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza la configuración de email de una empresa."""
    db_email_config = db.query(models.EmailConfig).filter(models.EmailConfig.empresa_id == empresa_id).first()
    if not db_email_config:
        raise HTTPException(status_code=404, detail="Configuración de email no encontrada")

    update_data = email_config_in.model_dump(exclude_unset=True)

    if "smtp_password" in update_data and update_data["smtp_password"]:
        update_data["smtp_password"] = encrypt_data(update_data["smtp_password"])

    for field, value in update_data.items():
        setattr(db_email_config, field, value)

    db.commit()
    db.refresh(db_email_config)
    return db_email_config

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_config(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    """Elimina la configuración de email de una empresa."""
    db_email_config = db.query(models.EmailConfig).filter(models.EmailConfig.empresa_id == empresa_id).first()
    if not db_email_config:
        raise HTTPException(status_code=404, detail="Configuración de email no encontrada")

    db.delete(db_email_config)
    db.commit()
    return
