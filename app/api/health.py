from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=['health'])

@router.get('/health', status_code=200)
async def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {'status': 'ok'}


