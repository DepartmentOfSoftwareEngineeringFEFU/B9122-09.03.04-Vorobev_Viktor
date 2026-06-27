# backend/import_ports.py
import asyncio
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings

async def import_ports():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    file_path = "ports_global.csv"
    
    print("📂 Чтение CSV файла портов...")
    df = pd.read_csv(file_path)
    
    print(f"📊 Всего записей: {len(df)}")
    print(f"📋 Колонки: {df.columns.tolist()}")
    
    async with async_session() as session:
        # Очищаем старую таблицу
        await session.execute(text("TRUNCATE ports_global RESTART IDENTITY"))
        await session.commit()
        
        # Вставляем данные
        for _, row in df.iterrows():
            await session.execute(
                text("""
                    INSERT INTO ports_global (index_no, port_name, country, latitude, longitude, geom_wkt)
                    VALUES (:index_no, :port_name, :country, :lat, :lon, :geom_wkt)
                """),
                {
                    "index_no": str(row.get('INDEX_NO', '')),
                    "port_name": str(row.get('PORT_NAME', '')),
                    "country": str(row.get('COUNTRY', '')),
                    "lat": float(row['LATITUDE']),
                    "lon": float(row['LONGITUDE']),
                    "geom_wkt": str(row.get('geom_WKT', ''))
                }
            )
        
        await session.commit()
        print(f"✅ Импортировано {len(df)} портов")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(import_ports())