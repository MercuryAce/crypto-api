from datetime import datetime, timezone

from app.db.models import OHLCVBar


def test_bars_requires_auth(client, monkeypatch):
    monkeypatch.setenv("API_KEYS", "test-key")
    resp = client.get("/bars/BTCUSDT")
    assert resp.status_code == 401


def test_bars_returns_data(client):
    pass