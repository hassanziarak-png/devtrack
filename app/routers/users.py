from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password, require_roles
from app.database import get_db
from app.models import Task, User, UserRole
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        phone=user.phone,
        department=user.department,
        bio=user.bio,
        is_active=getattr(user, "is_active", True),
        created_at=user.created_at,
        updated_at=getattr(user, "updated_at", None),
    )


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.MANAGER)),
):
    users = db.query(User).order_by(User.name).all()
    return [user_to_out(u) for u in users]


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.MANAGER)),
):
    if payload.role not in (UserRole.MANAGER, UserRole.DEVELOPER, UserRole.EXECUTIVE):
        raise HTTPException(400, "Invalid role")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
        department=payload.department,
        bio=payload.bio,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_out(user)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user_to_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    data.pop("role", None)
    data.pop("is_active", None)
    return _apply_user_update(db, user, data)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if current.role != UserRole.MANAGER and current.id != user_id:
        raise HTTPException(403, "Insufficient permissions")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user_to_out(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    data = payload.model_dump(exclude_unset=True)
    if current.role != UserRole.MANAGER:
        if current.id != user_id:
            raise HTTPException(403, "Insufficient permissions")
        data.pop("role", None)
        data.pop("is_active", None)

    if "email" in data and data["email"] != user.email:
        if db.query(User).filter(User.email == data["email"], User.id != user_id).first():
            raise HTTPException(400, "Email already in use")

    return _apply_user_update(db, user, data)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(UserRole.MANAGER)),
):
    if current.id == user_id:
        raise HTTPException(400, "Cannot delete your own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    task_count = db.query(Task).filter(Task.assignee_id == user_id).count()
    if task_count > 0:
        raise HTTPException(400, f"User has {task_count} assigned tasks. Reassign or delete them first.")
    db.delete(user)
    db.commit()
    return {"ok": True}


def _apply_user_update(db: Session, user: User, data: dict) -> UserOut:
    password = data.pop("password", None)
    if password:
        user.hashed_password = hash_password(password)
    for key, value in data.items():
        setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user_to_out(user)
