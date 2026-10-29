from app.db import connect, init_db


def test_alembic_migration_adopts_legacy_weighings(tmp_path):
    """Alembic preserves a pre-existing weighing table while adding eating tables."""
    database_path = tmp_path / "legacy.db"
    conn = connect(database_path)
    conn.executescript(
        """
        CREATE TABLE weighings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT
        );
        INSERT INTO weighings (date, weight_kg) VALUES ('2026-10-01', 73.5);
        """
    )
    conn.commit()
    conn.close()

    init_db(database_path)

    conn = connect(database_path)
    weighing = conn.execute("SELECT date, weight_kg FROM weighings").fetchone()
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    conn.close()

    assert weighing["date"] == "2026-10-01"
    assert weighing["weight_kg"] == 73.5
    assert {"alembic_version", "eating_targets", "foods", "weighings"} <= tables
