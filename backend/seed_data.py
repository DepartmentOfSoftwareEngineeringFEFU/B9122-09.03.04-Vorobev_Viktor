# seed_data.py
import asyncio
from datetime import datetime, timedelta
import random
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.vessel import Vessel, VesselPosition, VesselType
from app.models.rule import NavigationRule
from app.models.alert import Alert

async def seed_database():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Добавляем тестовые суда
        test_vessels = [
            {"mmsi": 273210001, "name": "Tanker Pro", "vessel_type": VesselType.TANKER, "length": 250},
            {"mmsi": 273210002, "name": "Container Master", "vessel_type": VesselType.CONTAINER, "length": 300},
            {"mmsi": 273210003, "name": "Passenger Ferry", "vessel_type": VesselType.PASSENGER, "length": 120},
            {"mmsi": 273210004, "name": "Tug Boat", "vessel_type": VesselType.TUG, "length": 30},
            {"mmsi": 273210005, "name": "Fishing Star", "vessel_type": VesselType.FISHING, "length": 45},
        ]
        
        for v in test_vessels:
            vessel = Vessel(**v)
            session.add(vessel)
        
        # 2. Добавляем тестовые правила
        rules = [
            NavigationRule(
                name="Speed limit in port",
                rule_type="local",
                rule_category="speed",
                condition={"parameter": "speed", "operator": ">", "value": 10},
                action_type="warning",
                message_template="Vessel {vessel_name} exceeded speed limit: {speed} knots (limit: {limit})",
                is_active=True,
                priority=5
            ),
            NavigationRule(
                name="Collision avoidance",
                rule_type="international",
                rule_category="distance",
                condition={"min_cpa_distance": 0.5, "min_tcpa_time": 10},
                action_type="critical",
                message_template="Collision risk between {vessel1} and {vessel2}. CPA: {dcpa} NM, TCPA: {tcpa} min",
                is_active=True,
                priority=10
            ),
        ]
        
        for rule in rules:
            session.add(rule)
        
        # 3. Добавляем тестовые позиции судов
        base_time = datetime.utcnow()
        for i, vessel in enumerate(test_vessels):
            for j in range(10):  # 10 позиций для каждого судна
                position = VesselPosition(
                    mmsi=vessel["mmsi"],
                    timestamp=base_time - timedelta(minutes=j*5),
                    latitude=43.115 + random.uniform(-0.05, 0.05),  # Владивосток
                    longitude=131.885 + random.uniform(-0.05, 0.05),
                    speed=random.uniform(5, 15),
                    course=random.uniform(0, 360),
                    heading=int(random.uniform(0, 360)),
                )
                session.add(position)
        
        await session.commit()
        print("✅ Тестовые данные добавлены!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_database())