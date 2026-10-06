import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, stdev


def iso_week(day: date) -> tuple[int, int]:
    year, week, _ = day.isocalendar()
    return year, week


def daily_series(conn: sqlite3.Connection, days: int = 7, today: date | None = None) -> list[dict]:
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    rows = conn.execute(
        "SELECT date, weight_kg FROM weighings WHERE date >= ? ORDER BY date",
        (start.isoformat(),),
    ).fetchall()

    buckets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        buckets[row["date"]].append(row["weight_kg"])

    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        values = buckets.get(day.isoformat(), [])
        series.append(
            {
                "date": day.isoformat(),
                "value": round(mean(values), 2) if values else None,
                "count": len(values),
            }
        )
    return series


def weekly_series(
    conn: sqlite3.Connection, weeks: int = 8, today: date | None = None
) -> list[dict]:
    today = today or date.today()
    rows = conn.execute("SELECT date, weight_kg FROM weighings").fetchall()

    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        buckets[iso_week(date.fromisoformat(row["date"]))].append(row["weight_kg"])

    keys: list[tuple[int, int]] = []
    day = today
    while len(keys) < weeks:
        key = iso_week(day)
        if key not in keys:
            keys.append(key)
        day -= timedelta(days=1)

    series = []
    for key in sorted(keys):
        values = buckets.get(key, [])
        series.append(
            {
                "year": key[0],
                "week": key[1],
                "label": f"{key[0]}-W{key[1]:02d}",
                "mean": round(mean(values), 2) if values else None,
                "std": round(stdev(values), 2) if len(values) > 1 else None,
                "count": len(values),
            }
        )
    return series


def last_weight(conn: sqlite3.Connection) -> float | None:
    row = conn.execute(
        "SELECT weight_kg FROM weighings ORDER BY date DESC, id DESC LIMIT 1"
    ).fetchone()
    return row["weight_kg"] if row else None
