from pathlib import Path

import pytest

from app.eating.v1.scraper import (
    InvalidProductUrl,
    canonical_product_url,
    parse_product_html,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.woolworths.co.nz/shop/product-details/milk",
        "https://woolworths.co.nz/shop/product-details/milk",
        "https://www.woolworths.co.nz/shop/product-details.evil/milk",
        "https://www.woolworths.co.nz.evil.test/shop/product-details/milk",
        "https://example.com/shop/product-details/milk",
    ],
)
def test_scraper_rejects_urls_outside_the_allowlist(url):
    """Only HTTPS Woolworths NZ product-detail pages are accepted by the scraper."""
    with pytest.raises(InvalidProductUrl):
        canonical_product_url(url)


def test_product_parser_strips_scripts_and_normalizes_nutrients():
    """The HTML parser removes script markup and converts table values to standard units."""
    html = """
    <html><body>
      <script>document.write('<h1>Not a product</h1>')</script>
      <h1 class="price-panel_productName-heading">Barista Soy Milk</h1>
      <table class="table_core-nutrition">
        <thead><tr><th>Nutrient</th><th>Average per 100 ml</th><th>Per serving</th></tr></thead>
        <tbody>
          <tr><th>Energy</th><td>138 kJ (33 kcal)</td><td>345 kJ</td></tr>
          <tr><th>Protein</th><td>3.3 g</td><td>8.2 g</td></tr>
          <tr><th>Total fat</th><td>1.8 g</td><td>4.5 g</td></tr>
          <tr><th>Sodium</th><td>45 mg</td><td>112 mg</td></tr>
          <tr><th>Calcium</th><td>120 mg</td><td>300 mg</td></tr>
        </tbody>
      </table>
    </body></html>
    """
    product = parse_product_html(
        html,
        "https://www.woolworths.co.nz/shop/product-details/barista-soy-milk?source=test#nutrition",
    )

    assert product.name == "Barista Soy Milk"
    assert product.basis_unit == "ml"
    assert product.source_url.endswith("/barista-soy-milk")
    assert product.energy_kcal == 33
    assert product.protein_g == 3.3
    assert product.sodium_g == 0.045
    assert product.nutrients["calcium"]["value"] == 0.12
    assert product.nutrients["calcium"]["unit"] == "g"


def test_scraper_normalizes_allowed_urls_for_storage():
    """Product URL query parameters and fragments are excluded from the stored canonical URL."""
    assert (
        canonical_product_url(
            "https://www.woolworths.co.nz/shop/product-details/milk?utm_source=x#nutrition"
        )
        == "https://www.woolworths.co.nz/shop/product-details/milk"
    )


def test_live_woolworths_product_capture_parses():
    """The captured Woolworths product markup parses its name and live nutrient labels."""
    fixture_path = Path(__file__).parents[1] / "data" / "woolworths_spaghetti_product.html"
    html = fixture_path.read_text(encoding="utf-8")
    product = parse_product_html(
        html,
        "https://www.woolworths.co.nz/shop/product-details/912755/"
        "woolworths-spaghetti-shortstrand-410g",
    )

    assert product.name == "Woolworths Spaghetti Shortstrand 410g"
    assert product.source_url.endswith("/912755/woolworths-spaghetti-shortstrand-410g")
    assert product.basis_unit == "g"
    assert product.energy_kcal == pytest.approx(253 / 4.184)
    assert product.protein_g == 1.5
    assert product.total_fat_g is None
    assert product.saturated_fat_g == 0.1
    assert product.carbohydrate_g == 12.5
    assert product.sugars_g == 4.8
    assert product.dietary_fibre_g == 0.9
    assert product.sodium_g == 0.22
    assert product.nutrients["total_fat_g"]["raw"] == "< 1.0g"


def test_vitasoy_product_capture_uses_millilitres_for_liquid_pack():
    """The Vitasoy live-page capture infers a 100 ml basis from its one-litre pack name."""
    fixture_path = Path(__file__).parents[1] / "data" / "woolworths_vitasoy_protein_plus.html"
    product = parse_product_html(
        fixture_path.read_text(encoding="utf-8"),
        "https://www.woolworths.co.nz/shop/product-details/564472/vitasoy-protein-plus-soy-milk",
    )

    assert product.name == "Vitasoy Protein Plus Soy Milk 1L Carton"
    assert product.basis_unit == "ml"
    assert product.energy_kcal == pytest.approx(225 / 4.184)
    assert product.protein_g == 4.2
    assert product.sodium_g == 0.04
