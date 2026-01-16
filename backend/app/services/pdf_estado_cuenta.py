from __future__ import annotations

import os
from io import BytesIO
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from collections import defaultdict

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.factura import Factura
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.config import settings
from app.services.pdf_factura import _money, _draw_label_wrap, _wrap_lines

# Layout constants
PAGE_W, PAGE_H = letter
MARGIN = 0.5 * inch
LOGO_W = 2.0 * inch
LOGO_H = 1.0 * inch
FONT = "Helvetica"
FONT_B = "Helvetica-Bold"

def generate_account_statement_pdf(db: Session, empresa_id: UUID, cliente_id: UUID) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle("Estado de Cuenta")

    # 1. Fetch Requesting Client and Company
    cliente_req = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    
    if not cliente_req or not empresa:
        return buffer

    # 2. Determine Scope (RFC Group or Single Client)
    rfc = cliente_req.rfc
    GENERIC_RFCS = ["XAXX010101000", "XEXX010101000", ""]
    
    target_clients = [cliente_req]
    is_group = False
    
    if rfc and rfc.upper() not in GENERIC_RFCS:
        # Find all clients with same RFC in this company
        # Cliente has M2M with Empresa, so we join
        siblings = (
            db.query(Cliente)
            .join(Cliente.empresas)
            .filter(
                Empresa.id == empresa_id,
                Cliente.rfc == rfc,
                # Cliente.id != cliente_id # Include the requested one too
            )
            .all()
        )
        if len(siblings) > 1:
            target_clients = siblings
            is_group = True

    # 3. Fetch Invoices for all target clients
    client_ids = [c.id for c in target_clients]
    
    facturas = (
        db.query(Factura)
        .filter(
            Factura.empresa_id == empresa_id,
            Factura.cliente_id.in_(client_ids),
            Factura.estatus == "TIMBRADA",
            Factura.status_pago == "NO_PAGADA"
        )
        .order_by(Factura.cliente_id, Factura.fecha_emision)
        .all()
    )
    
    # 4. Group by Client (Sucursal)
    # Map client_id -> list[Factura]
    invoices_by_client = defaultdict(list)
    for f in facturas:
        invoices_by_client[f.cliente_id].append(f)

    # 5. Draw PDF
    y = PAGE_H - MARGIN
    
    # --- Header (Logo & Company Info) ---
    logo_path = None
    if empresa.logo:
        p = empresa.logo
        if not os.path.isabs(p):
            p = os.path.join(settings.DATA_DIR, p)
        if os.path.exists(p):
            logo_path = p
    elif empresa.id:
         # Try default path
        p1 = os.path.join(settings.DATA_DIR, "logos", "empresas", f"{empresa.id}.png")
        p2 = os.path.join(settings.DATA_DIR, "logos", f"{empresa.id}.png")
        if os.path.exists(p1): logo_path = p1
        elif os.path.exists(p2): logo_path = p2

    if logo_path:
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            scale = min(LOGO_W / iw, LOGO_H / ih)
            dw, dh = iw * scale, ih * scale
            c.drawImage(img, MARGIN, y - dh, width=dw, height=dh, mask="auto")
        except:
            pass
            
    # Company Name Right Aligned
    c.setFont(FONT_B, 14)
    c.drawRightString(PAGE_W - MARGIN, y - 15, empresa.nombre_comercial or "Empresa")
    c.setFont(FONT, 10)
    c.drawRightString(PAGE_W - MARGIN, y - 30, "ESTADO DE CUENTA")
    c.setFont(FONT, 9)
    c.drawRightString(PAGE_W - MARGIN, y - 42, f"Fecha de corte: {datetime.now().strftime('%d/%m/%Y')}")

    y -= (LOGO_H + 20)

    # --- Client Fiscal Header ---
    c.setFont(FONT_B, 11)
    # If group, show common fiscal data. If single, show that client's data.
    nombre_fiscal = cliente_req.nombre_razon_social or cliente_req.nombre_comercial
    rfc_display = cliente_req.rfc or "Sin RFC"
    
    c.drawString(MARGIN, y, f"Cliente: {nombre_fiscal}")
    y -= 14
    c.setFont(FONT, 10)
    c.drawString(MARGIN, y, f"RFC: {rfc_display}")
    y -= 25

    # --- Content Loop ---
    total_global = Decimal(0)
    total_vencido = Decimal(0)
    total_por_vencer = Decimal(0)
    
    c.setLineWidth(0.5)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 20

    # Sort clients to keep consistent order (maybe by name)
    sorted_clients = sorted(target_clients, key=lambda x: x.nombre_comercial or "")

    for cli in sorted_clients:
        cli_invoices = invoices_by_client.get(cli.id, [])
        if not cli_invoices:
            continue
            
        # Check space for Section Header
        if y < 1.5 * inch:
            c.showPage()
            y = PAGE_H - MARGIN
        
        # Branch Header
        c.setFont(FONT_B, 10)
        c.setFillColor(colors.navy)
        sucursal_name = cli.nombre_comercial or cli.nombre_razon_social or "Sucursal"
        c.drawString(MARGIN, y, f"Sucursal: {sucursal_name}")
        c.setFillColor(colors.black)
        y -= 5
        
        # Table Data
        data = [["Folio", "Fecha", "Vence", "Monto", "Antig.", "Saldo"]]
        
        subtotal_sucursal = Decimal(0)
        
        for f in cli_invoices:
            folio = f"{f.serie or ''} {f.folio or ''}".strip()
            fecha = f.fecha_emision.strftime("%d/%m/%Y") if f.fecha_emision else "-"
            
            # Use same logic as aging report for due date base
            fecha_base = f.fecha_pago if f.fecha_pago else f.fecha_emision
            if isinstance(fecha_base, datetime): fecha_base = fecha_base.date()
            today = datetime.now().date()
            days_overdue = (today - fecha_base).days
            vence = fecha_base.strftime("%d/%m/%Y")
            
            saldo = Decimal(f.total or 0)
            
            subtotal_sucursal += saldo
            
            # Aging column
            aging_str = f"{days_overdue} días" if days_overdue > 0 else "Por vencer"
            if days_overdue > 0:
                total_vencido += saldo
            else:
                total_por_vencer += saldo
            
            data.append([
                folio, 
                fecha, 
                vence, 
                _money(f.total), 
                aging_str, 
                _money(saldo)
            ])
            
        # Add Subtotal Row
        data.append(["", "", "", "", "Total Sucursal:", _money(subtotal_sucursal)])
        total_global += subtotal_sucursal

        # Draw Table
        table = Table(data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), FONT_B),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
            
            ('FONTNAME', (0,1), (-1,-1), FONT),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('ALIGN', (3,0), (-1,-1), 'RIGHT'), # Amounts right aligned
            
            # Subtotal Row style
            ('FONTNAME', (-2,-1), (-1,-1), FONT_B),
            ('LINEABOVE', (-2,-1), (-1,-1), 1, colors.grey),
        ]))
        
        w, h = table.wrap(PAGE_W - 2*MARGIN, PAGE_H)
        
        if y - h < MARGIN:
            c.showPage()
            y = PAGE_H - MARGIN
            
        table.drawOn(c, MARGIN, y - h)
        y -= (h + 25) # Gap between branches

    # --- Grand Total Summary ---
    if y < 1.5 * inch:
        c.showPage()
        y = PAGE_H - MARGIN
    
    # Draw Summary Table (Right Aligned logic)
    y -= 10
    
    # We want a small table at right
    summary_data = [
        ["Saldo Vencido:", _money(total_vencido)],
        ["Saldo Por Vencer:", _money(total_por_vencer)],
        ["TOTAL A PAGAR:", _money(total_global)],
    ]
    
    sum_table = Table(summary_data, colWidths=[1.5*inch, 1.5*inch])
    sum_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), FONT),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        
        # Vencido color
        ('TEXTCOLOR', (1,0), (1,0), colors.red),
        # Por Vencer color
        ('TEXTCOLOR', (1,1), (1,1), colors.green),
        
        # Total Bold
        ('FONTNAME', (0,-1), (-1,-1), FONT_B),
        ('FONTSIZE', (0,-1), (-1,-1), 12),
        ('TOPPADDING', (0,-1), (-1,-1), 6),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
    ]))
    
    sw, sh = sum_table.wrap(PAGE_W, PAGE_H)
    sum_table.drawOn(c, PAGE_W - MARGIN - sw, y - sh)
    
    c.save()
    buffer.seek(0)
    return buffer
