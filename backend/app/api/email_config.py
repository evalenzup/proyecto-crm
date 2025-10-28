from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.schemas import email_config
from app.services.email_config_service import email_config_repo

router = APIRouter()

# Endpoints for /email-config/ (should ideally be nested under /empresas/{empresa_id}/email-config)

@router.post("/test-connection", status_code=status.HTTP_200_OK, summary="Probar conexión SMTP")
def test_email_config_connection(
    empresa_id: uuid.UUID,
    email_config_test: email_config.EmailConfigTest,
    db: Session = Depends(get_db),
):
    """Prueba la conexión a un servidor SMTP. Si no se envía `smtp_password`, usa la contraseña guardada en la empresa."""
    email_config_repo.test_connection(db, empresa_id=empresa_id, email_config_test=email_config_test)
    return {"message": "Conexión SMTP exitosa."}


@router.post(
    "/", response_model=email_config.EmailConfig, status_code=status.HTTP_201_CREATED, summary="Crear configuración de email"
)
def create_email_config(
    empresa_id: uuid.UUID,
    email_config_in: email_config.EmailConfigCreate,
    db: Session = Depends(get_db),
):
    """Crea una nueva configuración de email para una empresa."""
    return email_config_repo.create_for_empresa(db, empresa_id=empresa_id, obj_in=email_config_in)


@router.get("/", response_model=email_config.EmailConfig, summary="Obtener configuración de email")
def read_email_config(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtiene la configuración de email de una empresa."""
    db_email_config = email_config_repo.get_by_empresa(db, empresa_id=empresa_id)
    if not db_email_config:
        raise HTTPException(
            status_code=404, detail="Configuración de email no encontrada"
        )
    return db_email_config


@router.put("/", response_model=email_config.EmailConfig, summary="Actualizar configuración de email")
def update_email_config(
    empresa_id: uuid.UUID,
    email_config_in: email_config.EmailConfigUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza la configuración de email de una empresa."""
    return email_config_repo.update_for_empresa(db, empresa_id=empresa_id, obj_in=email_config_in)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar configuración de email")
def delete_email_config(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    """Elimina la configuración de email de una empresa."""
    db_email_config = email_config_repo.remove_for_empresa(db, empresa_id=empresa_id)
    if not db_email_config:
        raise HTTPException(
            status_code=404, detail="Configuración de email no encontrada"
        )
    return