from datetime import date
from typing import Annotated, Literal, Self, TypedDict

from pydantic import BaseModel, Field, model_validator

PositiveValue = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegativeValue = Annotated[float | None, Field(ge=0, allow_inf_nan=False)]


class TargetInput(BaseModel):
    start_date: date
    kcal_target: PositiveValue
    protein_target_g: PositiveValue


class FoodInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=120)
    basis_unit: Literal["g", "ml"]
    energy_kcal: NonNegativeValue = None
    protein_g: NonNegativeValue = None
    total_fat_g: NonNegativeValue = None
    saturated_fat_g: NonNegativeValue = None
    trans_fat_g: NonNegativeValue = None
    carbohydrate_g: NonNegativeValue = None
    sugars_g: NonNegativeValue = None
    dietary_fibre_g: NonNegativeValue = None
    sodium_g: NonNegativeValue = None
    salt_g: NonNegativeValue = None

    @model_validator(mode="after")
    def require_calories_and_protein(self) -> Self:
        if self.energy_kcal is None or self.protein_g is None:
            raise ValueError("Energy and protein values are required.")
        return self


class NutrientDatum(TypedDict):
    value: float | None
    unit: str
    raw: str


class ScrapedProduct(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_url: str
    basis_unit: Literal["g", "ml"]
    energy_kcal: NonNegativeValue = None
    protein_g: NonNegativeValue = None
    total_fat_g: NonNegativeValue = None
    saturated_fat_g: NonNegativeValue = None
    trans_fat_g: NonNegativeValue = None
    carbohydrate_g: NonNegativeValue = None
    sugars_g: NonNegativeValue = None
    dietary_fibre_g: NonNegativeValue = None
    sodium_g: NonNegativeValue = None
    salt_g: NonNegativeValue = None
    nutrients: dict[str, NutrientDatum]

    @model_validator(mode="after")
    def require_calories_and_protein(self) -> Self:
        if self.energy_kcal is None or self.protein_g is None:
            raise ValueError("The product must include energy and protein values.")
        return self
