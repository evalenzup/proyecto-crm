# app/api/health.py
"""Health check endpoints para liveness y readiness probes."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.config import settings

router = APIRouter()


@router.get("/live", summary="Liveness probe", tags=["health"])
def liveness():
    """Confirma que el proceso está corriendo. No requiere BD."""
    return {"status": "ok", "version": settings.VERSION if hasattr(settings, "VERSION") else "1.0.0"}


@router.get("/ready", summary="Readiness probe", tags=["health"])
def readiness(db: Session = Depends(get_db)):
    """
    Confirma que la aplicación está lista para recibir tráfico.
    Verifica que la base de datos sea alcanzable.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "db": "unreachable",
                "detail": str(exc),
            },
        )

    return {"status": "ok", "db": db_status}
