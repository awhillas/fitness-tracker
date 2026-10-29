import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app import config

AU_DATE_PATTERN = re.compile(r"[0-9]{2}-[0-9]{2}-[0-9]{4}")
ISO_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def parse_date_input(value: str) -> date:
    value = value.strip()
    try:
        if AU_DATE_PATTERN.fullmatch(value):
            day, month, year = (int(part) for part in value.split("-"))
            return date(year, month, day)
        if ISO_DATE_PATTERN.fullmatch(value):
            return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Date must be a valid date in DD-MM-YYYY format.") from exc
    raise ValueError("Date must be in DD-MM-YYYY format.")


def today() -> date:
    """Current date in the configured app timezone, not the server's (often UTC)."""
    return datetime.now(ZoneInfo(config.settings.timezone)).date()
