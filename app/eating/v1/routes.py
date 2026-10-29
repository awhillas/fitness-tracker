import json
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.dates import parse_date_input
from app.db import get_db
from app.dependencies import templates
from app.eating.v1 import scraper, services
from app.eating.v1.services import (
    DuplicateTargetDate,
    EatingValidationError,
    FoodNotFound,
    TargetNotFound,
)
from app.security.v1.services import require_user

router = APIRouter(prefix="/eating")


def _target_context(session, username: str, error: str | None = None) -> dict[str, object]:
    return {
        "user": username,
        "targets": services.list_targets(session, username),
        "error": error,
        "today": date.today().isoformat(),
    }


def _foods_context(session, query: str = "", error: str | None = None) -> dict[str, object]:
    return {
        "foods": services.list_foods(session, query),
        "query": query,
        "error": error,
    }


@router.get("")
def report(
    request: Request,
    day: str | None = None,
    session=Depends(get_db),
    user=Depends(require_user),
):
    error = None
    try:
        report_day = parse_date_input(day) if day else date.today()
    except ValueError:
        report_day = date.today()
        error = "Report date must be a valid date in DD-MM-YYYY format."
    target = services.current_target(session, user, report_day)
    consumed_kcal = 0.0
    consumed_protein_g = 0.0
    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "user": user,
            "day": report_day.isoformat(),
            "day_value": report_day.isoformat(),
            "error": error,
            "target": target,
            "consumed_kcal": consumed_kcal,
            "consumed_protein_g": consumed_protein_g,
            "remaining_kcal": max(0.0, target.kcal_target - consumed_kcal) if target else None,
            "remaining_protein_g": (
                max(0.0, target.protein_target_g - consumed_protein_g) if target else None
            ),
        },
    )


@router.get("/targets")
def target_history(
    request: Request,
    session=Depends(get_db),
    user=Depends(require_user),
):
    return templates.TemplateResponse(request, "targets.html", _target_context(session, user))


@router.post("/targets")
def create_target_route(
    request: Request,
    start_date: str = Form(...),
    kcal_target: str = Form(...),
    protein_target_g: str = Form(...),
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        target = services.parse_target(start_date, kcal_target, protein_target_g)
        services.create_target(session, user, target)
    except (EatingValidationError, DuplicateTargetDate) as exc:
        context = _target_context(session, user, str(exc))
        context["form"] = {
            "start_date": start_date,
            "kcal_target": kcal_target,
            "protein_target_g": protein_target_g,
        }
        return templates.TemplateResponse(request, "targets.html", context, status_code=400)
    return RedirectResponse("/eating/targets", status_code=303)


@router.get("/targets/{target_id}/edit")
def edit_target_form(
    request: Request,
    target_id: int,
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        target = services.get_target(session, user, target_id)
    except TargetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "target_edit.html",
        {"user": user, "target": target, "error": None},
    )


@router.post("/targets/{target_id}/edit")
def update_target_route(
    request: Request,
    target_id: int,
    start_date: str = Form(...),
    kcal_target: str = Form(...),
    protein_target_g: str = Form(...),
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        target = services.parse_target(start_date, kcal_target, protein_target_g)
        services.update_target(session, user, target_id, target)
    except (EatingValidationError, DuplicateTargetDate) as exc:
        try:
            services.get_target(session, user, target_id)
        except TargetNotFound as not_found:
            raise HTTPException(status_code=404, detail=str(not_found)) from not_found
        form_target = {
            "id": target_id,
            "start_date": start_date,
            "kcal_target": kcal_target,
            "protein_target_g": protein_target_g,
        }
        return templates.TemplateResponse(
            request,
            "target_edit.html",
            {"user": user, "target": form_target, "error": str(exc)},
            status_code=400,
        )
    except TargetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse("/eating/targets", status_code=303)


@router.post("/targets/{target_id}/delete")
def delete_target_route(
    target_id: int,
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        services.delete_target(session, user, target_id)
    except TargetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse("/eating/targets", status_code=303)


@router.get("/foods")
def food_list(
    request: Request,
    q: str = "",
    session=Depends(get_db),
    user=Depends(require_user),
):
    return templates.TemplateResponse(
        request,
        "foods.html",
        {"user": user, **_foods_context(session, q)},
    )


@router.get("/foods/new")
def new_food_form(
    request: Request,
    user=Depends(require_user),
):
    return templates.TemplateResponse(
        request,
        "food_form.html",
        {"user": user, "error": None, "food": {"basis_unit": "g"}},
    )


@router.post("/foods")
def create_natural_food_route(
    request: Request,
    name: str = Form(...),
    brand: str = Form(""),
    basis_unit: str = Form("g"),
    energy_kcal: str = Form(""),
    protein_g: str = Form(""),
    total_fat_g: str = Form(""),
    saturated_fat_g: str = Form(""),
    trans_fat_g: str = Form(""),
    carbohydrate_g: str = Form(""),
    sugars_g: str = Form(""),
    dietary_fibre_g: str = Form(""),
    sodium_g: str = Form(""),
    salt_g: str = Form(""),
    session=Depends(get_db),
    user=Depends(require_user),
):
    fields = {
        "name": name,
        "brand": brand,
        "basis_unit": basis_unit,
        "energy_kcal": energy_kcal,
        "protein_g": protein_g,
        "total_fat_g": total_fat_g,
        "saturated_fat_g": saturated_fat_g,
        "trans_fat_g": trans_fat_g,
        "carbohydrate_g": carbohydrate_g,
        "sugars_g": sugars_g,
        "dietary_fibre_g": dietary_fibre_g,
        "sodium_g": sodium_g,
        "salt_g": salt_g,
    }
    try:
        food = services.parse_food(fields)
    except EatingValidationError as exc:
        return templates.TemplateResponse(
            request,
            "food_form.html",
            {"user": user, "error": str(exc), "food": fields},
            status_code=400,
        )
    food_id = services.create_natural_food(session, food)
    return RedirectResponse(f"/eating/foods/{food_id}", status_code=303)


@router.post("/foods/import")
def import_product_route(
    request: Request,
    source_url: str = Form(...),
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        product = scraper.scrape_product(source_url)
    except scraper.InvalidProductUrl as exc:
        return templates.TemplateResponse(
            request,
            "foods.html",
            {"user": user, **_foods_context(session, error=str(exc)), "source_url": source_url},
            status_code=400,
        )
    except scraper.ScraperError as exc:
        return templates.TemplateResponse(
            request,
            "foods.html",
            {"user": user, **_foods_context(session, error=str(exc)), "source_url": source_url},
            status_code=502,
        )
    food_id = services.save_scraped_product(session, product)
    return RedirectResponse(f"/eating/foods/{food_id}", status_code=303)


@router.get("/foods/{food_id}")
def food_detail(
    request: Request,
    food_id: int,
    session=Depends(get_db),
    user=Depends(require_user),
):
    try:
        food = services.get_food(session, food_id)
    except FoodNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    nutrients = json.loads(food.nutrients_json)
    return templates.TemplateResponse(
        request,
        "food_detail.html",
        {"user": user, "food": food, "nutrients": nutrients},
    )
