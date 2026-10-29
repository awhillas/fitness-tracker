from datetime import timedelta

from app.dates import today as app_today
from app.db import connect
from tests.eating.support import login


def test_target_history_crud_and_effective_dates(client):
    """Target history preserves dated values and selects the target effective on a report day."""
    login(client)
    today = app_today()
    first_start = today - timedelta(days=8)
    second_start = today - timedelta(days=2)

    response = client.post(
        "/eating/targets",
        data={
            "start_date": first_start.strftime("%d-%m-%Y"),
            "kcal_target": "1800",
            "protein_target_g": "100",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert (
        client.get(f"/eating?day={(today - timedelta(days=5)).isoformat()}").text.find(
            "1800.0 kcal"
        )
        > 0
    )

    response = client.post(
        "/eating/targets",
        data={
            "start_date": second_start.isoformat(),
            "kcal_target": "2100",
            "protein_target_g": "125",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "2100.0 kcal" in client.get("/eating").text

    conn = connect()
    target_id = conn.execute(
        "SELECT id FROM eating_targets WHERE start_date = ?", (second_start.isoformat(),)
    ).fetchone()["id"]
    conn.close()

    response = client.post(
        f"/eating/targets/{target_id}/edit",
        data={
            "start_date": second_start.strftime("%d-%m-%Y"),
            "kcal_target": "2200",
            "protein_target_g": "130",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "2200.0 kcal" in client.get("/eating").text

    response = client.get("/eating/targets")
    assert "1800.0 kcal/day" in response.text
    assert "2200.0 kcal/day" in response.text
    assert first_start.strftime("%d-%m-%Y") in response.text
    assert 'type="date"' in response.text
    assert 'lang="en-AU"' in response.text
    edit_response = client.get(f"/eating/targets/{target_id}/edit")
    assert f'value="{second_start.isoformat()}"' in edit_response.text
    assert (
        client.post(f"/eating/targets/{target_id}/delete", follow_redirects=False).status_code
        == 303
    )
    assert "1800.0 kcal" in client.get("/eating").text


def test_target_validation_and_duplicate_start_date(client):
    """Targets require positive amounts and unique start dates for each user."""
    login(client)
    today = app_today()
    target_data = {
        "start_date": today.isoformat(),
        "kcal_target": "1900",
        "protein_target_g": "110",
    }
    invalid = client.post(
        "/eating/targets",
        data={
            **target_data,
            "start_date": today.strftime("%d-%m-%Y"),
            "kcal_target": "0",
        },
    )
    assert invalid.status_code == 400
    assert f'value="{today.isoformat()}"' in invalid.text
    assert (
        client.post("/eating/targets", data=target_data, follow_redirects=False).status_code == 303
    )
    duplicate = client.post("/eating/targets", data=target_data)
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.text


def test_report_shows_consumption_scaffold_and_navigation(client):
    """The eating report shows placeholder consumed totals and appears in the main navigation."""
    login(client)
    response = client.get("/eating")

    assert response.status_code == 200
    assert "0.0 kcal" in response.text
    assert "0.0 g" in response.text
    assert 'href="/eating"' in response.text
    assert "Meal recording is the next step" in response.text


def test_report_accepts_australian_date_format(client):
    login(client)
    response = client.get("/eating?day=09-01-2026")

    assert response.status_code == 200
    assert "Consumed on 09-01-2026" in response.text
    assert 'type="date"' in response.text
    assert 'value="2026-01-09"' in response.text
