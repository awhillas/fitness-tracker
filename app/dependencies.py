from datetime import date, datetime
from typing import Any

from babel.dates import format_date
from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import config
from app.dates import parse_date_input

TEMPLATE_DIRS = [
    config.settings.template_dir,
    config.settings.base_dir / "app" / "security" / "v1" / "templates",
    config.settings.base_dir / "app" / "weightings" / "v1" / "templates",
    config.settings.base_dir / "app" / "eating" / "v1" / "templates",
]
templates = Jinja2Templates(directory=[str(path) for path in TEMPLATE_DIRS])
globals_: dict[str, Any] = templates.env.globals
globals_["app_name"] = config.settings.app_name
globals_["html_lang"] = config.settings.locale.replace("_", "-")


def kg(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.1f}"
    except TypeError, ValueError:
        return str(value)


templates.env.filters["kg"] = kg


def localised_date(value: date | datetime | str | None) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return value
    return format_date(
        value,
        format=config.settings.date_format,
        locale=config.settings.locale,
    )


templates.env.filters["date"] = localised_date


def iso_date_input(value: date | datetime | str | None) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return parse_date_input(value).isoformat()
    except ValueError:
        return ""


templates.env.filters["iso_date"] = iso_date_input


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or accept in ("", "*/*")
