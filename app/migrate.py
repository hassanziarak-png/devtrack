"""Lightweight SQLite migrations for schema additions."""

from sqlalchemy import inspect, text

from app.database import engine


USER_COLUMNS = {
    "phone": "VARCHAR(50)",
    "department": "VARCHAR(255)",
    "bio": "TEXT",
    "is_active": "BOOLEAN DEFAULT 1",
    "updated_at": "DATETIME",
}


def run_migrations() -> None:
    from app.database import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("users")}
        with engine.begin() as conn:
            for col, col_type in USER_COLUMNS.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
