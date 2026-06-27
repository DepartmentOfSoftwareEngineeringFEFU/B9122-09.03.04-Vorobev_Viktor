# app/api/v1/endpoints/positions.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.vessel import VesselPosition
# from app.utils.auth import get_current_user_optional  # Временно отключаем
from typing import Optional

router = APIRouter()

@router.get("/latest")
async def get_latest_positions(
    limit: int = Query(100, ge=1, le=1000),
    mmsi: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    # current_user = Depends(get_current_user_optional)  # Временно отключаем
):
    """Получение последних позиций всех судов"""
    
    # user_id = current_user.id if current_user else None
    
    # Подзапрос для получения последнего timestamp по каждому судну
    subquery = select(
        VesselPosition.mmsi,
        func.max(VesselPosition.timestamp).label('max_time')
    # ).where(VesselPosition.user_id == user_id).group_by(VesselPosition.mmsi).subquery()
    ).group_by(VesselPosition.mmsi).subquery()  # Убираем фильтрацию по user_id
    
    query = select(VesselPosition).join(
        subquery,
        (VesselPosition.mmsi == subquery.c.mmsi) & 
        (VesselPosition.timestamp == subquery.c.max_time)
    # ).where(VesselPosition.user_id == user_id)
    )
    
    if mmsi:
        query = query.where(VesselPosition.mmsi == mmsi)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    positions = result.scalars().all()
    
    return [
        {
            "mmsi": p.mmsi,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "speed": p.speed,
            "course": p.course,
            "timestamp": p.timestamp.isoformat()
        }
        for p in positions
    ]


@router.get("/history/{mmsi}")
async def get_vessel_history(
    mmsi: int, 
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    # current_user = Depends(get_current_user_optional)  # Временно отключаем
):
    """Получение истории движения судна за последние N часов"""
    since = datetime.utcnow() - timedelta(hours=hours)
    # user_id = current_user.id if current_user else None
    
    query = select(VesselPosition).where(
        VesselPosition.mmsi == mmsi,
        # VesselPosition.user_id == user_id,  # Убираем фильтрацию
        VesselPosition.timestamp >= since
    ).order_by(VesselPosition.timestamp)
    
    result = await db.execute(query)
    positions = result.scalars().all()
    
    return [
        {
            "lat": p.latitude,
            "lon": p.longitude,
            "timestamp": p.timestamp.isoformat(),
            "speed": p.speed,
            "course": p.course
        }
        for p in positions
    ]