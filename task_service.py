import logging
from datetime import date

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    DeveloperLeave,
    Holiday,
    RecipientType,
    ReportRecipient,
    Task,
    TaskStatus,
    User,
    UserRole,
    expand_leave_dates,
)
from app.schemas import TaskOut
from app.timeline_engine import recalculate_developer_timeline

logger = logging.getLogger(__name__)


def get_holiday_dates(db: Session) -> set[date]:
    return {h.date for h in db.query(Holiday).all()}


def get_leave_dates(db: Session, user_id: int) -> set[date]:
    today = date.today()
    leaves = (
        db.query(DeveloperLeave)
        .filter(DeveloperLeave.user_id == user_id, DeveloperLeave.end_date >= today)
        .all()
    )
    return expand_leave_dates(leaves)


def task_to_out(task: Task) -> TaskOut:
    variance = None
    if task.actual_hours is not None and task.effort_hours:
        variance = round(((task.actual_hours - task.effort_hours) / task.effort_hours) * 100, 1)
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee_id,
        assignee_name=task.assignee.name if task.assignee else "",
        priority_weight=task.priority_weight,
        queue_order=task.queue_order,
        effort_hours=task.effort_hours,
        actual_hours=task.actual_hours,
        status=task.status,
        start_date=task.start_date,
        estimated_completion_date=task.estimated_completion_date,
        created_at=task.created_at,
        updated_at=task.updated_at,
        estimation_variance=variance,
    )


def renormalize_queue_orders(db: Session, assignee_id: int) -> None:
    """Compact queue_order to 1, 2, 3... after delete or reassignment."""
    tasks = (
        db.query(Task)
        .filter(Task.assignee_id == assignee_id)
        .order_by(Task.queue_order)
        .all()
    )
    for i, task in enumerate(tasks, start=1):
        task.queue_order = i
    db.commit()


def recalculate_assignee_timeline(db: Session, assignee_id: int) -> list[Task]:
    holidays = get_holiday_dates(db)
    leave_dates = get_leave_dates(db, assignee_id)
    tasks = (
        db.query(Task)
        .filter(Task.assignee_id == assignee_id)
        .order_by(Task.queue_order)
        .all()
    )
    updates = recalculate_developer_timeline(tasks, holidays, leave_dates=leave_dates)
    update_map = {u["task_id"]: u for u in updates}
    changed = []
    for task in tasks:
        if task.id in update_map:
            task.start_date = update_map[task.id]["start_date"]
            task.estimated_completion_date = update_map[task.id]["estimated_completion_date"]
            changed.append(task)
    db.commit()
    return changed


def get_next_queue_order(db: Session, assignee_id: int) -> int:
    max_order = (
        db.query(Task.queue_order)
        .filter(Task.assignee_id == assignee_id)
        .order_by(Task.queue_order.desc())
        .first()
    )
    return (max_order[0] if max_order else 0) + 1


def insert_task_at_position(db: Session, assignee_id: int, position: int) -> None:
    tasks = (
        db.query(Task)
        .filter(Task.assignee_id == assignee_id, Task.queue_order >= position)
        .order_by(Task.queue_order.desc())
        .all()
    )
    for task in tasks:
        task.queue_order += 1


def reorder_tasks(
    db: Session, assignee_id: int, order_items: list[tuple[int, int]]
) -> list[Task]:
    task_map = {
        t.id: t
        for t in db.query(Task).filter(Task.assignee_id == assignee_id).all()
    }
    for task_id, new_order in order_items:
        if task_id in task_map:
            task_map[task_id].queue_order = new_order
    db.commit()
    return recalculate_assignee_timeline(db, assignee_id)


def developer_remaining_hours(tasks: list[Task]) -> float:
    return sum(
        t.effort_hours
        for t in tasks
        if t.status not in (TaskStatus.COMPLETED,)
    )


def developer_clear_date(tasks: list[Task]) -> date | None:
    active = [t for t in tasks if t.status != TaskStatus.COMPLETED]
    if not active:
        return None
    return max(
        (t.estimated_completion_date for t in active if t.estimated_completion_date),
        default=None,
    )


def bottleneck_level(
    clear_date: date | None, holidays: set[date], leave_dates: set[date] | None = None
) -> str:
    if clear_date is None:
        return "green"
    from app.timeline_engine import business_days_between

    days_out = business_days_between(date.today(), clear_date, holidays, leave_dates)
    threshold = settings.bottleneck_threshold_days
    if days_out > threshold:
        return "red"
    if days_out > threshold * 0.7:
        return "orange"
    return "green"


def get_recipient_emails(db: Session, recipient_type: RecipientType) -> list[str]:
    rows = db.query(ReportRecipient).filter(ReportRecipient.recipient_type == recipient_type).all()
    return [r.email for r in rows]


def get_status_alert_emails(db: Session, developer_email: str) -> list[str]:
    configured = get_recipient_emails(db, RecipientType.STATUS_ALERT)
    return list(set(configured + [developer_email]))


def get_scheduled_report_emails(db: Session) -> list[str]:
    return get_recipient_emails(db, RecipientType.SCHEDULED_REPORT)


def build_timeline_table_html(tasks: list[Task], developer_name: str) -> str:
    rows = ""
    for t in sorted(tasks, key=lambda x: x.queue_order):
        rows += f"""
        <tr>
            <td>{t.queue_order}</td>
            <td>{t.title}</td>
            <td>{t.status.value}</td>
            <td>{t.effort_hours}h</td>
            <td>{t.start_date or '—'}</td>
            <td>{t.estimated_completion_date or '—'}</td>
        </tr>"""
    return f"""
    <h3>{developer_name} — Updated Timeline</h3>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%">
        <thead>
            <tr style="background:#1e293b;color:white">
                <th>#</th><th>Task</th><th>Status</th><th>Effort</th><th>Start</th><th>ECD</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


async def send_timeline_alert(
    db: Session,
    subject: str,
    change_description: str,
    developer: User,
    tasks: list[Task],
) -> None:
    from app.email_service import send_email

    recipients = get_status_alert_emails(db, developer.email)
    table = build_timeline_table_html(tasks, developer.name)
    body = f"""
    <html><body style="font-family:Arial,sans-serif">
        <h2>DevTrack Timeline Update</h2>
        <p><strong>Change:</strong> {change_description}</p>
        {table}
        <p style="color:#64748b;font-size:12px">Sent by Dynamic DevTrack</p>
    </body></html>"""

    await send_email(db, subject, recipients, body)
