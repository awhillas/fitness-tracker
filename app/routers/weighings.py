from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from app import config, security
from app.aggregates import last_weight
from app.db import get_db
from app.templating import templates

router = APIRouter(prefix="/weighings")


class ValidationError(Exception):
    pass


def parse_fields(date_value: str, weight_value: str) -> tuple[str, float]:
    try:
        day = date.fromisoformat(date_value)
    except ValueError as exc:
        raise ValidationError("Date must be in YYYY-MM-DD format.") from exc
    try:
        weight = float(weight_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Weight must be a number.") from exc
    if not 0 < weight < 500:
        raise ValidationError("Weight must be between 0 and 500 kg.")
    return day.isoformat(), round(weight, 2)


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def get_weighing(conn, weighing_id: int):
    row = conn.execute(
        "SELECT id, date, weight_kg, created_at, updated_at FROM weighings WHERE id = ?",
        (weighing_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Weighing not found.")
    return row


@router.get("")
def list_weighings(
    request: Request,
    page: int = 1,
    conn=Depends(get_db),
    user=Depends(security.require_user),
):
    total = conn.execute("SELECT COUNT(*) AS c FROM weighings").fetchone()["c"]
    pages = max(1, (total + config.PAGE_SIZE - 1) // config.PAGE_SIZE)
    page = max(1, min(page, pages))
    offset = (page - 1) * config.PAGE_SIZE
    rows = conn.execute(
        "SELECT id, date, weight_kg, created_at, updated_at FROM weighings "
        "ORDER BY date DESC, id DESC LIMIT ? OFFSET ?",
        (config.PAGE_SIZE, offset),
    ).fetchall()

    context = {
        "user": user,
        "weighings": rows,
        "page": page,
        "pages": pages,
        "total": total,
        "page_size": config.PAGE_SIZE,
    }
    if is_htmx(request):
        return templates.TemplateResponse(request, "partials/weighings_table.html", context)
    return templates.TemplateResponse(request, "weighings.html", context)


@router.get("/new")
def new_weighing(
    request: Request,
    conn=Depends(get_db),
    user=Depends(security.require_user),
):
    return templates.TemplateResponse(
        request,
        "add_weight.html",
        {
            "user": user,
            "today": date.today().isoformat(),
            "weight": last_weight(conn),
            "result": None,
        },
    )


@router.post("")
def create_weighing(
    request: Request,
    date_value: str = Form(...),
    weight_kg: str = Form(...),
    conn=Depends(get_db),
    user=Depends(security.require_user),
):
    try:
        day, weight = parse_fields(date_value, weight_kg)
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
                "today": date_value,
                "weight": weight_kg,
                "result": {"error": str(exc)},
            },
            status_code=400,
        )

    conn.execute("INSERT INTO weighings (date, weight_kg) VALUES (?, ?)", (day, weight))
    conn.commit()

    if is_htmx(request):
        return templates.TemplateResponse(
            request,
            "partials/add_result.html",
            {"user": user, "error": None, "date": day, "weight_kg": weight},
        )
    return RedirectResponse("/weighings", status_code=303)


@router.get("/{weighing_id}/edit")
def edit_form(
    request: Request,
    weighing_id: int,
    conn=Depends(get_db),
    user=Depends(security.require_user),
):
    return templates.TemplateResponse(
        request,
        "partials/edit_weighing.html",
        {"user": user, "w": get_weighing(conn, weighing_id), "error": None},
    )


@router.put("/{weighing_id}")
def update_weighing(
    request: Request,
    weighing_id: int,
    date_value: str = Form(...),
    weight_kg: str = Form(...),
    conn=Depends(get_db),
    user=Depends(security.require_user),
):
    try:
        day, weight = parse_fields(date_value, weight_kg)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "partials/edit_weighing.html",
            {"user": user, "w": get_weighing(conn, weighing_id), "error": str(exc)},
            status_code=400,
        )

    conn.execute(
        "UPDATE weighings SET date = ?, weight_kg = ?, updated_at = datetime('now') WHERE id = ?",
        (day, weight, weighing_id),
    )
    conn.commit()
    return templates.TemplateResponse(
        request,
        "partials/weighing_row.html",
        {"user": user, "w": get_weighing(conn, weighing_id)},
    )


@router.delete("/{weighing_id}")
def delete_weighing(
    request: Request,
    weighing_id: int,
    conn=Depends(get_db),
    user=Depends(security.require_user),
):
    get_weighing(conn, weighing_id)
    conn.execute("DELETE FROM weighings WHERE id = ?", (weighing_id,))
    conn.commit()
    return Response(status_code=204)
