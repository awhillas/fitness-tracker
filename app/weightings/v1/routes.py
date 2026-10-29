from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from app import config
from app.db import get_db
from app.dependencies import is_htmx, templates
from app.security.v1.services import require_user
from app.weightings.v1.aggregates import daily_series, weekly_series
from app.weightings.v1.services import (
    ValidationError,
    WeighingNotFound,
    create_weighing,
    delete_weighing,
    get_weighing,
    last_weight,
    list_weighings,
    update_weighing,
)

router = APIRouter()


@router.get("/")
def home(request: Request, session=Depends(get_db), user=Depends(require_user)):
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "user": user,
            "daily": daily_series(session, config.settings.daily_days),
            "weekly": weekly_series(session, config.settings.weekly_weeks),
            "last": last_weight(session),
        },
    )


@router.get("/weighings")
def list_weighings_route(
    request: Request,
    page: int = 1,
    session=Depends(get_db),
    user=Depends(require_user),
):
    rows, total, page, pages = list_weighings(session, page)
    context = {
        "user": user,
        "weighings": rows,
        "page": page,
        "pages": pages,
        "total": total,
        "page_size": config.settings.page_size,
    }
    if is_htmx(request):
        return templates.TemplateResponse(request, "partials/weighings_table.html", context)
    return templates.TemplateResponse(request, "weighings.html", context)


@router.get("/weighings/new")
def new_weighing(
    request: Request,
    session=Depends(get_db),
    user=Depends(require_user),
):
    return templates.TemplateResponse(
        request,
        "add_weight.html",
        {
            "user": user,
            "today": date.today().isoformat(),
            "weight": last_weight(session),
            "result": None,
        },
    )


@router.post("/weighings")
def create_weighing_route(
    request: Request,
    date_value: str = Form(...),
    weight_kg: str = Form(...),
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        day, weight = create_weighing(session, date_value, weight_kg)
    except ValidationError as exc:
        if is_htmx(request):
            return templates.TemplateResponse(
                request,
                "partials/add_result.html",
                {"user": user, "error": str(exc), "date": date_value, "weight_kg": weight_kg},
                status_code=400,
            )
        return templates.TemplateResponse(
            request,
            "add_weight.html",
            {
                "user": user,
                "error": str(exc),
                "today": date_value,
                "weight": weight_kg,
                "result": {"error": str(exc)},
            },
            status_code=400,
        )

    if is_htmx(request):
        return templates.TemplateResponse(
            request,
            "partials/add_result.html",
            {"user": user, "error": None, "date": day, "weight_kg": weight},
        )
    return RedirectResponse("/weighings", status_code=303)


@router.get("/weighings/{weighing_id}/edit")
def edit_form(
    request: Request,
    weighing_id: int,
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        weighing = get_weighing(session, weighing_id)
    except WeighingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "partials/edit_weighing.html",
        {"user": user, "w": weighing, "error": None, "date_value": None},
    )


@router.put("/weighings/{weighing_id}")
def update_weighing_route(
    request: Request,
    weighing_id: int,
    date_value: str = Form(...),
    weight_kg: str = Form(...),
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        weighing = update_weighing(session, weighing_id, date_value, weight_kg)
    except ValidationError as exc:
        try:
            weighing = get_weighing(session, weighing_id)
        except WeighingNotFound as not_found:
            raise HTTPException(status_code=404, detail=str(not_found)) from not_found
        return templates.TemplateResponse(
            request,
            "partials/edit_weighing.html",
            {"user": user, "w": weighing, "error": str(exc), "date_value": date_value},
            status_code=400,
        )
    except WeighingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "partials/weighing_row.html",
        {"user": user, "w": weighing},
    )


@router.delete("/weighings/{weighing_id}")
def delete_weighing_route(
    weighing_id: int,
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        delete_weighing(session, weighing_id)
    except WeighingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)
