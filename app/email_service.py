import logging
from typing import Optional

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import NotificationLog

logger = logging.getLogger(__name__)


def _real_recipients(recipients: list[str]) -> list[str]:
    """Skip fake demo addresses that cannot receive mail."""
    return [
        r.strip()
        for r in recipients
        if r.strip() and not r.strip().lower().endswith("@devtrack.local")
    ]


async def send_email(db: Session, subject: str, recipients: list[str], html_body: str) -> bool:
    all_recipients = list(dict.fromkeys(r.strip() for r in recipients if r.strip()))
    deliver_to = _real_recipients(all_recipients)

    log = NotificationLog(
        subject=subject,
        recipients=", ".join(all_recipients),
        body=html_body,
    )
    db.add(log)
    db.commit()
    log_id = log.id

    if not settings.email_enabled:
        _append_log_note(db, log_id, html_body, "Email not sent: EMAIL_ENABLED is false")
        logger.info("Email logged (disabled): %s", subject)
        return False

    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        _append_log_note(db, log_id, html_body, "Email not sent: SMTP not fully configured")
        logger.warning("SMTP incomplete: host=%s user=%s", settings.smtp_host, bool(settings.smtp_user))
        return False

    if not deliver_to:
        _append_log_note(
            db,
            log_id,
            html_body,
            "Email not sent: no real recipient addresses (demo @devtrack.local skipped)",
        )
        return False

    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(deliver_to)
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    try:
        smtp = aiosmtplib.SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            use_tls=False,
            start_tls=True,
            timeout=30,
        )
        await smtp.connect()
        await smtp.login(settings.smtp_user, settings.smtp_password)
        errors = await smtp.send_message(message, recipients=deliver_to)
        await smtp.quit()

        if errors:
            err_text = "; ".join(f"{addr}: {err}" for addr, err in errors.items())
            _append_log_note(db, log_id, html_body, f"SMTP partial failure: {err_text}")
            logger.error("SMTP errors: %s", err_text)
            return False

        _append_log_note(db, log_id, html_body, f"Email sent successfully to: {', '.join(deliver_to)}")
        logger.info("Email sent: %s -> %s", subject, deliver_to)
        return True

    except Exception as e:
        err_msg = f"SMTP failed: {type(e).__name__}: {e}"
        _append_log_note(db, log_id, html_body, err_msg)
        logger.exception("Failed to send email")
        return False


def _append_log_note(db: Session, log_id: int, original_body: str, note: str) -> None:
    log = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
    if log:
        log.body = original_body + f"<hr><p><strong>{note}</strong></p>"
        db.commit()


def get_email_config_status() -> dict:
    return {
        "email_enabled": settings.email_enabled,
        "smtp_host": settings.smtp_host or None,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user or None,
        "smtp_from": settings.smtp_from,
        "smtp_configured": bool(
            settings.smtp_host and settings.smtp_user and settings.smtp_password
        ),
    }
