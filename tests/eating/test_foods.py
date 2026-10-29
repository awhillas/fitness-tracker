from app.db import connect
from app.eating.v1.types import ScrapedProduct
from tests.eating.support import login


def test_natural_food_can_be_added_and_browsed(client):
    """Natural foods can be stored per 100 grams and viewed in the catalog and detail page."""
    login(client)
    response = client.post(
        "/eating/foods",
        data={
            "name": "Pear",
            "basis_unit": "g",
            "energy_kcal": "57",
            "protein_g": "0.4",
            "total_fat_g": "0.1",
            "carbohydrate_g": "15.2",
            "sugars_g": "9.8",
            "dietary_fibre_g": "3.1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    detail = client.get(response.headers["location"])
    assert detail.status_code == 200
    assert "Pear" in detail.text
    assert "57.0 kcal" in detail.text
    assert "0.4 g" in detail.text
    assert "per 100 g" in detail.text
    assert "Pear" in client.get("/eating/foods?q=pea").text


def test_scraped_product_import_is_idempotent(client, monkeypatch):
    """Importing the same product URL updates its existing food row rather than duplicating it."""
    login(client)
    product = ScrapedProduct(
        name="Unsweetened Soy Milk",
        source_url="https://www.woolworths.co.nz/shop/product-details/soy-milk",
        basis_unit="ml",
        energy_kcal=33,
        protein_g=3.3,
        nutrients={
            "energy_kcal": {"value": 33, "unit": "kcal", "raw": "138 kJ (33 kcal)"},
            "protein_g": {"value": 3.3, "unit": "g", "raw": "3.3 g"},
        },
    )
    monkeypatch.setattr("app.eating.v1.routes.scraper.scrape_product", lambda _url: product)
    source_url = "https://www.woolworths.co.nz/shop/product-details/soy-milk"

    first = client.post(
        "/eating/foods/import", data={"source_url": source_url}, follow_redirects=False
    )
    second = client.post(
        "/eating/foods/import", data={"source_url": source_url}, follow_redirects=False
    )

    assert first.status_code == second.status_code == 303
    assert first.headers["location"] == second.headers["location"]
    conn = connect()
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM foods WHERE source_url = ?", (source_url,)
    ).fetchone()["c"]
    conn.close()
    assert count == 1
