from app.db.models import AssetRegistry
from app.db.session import SessionLocal

SEED = [
    ("bitcoin", "btc", "BTCUSDT"),
    ("ethereum", "eth", "ETHUSDT"),
    ("gold", "xau", "GOLD"),
    ("silver", "xag", "SILVER"),
]

def main():
    db = SessionLocal()
    try:
        for cg_id, symbol, pair in SEED:
            row = db.get(AssetRegistry, cg_id) or AssetRegistry(cg_id=cg_id)
            row.symbol = symbol
            row.binance_symbol = pair
            db.merge(row)
        db.commit()
        print(f"Seeded {len(SEED)} assets")
    finally:
        db.close()

if __name__ == "__main__":
    main()