import re
from typing import Literal, cast
from urllib.parse import unquote, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from pydantic import ValidationError as PydanticValidationError

from app import config
from app.eating.v1.types import NutrientDatum, ScrapedProduct

WOOLWORTHS_HOST = "www.woolworths.co.nz"
PRODUCT_PATH_PREFIX = "/shop/product-details/"
PRODUCT_URL_PREFIX = f"https://{WOOLWORTHS_HOST}{PRODUCT_PATH_PREFIX}"
PRODUCT_NAME_CLASS_PREFIX = "price-panel_productName"
NUTRITION_TABLE_CLASS_PREFIX = "table_core-"


class ScraperError(Exception):
    pass


class InvalidProductUrl(ScraperError):
    pass


class ProductPageError(ScraperError):
    pass


_PER_100_RE = re.compile(r"(?:per\s*)?100\s*(ml|g)\b", re.IGNORECASE)
_VALUE_RE = re.compile(
    r"(?P<operator>[<>~])?\s*"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit>kcal|cal|kj|mcg|µg|μg|ug|mg|ml|g)\b",
    re.IGNORECASE,
)

_NUTRIENT_FIELDS = {
    "energy": "energy_kcal",
    "protein": "protein_g",
    "proteins": "protein_g",
    "fat": "total_fat_g",
    "total fat": "total_fat_g",
    "fat total": "total_fat_g",
    "saturated": "saturated_fat_g",
    "saturated fat": "saturated_fat_g",
    "saturates": "saturated_fat_g",
    "trans fat": "trans_fat_g",
    "carbohydrate": "carbohydrate_g",
    "carbohydrates": "carbohydrate_g",
    "sugars": "sugars_g",
    "total sugars": "sugars_g",
    "fibre": "dietary_fibre_g",
    "fiber": "dietary_fibre_g",
    "dietary fibre": "dietary_fibre_g",
    "dietary fiber": "dietary_fibre_g",
    "fibre dietary": "dietary_fibre_g",
    "fiber dietary": "dietary_fibre_g",
    "sodium": "sodium_g",
    "salt": "salt_g",
}


def canonical_product_url(url: str) -> str:
    candidate = url.strip()
    if not candidate.startswith(PRODUCT_URL_PREFIX):
        raise InvalidProductUrl("Only Woolworths NZ product-details URLs can be imported.")
    try:
        parts = urlsplit(candidate)
        hostname = (parts.hostname or "").lower()
        decoded_path = unquote(parts.path)
        valid = (
            parts.scheme.lower() == "https"
            and hostname == WOOLWORTHS_HOST
            and parts.port in (None, 443)
            and parts.username is None
            and parts.password is None
            and decoded_path.startswith(PRODUCT_PATH_PREFIX)
            and len(parts.path) > len(PRODUCT_PATH_PREFIX)
            and not any(segment in {".", ".."} for segment in decoded_path.split("/"))
        )
    except ValueError as exc:
        raise InvalidProductUrl("Enter a Woolworths NZ product-details URL.") from exc
    if not valid:
        raise InvalidProductUrl("Only Woolworths NZ product-details URLs can be imported.")
    return urlunsplit(("https", WOOLWORTHS_HOST, parts.path, "", ""))


def _nutrient_key(label: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", "", label).strip().casefold()
    cleaned = re.sub(r"^[^a-z0-9]+", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned).strip()
    known = _NUTRIENT_FIELDS.get(cleaned)
    if known:
        return known
    slug = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return slug


def _normalised_value(raw: str, nutrient_key: str) -> NutrientDatum:
    matches = list(_VALUE_RE.finditer(raw))
    energy_matches = [
        match for match in matches if match.group("unit").casefold() in {"kcal", "cal"}
    ]
    match = (energy_matches or matches)[0] if matches else None
    standard_unit = "kcal" if nutrient_key == "energy_kcal" else "g"

    if match is None:
        return {"value": None, "unit": standard_unit, "raw": raw.strip()}

    unit = match.group("unit").casefold()
    value = float(match.group("number").replace(",", ""))
    operator = match.group("operator")
    if operator == "<":
        value = None
    elif nutrient_key == "energy_kcal":
        if unit == "kj":
            value /= 4.184
        elif unit == "cal":
            value /= 1000
        unit = "kcal"
    elif unit in {"mg", "mcg", "µg", "μg", "ug"}:
        value /= 1_000_000 if unit in {"mcg", "µg", "μg", "ug"} else 1_000
        unit = "g"
    elif unit == "ml":
        standard_unit = "ml"
        unit = "ml"

    return {"value": value, "unit": unit, "raw": raw.strip()}


def _basis_unit(header_text: str, product_name: str) -> str:
    units = [match.group(1).lower() for match in _PER_100_RE.finditer(header_text)]
    if "g" in units and "ml" in units:
        volume_pack = re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:ml|l|litres?|liters?)\b",
            product_name,
            re.IGNORECASE,
        )
        return "ml" if volume_pack else "g"
    return units[0] if units else "g"


