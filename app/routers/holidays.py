from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models import Holiday, UserRole
from app.schemas import HolidayCreate, HolidayOut
from app.services.task_service import recalculate_assignee_timeline
from app.models import Task, User

router = APIRouter(prefix="/api/holidays", tags=["holidays"])


@router.get("", response_model=list[HolidayOut])
def list_holidays(db: Session = Depends(get_db)):
    return db.query(Holiday).order_by(Holiday.date).all()


@router.post("", response_model=HolidayOut)
def create_holiday(
    payload: HolidayCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(UserRole.MANAGER)),
):
    existing = db.query(Holiday).filter(Holiday.date == payload.date).first()
    if existing:
        raise HTTPException(400, "Holiday already exists for this date")
    holiday = Holiday(name=payload.name, date=payload.date)
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    _recalculate_all(db)
    return holiday


@router.delete("/{holiday_id}")
def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(UserRole.MANAGER)),
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(404, "Holiday not found")
    db.delete(holiday)
    db.commit()
    _recalculate_all(db)
    return {"ok": True}


def _recalculate_all(db: Session) -> None:
    dev_ids = [u.id for u in db.query(User).filter(User.role == UserRole.DEVELOPER).all()]
    for dev_id in dev_ids:
        recalculate_assignee_timeline(db, dev_id)
