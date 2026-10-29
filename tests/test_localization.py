from datetime import date

import pytest

from app.dates import parse_date_input
from app.dependencies import iso_date_input, localised_date


def test_localised_date_formats_iso_and_date_values_for_australia():
    assert localised_date("2026-01-09") == "09-01-2026"
    assert localised_date(date(2026, 10, 12)) == "12-10-2026"


def test_parse_date_input_accepts_australian_and_iso_formats():
    assert parse_date_input("09-01-2026") == date(2026, 1, 9)
    assert parse_date_input("2026-01-09") == date(2026, 1, 9)


def test_parse_date_input_rejects_invalid_dates():
    with pytest.raises(ValueError, match="DD-MM-YYYY"):
        parse_date_input("31-02-2026")


def test_iso_date_input_filter_normalizes_values_for_native_pickers():
    assert iso_date_input("09-01-2026") == "2026-01-09"
    assert iso_date_input(date(2026, 1, 9)) == "2026-01-09"
    assert iso_date_input("not a date") == ""
