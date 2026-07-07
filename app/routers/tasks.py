from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import can_modify_task, can_reorder_tasks, get_current_user, require_roles
from app.database import get_db
from app.models import Task, TaskStatus, User, UserRole
from app.schemas import (
    DeveloperSummary,
    TaskCreate,
    TaskOut,
    TaskReorderRequest,
    TaskUpdate,
)
from app.services.task_service import (
    bottleneck_level,
    developer_clear_date,
    developer_remaining_hours,
    get_holiday_dates,
    get_leave_dates,
    get_next_queue_order,
    insert_task_at_position,
    recalculate_assignee_timeline,
    reorder_tasks,
    send_timeline_alert,
    task_to_out,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    assignee_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Task)
    if user.role == UserRole.DEVELOPER:
        query = query.filter(Task.assignee_id == user.id)
    elif assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    tasks = query.order_by(Task.assignee_id, Task.queue_order).all()
    return [task_to_out(t) for t in tasks]


@router.post("", response_model=TaskOut)
async def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.MANAGER)),
):
    assignee = db.query(User).filter(User.id == payload.assignee_id).first()
    if not assignee:
        raise HTTPException(404, "Assignee not found")

    queue_order = payload.queue_order or get_next_queue_order(db, payload.assignee_id)
    if payload.queue_order:
        insert_task_at_position(db, payload.assignee_id, queue_order)

    task = Task(
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        priority_weight=payload.priority_weight,
        effort_hours=payload.effort_hours,
        status=payload.status,
        queue_order=queue_order,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    recalculate_assignee_timeline(db, payload.assignee_id)
    db.refresh(task)

    all_tasks = (
        db.query(Task).filter(Task.assignee_id == payload.assignee_id).order_by(Task.queue_order).all()
    )
    await send_timeline_alert(
        db,
        f"New Task: {task.title}",
        f'New task "{task.title}" inserted at position {queue_order}',
        assignee,
        all_tasks,
    )
    return task_to_out(task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if not can_modify_task(user, task.assignee_id):
        raise HTTPException(403, "Cannot modify this task")

    old_status = task.status
    data = payload.model_dump(exclude_unset=True)

    if "queue_order" in data and not can_reorder_tasks(user):
        raise HTTPException(403, "Only managers can reorder tasks")

    for key, value in data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    recalculate_assignee_timeline(db, task.assignee_id)
    db.refresh(task)

    status_changed = "status" in data and data["status"] != old_status
    if status_changed and task.status in (TaskStatus.TESTING, TaskStatus.COMPLETED):
        assignee = db.query(User).filter(User.id == task.assignee_id).first()
        all_tasks = (
            db.query(Task).filter(Task.assignee_id == task.assignee_id).order_by(Task.queue_order).all()
        )
        await send_timeline_alert(
            db,
            f"Task Status: {task.title} → {task.status.value}",
            f'Task "{task.title}" moved to {task.status.value}',
            assignee,
            all_tasks,
        )

    return task_to_out(task)


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.MANAGER)),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    assignee_id = task.assignee_id
    db.delete(task)
    db.commit()
    recalculate_assignee_timeline(db, assignee_id)
    return {"ok": True}


@router.post("/reorder", response_model=list[TaskOut])
async def reorder(
    payload: TaskReorderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.MANAGER)),
):
    assignee = db.query(User).filter(User.id == payload.assignee_id).first()
    if not assignee:
        raise HTTPException(404, "Assignee not found")

    order_items = [(item.task_id, item.queue_order) for item in payload.tasks]
    reorder_tasks(db, payload.assignee_id, order_items)
    all_tasks = (
        db.query(Task).filter(Task.assignee_id == payload.assignee_id).order_by(Task.queue_order).all()
    )
    await send_timeline_alert(
        db,
        f"Queue Reordered: {assignee.name}",
        f"Task priority order updated for {assignee.name}",
        assignee,
        all_tasks,
    )
    return [task_to_out(t) for t in all_tasks]


@router.get("/dashboard/developers", response_model=list[DeveloperSummary])
def developer_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    holidays = get_holiday_dates(db)
    today = date.today()
    dev_query = db.query(User).filter(User.role == UserRole.DEVELOPER, User.is_active == True)  # noqa: E712
    if user.role == UserRole.DEVELOPER:
        dev_query = dev_query.filter(User.id == user.id)

    summaries = []
    for dev in dev_query.order_by(User.name).all():
        tasks = db.query(Task).filter(Task.assignee_id == dev.id).order_by(Task.queue_order).all()
        leave_dates = get_leave_dates(db, dev.id)
        on_leave = today in leave_dates
        active = next(
            (t for t in tasks if t.status in (TaskStatus.IN_PROGRESS, TaskStatus.TESTING)),
            next((t for t in tasks if t.status == TaskStatus.TODO), None),
        )
        clear = developer_clear_date(tasks)
        level = bottleneck_level(clear, holidays, leave_dates)
        summaries.append(
            DeveloperSummary(
                id=dev.id,
                name=dev.name,
                email=dev.email,
                active_task=task_to_out(active) if active else None,
                remaining_hours=developer_remaining_hours(tasks),
                clear_date=clear,
                bottleneck=level in ("red", "orange"),
                bottleneck_level=level,
                on_leave=on_leave,
                tasks=[task_to_out(t) for t in tasks],
            )
        )
    return summaries
