from app import config


def test_requires_login(client):
    """Protected pages redirect HTML users and signal unauthenticated htmx users."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    response = client.get("/", headers={"HX-Request": "true"})
    assert response.status_code == 401
    assert response.headers["HX-Redirect"] == "/login"


def test_login_rejects_bad_password(client):
    """The login form rejects a password that does not match the configured user."""
    response = client.post(
        "/login", data={"username": config.settings.username, "password": "nope"}
    )
    assert response.status_code == 401
