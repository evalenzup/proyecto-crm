# app/services/cliente_service.py
from __future__ import annotations
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from uuid import UUID

from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.repository.base import BaseRepository
from app.catalogos_sat.regimenes_fiscales import obtener_clave_regimen_por_descripcion
from app.catalogos_sat.codigos_postales import validar_codigo_postal
from app.validators.rfc import validar_rfc_por_regimen


class ClienteRepository(BaseRepository[Cliente, ClienteCreate, ClienteUpdate]):
    def _validar_datos(
        self,
        db: Session,
        rfc: Optional[str] = None,
        regimen_fiscal: Optional[str] = None,
        codigo_postal: Optional[str] = None,
        cliente_existente: Optional[Cliente] = None,
    ):
        """Validaciones de negocio específicas para Cliente."""
        regimen_fiscal_clave = None
        if regimen_fiscal:
            regimen_fiscal_clave = obtener_clave_regimen_por_descripcion(regimen_fiscal)
            if not regimen_fiscal_clave:
                raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")

        if codigo_postal and not validar_codigo_postal(codigo_postal):
            raise HTTPException(status_code=400, detail="Código postal inválido.")
        
        if rfc:
            regimen_clave_a_usar = regimen_fiscal_clave
            if not regimen_clave_a_usar and cliente_existente:
                regimen_clave_a_usar = obtener_clave_regimen_por_descripcion(cliente_existente.regimen_fiscal)

            if regimen_clave_a_usar and not validar_rfc_por_regimen(rfc, regimen_clave_a_usar):
                raise HTTPException(
                    status_code=400, detail="RFC inválido para el régimen fiscal."
                )

    def create(self, db: Session, *, obj_in: ClienteCreate) -> Cliente:
        """
        Crea un nuevo cliente o asocia empresas a uno existente.
        - Valida los datos fiscales.
        - Si un cliente con el mismo nombre comercial ya existe, solo le asocia las nuevas empresas.
        - Convierte listas de email/teléfono a texto.
        """
        self._validar_datos(
            db=db,
            rfc=obj_in.rfc,
            regimen_fiscal=obj_in.regimen_fiscal,
            codigo_postal=obj_in.codigo_postal,
        )

        empresas_a_asociar = (
            db.query(Empresa).filter(Empresa.id.in_(obj_in.empresa_id)).all()
        )
        if len(empresas_a_asociar) != len(obj_in.empresa_id):
            raise HTTPException(status_code=404, detail="Una o más empresas no existen")

        cliente_existente = (
            db.query(Cliente)
            .filter(Cliente.nombre_comercial == obj_in.nombre_comercial)
            .first()
        )

        if cliente_existente:
            ids_empresas_actuales = {
                empresa.id for empresa in cliente_existente.empresas
            }
            for empresa in empresas_a_asociar:
                if empresa.id not in ids_empresas_actuales:
                    cliente_existente.empresas.append(empresa)
            db.commit()
            db.refresh(cliente_existente)
            return cliente_existente

        # Llama al método `create` de la clase base, pero con los datos procesados
        datos_cliente = obj_in.model_dump(exclude={"empresa_id"})
        if isinstance(datos_cliente.get("email"), list):
            datos_cliente["email"] = ",".join(datos_cliente["email"])
        if isinstance(datos_cliente.get("telefono"), list):
            datos_cliente["telefono"] = ",".join(datos_cliente["telefono"])

        

        # Aquí usamos el método `create` del padre, pero necesitamos pasarle un obj_in sin el campo `empresas`
        # para que el modelo SQLAlchemy lo acepte.
        db_obj = self.model(**datos_cliente)
        db_obj.empresas = empresas_a_asociar

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj, obj_in: ClienteUpdate):
        """
        Actualiza un cliente.
        - Valida los datos fiscales.
        - Maneja la actualización de la relación con empresas.
        - Convierte listas de email/teléfono a texto.
        """
        update_data = obj_in.model_dump(exclude_unset=True)

        self._validar_datos(
            db=db,
            rfc=update_data.get("rfc"),
            regimen_fiscal=update_data.get("regimen_fiscal"),
            codigo_postal=update_data.get("codigo_postal"),
            cliente_existente=db_obj,
        )

        # Si se provee `empresa_id`, se actualiza la relación
        if "empresa_id" in update_data and update_data["empresa_id"] is not None:
            empresas = (
                db.query(Empresa)
                .filter(Empresa.id.in_(update_data["empresa_id"]))
                .all()
            )
            if len(empresas) != len(update_data["empresa_id"]):
                raise HTTPException(404, "Alguna empresa no existe")
            db_obj.empresas = empresas
            del update_data["empresa_id"]  # No es un campo directo del modelo

        # Convertir listas a strings
        if "email" in update_data and isinstance(update_data["email"], list):
            update_data["email"] = ",".join(update_data["email"])
        if "telefono" in update_data and isinstance(update_data["telefono"], list):
            update_data["telefono"] = ",".join(update_data["telefono"])

        # Llama al método `update` de la clase base para los campos simples
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        empresa_id: Optional[UUID] = None,
        rfc: Optional[str] = None,
        nombre_comercial: Optional[str] = None,
    ) -> Tuple[List[Cliente], int]:
        query = db.query(self.model)

        if empresa_id:
            query = query.join(self.model.empresas).filter(Empresa.id == empresa_id)

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

    def search_by_name(
        self, db: Session, *, name_query: str, limit: int = 10, empresa_id: Optional[UUID] = None
    ) -> List[Cliente]:
        """Busca clientes por nombre comercial, opcionalmente filtrando por empresa."""
        if not name_query or len(name_query.strip()) < 3:
            return []
        texto = f"%{name_query.strip()}%"
        query = db.query(self.model)
        if empresa_id:
            from app.models.empresa import Empresa
            query = query.join(self.model.empresas).filter(Empresa.id == empresa_id)
        return (
            query.filter(self.model.nombre_comercial.ilike(texto))
            .order_by(self.model.nombre_comercial.asc())
            .limit(limit)
            .all()
        )

    def validar_rfc_global(self, db: Session, rfc: str, exclude_cliente_id: Optional[UUID] = None) -> List[str]:
        """
        Retorna una lista de nombres de empresas donde este RFC ya está registrado.
        Excluye al propio cliente editado si se provee exclude_cliente_id.
        """
        query = db.query(self.model).filter(self.model.rfc == rfc)
        
        if exclude_cliente_id:
            query = query.filter(self.model.id != exclude_cliente_id)
            
        clientes_con_mismo_rfc = query.all()
        
        empresas_nombres = set()
        for c in clientes_con_mismo_rfc:
            for empresa in c.empresas:
                empresas_nombres.add(empresa.nombre_comercial)
                
        return list(empresas_nombres)

    def get_by_rfc_and_name(self, db: Session, rfc: str, nombre_comercial: str) -> Optional[Cliente]:
        """Busca un cliente que coincida exactamente en RFC y Nombre Comercial (case insensitive)."""
        return (
            db.query(self.model)
            .filter(self.model.rfc == rfc)
            .filter(self.model.nombre_comercial.ilike(nombre_comercial))
            .first()
        )



# Se instancia el repositorio con el modelo SQLAlchemy correspondiente
cliente_repo = ClienteRepository(Cliente)
