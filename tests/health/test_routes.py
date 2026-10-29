def test_health(client):
    """The health endpoint reports that the initialized database is available."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
