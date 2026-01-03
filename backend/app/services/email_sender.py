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
    db: Session, empresa_id: uuid.UUID, factura_id: uuid.UUID, recipient_email: str
):
    # 1. Obtener la configuración de email de la empresa
    email_config = (
        db.query(models.EmailConfig)
        .filter(models.EmailConfig.empresa_id == empresa_id)
        .first()
    )
    if not email_config:
        raise EmailSendingError(
            "La empresa no tiene una configuración de correo electrónico."
        )

    # 2. Obtener la factura
    factura = (
        db.query(models.Factura)
        .options(selectinload(models.Factura.empresa))
        .filter(
            models.Factura.id == factura_id, models.Factura.empresa_id == empresa_id
        )
        .first()
    )
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
        raise EmailSendingError(
            "No se pudo desencriptar la contraseña del correo. Verifique la configuración."
        )

    msg = MIMEMultipart()
    msg["From"] = (
        f"{email_config.from_name} <{email_config.from_address}>"
        if email_config.from_name
        else email_config.from_address
    )
    msg["To"] = recipient_email

    subject_prefix = ""
    body_message = "Adjuntamos los archivos de su factura"
    if factura.estatus == "CANCELADA":
        subject_prefix = "[CANCELADA] "
        body_message = "Adjuntamos el PDF de su factura cancelada"

    msg["Subject"] = (
        f"{subject_prefix}Factura {factura.serie}-{factura.folio} de {factura.empresa.nombre}"
    )

    body = f"""
    <html>
      <body>
        <p>Estimado cliente,</p>
        <p>{body_message} con folio <strong>{factura.serie}-{factura.folio}</strong>.</p>
        <p>Saludos cordiales,<br/>{factura.empresa.nombre_comercial}</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

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
            logger.warning(
                f"XML path found for factura {factura.id} but file does not exist: {xml_full_path}"
            )

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
        raise EmailSendingError(
            "Error de autenticación SMTP. Verifique el usuario y la contraseña."
        )
    except Exception as e:
        raise EmailSendingError(f"Error al enviar el correo: {e}")


def send_preview_invoice_email(
    db: Session, empresa_id: uuid.UUID, factura_id: uuid.UUID, recipient_email: str
):
    # 1. Obtener la configuración de email de la empresa
    email_config = (
        db.query(models.EmailConfig)
        .filter(models.EmailConfig.empresa_id == empresa_id)
        .first()
    )
    if not email_config:
        raise EmailSendingError(
            "La empresa no tiene una configuración de correo electrónico."
        )

    # 2. Obtener la factura
    factura = (
        db.query(models.Factura)
        .options(selectinload(models.Factura.empresa))
        .filter(
            models.Factura.id == factura_id, models.Factura.empresa_id == empresa_id
        )
        .first()
    )
    if not factura:
        raise EmailSendingError("Factura no encontrada.")

    # 3. Generar PDF de vista previa en memoria
    try:
        from app.services.factura_service import generar_pdf_bytes

        pdf_bytes = generar_pdf_bytes(db, factura.id, preview=True)
    except Exception as e:
        raise EmailSendingError(
            f"No se pudo generar el PDF de vista previa para el envío: {e}"
        )

    # 4. Desencriptar contraseña y preparar datos del correo
    try:
        smtp_password = decrypt_data(email_config.smtp_password)
    except Exception:
        raise EmailSendingError(
            "No se pudo desencriptar la contraseña del correo. Verifique la configuración."
        )

    msg = MIMEMultipart()
    msg["From"] = (
        f"{email_config.from_name} <{email_config.from_address}>"
        if email_config.from_name
        else email_config.from_address
    )
    msg["To"] = recipient_email
    msg["Subject"] = (
        f"Vista Previa de Factura {factura.serie}-{factura.folio} de {factura.empresa.nombre}"
    )

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
    msg.attach(MIMEText(body, "html"))

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
        raise EmailSendingError(
            "Error de autenticación SMTP. Verifique el usuario y la contraseña."
        )
    except Exception as e:
        raise EmailSendingError(f"Error al enviar el correo: {e}")


async def send_pago_email(
    db: Session,
    pago_id: uuid.UUID,
    recipients: list[str],
    subject: str = None,
    body: str = None,
    pdf_content: bytes = None,
    pdf_filename: str = None,
    xml_content: bytes = None,
    xml_filename: str = None,
    empresa_id: uuid.UUID = None, # Optional if we can get it from pago
):
    # 1. Obtener el pago y su empresa
    pago = (
        db.query(models.Pago)
        .options(selectinload(models.Pago.empresa))
        .filter(models.Pago.id == pago_id)
        .first()
    )
    if not pago:
        raise EmailSendingError("Complemento de pago no encontrado.")
    
    empresa_id = pago.empresa_id

    # 2. Obtener la configuración de email de la empresa
    email_config = (
        db.query(models.EmailConfig)
        .filter(models.EmailConfig.empresa_id == empresa_id)
        .first()
    )
    if not email_config:
        raise EmailSendingError(
            "La empresa no tiene una configuración de correo electrónico."
        )

    # 3. Desencriptar contraseña
    try:
        smtp_password = decrypt_data(email_config.smtp_password)
    except Exception:
        raise EmailSendingError(
            "No se pudo desencriptar la contraseña del correo. Verifique la configuración."
        )

    msg = MIMEMultipart()
    msg["From"] = (
        f"{email_config.from_name} <{email_config.from_address}>"
        if email_config.from_name
        else email_config.from_address
    )
    # Join recipients with comma
    msg["To"] = ", ".join(recipients)
    
    # Subject
    if subject:
        msg["Subject"] = subject
    else:
        msg["Subject"] = (
            f"Complemento de Pago {pago.serie}-{pago.folio} de {pago.empresa.nombre}"
        )

    # Body
    if not body:
        body = f"""
        <html>
          <body>
            <p>Estimado cliente,</p>
            <p>Adjuntamos los archivos de su complemento de pago con folio <strong>{pago.serie}-{pago.folio}</strong>.</p>
            <p>Saludos cordiales,<br/>{pago.empresa.nombre_comercial}</p>
          </body>
        </html>
        """
    msg.attach(MIMEText(body, "html"))

    # 4. Adjuntar XML (usar el provider o leer del path)
    if xml_content:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(xml_content)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{xml_filename or f"PAGO-{pago.folio}.xml"}"',
        )
        msg.attach(part)
    elif pago.xml_path:
        # Fallback to reading file if not provided
        xml_full_path = os.path.join(settings.DATA_DIR, pago.xml_path)
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

    # 5. Adjuntar PDF (usar el provider o generar)
    if pdf_content:
        part_pdf = MIMEBase("application", "octet-stream")
        part_pdf.set_payload(pdf_content)
        encoders.encode_base64(part_pdf)
        part_pdf.add_header(
            "Content-Disposition",
            f'attachment; filename="{pdf_filename or f"PAGO-{pago.folio}.pdf"}"',
        )
        msg.attach(part_pdf)
    else:
        # Fallback generation
        try:
            from app.services.pago_service import generar_pdf_bytes_pago
            pdf_bytes = generar_pdf_bytes_pago(db, pago.id)
            
            emisor_rfc = (getattr(pago.empresa, "rfc", "") or "EMISOR").upper()
            pdf_fname = f"PAGO-{emisor_rfc}-{pago.serie}-{pago.folio}-{pago.cfdi_uuid}.pdf"
            
            part_pdf = MIMEBase("application", "octet-stream")
            part_pdf.set_payload(pdf_bytes)
            encoders.encode_base64(part_pdf)
            part_pdf.add_header(
                "Content-Disposition",
                f'attachment; filename="{pdf_fname}"',
            )
            msg.attach(part_pdf)
        except Exception as e:
            # Si falla generar PDF aquí, lo omitimos o logueamos, pero no detenemos si ya tenemos XML
             pass

    # 6. Enviar correo (usando SMTP sincrono, pero envuelto en funcion async si fuera necesario bloquear,
    # aqui smtplib es bloqueante, asi que bloqueara el thread. Para hacerlo verdaderamente async se requiere aiosmtplib.
    # Por ahora mantenemos smtplib pero la definicion es async para complacer al caller)
    try:
        server = smtplib.SMTP(email_config.smtp_server, email_config.smtp_port)
        if email_config.use_tls:
            server.starttls()
        server.login(email_config.smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except smtplib.SMTPAuthenticationError:
        raise EmailSendingError(
            "Error de autenticación SMTP. Verifique el usuario y la contraseña."
        )
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
        server.set_debuglevel(0)  # Desactivar salida de depuración para producción
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        raise EmailSendingError(
            "Error de autenticación SMTP. Verifique el usuario y la contraseña."
        )
    except smtplib.SMTPConnectError as e:
        raise EmailSendingError(f"No se pudo conectar al servidor SMTP: {e}")
    except Exception as e:
        raise EmailSendingError(f"Error al probar la conexión SMTP: {e}")


def send_presupuesto_email(
    db: Session, empresa_id: uuid.UUID, presupuesto_id: uuid.UUID, recipient_email: str
):
    # 1. Obtener la configuración de email de la empresa
    email_config = (
        db.query(models.EmailConfig)
        .filter(models.EmailConfig.empresa_id == empresa_id)
        .first()
    )
    if not email_config:
        raise EmailSendingError(
            "La empresa no tiene una configuración de correo electrónico."
        )

    # 2. Obtener el presupuesto
    presupuesto = (
        db.query(models.Presupuesto)
        .options(selectinload(models.Presupuesto.empresa), selectinload(models.Presupuesto.cliente))
        .filter(
            models.Presupuesto.id == presupuesto_id, models.Presupuesto.empresa_id == empresa_id
        )
        .first()
    )
    if not presupuesto:
        raise EmailSendingError("Presupuesto no encontrado.")

    # 3. Generar PDF en memoria
    try:
        from app.services.pdf_generator import generate_presupuesto_pdf
        pdf_bytes = generate_presupuesto_pdf(presupuesto, db)
    except Exception as e:
        raise EmailSendingError(f"No se pudo generar el PDF para el envío: {e}")

    # 4. Desencriptar contraseña y preparar datos del correo
    try:
        smtp_password = decrypt_data(email_config.smtp_password)
    except Exception:
        raise EmailSendingError(
            "No se pudo desencriptar la contraseña del correo. Verifique la configuración."
        )

    msg = MIMEMultipart()
    msg["From"] = (
        f"{email_config.from_name} <{email_config.from_address}>"
        if email_config.from_name
        else email_config.from_address
    )
    msg["To"] = recipient_email
    msg["Subject"] = (
        f"Presupuesto {presupuesto.folio} de {presupuesto.empresa.nombre_comercial}"
    )

    body = f"""
    <html>
      <body>
        <p>Estimado cliente {presupuesto.cliente.nombre_comercial},</p>
        <p>Adjuntamos el presupuesto con folio <strong>{presupuesto.folio}</strong>.</p>
        <p>Saludos cordiales,<br/>{presupuesto.empresa.nombre_comercial}</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

    # 5. Adjuntar PDF desde memoria
    pdf_filename = f"Presupuesto-{presupuesto.folio}.pdf"
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
        raise EmailSendingError(
            "Error de autenticación SMTP. Verifique el usuario y la contraseña."
        )
    except Exception as e:
        raise EmailSendingError(f"Error al enviar el correo: {e}")
