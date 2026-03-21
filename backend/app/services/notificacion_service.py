import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.notificacion import Notificacion

logger = logging.getLogger("app")

# Tipos válidos — usados como constantes para evitar strings sueltos en el código
EXITO = "EXITO"
INFO = "INFO"
ADVERTENCIA = "ADVERTENCIA"
ERROR = "ERROR"


def crear_notificacion(
    db: Session,
    empresa_id: uuid.UUID,
    tipo: str,
    titulo: str,
    mensaje: str,
    usuario_id: Optional[uuid.UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Notificacion:
    """Crea y persiste una notificación. Nunca lanza excepciones para no interrumpir flujos principales."""
    try:
        notif = Notificacion(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            metadata_=metadata,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif
    except Exception as e:
        db.rollback()
        logger.error("Error al crear notificación: %s", e)
        raise


def listar_notificaciones(
    db: Session,
    empresa_id: uuid.UUID,
    usuario_id: Optional[uuid.UUID] = None,
    solo_no_leidas: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """Devuelve notificaciones de la empresa. Si usuario_id está presente,
    incluye las globales de empresa y las específicas de ese usuario."""
    query = db.query(Notificacion).filter(Notificacion.empresa_id == empresa_id)

    if usuario_id:
        query = query.filter(
            (Notificacion.usuario_id == None) | (Notificacion.usuario_id == usuario_id)
        )

    if solo_no_leidas:
        query = query.filter(Notificacion.leida == False)

    total = query.count()
    no_leidas = query.filter(Notificacion.leida == False).count() if not solo_no_leidas else total
    items = (
        query.order_by(Notificacion.creada_en.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total, no_leidas


def marcar_leida(db: Session, notificacion_id: uuid.UUID, empresa_id: uuid.UUID) -> Optional[Notificacion]:
    notif = (
        db.query(Notificacion)
        .filter(Notificacion.id == notificacion_id, Notificacion.empresa_id == empresa_id)
        .first()
    )
    if not notif:
        return None
    notif.leida = True
    db.commit()
    db.refresh(notif)
    return notif


def marcar_todas_leidas(
    db: Session,
    empresa_id: uuid.UUID,
    usuario_id: Optional[uuid.UUID] = None,
) -> int:
    """Marca como leídas las notificaciones del usuario (y las globales de la empresa).
    Devuelve el número de registros actualizados."""
    query = db.query(Notificacion).filter(
        Notificacion.empresa_id == empresa_id,
        Notificacion.leida == False,
    )
    if usuario_id:
        query = query.filter(
            (Notificacion.usuario_id == None) | (Notificacion.usuario_id == usuario_id)
        )
    count = query.update({"leida": True}, synchronize_session=False)
    db.commit()
    return count
