import pytest
from fastapi.testclient import TestClient

from app import config
from app.db import init_db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    init_db()
    with TestClient(app) as test_client:
        yield test_client
