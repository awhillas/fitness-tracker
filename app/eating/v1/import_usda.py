"""Import basic foods from the USDA FoodData Central Foundation Foods CSV archive."""

import argparse
import csv
import io
import json
import math
import re
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import make_session
from app.eating.v1.schema import Food
from app.eating.v1.types import NutrientDatum

FDC_RELEASE = "2026-04-30"
FDC_ARCHIVE_URL = (
    f"https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_{FDC_RELEASE}.zip"
)
FDC_ARCHIVE_NAME = f"fdc_foundation_foods_{FDC_RELEASE}.zip"
FDC_FOOD_URL = "https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients"

CATEGORY_NAMES = {
    "Dairy and Egg Products",
    "Beef Products",
    "Fruits and Fruit Juices",
    "Lamb, Veal, and Game Products",
    "Nut and Seed Products",
    "Pork Products",
    "Poultry Products",
    "Vegetables and Vegetable Products",
}

FRUIT_VEGETABLE_CATEGORIES = {
    "Fruits and Fruit Juices",
    "Vegetables and Vegetable Products",
}
MEAT_CATEGORIES = {
    "Beef Products",
    "Lamb, Veal, and Game Products",
    "Pork Products",
    "Poultry Products",
}
NUT_CATEGORY = "Nut and Seed Products"
EGG_CATEGORY = "Dairy and Egg Products"

CORE_NUTRIENT_PRIORITY: dict[str, tuple[str, ...]] = {
    "energy_kcal": ("1008", "2048", "2047", "1062"),
    "protein_g": ("1003",),
    "total_fat_g": ("1004",),
    "saturated_fat_g": ("1258",),
    "trans_fat_g": ("1257",),
    "carbohydrate_g": ("1005", "1050", "2039"),
    "sugars_g": ("2000", "1063"),
    "dietary_fibre_g": ("1079", "2033"),
    "sodium_g": ("1093",),
}
CORE_NUTRIENT_IDS = {nutrient_id for ids in CORE_NUTRIENT_PRIORITY.values() for nutrient_id in ids}


@dataclass(frozen=True)
class ImportedFood:
    fdc_id: str
    name: str
    source_url: str
    energy_kcal: float
    protein_g: float
    total_fat_g: float | None
    saturated_fat_g: float | None
    trans_fat_g: float | None
    carbohydrate_g: float | None
    sugars_g: float | None
    dietary_fibre_g: float | None
    sodium_g: float | None
    nutrients_json: str


@dataclass(frozen=True)
class ImportCounts:
    inserted: int
    updated: int


def _csv_member(archive: zipfile.ZipFile, filename: str):
    member = next(
        (name for name in archive.namelist() if name.rsplit("/", maxsplit=1)[-1] == filename),
        None,
    )
    if member is None:
        raise ValueError(f"USDA archive is missing {filename}.")
    with archive.open(member) as data:
        yield from csv.DictReader(io.TextIOWrapper(data, encoding="utf-8-sig", newline=""))


def _contains_word(text: str, *words: str) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def _is_ingredient_food(name: str, category: str) -> bool:
    description = name.casefold()
    if (
        _contains_word(
            description,
            "breaded",
            "canned",
            "juice",
            "pickle",
            "pickles",
            "puree",
            "sauce",
            "restaurant",
        )
        or "onion rings" in description
    ):
        return False
    if category == EGG_CATEGORY:
        return description.startswith("egg") and not _contains_word(description, "dried", "frozen")
    if category in MEAT_CATEGORIES:
        return _contains_word(description, "raw")
    if category == NUT_CATEGORY:
        return not _contains_word(description, "butter", "oil", "milk", "flour", "powder")
    if category in FRUIT_VEGETABLE_CATEGORIES:
        return not _contains_word(description, "cooked", "boiled", "fried", "grilled", "roasted")
    return category in FRUIT_VEGETABLE_CATEGORIES or category == EGG_CATEGORY


def _source_foods(archive: zipfile.ZipFile) -> tuple[dict[str, str], int]:
    categories = {
        row["id"]: row["description"] for row in _csv_member(archive, "food_category.csv")
    }
    selected: dict[str, str] = {}
    candidate_count = 0
    for row in _csv_member(archive, "food.csv"):
        if row["data_type"] != "foundation_food":
            continue
        category = categories.get(row["food_category_id"], "")
        name = row["description"].strip()
        if category not in CATEGORY_NAMES or not _is_ingredient_food(name, category):
            continue
        candidate_count += 1
        selected[row["fdc_id"]] = name
    return selected, candidate_count


