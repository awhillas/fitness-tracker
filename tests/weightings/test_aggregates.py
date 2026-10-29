from datetime import date, timedelta

from app.dates import today as app_today
from app.db import connect, make_session
from app.weightings.v1.aggregates import daily_series, iso_week, weekly_series


def test_aggregates(client):
    """Daily and weekly series aggregate all readings across their date windows."""
    today = app_today()
    conn = connect()
    for offset in range(10):
        day = today - timedelta(days=offset)
        conn.execute(
            "INSERT INTO weighings (date, weight_kg) VALUES (?, ?)", (day.isoformat(), 70.0)
        )
        conn.execute(
            "INSERT INTO weighings (date, weight_kg) VALUES (?, ?)", (day.isoformat(), 72.0)
        )
    conn.commit()
    conn.close()

    session = make_session()
    daily = daily_series(session, days=7)
    weekly = weekly_series(session, weeks=8)
    session.close()

    assert len(daily) == 7
    assert all(day["value"] == 71.0 for day in daily)
    assert len(weekly) == 8
    assert sum(week["count"] for week in weekly) == 20
    assert all(week["mean"] == 71.0 for week in weekly if week["count"])
    assert any(week["std"] is not None for week in weekly)


def test_weekly_series_uses_sample_standard_deviation(client):
    """Weekly variation uses the sample standard deviation for two readings."""
    today = app_today()
    conn = connect()
    conn.execute("INSERT INTO weighings (date, weight_kg) VALUES (?, ?)", (today.isoformat(), 70.0))
    conn.execute("INSERT INTO weighings (date, weight_kg) VALUES (?, ?)", (today.isoformat(), 72.0))
    conn.commit()
    conn.close()

    current_week = iso_week(today)
    session = make_session()
    current = next(
        item
        for item in weekly_series(session, weeks=8)
        if (item["year"], item["week"]) == current_week
    )
    session.close()

    assert current["count"] == 2
    assert current["std"] == 1.41


def test_app_today_uses_configured_timezone(monkeypatch):
    """App "today" follows the configured timezone rather than the server clock."""
    from datetime import UTC, datetime

    from app import config, dates

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 28, 20, 0, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(dates, "datetime", FrozenDatetime)
    monkeypatch.setattr(config.settings, "timezone", "Pacific/Auckland")
    assert dates.today() == date(2026, 10, 29)
    monkeypatch.setattr(config.settings, "timezone", "UTC")
    assert dates.today() == date(2026, 10, 28)
