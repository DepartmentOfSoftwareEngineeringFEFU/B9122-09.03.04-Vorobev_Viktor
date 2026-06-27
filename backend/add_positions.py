# add_positions.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.vessel import VesselPosition
from datetime import datetime
import random

async def add_positions():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Координаты для разных типов судов (разные районы акватории)
        vessels_coords = {
            273210001: {"lat": 43.115, "lon": 131.885},   # Tanker Pro - центр
            273210002: {"lat": 43.108, "lon": 131.892},   # Container Master - восточнее
            273210003: {"lat": 43.120, "lon": 131.878},   # Passenger Ferry - западнее
            273210004: {"lat": 43.112, "lon": 131.890},   # Tug Boat - у причала
            273210005: {"lat": 43.125, "lon": 131.882},   # Fishing Star - севернее
        }
        
        positions = []
        for mmsi, coords in vessels_coords.items():
            pos = VesselPosition(
                mmsi=mmsi,
                timestamp=datetime.utcnow(),
                latitude=coords["lat"] + random.uniform(-0.005, 0.005),
                longitude=coords["lon"] + random.uniform(-0.005, 0.005),
                speed=random.uniform(5, 15),
                course=random.uniform(0, 360)
            )
            positions.append(pos)
            print(f"Добавлена позиция для судна {mmsi}")
        
        session.add_all(positions)
        await session.commit()
        print("✅ Позиции добавлены!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_positions())