def _normalized_nutrient(amount: float, source_unit: str, raw: str) -> NutrientDatum:
    unit = source_unit.strip().casefold()
    value = amount
    if unit in {"mg", "milligram", "milligrams"}:
        value /= 1_000
        unit = "g"
    elif unit in {"ug", "µg", "μg", "mcg"}:
        value /= 1_000_000
        unit = "g"
    elif unit in {"kj", "kilojoule", "kilojoules"}:
        value /= 4.184
        unit = "kcal"
    elif unit in {"g", "gram", "grams"}:
        unit = "g"
    elif unit in {"kcal", "calorie", "calories"}:
        unit = "kcal"
    if not math.isfinite(value):
        return {"value": None, "unit": unit, "raw": raw}
    return {"value": value, "unit": unit, "raw": raw}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def parse_foundation_archive(archive: zipfile.ZipFile) -> tuple[list[ImportedFood], int, int]:
    selected, candidate_count = _source_foods(archive)
    nutrient_definitions = {row["id"]: row for row in _csv_member(archive, "nutrient.csv")}
    nutrient_rows: dict[str, dict[str, tuple[float, str, str]]] = defaultdict(dict)
    for row in _csv_member(archive, "food_nutrient.csv"):
        fdc_id = row["fdc_id"]
        nutrient_id = row["nutrient_id"]
        if fdc_id not in selected or nutrient_id not in nutrient_definitions:
            continue
        amount_text = row["amount"].strip()
        if not amount_text:
            continue
        try:
            amount = float(amount_text)
        except ValueError:
            continue
        if not math.isfinite(amount) or amount < 0:
            continue
        definition = nutrient_definitions[nutrient_id]
        unit = definition["unit_name"]
        raw = f"{amount_text} {unit} per 100 g (USDA FoodData Central)"
        nutrient_rows[fdc_id].setdefault(nutrient_id, (amount, unit, raw))

    foods: list[ImportedFood] = []
    skipped = 0
    for fdc_id, name in selected.items():
        source_values = nutrient_rows.get(fdc_id, {})
        normalized: dict[str, NutrientDatum] = {}
        values: dict[str, float | None] = {}
        chosen_ids: set[str] = set()
        for field, priority_ids in CORE_NUTRIENT_PRIORITY.items():
            selected_id = next((item for item in priority_ids if item in source_values), None)
            if selected_id is None:
                values[field] = None
                continue
            amount, unit, raw = source_values[selected_id]
            datum = _normalized_nutrient(amount, unit, raw)
            values[field] = datum["value"]
            normalized[field] = datum
            chosen_ids.add(selected_id)

        energy_kcal = values.get("energy_kcal")
        protein_g = values.get("protein_g")
        if energy_kcal is None or protein_g is None:
            skipped += 1
            continue

        for nutrient_id, (amount, unit, raw) in source_values.items():
            if nutrient_id in chosen_ids:
                continue
            definition = nutrient_definitions[nutrient_id]
            key = _slug(definition["name"])
            if not key:
                continue
            if key in normalized:
                key = f"{key}_{nutrient_id}"
            normalized[key] = _normalized_nutrient(amount, unit, raw)

        foods.append(
            ImportedFood(
                fdc_id=fdc_id,
                name=name,
                source_url=FDC_FOOD_URL.format(fdc_id=fdc_id),
                energy_kcal=energy_kcal,
                protein_g=protein_g,
                total_fat_g=values.get("total_fat_g"),
                saturated_fat_g=values.get("saturated_fat_g"),
                trans_fat_g=values.get("trans_fat_g"),
                carbohydrate_g=values.get("carbohydrate_g"),
                sugars_g=values.get("sugars_g"),
                dietary_fibre_g=values.get("dietary_fibre_g"),
                sodium_g=values.get("sodium_g"),
                nutrients_json=json.dumps(normalized, sort_keys=True),
            )
        )
    return foods, candidate_count, skipped


def import_foods(session: Session, foods: list[ImportedFood]) -> ImportCounts:
    source_urls = [food.source_url for food in foods]
    existing = (
        {
            row.source_url: row
            for row in session.scalars(select(Food).where(Food.source_url.in_(source_urls))).all()
        }
        if source_urls
        else {}
    )
    inserted = 0
    updated = 0

    for imported in foods:
        row = existing.get(imported.source_url)
        if row is None:
            row = Food(source_type="natural", source_url=imported.source_url)
            session.add(row)
            inserted += 1
        else:
            updated += 1
        row.name = imported.name
        row.brand = None
        row.basis_unit = "g"
        row.energy_kcal = imported.energy_kcal
        row.protein_g = imported.protein_g
        row.total_fat_g = imported.total_fat_g
        row.saturated_fat_g = imported.saturated_fat_g
        row.trans_fat_g = imported.trans_fat_g
        row.carbohydrate_g = imported.carbohydrate_g
        row.sugars_g = imported.sugars_g
        row.dietary_fibre_g = imported.dietary_fibre_g
        row.sodium_g = imported.sodium_g
        row.salt_g = None
        row.nutrients_json = imported.nutrients_json

    session.commit()
    return ImportCounts(inserted=inserted, updated=updated)


def download_archive(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(FDC_ARCHIVE_URL, headers={"User-Agent": "fitness-tracker"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    temporary.replace(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an existing USDA FDC Foundation CSV zip")
    parser.add_argument(
        "--dry-run", action="store_true", help="Parse and report without writing foods"
    )
    parser.add_argument("--limit", type=int, help="Only process the first N importable foods")
    args = parser.parse_args()

    archive_path = args.archive or settings.db_path.parent / "imports" / FDC_ARCHIVE_NAME
    if not archive_path.is_file():
        print(f"Downloading USDA FoodData Central Foundation Foods {FDC_RELEASE}…")
        download_archive(archive_path)

    with zipfile.ZipFile(archive_path) as archive:
        foods, candidate_count, skipped = parse_foundation_archive(archive)
    if args.limit is not None:
        foods = foods[: max(0, args.limit)]

    print(
        f"Selected {len(foods)} foods from {candidate_count} Foundation Foods "
        "in the target categories; "
        f"skipped {skipped} without energy/protein."
    )
    for food in foods[:10]:
        print(
            f"  {food.name} — {food.energy_kcal:.1f} kcal, {food.protein_g:.1f} g protein per 100 g"
        )
    if args.dry_run:
        print("Dry run: no food rows written.")
        return

    with make_session() as session:
        result = import_foods(session, foods)
    print(f"Food database updated: {result.inserted} inserted, {result.updated} updated.")


if __name__ == "__main__":
    main()
