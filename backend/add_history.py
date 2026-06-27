import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.vessel import VesselPosition
from datetime import datetime, timedelta

async def add_realistic_history():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Очищаем старые позиции
        await session.execute(text("DELETE FROM vessel_positions"))
        await session.commit()
        print("🗑️ Старые позиции удалены")
        
        # Определяем маршруты для каждого судна (от точки А к точке Б)
        routes = {
            273210001: {  # Tanker Pro
                "start": {"lat": 43.145, "lon": 131.865},
                "end": {"lat": 43.085, "lon": 131.905}
            },
            273210002: {  # Container Master
                "start": {"lat": 43.135, "lon": 131.875},
                "end": {"lat": 43.095, "lon": 131.895}
            },
            273210003: {  # Passenger Ferry
                "start": {"lat": 43.140, "lon": 131.880},
                "end": {"lat": 43.100, "lon": 131.885}
            },
            273210004: {  # Tug Boat
                "start": {"lat": 43.130, "lon": 131.890},
                "end": {"lat": 43.105, "lon": 131.885}
            },
            273210005: {  # Fishing Star
                "start": {"lat": 43.125, "lon": 131.895},
                "end": {"lat": 43.110, "lon": 131.875}
            }
        }
        
        positions_added = 0
        
        for mmsi, route in routes.items():
            start = route["start"]
            end = route["end"]
            
            # Создаём 10 позиций по прямой линии между start и end
            for i in range(10):
                t = datetime.utcnow() - timedelta(hours=(10 - i))
                
                # Линейная интерполяция между start и end
                fraction = i / 9  # от 0 до 1
                lat = start["lat"] + (end["lat"] - start["lat"]) * fraction
                lon = start["lon"] + (end["lon"] - start["lon"]) * fraction
                
                pos = VesselPosition(
                    mmsi=mmsi,
                    timestamp=t,
                    latitude=lat,
                    longitude=lon,
                    speed=float(10 - i),  # скорость снижается к порту
                    course=45.0,
                    heading=45
                )
                session.add(pos)
                positions_added += 1
                print(f"Добавлена позиция для судна {mmsi}: точка {i+1}/10")
        
        await session.commit()
        print(f"✅ Добавлено {positions_added} позиций")
        
        # Проверка
        result = await session.execute(text("SELECT COUNT(*) FROM vessel_positions"))
        count = result.scalar()
        print(f"📊 Всего позиций в БД: {count}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_realistic_history())