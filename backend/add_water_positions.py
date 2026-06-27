import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.vessel import VesselPosition
from datetime import datetime, timedelta

async def add_water_positions():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Очищаем старые позиции
        await session.execute(text("DELETE FROM vessel_positions"))
        await session.commit()
        print("🗑️ Старые позиции удалены")
        
        # Координаты ТОЛЬКО в акватории (в море/бухте, не на суше)
        # Владивосток: бухта Золотой Рог, Амурский залив, Уссурийский залив
        water_routes = {
            273210001: {  # Tanker Pro - стоит в бухте Золотой Рог
                "positions": [
                    {"lat": 43.1150, "lon": 131.8850},  # центр бухты
                    {"lat": 43.1120, "lon": 131.8880},
                    {"lat": 43.1180, "lon": 131.8820},
                    {"lat": 43.1150, "lon": 131.8850},
                ]
            },
            273210002: {  # Container Master - у причала
                "positions": [
                    {"lat": 43.1080, "lon": 131.8920},
                    {"lat": 43.1060, "lon": 131.8940},
                    {"lat": 43.1100, "lon": 131.8900},
                    {"lat": 43.1080, "lon": 131.8920},
                ]
            },
            273210003: {  # Passenger Ferry - на рейде
                "positions": [
                    {"lat": 43.1200, "lon": 131.8780},
                    {"lat": 43.1220, "lon": 131.8750},
                    {"lat": 43.1180, "lon": 131.8800},
                    {"lat": 43.1200, "lon": 131.8780},
                ]
            },
            273210004: {  # Tug Boat - у входа в порт
                "positions": [
                    {"lat": 43.1120, "lon": 131.8900},
                    {"lat": 43.1100, "lon": 131.8920},
                    {"lat": 43.1140, "lon": 131.8880},
                    {"lat": 43.1120, "lon": 131.8900},
                ]
            },
            273210005: {  # Fishing Star - в Амурском заливе
                "positions": [
                    {"lat": 43.1250, "lon": 131.8820},
                    {"lat": 43.1280, "lon": 131.8800},
                    {"lat": 43.1220, "lon": 131.8850},
                    {"lat": 43.1250, "lon": 131.8820},
                ]
            }
        }
        
        positions_added = 0
        
        for mmsi, route in water_routes.items():
            positions_list = route["positions"]
            num_positions = len(positions_list)
            
            for i, pos_coords in enumerate(positions_list):
                t = datetime.utcnow() - timedelta(hours=(num_positions - i))
                
                pos = VesselPosition(
                    mmsi=mmsi,
                    timestamp=t,
                    latitude=pos_coords["lat"],
                    longitude=pos_coords["lon"],
                    speed=float(8 - i * 2) if i < 3 else 2.0,
                    course=45.0 + i * 10,
                    heading=45 + i * 10
                )
                session.add(pos)
                positions_added += 1
                print(f"Добавлена позиция для судна {mmsi}: [{pos_coords['lat']}, {pos_coords['lon']}]")
        
        # Добавляем текущие позиции (последние)
        current_positions = {
            273210001: {"lat": 43.1150, "lon": 131.8850, "speed": 0.5},
            273210002: {"lat": 43.1080, "lon": 131.8920, "speed": 0.3},
            273210003: {"lat": 43.1200, "lon": 131.8780, "speed": 1.2},
            273210004: {"lat": 43.1120, "lon": 131.8900, "speed": 2.0},
            273210005: {"lat": 43.1250, "lon": 131.8820, "speed": 0.8},
        }
        
        for mmsi, coords in current_positions.items():
            pos = VesselPosition(
                mmsi=mmsi,
                timestamp=datetime.utcnow(),
                latitude=coords["lat"],
                longitude=coords["lon"],
                speed=coords["speed"],
                course=90.0,
                heading=90
            )
            session.add(pos)
            positions_added += 1
        
        await session.commit()
        print(f"\n✅ Добавлено {positions_added} позиций (все в акватории)")
        
        # Проверка
        result = await session.execute(text("SELECT COUNT(*) FROM vessel_positions"))
        count = result.scalar()
        print(f"📊 Всего позиций в БД: {count}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_water_positions())