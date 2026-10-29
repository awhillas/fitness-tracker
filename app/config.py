from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    base_dir: Path = Path(__file__).resolve().parent.parent
    template_dir: Path = Path(__file__).resolve().parent / "templates"
    static_dir: Path = Path(__file__).resolve().parent.parent / "static"
    app_name: str = "Fitness Tracker"
    secret_key: str = "dev-insecure-secret-change-me"
    db_path: Path = Path(__file__).resolve().parent.parent / "data" / "fitness.db"
    page_size: int = 30
    daily_days: int = 7
    weekly_weeks: int = 8
    locale: str = "en_AU"
    date_format: str = "dd-MM-yyyy"
    username: str = "alex"
    password: str = "changeme"
    log_level: str = "INFO"
    obscura_cdp_url: str = "ws://127.0.0.1:3000/devtools/browser"


settings = Settings()
