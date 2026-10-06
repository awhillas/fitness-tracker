import sqlite3
from collections.abc import Iterator

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS weighings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_weighings_date ON weighings (date DESC);
"""


def connect(path=None) -> sqlite3.Connection:
    path = path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path=None) -> None:
    conn = connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
