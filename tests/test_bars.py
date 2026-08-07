from datetime import datetime, timezone

from app.db.models import OHLCVBar


def test_bars_requires_auth(client, monkeypatch):
    from config import settings

    # Settings are loaded once at import; patch the live object, not only the env.
    monkeypatch.setattr(settings, "api_keys", "test-key")
    resp = client.get("/v1/bars/BTCUSDT")
    assert resp.status_code == 401


def test_bars_returns_data(client):
    pass