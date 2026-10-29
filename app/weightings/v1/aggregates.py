from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, stdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.weightings.v1.schema import Weighing
from app.weightings.v1.types import DailySeriesItem, WeeklySeriesItem


def iso_week(day: date) -> tuple[int, int]:
    year, week, _ = day.isocalendar()
    return year, week


def daily_series(
    session: Session, days: int = 7, today: date | None = None
) -> list[DailySeriesItem]:
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    rows = session.execute(
        select(Weighing.date, Weighing.weight_kg)
        .where(Weighing.date >= start.isoformat())
        .order_by(Weighing.date)
    ).all()

    buckets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        buckets[row.date].append(row.weight_kg)

    series: list[DailySeriesItem] = []
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
    session: Session, weeks: int = 8, today: date | None = None
) -> list[WeeklySeriesItem]:
    today = today or date.today()
    rows = session.execute(select(Weighing.date, Weighing.weight_kg)).all()

    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        buckets[iso_week(date.fromisoformat(row.date))].append(row.weight_kg)

    keys: list[tuple[int, int]] = []
    day = today
    while len(keys) < weeks:
        key = iso_week(day)
        if key not in keys:
            keys.append(key)
        day -= timedelta(days=1)

    series: list[WeeklySeriesItem] = []
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
