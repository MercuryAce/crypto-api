from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analysis import run_analysis
from auth import require_api_key

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("")
async def get_analysis(
    asset: str = Query(...),
    vs: str = Query(default="gold"),
    window: int = Query(default=90, ge=7, le=3650),
    interval: str = Query(default="1d"),
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    return run_analysis(db, asset=asset, vs=vs, window=window, interval=interval)