"""Alpha Vantage client (commodities: gold/silver history)."""

from __future__ import annotations

import httpx

from config import settings

SOFT_ERROR_KEYS = ("Note", "Information", "Error Message")
BASE_URL = "https://www.alphavantage.co/query"
REQUEST_GAP_SECONDS = 13


class AvAPIError(Exception):
    """Raised when Alpha Vantage returns an HTTP or soft-error response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"{status_code} {message}")


def get_gold_silver_history(
    symbol: str,
    *,
    interval: str = "daily",
    timeout: float | None = None,
) -> dict:
    """Fetch GOLD_SILVER_HISTORY for GOLD, XAU, SILVER, or XAG."""
    if not settings.alphavantage_api_key:
        raise AvAPIError(0, "ALPHAVANTAGE_API_KEY is not configured")

    params = {
        "function": "GOLD_SILVER_HISTORY",
        "symbol": symbol.upper(),
        "interval": interval,
        "apikey": settings.alphavantage_api_key,
    }
    if settings.alphavantage_base_url:
        url = settings.alphavantage_base_url.rstrip("/")
    else:
        url = BASE_URL

    response = httpx.get(
        url,
        params=params,
        timeout=timeout or settings.alphavantage_request_timeout,
    )
    if not response.is_success:
        raise AvAPIError(response.status_code, response.text[:200])

    data = response.json()
    if not isinstance(data, dict):
        raise AvAPIError(200, "Unexpected response type")

    for key in SOFT_ERROR_KEYS:
        if data.get(key):
            raise AvAPIError(200, str(data[key]))

    return data
