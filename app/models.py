import enum
from datetime import date, datetime, timedelta

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    EXECUTIVE = "executive"
    MANAGER = "manager"
    DEVELOPER = "developer"


class PriorityWeight(str, enum.Enum):
    HIGH = "high"
    AVERAGE = "average"
    LOW = "low"


class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETED = "completed"


class ReportFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    OFF = "off"


class RecipientType(str, enum.Enum):
    STATUS_ALERT = "status_alert"
    SCHEDULED_REPORT = "scheduled_report"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.DEVELOPER)
    is_stakeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="assignee")
    leaves: Mapped[list["DeveloperLeave"]] = relationship("DeveloperLeave", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    priority_weight: Mapped[PriorityWeight] = mapped_column(
        Enum(PriorityWeight), default=PriorityWeight.AVERAGE
    )
    queue_order: Mapped[int] = mapped_column(Integer, default=1)
    effort_hours: Mapped[float] = mapped_column(Float, default=8.0)
    actual_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.BACKLOG)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    assignee: Mapped["User"] = relationship("User", back_populates="tasks")


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeveloperLeave(Base):
    __tablename__ = "developer_leaves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="leaves")


class ReportRecipient(Base):
    __tablename__ = "report_recipients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_type: Mapped[RecipientType] = mapped_column(Enum(RecipientType))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportSettings(Base):
    __tablename__ = "report_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    frequency: Mapped[ReportFrequency] = mapped_column(
        Enum(ReportFrequency), default=ReportFrequency.OFF
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject: Mapped[str] = mapped_column(String(500))
    recipients: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def expand_leave_dates(leaves: list[DeveloperLeave]) -> set[date]:
    dates: set[date] = set()
    for leave in leaves:
        current = leave.start_date
        while current <= leave.end_date:
            dates.add(current)
            current += timedelta(days=1)
    return dates
