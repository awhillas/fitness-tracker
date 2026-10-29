from datetime import date
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field


class WeighingInput(BaseModel):
    date_value: date
    weight_kg: Annotated[float, Field(gt=0, lt=500, allow_inf_nan=False)]

    def values(self) -> tuple[str, float]:
        return self.date_value.isoformat(), round(self.weight_kg, 2)


class DailySeriesItem(TypedDict):
    date: str
    value: float | None
    count: int


class WeeklySeriesItem(TypedDict):
    year: int
    week: int
    label: str
    mean: float | None
    std: float | None
    count: int
