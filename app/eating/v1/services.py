import json
from datetime import date

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dates import parse_date_input, today
from app.eating.v1.schema import EatingTarget, Food
from app.eating.v1.types import FoodInput, NutrientDatum, ScrapedProduct, TargetInput


class EatingValidationError(Exception):
    pass


class TargetNotFound(Exception):
    pass


class DuplicateTargetDate(Exception):
    pass


class FoodNotFound(Exception):
    pass


def parse_target(start_date: str, kcal_target: str, protein_target_g: str) -> TargetInput:
    try:
        parsed_start_date = parse_date_input(start_date)
    except ValueError as exc:
        raise EatingValidationError(
            "Start date must be a valid date in DD-MM-YYYY format."
        ) from exc

    try:
        return TargetInput(
            start_date=parsed_start_date,
            kcal_target=kcal_target,
            protein_target_g=protein_target_g,
        )
    except PydanticValidationError as exc:
        field = exc.errors()[0]["loc"][0]
        if field == "start_date":
            message = "Start date must be in DD-MM-YYYY format."
        else:
            message = "Calorie and protein targets must be positive numbers."
        raise EatingValidationError(message) from exc


def current_target(
    session: Session, username: str, on_date: date | None = None
) -> EatingTarget | None:
    on_date = on_date or today()
    return session.scalar(
        select(EatingTarget)
        .where(EatingTarget.username == username, EatingTarget.start_date <= on_date.isoformat())
        .order_by(EatingTarget.start_date.desc())
        .limit(1)
    )


def list_targets(session: Session, username: str) -> list[EatingTarget]:
    return list(
        session.scalars(
            select(EatingTarget)
            .where(EatingTarget.username == username)
            .order_by(EatingTarget.start_date.desc(), EatingTarget.id.desc())
        ).all()
    )


def get_target(session: Session, username: str, target_id: int) -> EatingTarget:
    target = session.scalar(
        select(EatingTarget).where(
            EatingTarget.username == username,
            EatingTarget.id == target_id,
        )
    )
    if target is None:
        raise TargetNotFound("Target not found.")
    return target


def _duplicate_target_error(exc: IntegrityError) -> DuplicateTargetDate | None:
    if "UNIQUE constraint failed" in str(exc.orig):
        return DuplicateTargetDate("A target already exists for that start date.")
    return None


def create_target(session: Session, username: str, target: TargetInput) -> None:
    session.add(
        EatingTarget(
            username=username,
            start_date=target.start_date.isoformat(),
            kcal_target=target.kcal_target,
            protein_target_g=target.protein_target_g,
        )
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        duplicate_error = _duplicate_target_error(exc)
        if duplicate_error:
            raise duplicate_error from exc
        raise


def update_target(
    session: Session,
    username: str,
    target_id: int,
    target: TargetInput,
) -> None:
    existing = get_target(session, username, target_id)
    existing.start_date = target.start_date.isoformat()
    existing.kcal_target = target.kcal_target
    existing.protein_target_g = target.protein_target_g
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        duplicate_error = _duplicate_target_error(exc)
        if duplicate_error:
            raise duplicate_error from exc
        raise


def delete_target(session: Session, username: str, target_id: int) -> None:
    session.delete(get_target(session, username, target_id))
    session.commit()


def parse_food(fields: dict[str, str]) -> FoodInput:
    values: dict[str, str | None] = {key: value.strip() or None for key, value in fields.items()}
    try:
        return FoodInput.model_validate(values)
    except PydanticValidationError as exc:
        raise EatingValidationError(
            "Enter a name, energy, protein, and valid non-negative nutrient values."
        ) from exc


def _manual_nutrients(food: FoodInput) -> dict[str, NutrientDatum]:
    fields = {
        "energy_kcal": (food.energy_kcal, "kcal"),
        "protein_g": (food.protein_g, "g"),
        "total_fat_g": (food.total_fat_g, "g"),
        "saturated_fat_g": (food.saturated_fat_g, "g"),
        "trans_fat_g": (food.trans_fat_g, "g"),
        "carbohydrate_g": (food.carbohydrate_g, "g"),
        "sugars_g": (food.sugars_g, "g"),
        "dietary_fibre_g": (food.dietary_fibre_g, "g"),
        "sodium_g": (food.sodium_g, "g"),
        "salt_g": (food.salt_g, "g"),
    }
    return {
        key: {"value": value, "unit": unit, "raw": f"{value} {unit}"}
        for key, (value, unit) in fields.items()
        if value is not None
    }


def create_natural_food(session: Session, food: FoodInput) -> int:
    if food.energy_kcal is None or food.protein_g is None:
        raise EatingValidationError("Energy and protein values are required.")
    row = Food(
        name=food.name.strip(),
        brand=food.brand.strip() if food.brand else None,
        source_type="natural",
        basis_unit=food.basis_unit,
        energy_kcal=food.energy_kcal,
        protein_g=food.protein_g,
        total_fat_g=food.total_fat_g,
        saturated_fat_g=food.saturated_fat_g,
        trans_fat_g=food.trans_fat_g,
        carbohydrate_g=food.carbohydrate_g,
        sugars_g=food.sugars_g,
        dietary_fibre_g=food.dietary_fibre_g,
        sodium_g=food.sodium_g,
        salt_g=food.salt_g,
        nutrients_json=json.dumps(_manual_nutrients(food), sort_keys=True),
    )
    session.add(row)
    session.commit()
    return row.id


def save_scraped_product(session: Session, product: ScrapedProduct) -> int:
    if product.energy_kcal is None or product.protein_g is None:
        raise EatingValidationError("The product must include energy and protein values.")
    row = session.scalar(select(Food).where(Food.source_url == product.source_url))
    if row is None:
        row = Food(source_type="product", source_url=product.source_url)
        session.add(row)
    row.name = product.name
    row.basis_unit = product.basis_unit
    row.energy_kcal = product.energy_kcal
    row.protein_g = product.protein_g
    row.total_fat_g = product.total_fat_g
    row.saturated_fat_g = product.saturated_fat_g
    row.trans_fat_g = product.trans_fat_g
    row.carbohydrate_g = product.carbohydrate_g
    row.sugars_g = product.sugars_g
    row.dietary_fibre_g = product.dietary_fibre_g
    row.sodium_g = product.sodium_g
    row.salt_g = product.salt_g
    row.nutrients_json = json.dumps(product.nutrients, sort_keys=True)
    session.commit()
    return row.id


def list_foods(session: Session, query: str = "") -> list[Food]:
    statement = select(Food)
    if query:
        pattern = f"%{query}%"
        statement = statement.where(or_(Food.name.ilike(pattern), Food.brand.ilike(pattern)))
    return list(session.scalars(statement.order_by(func.lower(Food.name))).all())


def get_food(session: Session, food_id: int) -> Food:
    food = session.get(Food, food_id)
    if food is None:
        raise FoodNotFound("Food not found.")
    return food
