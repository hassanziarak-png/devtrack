import logging

import httpx
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import NotificationLog

logger = logging.getLogger(__name__)


def _real_recipients(recipients: list[str]) -> list[str]:
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
        _finalize_log(db, log_id, html_body, subject, False, "EMAIL_ENABLED is false")
        return False

    if not deliver_to:
        _finalize_log(
            db, log_id, html_body, subject, False,
            "No real recipient addresses (demo @devtrack.local addresses are skipped)",
        )
        return False

    if not settings.smtp_from or settings.smtp_from == "devtrack@localhost":
        _finalize_log(db, log_id, html_body, subject, False, "SMTP_FROM is not set")
        return False

    # Prefer Brevo HTTP API — more reliable from cloud hosts than SMTP
    if settings.brevo_api_key:
        ok, note = await _send_brevo_api(deliver_to, subject, html_body)
        _finalize_log(db, log_id, html_body, subject, ok, note)
        return ok

    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        ok, note = await _send_smtp(deliver_to, subject, html_body)
        _finalize_log(db, log_id, html_body, subject, ok, note)
        return ok

    _finalize_log(db, log_id, html_body, subject, False, "No BREVO_API_KEY or SMTP credentials configured")
    return False


async def _send_brevo_api(recipients: list[str], subject: str, html_body: str) -> tuple[bool, str]:
    payload = {
        "sender": {"name": settings.smtp_from_name, "email": settings.smtp_from},
        "to": [{"email": r} for r in recipients],
        "subject": subject,
        "htmlContent": html_body,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": settings.brevo_api_key,
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json=payload,
            )
        if resp.status_code in (200, 201):
            msg_id = resp.json().get("messageId", "ok")
            return True, f"Brevo API sent successfully (messageId: {msg_id}) to {', '.join(recipients)}"
        return False, f"Brevo API error {resp.status_code}: {resp.text[:500]}"
    except Exception as e:
        return False, f"Brevo API failed: {type(e).__name__}: {e}"


async def _send_smtp(recipients: list[str], subject: str, html_body: str) -> tuple[bool, str]:
    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    attempts = [
        (settings.smtp_port, False, settings.smtp_port != 465),
        (465, True, False),
        (587, False, True),
    ]
    seen = set()
    errors = []

    for port, use_tls, start_tls in attempts:
        key = (port, use_tls, start_tls)
        if key in seen:
            continue
        seen.add(key)
        try:
            smtp = aiosmtplib.SMTP(
                hostname=settings.smtp_host,
                port=port,
                use_tls=use_tls,
                start_tls=start_tls,
                timeout=30,
            )
            await smtp.connect()
            await smtp.login(settings.smtp_user, settings.smtp_password)
            send_errors = await smtp.send_message(message, recipients=recipients)
            await smtp.quit()
            if send_errors:
                err_text = "; ".join(f"{a}: {e}" for a, e in send_errors.items())
                errors.append(f"port {port}: {err_text}")
                continue
            return True, f"SMTP sent via port {port} to {', '.join(recipients)}"
        except Exception as e:
            errors.append(f"port {port}: {type(e).__name__}: {e}")

    return False, "SMTP failed — " + " | ".join(errors)


def _finalize_log(
    db: Session, log_id: int, original_body: str, subject: str, success: bool, note: str
) -> None:
    log = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
    if not log:
        return
    prefix = "SENT" if success else "FAILED"
    log.subject = f"[{prefix}] {subject}"
    color = "#22c55e" if success else "#ef4444"
    log.body = original_body + f"<hr><p style='color:{color}'><strong>{note}</strong></p>"
    db.commit()
    if success:
        logger.info("Email %s: %s", prefix, note)
    else:
        logger.error("Email %s: %s", prefix, note)


def get_email_config_status() -> dict:
    return {
        "email_enabled": settings.email_enabled,
        "smtp_from": settings.smtp_from,
        "smtp_from_name": settings.smtp_from_name,
        "brevo_api_configured": bool(settings.brevo_api_key),
        "smtp_host": settings.smtp_host or None,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user or None,
        "smtp_configured": bool(
            settings.smtp_host and settings.smtp_user and settings.smtp_password
        ),
        "send_method": (
            "brevo_api" if settings.brevo_api_key
            else "smtp" if settings.smtp_host and settings.smtp_user and settings.smtp_password
            else "none"
        ),
    }
