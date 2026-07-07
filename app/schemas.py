from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import PriorityWeight, RecipientType, ReportFrequency, TaskStatus, UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: str
    name: str
    password: str = Field(min_length=6)
    role: UserRole = UserRole.DEVELOPER
    phone: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(default=None, min_length=6)
    is_active: Optional[bool] = None


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: int
    priority_weight: PriorityWeight = PriorityWeight.AVERAGE
    effort_hours: float = Field(default=8.0, gt=0)
    status: TaskStatus = TaskStatus.BACKLOG
    queue_order: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority_weight: Optional[PriorityWeight] = None
    effort_hours: Optional[float] = Field(default=None, gt=0)
    actual_hours: Optional[float] = Field(default=None, ge=0)
    status: Optional[TaskStatus] = None
    queue_order: Optional[int] = None


class TaskReorderItem(BaseModel):
    task_id: int
    queue_order: int


class TaskReorderRequest(BaseModel):
    assignee_id: int
    tasks: list[TaskReorderItem]


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignee_id: int
    assignee_name: str
    priority_weight: PriorityWeight
    queue_order: int
    effort_hours: float
    actual_hours: Optional[float]
    status: TaskStatus
    start_date: Optional[date]
    estimated_completion_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    estimation_variance: Optional[float] = None

    class Config:
        from_attributes = True


class DeveloperSummary(BaseModel):
    id: int
    name: str
    email: str
    active_task: Optional[TaskOut]
    remaining_hours: float
    clear_date: Optional[date]
    bottleneck: bool
    bottleneck_level: str
    on_leave: bool = False
    tasks: list[TaskOut]


class HolidayCreate(BaseModel):
    name: str
    date: date


class HolidayOut(BaseModel):
    id: int
    name: str
    date: date

    class Config:
        from_attributes = True


class LeaveCreate(BaseModel):
    user_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None
    notes: Optional[str] = None


class LeaveUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class LeaveOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    start_date: date
    end_date: date
    reason: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportSettingsUpdate(BaseModel):
    frequency: ReportFrequency


class ReportSettingsOut(BaseModel):
    frequency: ReportFrequency

    class Config:
        from_attributes = True


class ReportRecipientCreate(BaseModel):
    email: str
    name: Optional[str] = None
    recipient_type: RecipientType


class ReportRecipientOut(BaseModel):
    id: int
    email: str
    name: Optional[str]
    recipient_type: RecipientType
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    subject: str
    recipients: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True
