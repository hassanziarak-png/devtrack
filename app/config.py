from pydantic_settings import BaseSettings


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
