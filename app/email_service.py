import logging

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import NotificationLog

logger = logging.getLogger(__name__)


async def send_email(db: Session, subject: str, recipients: list[str], html_body: str) -> bool:
    log = NotificationLog(
        subject=subject,
        recipients=", ".join(recipients),
        body=html_body,
    )
    db.add(log)
    db.commit()

    if not settings.email_enabled or not settings.smtp_host:
        logger.info("Email logged (SMTP disabled): %s -> %s", subject, recipients)
        return True

    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False
