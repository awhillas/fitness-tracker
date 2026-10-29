from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.dates import parse_date_input
from app.weightings.v1.schema import Weighing
from app.weightings.v1.types import WeighingInput


class ValidationError(Exception):
    pass


class WeighingNotFound(Exception):
    pass


def parse_fields(date_value: str, weight_value: str) -> tuple[str, float]:
    try:
        parsed_date = parse_date_input(date_value)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    try:
        return WeighingInput(date_value=parsed_date, weight_kg=weight_value).values()
    except ValueError as exc:
        message = str(exc)
        if "date_value" in message or "valid date" in message:
            message = "Date must be in DD-MM-YYYY format."
        elif "weight_kg" in message and "input" in message:
            message = "Weight must be a number."
        else:
            message = "Weight must be between 0 and 500 kg."
        raise ValidationError(message) from exc


def get_weighing(session: Session, weighing_id: int) -> Weighing:
    weighing = session.get(Weighing, weighing_id)
    if weighing is None:
        raise WeighingNotFound("Weighing not found.")
    return weighing


def list_weighings(session: Session, page: int) -> tuple[list[Weighing], int, int, int]:
    total = session.scalar(select(func.count()).select_from(Weighing)) or 0
    pages = max(1, (total + config.settings.page_size - 1) // config.settings.page_size)
    page = max(1, min(page, pages))
    offset = (page - 1) * config.settings.page_size
    rows = list(
        session.scalars(
            select(Weighing)
            .order_by(Weighing.date.desc(), Weighing.id.desc())
            .limit(config.settings.page_size)
            .offset(offset)
        ).all()
    )
    return rows, total, page, pages


def last_weight(session: Session) -> float | None:
    return session.scalar(
        select(Weighing.weight_kg).order_by(Weighing.date.desc(), Weighing.id.desc()).limit(1)
    )


def create_weighing(session: Session, date_value: str, weight_value: str) -> tuple[str, float]:
    day, weight = parse_fields(date_value, weight_value)
    session.add(Weighing(date=day, weight_kg=weight))
    session.commit()
    return day, weight


def update_weighing(
    session: Session,
    weighing_id: int,
    date_value: str,
    weight_value: str,
) -> Weighing:
    day, weight = parse_fields(date_value, weight_value)
    weighing = get_weighing(session, weighing_id)
    weighing.date = day
    weighing.weight_kg = weight
    weighing.updated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    session.commit()
    return weighing


def delete_weighing(session: Session, weighing_id: int) -> None:
    weighing = get_weighing(session, weighing_id)
    session.delete(weighing)
    session.commit()
