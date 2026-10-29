from fastapi.testclient import TestClient

from app import config


def login(client: TestClient):
    return client.post(
        "/login",
        data={"username": config.settings.username, "password": config.settings.password},
        follow_redirects=True,
    )
