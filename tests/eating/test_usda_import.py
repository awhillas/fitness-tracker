import io
import json
import zipfile

from sqlalchemy import select

from app.db import make_session
from app.eating.v1.import_usda import import_foods, parse_foundation_archive
from app.eating.v1.schema import Food


def _foundation_archive() -> zipfile.ZipFile:
    files = {
        "food_category.csv": (
            "id,description\n"
            "1,Vegetables and Vegetable Products\n"
            "2,Dairy and Egg Products\n"
            "3,Fruits and Fruit Juices\n"
        ),
        "food.csv": (
            "fdc_id,data_type,description,food_category_id,publication_date\n"
            "101,foundation_food,Broccoli raw,1,2026-04-30\n"
            "102,foundation_food,Egg whole raw,2,2026-04-30\n"
            "103,foundation_food,Milk whole,2,2026-04-30\n"
            "104,sample_food,Apple raw,3,2026-04-30\n"
            "105,foundation_food,Apple raw,3,2026-04-30\n"
            "106,foundation_food,Carrots canned,1,2026-04-30\n"
            "107,foundation_food,Carrots cooked,1,2026-04-30\n"
        ),
        "nutrient.csv": (
            "id,name,unit_name,nutrient_nbr,rank\n"
            "1008,Energy,KCAL,208,300\n"
            "1003,Protein,G,203,600\n"
            "1004,Total lipid (fat),G,204,800\n"
            "1093,Sodium MG,MG,307,5800\n"
            "1162,Vitamin C,MG,401,6300\n"
        ),
        "food_nutrient.csv": (
            "id,fdc_id,nutrient_id,amount\n"
            "1,101,1008,34\n"
            "2,101,1003,2.8\n"
            "3,101,1004,0.4\n"
            "4,101,1093,33\n"
            "5,101,1162,89.2\n"
            "6,102,1008,143\n"
            "7,102,1003,12.6\n"
            "8,105,1008,52\n"
            "9,105,1003,0.3\n"
        ),
    }
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        for filename, contents in files.items():
            archive.writestr(f"foundation/{filename}", contents)
    archive_buffer.seek(0)
    return zipfile.ZipFile(archive_buffer)


def test_usda_archive_filters_categories_and_normalizes_nutrients():
    """The USDA importer selects foundation produce and eggs and converts nutrient mass to grams."""
    with _foundation_archive() as archive:
        foods, candidates, skipped = parse_foundation_archive(archive)

    assert candidates == 3
    assert skipped == 0
    assert {food.name for food in foods} == {"Broccoli raw", "Egg whole raw", "Apple raw"}
    broccoli = next(food for food in foods if food.name == "Broccoli raw")
    nutrients = json.loads(broccoli.nutrients_json)
    assert broccoli.source_url == "https://fdc.nal.usda.gov/food-details/101/nutrients"
    assert broccoli.energy_kcal == 34
    assert broccoli.protein_g == 2.8
    assert broccoli.sodium_g == 0.033
    assert nutrients["vitamin_c"]["value"] == 0.0892
    assert nutrients["vitamin_c"]["unit"] == "g"


def test_usda_food_import_is_idempotent(client):
    """Repeated USDA imports update matching FDC URLs rather than creating duplicate foods."""
    with _foundation_archive() as archive:
        foods, _, _ = parse_foundation_archive(archive)

    session = make_session()
    first = import_foods(session, foods)
    second = import_foods(session, foods)
    count = len(session.scalars(select(Food).where(Food.source_url.is_not(None))).all())
    session.close()

    assert first.inserted == 3
    assert first.updated == 0
    assert second.inserted == 0
    assert second.updated == 3
    assert count == 3
