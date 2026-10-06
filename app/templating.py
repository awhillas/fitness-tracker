from typing import Any

from fastapi.templating import Jinja2Templates

from app import config

templates = Jinja2Templates(directory=str(config.TEMPLATE_DIR))
globals_: dict[str, Any] = templates.env.globals
globals_["app_name"] = config.APP_NAME


def kg(value):
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.1f}"
    except TypeError, ValueError:
        return str(value)


templates.env.filters["kg"] = kg
