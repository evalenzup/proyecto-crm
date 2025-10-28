# app/services/empresa_service.py
import os
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import date, datetime

from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate
from app.repository.base import BaseRepository
from app.catalogos_sat import validar_regimen_fiscal
from app.catalogos_sat.codigos_postales import validar_codigo_postal
from app.services.certificado import CertificadoService
from app.validators.rfc import validar_rfc_por_regimen
from app.validators.email import validar_email
from app.validators.telefono import validar_telefono
from app.config import settings
from app.core.logger import logger


class EmpresaRepository(BaseRepository[Empresa, EmpresaCreate, EmpresaUpdate]):
    def _validar_datos(
        self,
        db: Session,
        email: Optional[str] = None,
        regimen_fiscal: Optional[str] = None,
        codigo_postal: Optional[str] = None,
        rfc: Optional[str] = None,
        ruc: Optional[str] = None,
        nombre_comercial: Optional[str] = None,
        telefono: Optional[str] = None,
        empresa_existente: Optional[Empresa] = None,
    ):
        """Validaciones de negocio específicas para Empresa."""
        if regimen_fiscal and not validar_regimen_fiscal(regimen_fiscal):
            raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")
        if codigo_postal and not validar_codigo_postal(codigo_postal):
            raise HTTPException(status_code=400, detail="Código postal inválido.")
        if rfc:
            regimen = regimen_fiscal or getattr(
                empresa_existente, "regimen_fiscal", None
            )
            if not validar_rfc_por_regimen(rfc, regimen):
                raise HTTPException(
                    status_code=400, detail="RFC inválido para el régimen fiscal."
                )
        if ruc and (not empresa_existente or ruc != empresa_existente.ruc):
            if db.query(Empresa).filter(Empresa.ruc == ruc).first():
                raise HTTPException(
                    status_code=400, detail="El RUC ya está registrado."
                )
        if nombre_comercial and (
            not empresa_existente
            or nombre_comercial != empresa_existente.nombre_comercial
        ):
            if (
                db.query(Empresa)
                .filter(Empresa.nombre_comercial == nombre_comercial)
                .first()
            ):
                raise HTTPException(
                    status_code=400, detail="El nombre comercial ya está registrado."
                )
        if email and not validar_email(email):
            raise HTTPException(status_code=400, detail="Email no válido.")
        if telefono and not validar_telefono(telefono):
            raise HTTPException(status_code=400, detail="Teléfono no válido.")

    @staticmethod
    def _bytes_from_upload(f: UploadFile) -> bytes:
        f.file.seek(0)
        data = f.file.read()
        f.file.seek(0)
        return data

    def create(
        self,
        db: Session,
        *,
        obj_in: EmpresaCreate,
        archivo_cer: UploadFile,
        archivo_key: UploadFile,
        logo: Optional[UploadFile] = None,
    ) -> Empresa:
        logger.info("➡️ EmpresaRepository.create: iniciando")
        self._validar_datos(
            db=db,
            email=obj_in.email,
            regimen_fiscal=obj_in.regimen_fiscal,
            codigo_postal=obj_in.codigo_postal,
            rfc=obj_in.rfc,
            ruc=obj_in.ruc,
            nombre_comercial=obj_in.nombre_comercial,
            telefono=obj_in.telefono,
        )

        # Validar EN MEMORIA (no tocar disco) con la contraseña en texto plano
        cer_bytes = self._bytes_from_upload(archivo_cer)
        key_bytes = self._bytes_from_upload(archivo_key)
        resultado = CertificadoService.validar_bytes(
            cer_bytes, key_bytes, obj_in.contrasena
        )
        if not resultado["valido"]:
            logger.info(
                "❌ EmpresaRepository.create: validación falló → %s", resultado["error"]
            )
            raise HTTPException(
                status_code=400, detail=resultado["error"] or "Certificado inválido"
            )
        if (
            resultado.get("valido_hasta")
            and datetime.fromisoformat(resultado["valido_hasta"]).date() < date.today()
        ):
            raise HTTPException(status_code=400, detail="El certificado está vencido.")

        # Crear la empresa en la base de datos
        nueva_empresa = super().create(db, obj_in=obj_in)

        # Guardar a disco
        filename_cer = f"{nueva_empresa.id}.cer"
        filename_key = f"{nueva_empresa.id}.key"
        CertificadoService.guardar(archivo_cer, filename_cer)
        CertificadoService.guardar(archivo_key, filename_key)
        nueva_empresa.archivo_cer = filename_cer
        nueva_empresa.archivo_key = filename_key

        # Logo opcional
        if logo:
            logos_dir = os.path.join(settings.DATA_DIR, "logos")
            os.makedirs(logos_dir, exist_ok=True)
            logo_filename = f"{nueva_empresa.id}.png"
            with open(os.path.join(logos_dir, logo_filename), "wb") as buf:
                buf.write(logo.file.read())
            nueva_empresa.logo = os.path.join("logos", logo_filename)

        try:
            db.commit()
            db.refresh(nueva_empresa)
            logger.info("✅ EmpresaRepository.create: OK")
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400, detail="RUC duplicado o error de integridad."
            )
        return nueva_empresa

    def update(
        self,
        db: Session,
        *,
        db_obj: Empresa,
        obj_in: EmpresaUpdate,
        archivo_cer: Optional[UploadFile] = None,
        archivo_key: Optional[UploadFile] = None,
        logo: Optional[UploadFile] = None,
    ) -> Optional[Empresa]:
        logger.info("➡️ EmpresaRepository.update: iniciando update %s", db_obj.id)
        from os.path import join, basename, exists

        update_data = obj_in.model_dump(exclude_unset=True)
        self._validar_datos(
            db=db,
            email=update_data.get("email"),
            regimen_fiscal=update_data.get("regimen_fiscal"),
            codigo_postal=update_data.get("codigo_postal"),
            rfc=update_data.get("rfc"),
            ruc=update_data.get("ruc"),
            nombre_comercial=update_data.get("nombre_comercial"),
            telefono=update_data.get("telefono"),
            empresa_existente=db_obj,
        )

        # Detectar archivos realmente subidos
        cer_new = bool(archivo_cer and getattr(archivo_cer, "filename", ""))
        key_new = bool(archivo_key and getattr(archivo_key, "filename", ""))

        if cer_new ^ key_new:
            raise HTTPException(
                status_code=400,
                detail="Si actualizas certificados, debes subir ambos archivos: CER y KEY.",
            )

        cer_abs = (
            join(settings.CERT_DIR, basename(db_obj.archivo_cer))
            if db_obj.archivo_cer
            else None
        )
        key_abs = (
            join(settings.CERT_DIR, basename(db_obj.archivo_key))
            if db_obj.archivo_key
            else None
        )
        missing_files = (not cer_abs or not exists(cer_abs)) or (
            not key_abs or not exists(key_abs)
        )

        if missing_files and not (cer_new and key_new):
            raise HTTPException(
                status_code=400,
                detail="No se encontraron ambos archivos en el servidor. Sube CER y KEY para continuar.",
            )

        if cer_new and key_new:
            if not obj_in.contrasena:
                raise HTTPException(
                    status_code=400,
                    detail="Debes proporcionar la contraseña para validar los certificados.",
                )

            # Validación EN MEMORIA con la nueva contraseña
            cer_bytes = self._bytes_from_upload(archivo_cer)
            key_bytes = self._bytes_from_upload(archivo_key)
            resultado = CertificadoService.validar_bytes(
                cer_bytes, key_bytes, obj_in.contrasena
            )
            if not resultado["valido"]:
                logger.info(
                    "❌ EmpresaRepository.update: validación falló → %s",
                    resultado["error"],
                )
                raise HTTPException(
                    status_code=400, detail=resultado["error"] or "Certificado inválido"
                )
            if (
                resultado.get("valido_hasta")
                and datetime.fromisoformat(resultado["valido_hasta"]).date()
                < date.today()
            ):
                raise HTTPException(
                    status_code=400, detail="El certificado está vencido."
                )

            # Reemplazar en disco
            try:
                if cer_abs and os.path.exists(cer_abs):
                    os.remove(cer_abs)
            except Exception:
                pass
            try:
                if key_abs and os.path.exists(key_abs):
                    os.remove(key_abs)
            except Exception:
                pass

            filename_cer = f"{db_obj.id}.cer"
            filename_key = f"{db_obj.id}.key"
            CertificadoService.guardar(archivo_cer, filename_cer)
            CertificadoService.guardar(archivo_key, filename_key)
            db_obj.archivo_cer = filename_cer
            db_obj.archivo_key = filename_key

            # Actualizar contraseña (texto plano)
            db_obj.contrasena = obj_in.contrasena
            logger.info(
                "✅ EmpresaRepository.update: certificados reemplazados y contraseña actualizada"
            )
        else:
            # No cambiaron certificados; si mandan solo la contraseña, se actualiza en claro
            if "contrasena" in update_data and update_data["contrasena"]:
                db_obj.contrasena = update_data["contrasena"]
                logger.info(
                    "ℹ️ EmpresaRepository.update: contraseña actualizada (sin cambiar certificados)"
                )

        # Logo
        if logo:
            try:
                if db_obj.logo and os.path.exists(
                    os.path.join(settings.DATA_DIR, db_obj.logo)
                ):
                    os.remove(os.path.join(settings.DATA_DIR, db_obj.logo))
            except Exception:
                pass
            logos_dir = os.path.join(settings.DATA_DIR, "logos")
            os.makedirs(logos_dir, exist_ok=True)
            logo_filename = f"{db_obj.id}.png"
            with open(os.path.join(logos_dir, logo_filename), "wb") as buf:
                buf.write(logo.file.read())
            db_obj.logo = os.path.join("logos", logo_filename)

        # Llama al método `update` de la clase base para los campos simples
        return super().update(db, db_obj=db_obj, obj_in=obj_in)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        rfc: Optional[str] = None,
        nombre_comercial: Optional[str] = None,
    ) -> Tuple[List[Empresa], int]:
        query = db.query(self.model)

        if rfc:
            query = query.filter(self.model.rfc.ilike(f"%{rfc}%"))

        if nombre_comercial:
            query = query.filter(self.model.nombre_comercial.ilike(f"%{nombre_comercial}%"))

        total = query.count()
        items = (
            query.order_by(self.model.nombre_comercial.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return items, total

    def remove(self, db: Session, *, id: UUID) -> Optional[Empresa]:
        """
        Elimina una empresa y sus archivos asociados (certificados y logo).
        """
        empresa = self.get(db, id)
        if not empresa:
            return None

        # Eliminar archivos asociados
        for fname in (empresa.archivo_cer, empresa.archivo_key):
            if fname:
                path = os.path.join(settings.CERT_DIR, fname)
                try:
                    if os.path.exists(path):
                        os.remove(path)  # type: ignore
                except Exception as e:
                    logger.error(
                        f"Error al eliminar archivo de certificado {path}: {e}"
                    )

        if empresa.logo:
            logo_path = os.path.join(settings.DATA_DIR, empresa.logo)  # type: ignore
            try:
                if os.path.exists(logo_path):
                    os.remove(logo_path)  # type: ignore
            except Exception as e:
                logger.error(f"Error al eliminar archivo de logo {logo_path}: {e}")

        return super().remove(db, id=id)


# Se instancia el repositorio con el modelo SQLAlchemy correspondiente
empresa_repo = EmpresaRepository(Empresa)
