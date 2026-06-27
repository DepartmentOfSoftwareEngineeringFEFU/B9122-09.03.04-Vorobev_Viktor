# app/api/v1/endpoints/vessels.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.vessel import Vessel
# from app.utils.auth import get_current_user_optional  # Временно отключаем

router = APIRouter()

# app/api/v1/endpoints/vessels.py

@router.get("/")
async def get_vessels(
    db: AsyncSession = Depends(get_db)
):
    # Убираем фильтрацию по user_id
    result = await db.execute(select(Vessel))
    vessels = result.scalars().all()
    return vessels