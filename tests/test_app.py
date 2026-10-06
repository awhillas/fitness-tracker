from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import config
from app.aggregates import daily_series, weekly_series
from app.db import connect, init_db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    init_db()
    with TestClient(app) as c:
        yield c


def login(client):
    return client.post(
        "/login",
        data={"username": config.USERNAME, "password": config.PASSWORD},
        follow_redirects=True,
    )


def test_health(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_requires_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    response = client.get("/", headers={"HX-Request": "true"})
    assert response.status_code == 401
    assert response.headers["HX-Redirect"] == "/login"


def test_login_rejects_bad_password(client):
    response = client.post("/login", data={"username": config.USERNAME, "password": "nope"})
    assert response.status_code == 401


def test_login_and_add_weighing(client):
    assert login(client).status_code == 200

    response = client.post(
        "/weighings",
        data={"date_value": date.today().isoformat(), "weight_kg": "72.5"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get("/weighings")
    assert "72.5" in response.text

    response = client.get("/weighings/new")
    assert f'value="{date.today().isoformat()}"' in response.text
    assert 'value="72.5"' in response.text


def test_add_weighing_rejects_bad_weight(client):
    login(client)
    response = client.post("/weighings", data={"date_value": "2026-01-01", "weight_kg": "0"})
    assert response.status_code == 400


def test_edit_and_delete(client):
    login(client)
    client.post("/weighings", data={"date_value": "2026-01-01", "weight_kg": "70.0"})
    conn = connect()
    row = conn.execute("SELECT id FROM weighings").fetchone()
    conn.close()
    weighing_id = row["id"]

    response = client.put(
        f"/weighings/{weighing_id}",
        data={"date_value": "2026-01-02", "weight_kg": "71.2"},
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
    login(client)
    for i in range(35):
        client.post(
            "/weighings", data={"date_value": f"2026-01-{i % 28 + 1:02d}", "weight_kg": "70.0"}
        )

    response = client.get("/weighings")
    assert response.status_code == 200
    assert "page 1 of 2" in response.text

    response = client.get("/weighings?page=2")
    assert "page 2 of 2" in response.text


def test_aggregates(client):
    login(client)
    today = date.today()
    for offset in range(10):
        day = today - timedelta(days=offset)
        client.post("/weighings", data={"date_value": day.isoformat(), "weight_kg": "70.0"})
        client.post("/weighings", data={"date_value": day.isoformat(), "weight_kg": "72.0"})

    conn = connect()
    daily = daily_series(conn, days=7)
    weekly = weekly_series(conn, weeks=8)
    conn.close()

    assert len(daily) == 7
    assert all(d["value"] == 71.0 for d in daily)
    assert len(weekly) == 8
    assert sum(w["count"] for w in weekly) == 20
    assert all(w["mean"] == 71.0 for w in weekly if w["count"])
    assert any(w["std"] == 1.41 for w in weekly)
