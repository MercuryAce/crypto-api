# CryptoAPI

## Overview 
Crypto API ingests data from 3rd parties (including Binance Vision) and provides OHVLC data with anlaysis 

## Requirements 

## Setup
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
./venv/bin/python scripts/seed_registry.py
```

### Run
```uviorn main:App --host 0.0.0.0 --port 8080 --reload```

### Ingest
```
./venv/bin/python scripts/backfill_monthly.py BTCUSDT 2024-01-01 2024-12-31
./venv/bin/python scripts/backfill_monthly.py ETHUSDT 2024-01-01 2024-12-31
```

### Curl
```
curl -H "X-API-Key: YOUR_KEY" "http://127.0.0.1:8080/v1/analysis?asset=bitcoin&vs=ethereum&window=90"
```