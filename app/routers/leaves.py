from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import DeveloperLeave, User, UserRole
from app.schemas import LeaveCreate, LeaveOut, LeaveUpdate
from app.services.task_service import recalculate_assignee_timeline

router = APIRouter(prefix="/api/leaves", tags=["leaves"])


def leave_to_out(leave: DeveloperLeave) -> LeaveOut:
    return LeaveOut(
        id=leave.id,
        user_id=leave.user_id,
        user_name=leave.user.name if leave.user else "",
        start_date=leave.start_date,
        end_date=leave.end_date,
        reason=leave.reason,
        notes=leave.notes,
        created_at=leave.created_at,
    )


def _validate_leave_dates(start: date, end: date) -> None:
    if end < start:
        raise HTTPException(400, "End date must be on or after start date")


@router.get("", response_model=list[LeaveOut])
def list_leaves(
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = db.query(DeveloperLeave)
    if current.role == UserRole.DEVELOPER:
        query = query.filter(DeveloperLeave.user_id == current.id)
    elif user_id:
        query = query.filter(DeveloperLeave.user_id == user_id)
    leaves = query.order_by(DeveloperLeave.start_date.desc()).all()
    return [leave_to_out(l) for l in leaves]


@router.post("", response_model=LeaveOut)
def create_leave(
    payload: LeaveCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.MANAGER)),
):
    _validate_leave_dates(payload.start_date, payload.end_date)
    dev = db.query(User).filter(
        User.id == payload.user_id, User.role == UserRole.DEVELOPER
    ).first()
    if not dev:
        raise HTTPException(404, "Developer not found")

    leave = DeveloperLeave(
        user_id=payload.user_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        notes=payload.notes,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    recalculate_assignee_timeline(db, payload.user_id)
    return leave_to_out(leave)


@router.patch("/{leave_id}", response_model=LeaveOut)
def update_leave(
    leave_id: int,
    payload: LeaveUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.MANAGER)),
):
    leave = db.query(DeveloperLeave).filter(DeveloperLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(404, "Leave not found")

    data = payload.model_dump(exclude_unset=True)
    start = data.get("start_date", leave.start_date)
    end = data.get("end_date", leave.end_date)
    _validate_leave_dates(start, end)

    for key, value in data.items():
        setattr(leave, key, value)
    db.commit()
    db.refresh(leave)
    recalculate_assignee_timeline(db, leave.user_id)
    return leave_to_out(leave)


@router.delete("/{leave_id}")
def delete_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.MANAGER)),
):
    leave = db.query(DeveloperLeave).filter(DeveloperLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(404, "Leave not found")
    user_id = leave.user_id
    db.delete(leave)
    db.commit()
    recalculate_assignee_timeline(db, user_id)
    return {"ok": True}
