from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import (
    DeveloperLeave,
    NotificationLog,
    RecipientType,
    ReportRecipient,
    ReportSettings,
    Task,
    User,
    UserRole,
)
from app.email_service import get_email_config_status, send_email
from app.pdf_service import generate_department_pdf
from app.schemas import (
    NotificationOut,
    ReportRecipientCreate,
    ReportRecipientOut,
    ReportSettingsOut,
    ReportSettingsUpdate,
    UserOut,
)

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/developers", response_model=list[UserOut])
def list_developers(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    users = db.query(User).filter(
        User.role == UserRole.DEVELOPER, User.is_active == True  # noqa: E712
    ).order_by(User.name).all()
    return users


@router.get("/reports/settings", response_model=ReportSettingsOut)
def get_report_settings(db: Session = Depends(get_db), _user=Depends(require_roles(UserRole.MANAGER))):
    settings_row = db.query(ReportSettings).first()
    if not settings_row:
        settings_row = ReportSettings()
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


@router.put("/reports/settings", response_model=ReportSettingsOut)
def update_report_settings(
    payload: ReportSettingsUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(UserRole.MANAGER)),
):
    settings_row = db.query(ReportSettings).first()
    if not settings_row:
        settings_row = ReportSettings()
        db.add(settings_row)
    settings_row.frequency = payload.frequency
    db.commit()
    db.refresh(settings_row)
    return settings_row


@router.get("/reports/recipients", response_model=list[ReportRecipientOut])
def list_recipients(
    recipient_type: RecipientType | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(UserRole.MANAGER)),
):
    query = db.query(ReportRecipient)
    if recipient_type:
        query = query.filter(ReportRecipient.recipient_type == recipient_type)
    return query.order_by(ReportRecipient.recipient_type, ReportRecipient.email).all()


@router.post("/reports/recipients", response_model=ReportRecipientOut)
def add_recipient(
    payload: ReportRecipientCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(UserRole.MANAGER)),
):
    existing = db.query(ReportRecipient).filter(
        ReportRecipient.email == payload.email,
        ReportRecipient.recipient_type == payload.recipient_type,
    ).first()
    if existing:
        raise HTTPException(400, "Email already added for this notification type")
    row = ReportRecipient(
        email=payload.email,
        name=payload.name,
        recipient_type=payload.recipient_type,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/reports/recipients/{recipient_id}")
def remove_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(UserRole.MANAGER)),
):
    row = db.query(ReportRecipient).filter(ReportRecipient.id == recipient_id).first()
    if not row:
        raise HTTPException(404, "Recipient not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/reports/email-status")
def email_status(_user=Depends(require_roles(UserRole.MANAGER))):
    return get_email_config_status()


@router.post("/reports/test-email")
async def test_email(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.MANAGER)),
):
    body = """
    <html><body style="font-family:Arial,sans-serif">
        <h2>DevTrack Test Email</h2>
        <p>If you received this, SMTP is working correctly.</p>
    </body></html>"""
    ok = await send_email(
        db,
        "DevTrack SMTP Test",
        [user.email],
        body,
    )
    if not ok:
        raise HTTPException(
            502,
            "Test email failed. Open Notification Log for the error details.",
        )
    return {"ok": True, "message": f"Test email sent to {user.email}"}


@router.get("/reports/pdf")
def download_pdf(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    developers = db.query(User).filter(User.role == UserRole.DEVELOPER).order_by(User.name).all()
    tasks_by_dev: dict[int, list[Task]] = {}
    for dev in developers:
        tasks_by_dev[dev.id] = (
            db.query(Task).filter(Task.assignee_id == dev.id).order_by(Task.queue_order).all()
        )
    pdf_bytes = generate_department_pdf(developers, tasks_by_dev, date.today())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=devtrack-report.pdf"},
    )


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    _user=Depends(require_roles(UserRole.MANAGER, UserRole.EXECUTIVE)),
):
    return (
        db.query(NotificationLog)
        .order_by(NotificationLog.created_at.desc())
        .limit(50)
        .all()
    )
