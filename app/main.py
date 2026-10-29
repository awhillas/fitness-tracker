from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.dependencies import templates, wants_html
from app.eating.v1.routes import router as eating_router
from app.health.routes import router as health_router
from app.logging_config import configure_logging
from app.security.v1.routes import router as security_router
from app.security.v1.services import Unauthenticated, current_user
from app.weightings.v1.routes import router as weightings_router

configure_logging(config.settings.log_level)

app = FastAPI(
    title=config.settings.app_name,
    middleware=[Middleware(SessionMiddleware, secret_key=config.settings.secret_key)],
)
app.mount("/static", StaticFiles(directory=str(config.settings.static_dir)), name="static")

app.include_router(health_router)
app.include_router(security_router)
app.include_router(weightings_router)
app.include_router(eating_router)


@app.exception_handler(Unauthenticated)
async def unauthenticated_handler(request: Request, exc: Unauthenticated):
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
            "404.html",
            {"user": current_user(request), "status": 404, "detail": exc.detail},
            status_code=404,
        )
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
