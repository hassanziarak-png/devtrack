import logging
from datetime import date

from app.database import SessionLocal
from app.email_service import send_email
from app.models import ReportFrequency, ReportSettings, Task, User, UserRole
from app.pdf_service import generate_department_pdf
from app.services.task_service import get_scheduled_report_emails

logger = logging.getLogger(__name__)


async def run_scheduled_report() -> None:
    db = SessionLocal()
    try:
        settings_row = db.query(ReportSettings).first()
        if not settings_row or settings_row.frequency == ReportFrequency.OFF:
            return

        today = date.today()
        if settings_row.frequency == ReportFrequency.WEEKLY and today.weekday() != 0:
            return
        if settings_row.frequency == ReportFrequency.MONTHLY and today.day != 1:
            return

        developers = db.query(User).filter(User.role == UserRole.DEVELOPER).all()
        tasks_by_dev = {
            dev.id: db.query(Task).filter(Task.assignee_id == dev.id).order_by(Task.queue_order).all()
            for dev in developers
        }
        generate_department_pdf(developers, tasks_by_dev, today)
        recipients = get_scheduled_report_emails(db)

        if not recipients:
            logger.info("No recipients for scheduled report")
            return

        body = f"""
        <html><body>
            <h2>DevTrack Scheduled Report</h2>
            <p>Department workload PDF for {today.isoformat()}.</p>
        </body></html>"""

        await send_email(
            db,
            f"DevTrack {settings_row.frequency.value.title()} Report — {today}",
            recipients,
            body + "<p><em>Download the latest PDF from the Reports page.</em></p>",
        )
        logger.info("Scheduled report sent to %s", recipients)
    finally:
        db.close()
