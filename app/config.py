import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


APP_NAME = env("APP_NAME", "Fitness Tracker")
SECRET_KEY = env("SECRET_KEY", "dev-insecure-secret-change-me")

DB_PATH = Path(env("DB_PATH", str(BASE_DIR / "data" / "fitness.db")))
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

PAGE_SIZE = int(env("PAGE_SIZE", "30"))
DAILY_DAYS = int(env("DAILY_DAYS", "7"))
WEEKLY_WEEKS = int(env("WEEKLY_WEEKS", "8"))

# Single hard-coded user for now (see docs/todos.md).
USERNAME = env("USERNAME", "alex")
PASSWORD = env("PASSWORD", "changeme")
