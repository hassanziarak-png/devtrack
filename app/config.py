from pydantic import field_validator
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
    smtp_from_name: str = "DevTrack"
    brevo_api_key: str = ""
    email_enabled: bool = False

    @field_validator("email_enabled", mode="before")
    @classmethod
    def parse_bool(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    class Config:
        env_file = ".env"


settings = Settings()
settings.database_url = _fix_database_url(settings.database_url)
