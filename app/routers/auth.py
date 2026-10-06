from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app import security
from app.templating import templates

router = APIRouter()


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if security.check_login(username, password):
        request.session["user"] = username
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password."},
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
