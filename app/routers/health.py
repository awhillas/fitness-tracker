from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import config
from app.db import connect

router = APIRouter()


@router.get("/healthz")
def healthz():
    try:
        conn = connect()
        conn.execute("SELECT 1").fetchone()
        weighings = conn.execute("SELECT COUNT(*) AS c FROM weighings").fetchone()["c"]
        conn.close()
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse(
            {"status": "degraded", "db": "error", "detail": str(exc)},
            status_code=503,
        )
    return {"status": "ok", "db": "ok", "db_path": str(config.DB_PATH), "weighings": weighings}
