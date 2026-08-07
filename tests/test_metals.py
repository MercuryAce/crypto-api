"""Unit tests for Alpha Vantage metals ingest parsing."""

from app.ingest.metals import history_to_bars


SAMPLE_PAYLOAD = {
    "name": "Gold",
    "interval": "daily",
    "unit": "USD per troy ounce",
    "data": [
        {"date": "2026-08-05", "value": "2650.12"},
        {"date": "2026-08-06", "value": "2660.00"},
        {"date": "2026-08-07", "value": "."},
    ],
}


def test_history_to_bars_gold():
    bars = history_to_bars(SAMPLE_PAYLOAD, av_symbol="GOLD")
    assert len(bars) == 2
    assert bars[0]["symbol"] == "GOLD"
    assert bars[0]["interval"] == "1d"
    assert bars[0]["close"] == 2650.12
    assert bars[0]["open_"] == bars[0]["high"] == bars[0]["low"]
    assert bars[0]["source"] == "alphavantage"
    assert bars[0]["timestamp"].year == 2026


def test_history_to_bars_xau_maps_to_gold():
    bars = history_to_bars(SAMPLE_PAYLOAD, av_symbol="XAU")
    assert bars[0]["symbol"] == "GOLD"


def test_history_to_bars_silver():
    bars = history_to_bars(SAMPLE_PAYLOAD, av_symbol="SILVER")
    assert bars[0]["symbol"] == "SILVER"
