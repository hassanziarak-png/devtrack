"""Seed database with demo users and tasks."""

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    Holiday,
    PriorityWeight,
    RecipientType,
    ReportRecipient,
    ReportSettings,
    Task,
    TaskStatus,
    User,
    UserRole,
)
from app.services.task_service import recalculate_assignee_timeline


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(User).count() > 0:
        print("Database already seeded.")
        db.close()
        return

    users = [
        User(
            email="manager@devtrack.local",
            name="Alex Manager",
            hashed_password=hash_password("manager123"),
            role=UserRole.MANAGER,
        ),
        User(
            email="exec@devtrack.local",
            name="Sam Executive",
            hashed_password=hash_password("exec123"),
            role=UserRole.EXECUTIVE,
            is_stakeholder=True,
        ),
        User(
            email="dev1@devtrack.local",
            name="Jordan Dev",
            hashed_password=hash_password("dev123"),
            role=UserRole.DEVELOPER,
        ),
        User(
            email="dev2@devtrack.local",
            name="Casey Dev",
            hashed_password=hash_password("dev123"),
            role=UserRole.DEVELOPER,
        ),
        User(
            email="dev3@devtrack.local",
            name="Riley Dev",
            hashed_password=hash_password("dev123"),
            role=UserRole.DEVELOPER,
        ),
    ]
    db.add_all(users)
    db.commit()

    dev1, dev2, dev3 = (
        db.query(User).filter(User.role == UserRole.DEVELOPER).order_by(User.id).all()
    )

    tasks = [
        Task(title="Auth module refactor", description="Migrate to OAuth2", assignee_id=dev1.id, priority_weight=PriorityWeight.HIGH, queue_order=1, effort_hours=24, status=TaskStatus.IN_PROGRESS),
        Task(title="API rate limiting", assignee_id=dev1.id, priority_weight=PriorityWeight.AVERAGE, queue_order=2, effort_hours=16, status=TaskStatus.TODO),
        Task(title="Dashboard widgets", assignee_id=dev1.id, priority_weight=PriorityWeight.LOW, queue_order=3, effort_hours=40, status=TaskStatus.BACKLOG),
        Task(title="Payment integration", assignee_id=dev2.id, priority_weight=PriorityWeight.HIGH, queue_order=1, effort_hours=32, status=TaskStatus.IN_PROGRESS),
        Task(title="Email templates", assignee_id=dev2.id, priority_weight=PriorityWeight.AVERAGE, queue_order=2, effort_hours=8, status=TaskStatus.TODO),
        Task(title="Mobile responsive fixes", assignee_id=dev3.id, priority_weight=PriorityWeight.HIGH, queue_order=1, effort_hours=20, status=TaskStatus.TESTING),
        Task(title="Performance audit", assignee_id=dev3.id, priority_weight=PriorityWeight.AVERAGE, queue_order=2, effort_hours=24, status=TaskStatus.BACKLOG),
        Task(title="Documentation update", assignee_id=dev3.id, priority_weight=PriorityWeight.LOW, queue_order=3, effort_hours=16, status=TaskStatus.BACKLOG),
    ]
    db.add_all(tasks)
    db.add(ReportSettings())
    db.add(Holiday(name="New Year", date=__import__("datetime").date(2026, 1, 1)))
    db.add(ReportRecipient(email="exec@devtrack.local", name="Sam Executive", recipient_type=RecipientType.STATUS_ALERT))
    db.add(ReportRecipient(email="exec@devtrack.local", name="Sam Executive", recipient_type=RecipientType.SCHEDULED_REPORT))
    db.commit()

    for dev in [dev1, dev2, dev3]:
        recalculate_assignee_timeline(db, dev.id)

    db.close()
    print("Database seeded successfully!")
    print("Login: manager@devtrack.local / manager123")


if __name__ == "__main__":
    seed()
