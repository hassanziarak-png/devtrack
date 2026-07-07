"""Dynamic timeline engine: business-day scheduling with weekend, holiday, and leave skips."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from app.config import settings
from app.models import TaskStatus


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def is_business_day(
    d: date,
    holidays: set[date],
    leave_dates: set[date] | None = None,
) -> bool:
    if is_weekend(d) or d in holidays:
        return False
    if leave_dates and d in leave_dates:
        return False
    return True


def next_business_day(
    d: date,
    holidays: set[date],
    leave_dates: set[date] | None = None,
) -> date:
    current = d
    while not is_business_day(current, holidays, leave_dates):
        current += timedelta(days=1)
    return current


def add_business_days(
    start: date,
    business_days: int,
    holidays: set[date],
    leave_dates: set[date] | None = None,
) -> date:
    if business_days <= 0:
        return next_business_day(start, holidays, leave_dates)

    current = next_business_day(start, holidays, leave_dates)
    remaining = business_days - 1
    while remaining > 0:
        current += timedelta(days=1)
        if is_business_day(current, holidays, leave_dates):
            remaining -= 1
    return current


def hours_to_business_days(hours: float) -> int:
    if hours <= 0:
        return 0
    import math

    return max(1, math.ceil(hours / settings.hours_per_day))


def calculate_task_dates(
    start: date,
    effort_hours: float,
    holidays: set[date],
    leave_dates: set[date] | None = None,
) -> tuple[date, date]:
    task_start = next_business_day(start, holidays, leave_dates)
    days = hours_to_business_days(effort_hours)
    ecd = add_business_days(task_start, days, holidays, leave_dates)
    return task_start, ecd


def recalculate_developer_timeline(
    tasks: list,
    holidays: Iterable[date],
    anchor_date: date | None = None,
    leave_dates: set[date] | None = None,
) -> list[dict]:
    holiday_set = set(holidays)
    leaves = leave_dates or set()
    today = anchor_date or date.today()
    current_start = next_business_day(today, holiday_set, leaves)

    sorted_tasks = sorted(tasks, key=lambda t: t.queue_order)
    results: list[dict] = []

    for task in sorted_tasks:
        if task.status == TaskStatus.COMPLETED:
            if task.start_date and task.estimated_completion_date:
                current_start = task.estimated_completion_date
            continue

        start, ecd = calculate_task_dates(current_start, task.effort_hours, holiday_set, leaves)
        results.append(
            {
                "task_id": task.id,
                "start_date": start,
                "estimated_completion_date": ecd,
            }
        )
        current_start = ecd

    return results


def business_days_between(
    start: date,
    end: date,
    holidays: set[date],
    leave_dates: set[date] | None = None,
) -> int:
    if end < start:
        return 0
    count = 0
    current = start
    while current <= end:
        if is_business_day(current, holidays, leave_dates):
            count += 1
        current += timedelta(days=1)
    return count


def backlog_business_days(remaining_hours: float) -> int:
    return hours_to_business_days(remaining_hours)


def is_bottleneck(
    clear_date: date | None,
    holidays: set[date],
    threshold: int | None = None,
    leave_dates: set[date] | None = None,
) -> bool:
    if clear_date is None:
        return False
    threshold = threshold or settings.bottleneck_threshold_days
    today = date.today()
    days_out = business_days_between(today, clear_date, holidays, leave_dates)
    return days_out > threshold