def _nutrition_column(table: Tag, product_name: str) -> tuple[int, int, str]:
    rows = table.find_all("tr")
    for row_index, row in enumerate(rows):
        cells = row.find_all(["th", "td"], recursive=False)
        for column_index, cell in enumerate(cells):
            header_text = cell.get_text(" ", strip=True)
            if _PER_100_RE.search(header_text):
                return row_index, max(column_index, 1), _basis_unit(header_text, product_name)

    table_text = table.get_text(" ", strip=True)
    if _PER_100_RE.search(table_text):
        return -1, 1, _basis_unit(table_text, product_name)
    raise ProductPageError("The nutrition table has no per-100g or per-100ml column.")


def parse_product_html(html: str, source_url: str) -> ScrapedProduct:
    canonical_url = canonical_product_url(source_url)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    name_element = soup.select_one(f'h1[class^="{PRODUCT_NAME_CLASS_PREFIX}"]')
    table = soup.select_one(f'table[class^="{NUTRITION_TABLE_CLASS_PREFIX}"]')
    if not isinstance(name_element, Tag) or not name_element.get_text(" ", strip=True):
        raise ProductPageError("Could not find the product name on this page.")
    if not isinstance(table, Tag):
        raise ProductPageError("Could not find the Woolworths nutrition table on this page.")

    product_name = name_element.get_text(" ", strip=True)
    header_row, value_column, basis_unit = _nutrition_column(table, product_name)
    nutrients: dict[str, NutrientDatum] = {}
    for row_index, row in enumerate(table.find_all("tr")):
        if row_index <= header_row:
            continue
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) <= value_column:
            continue
        label = cells[0].get_text(" ", strip=True)
        if not label:
            continue
        key = _nutrient_key(label)
        if not key:
            continue
        nutrients[key] = _normalised_value(cells[value_column].get_text(" ", strip=True), key)

    if not nutrients:
        raise ProductPageError("No nutrient values were found in the nutrition table.")

    core = {
        "energy_kcal",
        "protein_g",
        "total_fat_g",
        "saturated_fat_g",
        "trans_fat_g",
        "carbohydrate_g",
        "sugars_g",
        "dietary_fibre_g",
        "sodium_g",
        "salt_g",
    }
    values = {key: datum["value"] for key, datum in nutrients.items() if key in core}
    if values.get("energy_kcal") is None or values.get("protein_g") is None:
        raise ProductPageError("The nutrition table must include energy and protein values.")
    try:
        return ScrapedProduct(
            name=product_name,
            source_url=canonical_url,
            basis_unit=cast(Literal["g", "ml"], basis_unit),
            nutrients=nutrients,
            **values,
        )
    except PydanticValidationError as exc:
        raise ProductPageError("The product contains invalid or incomplete nutrient data.") from exc


def fetch_product_html(url: str, cdp_url: str | None = None) -> tuple[str, str]:
    canonical_url = canonical_product_url(url)
    endpoint = cdp_url or config.settings.obscura_cdp_url
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint, timeout=15_000)
            page = None
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.new_page()
                page.goto(canonical_url, wait_until="domcontentloaded", timeout=30_000)
                final_url = canonical_product_url(page.url)
                try:
                    page.wait_for_selector(
                        f'table[class^="{NUTRITION_TABLE_CLASS_PREFIX}"]',
                        state="attached",
                        timeout=20_000,
                    )
                except PlaywrightTimeoutError as exc:
                    raise ProductPageError(
                        "The Woolworths nutrition table did not load on this product page."
                    ) from exc
                return page.content(), final_url
            finally:
                if page is not None:
                    page.close()
                browser.close()
    except ScraperError:
        raise
    except PlaywrightError as exc:
        raise ProductPageError(
            "Could not load this product through Obscura. Check that its CDP server is running."
        ) from exc


def scrape_product(url: str, cdp_url: str | None = None) -> ScrapedProduct:
    html, final_url = fetch_product_html(url, cdp_url)
    return parse_product_html(html, final_url)
