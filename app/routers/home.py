from fastapi import APIRouter, Depends, Request

from app import config, security
from app.aggregates import daily_series, last_weight, weekly_series
from app.db import get_db
from app.templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, conn=Depends(get_db), user=Depends(security.require_user)):
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "user": user,
            "daily": daily_series(conn, config.DAILY_DAYS),
            "weekly": weekly_series(conn, config.WEEKLY_WEEKS),
            "last": last_weight(conn),
        },
    )
