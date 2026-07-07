import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Task, TaskStatus, User


def generate_department_pdf(
    developers: list[User],
    tasks_by_dev: dict[int, list[Task]],
    generated_at: date,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#1e293b"),
    )
    elements = [
        Paragraph("Dynamic DevTrack — Department Workload Report", title_style),
        Paragraph(f"Generated: {generated_at.isoformat()}", styles["Normal"]),
        Spacer(1, 0.25 * inch),
    ]

    for dev in developers:
        tasks = sorted(tasks_by_dev.get(dev.id, []), key=lambda t: t.queue_order)
        remaining = sum(t.effort_hours for t in tasks if t.status != TaskStatus.COMPLETED)
        clear = max(
            (t.estimated_completion_date for t in tasks if t.estimated_completion_date),
            default=None,
        )
        elements.append(
            Paragraph(
                f"<b>{dev.name}</b> — Remaining: {remaining}h | Clear Date: {clear or 'N/A'}",
                styles["Heading2"],
            )
        )
        if tasks:
            data = [["#", "Task", "Status", "Hours", "Start", "ECD"]]
            for t in tasks:
                data.append(
                    [
                        str(t.queue_order),
                        t.title[:40],
                        t.status.value,
                        f"{t.effort_hours}h",
                        str(t.start_date or "—"),
                        str(t.estimated_completion_date or "—"),
                    ]
                )
            table = Table(data, colWidths=[0.4 * inch, 2.5 * inch, 1 * inch, 0.7 * inch, 1 * inch, 1 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ]
                )
            )
            elements.append(table)
        else:
            elements.append(Paragraph("No tasks assigned.", styles["Italic"]))
        elements.append(Spacer(1, 0.2 * inch))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
