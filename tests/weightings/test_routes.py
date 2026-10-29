from datetime import date

from app import config
from app.db import connect


def login(client):
    return client.post(
        "/login",
        data={"username": config.settings.username, "password": config.settings.password},
        follow_redirects=True,
    )


def test_login_and_add_weighing(client):
    """A signed-in user can add a weighing and see it in the list and form defaults."""
    assert login(client).status_code == 200
    today = date.today()

    response = client.post(
        "/weighings",
        data={"date_value": today.strftime("%d-%m-%Y"), "weight_kg": "72.5"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get("/weighings")
    assert "72.5" in response.text
    assert today.strftime("%d-%m-%Y") in response.text
    assert 'lang="en-AU"' in response.text
    conn = connect()
    stored_date = conn.execute("SELECT date FROM weighings").fetchone()["date"]
    conn.close()
    assert stored_date == today.isoformat()

    response = client.get("/weighings/new")
    assert 'type="date"' in response.text
    assert 'lang="en-AU"' in response.text
    assert f'value="{today.isoformat()}"' in response.text
    assert 'value="72.5"' in response.text


def test_add_weighing_rejects_bad_weight(client):
    """Invalid weight input returns a client error instead of inserting a record."""
    login(client)
    response = client.post("/weighings", data={"date_value": "01-01-2026", "weight_kg": "0"})
    assert response.status_code == 400
    assert 'value="2026-01-01"' in response.text


def test_add_weighing_rejects_non_australian_date_format(client):
    login(client)
    response = client.post(
        "/weighings",
        data={"date_value": "01/02/2026", "weight_kg": "70"},
    )

    assert response.status_code == 400
    assert "DD-MM-YYYY" in response.text


def test_edit_and_delete(client):
    """A weighing can be edited and deleted through its item endpoints."""
    login(client)
    client.post("/weighings", data={"date_value": "2026-01-01", "weight_kg": "70.0"})
    conn = connect()
    row = conn.execute("SELECT id FROM weighings").fetchone()
    conn.close()
    weighing_id = row["id"]

    edit_form = client.get(f"/weighings/{weighing_id}/edit")
    assert 'type="date"' in edit_form.text
    assert 'value="2026-01-01"' in edit_form.text

    response = client.put(
        f"/weighings/{weighing_id}",
        data={"date_value": "02-01-2026", "weight_kg": "71.2"},
    )
    assert response.status_code == 200

    conn = connect()
    updated = conn.execute(
        "SELECT date, weight_kg FROM weighings WHERE id = ?", (weighing_id,)
    ).fetchone()
    conn.close()
    assert updated["date"] == "2026-01-02"
    assert updated["weight_kg"] == 71.2

    assert client.delete(f"/weighings/{weighing_id}").status_code == 204
    assert client.get(f"/weighings/{weighing_id}/edit").status_code == 404


def test_pagination(client):
    """The weighing list paginates records using the configured page size."""
    login(client)
    for i in range(35):
        client.post(
            "/weighings",
            data={"date_value": f"2026-01-{i % 28 + 1:02d}", "weight_kg": "70.0"},
        )

    response = client.get("/weighings")
    assert response.status_code == 200
    assert "page 1 of 2" in response.text

    response = client.get("/weighings?page=2")
    assert "page 2 of 2" in response.text
