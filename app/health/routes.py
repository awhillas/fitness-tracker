from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.weightings.v1.schema import Weighing

router = APIRouter()


@router.get("/healthz", response_model=None)
def healthz(session: Session = Depends(get_db)) -> dict[str, str | int] | JSONResponse:
    try:
        session.execute(select(1))
        weighings = session.scalar(select(func.count()).select_from(Weighing)) or 0
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse(
            {"status": "degraded", "db": "error", "detail": str(exc)},
            status_code=503,
        )
    return {
        "status": "ok",
        "db": "ok",
        "db_path": str(config.settings.db_path),
        "weighings": weighings,
    }
