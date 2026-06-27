# app/api/v1/endpoints/rules.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="/rules", tags=["rules"])

@router.get("/")
async def get_rules(db: AsyncSession = Depends(get_db)):
    """Получение списка правил"""
    return {"message": "Rules endpoint - to be implemented"}