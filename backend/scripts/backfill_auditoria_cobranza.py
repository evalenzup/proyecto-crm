"""
Backfill de auditoría para el módulo de cobranza.

Reconstruye en `auditoria_log` la acción CREAR_NOTA_COBRANZA a partir de las
notas existentes en `cobranza_notas` (que conservan autor y fecha originales).

Sólo esta acción es reconstruible:
  - Notas de cobranza  -> SÍ (viven en cobranza_notas con creado_po + creado_en)
  - Notas eliminadas   -> NO (no queda rastro)
  - Estados de cuenta  -> NO (el envío no se persiste)

Características:
  - Fecha histórica: cada registro usa creado_en = nota.creado_en, de modo que
    el reporte de actividad lo ubica en el día/semana correcto.
  - Marca de origen: detalle = {"origen": "backfill", "nota_id": <id>}.
  - Idempotente: omite notas que ya tengan su registro de backfill (por nota_id).

Uso (dentro del contenedor):
  docker exec crm_prod-backend-1 python scripts/backfill_auditoria_cobranza.py [--dry-run]
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.auditoria import AuditoriaLog
from app.models.cobranza import CobranzaNota
from app.models.usuario import Usuario
from app.services import auditoria_service as audit_svc


def run(dry_run: bool = False) -> None:
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Notas ya respaldadas (para idempotencia). Buscamos por marca de origen.
        ya = (
            db.query(AuditoriaLog.detalle)
            .filter(
                AuditoriaLog.accion == audit_svc.CREAR_NOTA_COBRANZA,
                AuditoriaLog.detalle.like('%"origen": "backfill"%'),
            )
            .all()
        )
        respaldadas = set()
        for (det,) in ya:
            try:
                nid = json.loads(det or "{}").get("nota_id")
                if nid:
                    respaldadas.add(str(nid))
            except Exception:
                pass

        emails = {str(u.id): u.email for u in db.query(Usuario.id, Usuario.email).all()}

        notas = db.query(CobranzaNota).order_by(CobranzaNota.creado_en).all()
        print(f"Notas de cobranza encontradas: {len(notas)}")
        print(f"Ya respaldadas previamente:     {len(respaldadas)}")

        creados = 0
        sin_autor = 0
        for n in notas:
            if str(n.id) in respaldadas:
                continue
            autor_id = str(n.creado_po) if n.creado_po else None
            if autor_id is None:
                sin_autor += 1
            log = AuditoriaLog(
                accion=audit_svc.CREAR_NOTA_COBRANZA,
                entidad="cobranza",
                usuario_id=n.creado_po,
                usuario_email=emails.get(autor_id) if autor_id else None,
                empresa_id=n.empresa_id,
                entidad_id=str(n.cliente_id) if n.cliente_id else None,
                detalle=json.dumps({"origen": "backfill", "nota_id": str(n.id)}),
                ip=None,
                creado_en=n.creado_en,  # conserva la fecha histórica real
            )
            db.add(log)
            creados += 1

        if dry_run:
            db.rollback()
            print(f"[DRY-RUN] Se insertarían {creados} registros "
                  f"({sin_autor} sin autor). No se guardó nada.")
        else:
            db.commit()
            print(f"OK: {creados} registros insertados en auditoria_log "
                  f"({sin_autor} sin autor).")
    finally:
        db.close()


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
