from pydantic_settings import BaseSettings


def _fix_database_url(url: str) -> str:
    """Render provides postgres:// but SQLAlchemy needs postgresql://"""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Settings(BaseSettings):
    app_name: str = "Dynamic DevTrack"
    secret_key: str = "devtrack-secret-change-in-production"
    database_url: str = "sqlite:///./devtrack.db"
    hours_per_day: int = 8
    bottleneck_threshold_days: int = 30
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "devtrack@localhost"
    email_enabled: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
settings.database_url = _fix_database_url(settings.database_url)
