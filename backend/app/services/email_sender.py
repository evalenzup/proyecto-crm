# backend/app/services/email_sender.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from sqlalchemy.orm import Session, selectinload
import uuid
import os

from app import models
from app.core.security import decrypt_data
from app.config import settings

class EmailSendingError(Exception):
    pass

def send_invoice_email(
    db: Session,
    empresa_id: uuid.UUID,
    factura_id: uuid.UUID,
    recipient_email: str
):
    # 1. Obtener la configuración de email de la empresa
    email_config = db.query(models.EmailConfig).filter(models.EmailConfig.empresa_id == empresa_id).first()
    if not email_config:
        raise EmailSendingError("La empresa no tiene una configuración de correo electrónico.")

    # 2. Obtener la factura
    factura = db.query(models.Factura).options(selectinload(models.Factura.empresa)).filter(models.Factura.id == factura_id, models.Factura.empresa_id == empresa_id).first()
    if not factura:
        raise EmailSendingError("Factura no encontrada.")

    # 3. Generar PDF en memoria
    try:
        from app.services.factura_service import generar_pdf_bytes
        pdf_bytes = generar_pdf_bytes(db, factura.id, preview=False)
    except Exception as e:
        raise EmailSendingError(f"No se pudo generar el PDF para el envío: {e}")

    # 4. Desencriptar contraseña y preparar datos del correo
    try:
        smtp_password = decrypt_data(email_config.smtp_password)
    except Exception:
        raise EmailSendingError("No se pudo desencriptar la contraseña del correo. Verifique la configuración.")

    msg = MIMEMultipart()
    msg['From'] = f"{email_config.from_name} <{email_config.from_address}>" if email_config.from_name else email_config.from_address
    msg['To'] = recipient_email

    subject_prefix = ""
    body_message = "Adjuntamos los archivos de su factura"
    if factura.estatus == "CANCELADA":
        subject_prefix = "[CANCELADA] "
        body_message = "Adjuntamos el PDF de su factura cancelada"
    
    msg['Subject'] = f"{subject_prefix}Factura {factura.serie}-{factura.folio} de {factura.empresa.nombre}"

    body = f"""
    <html>
      <body>
        <p>Estimado cliente,</p>
        <p>{body_message} con folio <strong>{factura.serie}-{factura.folio}</strong>.</p>
        <p>Saludos cordiales,<br/>{factura.empresa.nombre_comercial}</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    # 5. Adjuntar XML desde archivo (solo si la factura no está cancelada y tiene XML)
    if factura.estatus != "CANCELADA" and factura.xml_path:
        xml_full_path = os.path.join(settings.DATA_DIR, factura.xml_path)
        if os.path.exists(xml_full_path):
            with open(xml_full_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(xml_full_path)}"',
            )
            msg.attach(part)
        else:
            # Log a warning if XML path exists but file is not found for non-cancelled invoice
            import logging
            logger = logging.getLogger("app")
            logger.warning(f"XML path found for factura {factura.id} but file does not exist: {xml_full_path}")

    # 6. Adjuntar PDF desde memoria
    emisor_rfc = (getattr(factura.empresa, "rfc", "") or "EMISOR").upper()
    pdf_filename = f"{emisor_rfc}-{factura.serie}-{factura.folio}-{factura.cfdi_uuid or factura.id}.pdf"
    part_pdf = MIMEBase("application", "octet-stream")
    part_pdf.set_payload(pdf_bytes)
    encoders.encode_base64(part_pdf)
    part_pdf.add_header(
        "Content-Disposition",
        f'attachment; filename="{pdf_filename}"',
    )
    msg.attach(part_pdf)

    # 7. Enviar correo
    try:
        server = smtplib.SMTP(email_config.smtp_server, email_config.smtp_port)
        if email_config.use_tls:
            server.starttls()
        server.login(email_config.smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except smtplib.SMTPAuthenticationError:
        raise EmailSendingError("Error de autenticación SMTP. Verifique el usuario y la contraseña.")
    except Exception as e:
        raise EmailSendingError(f"Error al enviar el correo: {e}")

def send_preview_invoice_email(
    db: Session,
    empresa_id: uuid.UUID,
    factura_id: uuid.UUID,
    recipient_email: str
):
    # 1. Obtener la configuración de email de la empresa
    email_config = db.query(models.EmailConfig).filter(models.EmailConfig.empresa_id == empresa_id).first()
    if not email_config:
        raise EmailSendingError("La empresa no tiene una configuración de correo electrónico.")

    # 2. Obtener la factura
    factura = db.query(models.Factura).options(selectinload(models.Factura.empresa)).filter(models.Factura.id == factura_id, models.Factura.empresa_id == empresa_id).first()
    if not factura:
        raise EmailSendingError("Factura no encontrada.")

    # 3. Generar PDF de vista previa en memoria
    try:
        from app.services.factura_service import generar_pdf_bytes
        pdf_bytes = generar_pdf_bytes(db, factura.id, preview=True)
    except Exception as e:
        raise EmailSendingError(f"No se pudo generar el PDF de vista previa para el envío: {e}")

    # 4. Desencriptar contraseña y preparar datos del correo
    try:
        smtp_password = decrypt_data(email_config.smtp_password)
    except Exception:
        raise EmailSendingError("No se pudo desencriptar la contraseña del correo. Verifique la configuración.")

    msg = MIMEMultipart()
    msg['From'] = f"{email_config.from_name} <{email_config.from_address}>" if email_config.from_name else email_config.from_address
    msg['To'] = recipient_email
    msg['Subject'] = f"Vista Previa de Factura {factura.serie}-{factura.folio} de {factura.empresa.nombre}"

    body = f"""
    <html>
      <body>
        <p>Estimado cliente,</p>
        <p>Adjuntamos la vista previa de su factura con folio <strong>{factura.serie}-{factura.folio}</strong>.</p>
        <p><strong>Este es un borrador y no tiene validez fiscal.</strong></p>
        <p>Saludos cordiales,<br/>{factura.empresa.nombre_comercial}</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    # 5. Adjuntar PDF desde memoria
    emisor_rfc = (getattr(factura.empresa, "rfc", "") or "EMISOR").upper()
    pdf_filename = f"VISTAPREVIA-{emisor_rfc}-{factura.serie}-{factura.folio}.pdf"
    part_pdf = MIMEBase("application", "octet-stream")
    part_pdf.set_payload(pdf_bytes)
    encoders.encode_base64(part_pdf)
    part_pdf.add_header(
        "Content-Disposition",
        f'attachment; filename="{pdf_filename}"',
    )
    msg.attach(part_pdf)

    # 6. Enviar correo
    try:
        server = smtplib.SMTP(email_config.smtp_server, email_config.smtp_port)
        if email_config.use_tls:
            server.starttls()
        server.login(email_config.smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except smtplib.SMTPAuthenticationError:
        raise EmailSendingError("Error de autenticación SMTP. Verifique el usuario y la contraseña.")
    except Exception as e:
        raise EmailSendingError(f"Error al enviar el correo: {e}")

def send_pago_email(
    db: Session,
    empresa_id: uuid.UUID,
    pago_id: uuid.UUID,
    recipient_email: str
):
    # 1. Obtener la configuración de email de la empresa
    email_config = db.query(models.EmailConfig).filter(models.EmailConfig.empresa_id == empresa_id).first()
    if not email_config:
        raise EmailSendingError("La empresa no tiene una configuración de correo electrónico.")

    # 2. Obtener el pago
    pago = db.query(models.Pago).options(selectinload(models.Pago.empresa)).filter(models.Pago.id == pago_id, models.Pago.empresa_id == empresa_id).first()
    if not pago:
        raise EmailSendingError("Complemento de pago no encontrado.")

    # 3. Verificar existencia del XML del pago
    if not pago.xml_path:
        raise EmailSendingError("El complemento de pago no tiene un archivo XML generado.")
    xml_full_path = os.path.join(settings.DATA_DIR, pago.xml_path)
    if not os.path.exists(xml_full_path):
        raise EmailSendingError(f"No se encontró el archivo XML del pago en el servidor: {xml_full_path}")

    # 4. Generar PDF del pago en memoria
    try:
        from app.services.pago_service import generar_pdf_bytes_pago
        pdf_bytes = generar_pdf_bytes_pago(db, pago.id)
    except Exception as e:
        raise EmailSendingError(f"No se pudo generar el PDF para el complemento de pago: {e}")

    # 5. Desencriptar contraseña y preparar datos del correo
    try:
        smtp_password = decrypt_data(email_config.smtp_password)
    except Exception:
        raise EmailSendingError("No se pudo desencriptar la contraseña del correo. Verifique la configuración.")

    msg = MIMEMultipart()
    msg['From'] = f"{email_config.from_name} <{email_config.from_address}>" if email_config.from_name else email_config.from_address
    msg['To'] = recipient_email
    msg['Subject'] = f"Complemento de Pago {pago.serie}-{pago.folio} de {pago.empresa.nombre}"

    body = f"""
    <html>
      <body>
        <p>Estimado cliente,</p>
        <p>Adjuntamos los archivos de su complemento de pago con folio <strong>{pago.serie}-{pago.folio}</strong>.</p>
        <p>Saludos cordiales,<br/>{pago.empresa.nombre_comercial}</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    # 6. Adjuntar XML del pago desde archivo
    with open(xml_full_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(xml_full_path)}"',
    )
    msg.attach(part)

    # 7. Adjuntar PDF del pago desde memoria
    emisor_rfc = (getattr(pago.empresa, "rfc", "") or "EMISOR").upper()
    pdf_filename = f"PAGO-{emisor_rfc}-{pago.serie}-{pago.folio}-{pago.cfdi_uuid}.pdf"
    part_pdf = MIMEBase("application", "octet-stream")
    part_pdf.set_payload(pdf_bytes)
    encoders.encode_base64(part_pdf)
    part_pdf.add_header(
        "Content-Disposition",
        f'attachment; filename="{pdf_filename}"',
    )
    msg.attach(part_pdf)

    # 8. Enviar correo
    try:
        server = smtplib.SMTP(email_config.smtp_server, email_config.smtp_port)
        if email_config.use_tls:
            server.starttls()
        server.login(email_config.smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except smtplib.SMTPAuthenticationError:
        raise EmailSendingError("Error de autenticación SMTP. Verifique el usuario y la contraseña.")
    except Exception as e:
        raise EmailSendingError(f"Error al enviar el correo: {e}")

def test_smtp_connection(
    smtp_server: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    use_tls: bool,
):
    """Prueba la conexión a un servidor SMTP con las credenciales dadas."""
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(0) # Desactivar salida de depuración para producción
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        raise EmailSendingError("Error de autenticación SMTP. Verifique el usuario y la contraseña.")
    except smtplib.SMTPConnectError as e:
        raise EmailSendingError(f"No se pudo conectar al servidor SMTP: {e}")
    except Exception as e:
        raise EmailSendingError(f"Error al probar la conexión SMTP: {e}")
