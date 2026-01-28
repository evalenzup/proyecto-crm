from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from datetime import datetime, date
from uuid import UUID
from typing import List, Optional

from app.models.factura import Factura
from app.models.cobranza import CobranzaNota
from app.models.cliente import Cliente
from app.schemas.cobranza import CobranzaNotaCreate, AgingReportResponse, ClienteAging, AgingBucket
from app.models.usuario import Usuario

class CobranzaService:
    @staticmethod
    def get_aging_report(db: Session, empresa_id: UUID) -> AgingReportResponse:
        today = date.today()
        
        # 1. Obtener todas las facturas NO PAGADAS y TIMBRADAS
        facturas = (
            db.query(Factura)
            .filter(
                Factura.empresa_id == empresa_id,
                Factura.estatus == "TIMBRADA",
                Factura.status_pago == "NO_PAGADA"
            )
            .all()
        )
        
        # Estructura para agrupar por RFC (o por ID si no tiene RFC valido)
        # { key: { "ids": {cid1, cid2}, "nombre": Str, "rfc": Str, "buckets": {...} } }
        grouped_map = {}
        
        # RFCs genéricos que no debemos agrupar
        # XAXX010101000, XEXX010101000
        GENERIC_RFCS = ["XAXX010101000", "XEXX010101000", ""]

        for f in facturas:
            if not f.cliente_id:
                continue
                
            # Determinar llave de agrupamiento
            key = str(f.cliente_id) # Default: ID único
            rfc = None
            nombre_fiscal = "Sin Nombre"
            
            if f.cliente:
                rfc = f.cliente.rfc or ""
                nombre_fiscal = f.cliente.nombre_razon_social or f.cliente.nombre_comercial or "Sin Nombre"
                
                # Si tiene RFC valido y no es genérico, agrupar por RFC
                if rfc and rfc.upper() not in GENERIC_RFCS:
                    key = rfc.upper()
            
            if key not in grouped_map:
                grouped_map[key] = {
                    "ids": set(), # Set of client IDs in this group
                    "nombre": nombre_fiscal,
                    "rfc": rfc,
                    "email": None, # Will populate
                    "total": 0.0,
                    "por_vencer": 0.0,
                    "0_30": 0.0,
                    "31_60": 0.0,
                    "61_90": 0.0,
                    "90+": 0.0
                }
            
            # Keep first valid email found
            if not grouped_map[key]["email"] and f.cliente and f.cliente.email:
                grouped_map[key]["email"] = f.cliente.email
                
            grouped_map[key]["ids"].add(f.cliente_id)
            
            # Calcular días vencidos
            fecha_base = f.fecha_pago if f.fecha_pago else f.fecha_emision
            if isinstance(fecha_base, datetime):
                fecha_base = fecha_base.date()
                
            days_overdue = (today - fecha_base).days
            monto = float(f.total or 0.0)
            
            data = grouped_map[key]
            data["total"] += monto
            
            if days_overdue < 0:
                data["por_vencer"] += monto
            elif days_overdue <= 30:
                data["0_30"] += monto
            elif days_overdue <= 60:
                data["31_60"] += monto
            elif days_overdue <= 90:
                data["61_90"] += monto
            else:
                data["90+"] += monto

        # Convertir a lista de respuesta
        items = []
        total_general = 0.0
        
        for key, info in grouped_map.items():
            # Buscar nota más reciente de CUALQUIERA de los clientes del grupo
            # Convertimos el set de IDs a lista
            client_ids = list(info["ids"])
            
            last_note = (
                db.query(CobranzaNota)
                .filter(
                    CobranzaNota.cliente_id.in_(client_ids),
                    CobranzaNota.empresa_id == empresa_id
                )
                .order_by(CobranzaNota.creado_en.desc())
                .first()
            )
            
            nota_txt = last_note.nota if last_note else None
            promesa = last_note.fecha_promesa_pago if last_note else None
            
            # Usamos el primer ID como identificador principal para el frontend
            representative_id = client_ids[0] if client_ids else None
            
            if representative_id:
                items.append(ClienteAging(
                    cliente_id=representative_id,
                    nombre_cliente=info["nombre"],
                    rfc=info["rfc"],
                    total_deuda=info["total"],
                    por_vencer=info["por_vencer"],
                    vencido_0_30=info["0_30"],
                    vencido_31_60=info["31_60"],
                    vencido_61_90=info["61_90"],
                    vencido_mas_90=info["90+"],
                    nota_mas_reciente=nota_txt,
                    fecha_promesa=promesa,
                    email=info.get("email")
                ))
                total_general += info["total"]
            
        # Ordenar por deuda descendente
        items.sort(key=lambda x: x.total_deuda, reverse=True)
        
        return AgingReportResponse(
            total_general_vencido=total_general,
            items=items
        )

    @staticmethod
    def create_nota(db: Session, obj_in: CobranzaNotaCreate, user_id: UUID, empresa_id: UUID) -> CobranzaNota:
        nota = CobranzaNota(
            empresa_id=empresa_id,
            cliente_id=obj_in.cliente_id,
            factura_id=obj_in.factura_id,
            nota=obj_in.nota,
            fecha_promesa_pago=obj_in.fecha_promesa_pago,
            creado_po=user_id
        )
        db.add(nota)
        db.commit()
        db.refresh(nota)
        
        # Populate creator name for response
        if nota.usuario_creador:
            nota.nombre_creador = nota.usuario_creador.nombre_completo or "Usuario"
        
        return nota

    @staticmethod
    def get_notas_by_cliente(db: Session, cliente_id: UUID, empresa_id: UUID) -> List[CobranzaNota]:
        # 1. Obtener cliente para ver si tiene RFC agrupable
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        target_ids = [cliente_id]
        
        GENERIC_RFCS = ["XAXX010101000", "XEXX010101000", ""]

        if cliente and cliente.rfc and cliente.rfc.upper() not in GENERIC_RFCS:
            # Buscar otros clientes de esta empresa con el mismo RFC
            # Nota: La relación Cliente-Empresa es many-to-many.
            # Buscamos clientes que tengan relación con esta empresa Y el mismo RFC
            from app.models.empresa import Empresa
            
            same_rfc_clients = (
                db.query(Cliente.id)
                .join(Cliente.empresas)
                .filter(
                    Cliente.rfc == cliente.rfc,
                    Empresa.id == empresa_id
                )
                .all()
            )
            # same_rfc_clients es lista de tuplas [(uuid,), (uuid,)]
            target_ids = [c[0] for c in same_rfc_clients]

        notas = (
            db.query(CobranzaNota)
            .options(selectinload(CobranzaNota.usuario_creador))
            .filter(CobranzaNota.cliente_id.in_(target_ids), CobranzaNota.empresa_id == empresa_id)
            .order_by(CobranzaNota.creado_en.desc())
            .all()
        )
        # Populate creator name for schema
        for n in notas:
            if n.usuario_creador:
                n.nombre_creador = n.usuario_creador.nombre_completo
            else:
                n.nombre_creador = "Usuario"
        return notas

    @staticmethod
    def process_email_estado_cuenta(
        db: Session, 
        empresa_id: UUID, 
        cliente_id: UUID, 
        recipients: List[str], 
        user_id: UUID
    ):
        from app.services.email_sender import send_estado_cuenta_email
        
        # 1. Enviar correo
        send_estado_cuenta_email(db, empresa_id, cliente_id, recipients)
        
        # 2. Registrar en bitácora
        emails_str = ", ".join(recipients)
        nota = CobranzaNota(
            empresa_id=empresa_id,
            cliente_id=cliente_id,
            nota=f"Enviado Estado de Cuenta a: {emails_str}",
            creado_po=user_id
        )
        db.add(nota)
        db.commit()

    @staticmethod
    def delete_nota(db: Session, nota_id: UUID, user_id: UUID, is_admin: bool) -> bool:
        nota = db.query(CobranzaNota).filter(CobranzaNota.id == nota_id).first()
        if not nota:
            return False
            
        # Check permissions: Creator or Admin
        if not is_admin and nota.creado_po != user_id:
            raise PermissionError("No tienes permiso para eliminar esta nota.")
            
        db.delete(nota)
        db.commit()
        return True

cobranza_service = CobranzaService()
