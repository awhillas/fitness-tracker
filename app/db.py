import sqlite3
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import settings


class Base(DeclarativeBase):
    pass


def configure_sqlite_engine(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache(maxsize=8)
def engine_for_path(path: str) -> Engine:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"check_same_thread": False},
    )

    configure_sqlite_engine(engine)
    return engine


def make_session(path: Path | None = None) -> Session:
    database_path = path or settings.db_path
    return Session(engine_for_path(str(database_path)), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with make_session() as session:
        yield session


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open a low-level SQLite connection for scripts and compatibility tests."""
    database_path = path or settings.db_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: Path | None = None) -> None:
    """Apply Alembic migrations to the configured database (primarily used by tests)."""
    previous_path = settings.db_path
    if path is not None:
        settings.db_path = path
    try:
        alembic_config = Config(str(settings.base_dir / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(settings.base_dir / "migrations"))
        alembic_config.set_main_option("prepend_sys_path", str(settings.base_dir))
        command.upgrade(alembic_config, "head")
    finally:
        settings.db_path = previous_path
