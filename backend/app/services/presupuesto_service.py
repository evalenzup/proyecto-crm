# app/services/presupuesto_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
from datetime import datetime
from app.repository.base import BaseRepository
from app.models.presupuestos import Presupuesto, PresupuestoDetalle, PresupuestoEvento
from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle as FacturaDetalleModel
from app.schemas.presupuestos import PresupuestoCreate, PresupuestoUpdate, PresupuestoDetalleCreate
from app.services.factura_service import siguiente_folio
from decimal import Decimal
from fastapi import HTTPException, UploadFile
import shutil
import os

class PresupuestoRepository(BaseRepository[Presupuesto, PresupuestoCreate, PresupuestoUpdate]):
    
    def _generate_folio(self, db: Session, empresa_id: str) -> str:
        """
        Genera un folio secuencial para un nuevo presupuesto.
        Formato: PRE-YYYY-NNNN
        """
        current_year = extract('year', func.now())
        # Obtener el último folio para la empresa y el año actual
        last_folio = db.query(func.max(Presupuesto.folio)).filter(
            Presupuesto.empresa_id == empresa_id,
            extract('year', Presupuesto.creado_en) == current_year
        ).scalar()

        if last_folio:
            # Extraer el número secuencial y aumentarlo
            last_sequence = int(last_folio.split('-')[-1])
            new_sequence = last_sequence + 1
        else:
            # Empezar desde 1 si no hay folios este año
            new_sequence = 1
            
        year = datetime.utcnow().year
        
        return f"PRE-{year}-{new_sequence:04d}"

    def create(self, db: Session, *, obj_in: PresupuestoCreate) -> Presupuesto:
        """
        Crea un nuevo presupuesto y sus detalles.
        """
        folio_a_usar = obj_in.folio
        if not folio_a_usar:
            folio_a_usar = self._generate_folio(db, obj_in.empresa_id)

        db_obj = Presupuesto(
            **obj_in.model_dump(exclude={"detalles", "folio"}),
            folio=folio_a_usar
        )
        
        # Calcular totales
        subtotal = Decimal(0)
        impuestos_total = Decimal(0)
        for detalle_in in obj_in.detalles:
            importe = detalle_in.cantidad * detalle_in.precio_unitario
            impuesto_estimado = importe * detalle_in.tasa_impuesto
            subtotal += importe
            impuestos_total += impuesto_estimado
            db_detalle = PresupuestoDetalle(
                **detalle_in.model_dump(),
                importe=importe,
                impuesto_estimado=impuesto_estimado
            )
            db_obj.detalles.append(db_detalle)

        db_obj.subtotal = subtotal
        db_obj.impuestos = impuestos_total
        if db_obj.descuento_total is None:
            db_obj.descuento_total = Decimal(0)
        db_obj.total = subtotal + impuestos_total - db_obj.descuento_total

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Presupuesto, obj_in: PresupuestoUpdate) -> Presupuesto:
        """
        Crea una nueva versión de un presupuesto existente en lugar de actualizarlo.
        La versión anterior se marca como 'ARCHIVADO'.
        """
        # 1. Marcar la versión anterior como 'ARCHIVADO'
        db_obj.estado = "ARCHIVADO"
        db.add(db_obj)

        # 2. Crear una nueva instancia de Presupuesto para la nueva versión
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Copiar campos del objeto anterior al nuevo
        new_version_data = {
            "folio": db_obj.folio,
            "empresa_id": db_obj.empresa_id,
            "cliente_id": db_obj.cliente_id,
            "responsable_id": db_obj.responsable_id,
            "fecha_emision": db_obj.fecha_emision,
            "fecha_vencimiento": db_obj.fecha_vencimiento,
            "moneda": db_obj.moneda,
            "tipo_cambio": db_obj.tipo_cambio,
            "condiciones_comerciales": db_obj.condiciones_comerciales,
            "notas_internas": db_obj.notas_internas,
            "descuento_total": db_obj.descuento_total,
        }

        # Sobrescribir con los datos de la actualización
        for field, value in update_data.items():
            if field != "detalles":
                new_version_data[field] = value
        
        # Incrementar la versión
        new_version_data["version"] = db_obj.version + 1
        
        # El estado por defecto será 'BORRADOR' para la nueva versión
        new_version_data["estado"] = "BORRADOR"

        new_presupuesto = Presupuesto(**new_version_data)

        # 3. Manejar los detalles para la nueva versión
        detalles_a_procesar = []
        if "detalles" in update_data and update_data["detalles"] is not None:
            detalles_a_procesar = [PresupuestoDetalleCreate(**d) for d in update_data["detalles"]]
        else:
            # Si no se envían detalles, copiar los de la versión anterior
            detalles_a_procesar = [
                PresupuestoDetalleCreate(
                    producto_servicio_id=d.producto_servicio_id,
                    descripcion=d.descripcion,
                    cantidad=d.cantidad,
                    unidad=d.unidad,
                    precio_unitario=d.precio_unitario,
                    tasa_impuesto=d.tasa_impuesto,
                    costo_estimado=d.costo_estimado,
                ) for d in db_obj.detalles
            ]

        subtotal = Decimal(0)
        impuestos_total = Decimal(0)
        for detalle_in in detalles_a_procesar:
            importe = detalle_in.cantidad * detalle_in.precio_unitario
            impuesto_estimado = importe * detalle_in.tasa_impuesto
            subtotal += importe
            impuestos_total += impuesto_estimado
            db_detalle = PresupuestoDetalle(
                **detalle_in.model_dump(),
                importe=importe,
                impuesto_estimado=impuesto_estimado
            )
            new_presupuesto.detalles.append(db_detalle)

        new_presupuesto.subtotal = subtotal
        new_presupuesto.impuestos = impuestos_total
        new_presupuesto.total = subtotal + impuestos_total - new_presupuesto.descuento_total

        # 4. Crear evento para la nueva versión
        evento = PresupuestoEvento(
            usuario_id=new_presupuesto.responsable_id,
            accion="CREADO",
            comentario=f"Nueva versión {new_presupuesto.version} creada a partir de la v{db_obj.version}",
        )
        new_presupuesto.eventos.append(evento)

        db.add(new_presupuesto)
        db.commit()
        db.refresh(new_presupuesto)
        
        return new_presupuesto

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        empresa_id: str = None,
        cliente_id: str = None,
        estado: str = None,
        fecha_inicio: str = None,
        fecha_fin: str = None,
    ) -> (List[Presupuesto], int):
        # Subquery to find the latest version of each budget
        latest_versions_subquery = db.query(
            self.model.id,
            func.row_number().over(
                partition_by=(self.model.folio, self.model.empresa_id),
                order_by=self.model.version.desc()
            ).label("row_num")
        ).subquery()

        # Main query joins with the subquery to get only the latest versions
        query = db.query(self.model).join(
            latest_versions_subquery, self.model.id == latest_versions_subquery.c.id
        ).filter(latest_versions_subquery.c.row_num == 1)

        # Apply filters to the main query
        if empresa_id:
            query = query.filter(self.model.empresa_id == empresa_id)
        if cliente_id:
            query = query.filter(self.model.cliente_id == cliente_id)
        
        if estado:
            query = query.filter(self.model.estado == estado)
        else:
            # Exclude archived by default if no specific estado is requested
            query = query.filter(self.model.estado != 'ARCHIVADO')

        if fecha_inicio:
            query = query.filter(self.model.fecha_emision >= fecha_inicio)
        if fecha_fin:
            query = query.filter(self.model.fecha_emision <= fecha_fin)

        total = query.count()
        items = query.order_by(self.model.folio.desc()).offset(skip).limit(limit).all()
        
        return items, total

    def update_status(self, db: Session, *, db_obj: Presupuesto, new_status: str, user_id: str = None) -> Presupuesto:
        """
        Actualiza solo el estado de un presupuesto y crea un evento de log.
        No crea una nueva versión.
        """
        db_obj.estado = new_status
        
        evento = PresupuestoEvento(
            presupuesto_id=db_obj.id,
            usuario_id=user_id, # Can be None
            accion=new_status, # Use the status as the action name
            comentario=f"El estado del presupuesto cambió a {new_status}",
        )
        db.add(db_obj)
        db.add(evento)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def add_evidencia(self, db: Session, *, db_obj: Presupuesto, file: UploadFile, user_id: str = None) -> Presupuesto:
        """
        Sube un archivo de evidencia, borra el anterior si existe,
        lo asocia al presupuesto y lo marca como ACEPTADO.
        """
        # 1. Check for and delete the old file
        if db_obj.firma_cliente:
            old_file_path = db_obj.firma_cliente
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except OSError as e:
                    # Log the error, but don't block the upload
                    print(f"Error deleting old evidence file {old_file_path}: {e}")

        # 2. Save the new file
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        unique_filename = f"{db_obj.id}_evidencia.{file_extension}"
        file_path = f"data/presupuestos_evidencia/{unique_filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Update the database object
        db_obj.firma_cliente = file_path # Store the path
        db_obj.estado = "ACEPTADO"
        
        # 4. Create an event
        evento = PresupuestoEvento(
            presupuesto_id=db_obj.id,
            usuario_id=user_id,
            accion="ACEPTADO",
            comentario=f"Se adjuntó/reemplazó evidencia: {file.filename}",
        )
        db.add(db_obj)
        db.add(evento)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_history_by_folio(self, db: Session, *, folio: str, empresa_id: str) -> List[Presupuesto]:
        """
        Obtiene todas las versiones de un presupuesto por su folio y empresa.
        """
        return db.query(self.model).filter(
            self.model.folio == folio,
            self.model.empresa_id == empresa_id
        ).order_by(self.model.version.asc()).all()

    def convertir_a_factura(self, db: Session, *, presupuesto_id: str) -> Factura:
        presupuesto = db.query(Presupuesto).filter(Presupuesto.id == presupuesto_id).first()
        if not presupuesto:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        if presupuesto.estado != "ACEPTADO":
            raise HTTPException(status_code=400, detail="Solo se pueden convertir presupuestos ACEPTADOS")

        # Crear nueva factura
        serie_factura = "A" # O la lógica que se decida
        folio_factura = siguiente_folio(db, presupuesto.empresa_id, serie_factura)

        factura = Factura(
            empresa_id=presupuesto.empresa_id,
            cliente_id=presupuesto.cliente_id,
            serie=serie_factura,
            folio=folio_factura,
            moneda=presupuesto.moneda,
            tipo_cambio=presupuesto.tipo_cambio,
            subtotal=presupuesto.subtotal,
            descuento=presupuesto.descuento_total,
            impuestos_trasladados=presupuesto.impuestos,
            total=presupuesto.total,
            condiciones_pago=presupuesto.condiciones_comerciales,
            estatus="BORRADOR",
            status_pago="NO_PAGADA",
            uso_cfdi="G01", # Adquisición de mercancías por defecto, se puede cambiar en la UI de factura
        )

        for detalle_presupuesto in presupuesto.detalles:
            factura_detalle = FacturaDetalleModel(
                factura_id=factura.id,
                producto_servicio_id=detalle_presupuesto.producto_servicio_id,
                descripcion=detalle_presupuesto.descripcion,
                cantidad=detalle_presupuesto.cantidad,
                valor_unitario=detalle_presupuesto.precio_unitario,
                importe=detalle_presupuesto.importe,
                # TODO: Mapear claves SAT y tasas de impuestos si existen en el presupuesto
                clave_producto="01010101", # Sin clasificación
                clave_unidad="H87", # Pieza
            )
            factura.conceptos.append(factura_detalle)
        
        presupuesto.estado = "FACTURADO"
        evento = PresupuestoEvento(
            presupuesto_id=presupuesto.id,
            usuario_id=presupuesto.responsable_id, # Placeholder
            accion="FACTURADO",
            comentario=f"Convertido a factura con folio {serie_factura}-{folio_factura}",
        )
        db.add(factura)
        db.add(evento)
        db.commit()
        db.refresh(factura)
        return factura

presupuesto_repo = PresupuestoRepository(Presupuesto)
