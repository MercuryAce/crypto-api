# CryptoAPI

## Overview
CryptoAPI ingests market data (Binance Vision spot klines, Alpha Vantage gold/silver) and serves comparative analysis over Postgres.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit DATABASE_URL, API_KEYS, ALPHAVANTAGE_API_KEY
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
PYTHONPATH=. python scripts/seed_registry.py
```

## Run
```bash
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8080
# production: gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080
```

## Ingest

Binance Vision (crypto daily klines):
```bash
PYTHONPATH=. python scripts/backfill_monthly.py BTCUSDT 2024-01-01 2025-08-06
PYTHONPATH=. python scripts/backfill_monthly.py ETHUSDT 2024-01-01 2025-08-06
PYTHONPATH=. python scripts/daily_ingest.py
```

Alpha Vantage metals (gold/silver daily — `GOLD_SILVER_HISTORY`):
```bash
PYTHONPATH=. python scripts/backfill_metals.py
# or: PYTHONPATH=. python scripts/backfill_metals.py GOLD SILVER
```

## Smoke test
```bash
curl http://127.0.0.1:8080/health
curl -H "X-API-Key: YOUR_KEY" "http://127.0.0.1:8080/v1/analysis?asset=bitcoin&vs=gold&window=90"
```

## Tests
```bash
PYTHONPATH=. pytest tests/ -q
```
