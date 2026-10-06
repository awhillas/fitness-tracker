from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from app import config, security
from app.db import init_db
from app.routers import auth, health, home, weighings
from app.templating import templates

app = FastAPI(
    title=config.APP_NAME,
    middleware=[Middleware(SessionMiddleware, secret_key=config.SECRET_KEY)],
)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(home.router)
app.include_router(weighings.router)

init_db()


def wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or accept in ("", "*/*")


@app.exception_handler(security.Unauthenticated)
async def unauthenticated_handler(request: Request, exc: security.Unauthenticated):
    if request.headers.get("HX-Request") == "true":
        return JSONResponse(
            {"error": "unauthenticated"},
            status_code=401,
            headers={"HX-Redirect": "/login"},
        )
    if wants_html(request):
        return RedirectResponse(url="/login", status_code=303)
    return JSONResponse({"error": "unauthenticated"}, status_code=401)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and wants_html(request):
        return templates.TemplateResponse(
            request,
            "error.html",
            {"user": security.current_user(request), "status": 404, "detail": exc.detail},
            status_code=404,
        )
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
