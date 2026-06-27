# backend/import_ais.py
import asyncio
import pandas as pd
import random
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.vessel import Vessel, VesselPosition, VesselType
from datetime import datetime

# Функция для преобразования типа судна из CSV в Enum
def map_vessel_type(csv_type) -> VesselType:
    """Маппинг типов судов по стандарту ITU-R M.1371-5"""
    if pd.isna(csv_type) or csv_type is None:
        return VesselType.OTHER
    
    # Преобразуем в число
    try:
        type_code = int(float(csv_type))
    except (ValueError, TypeError):
        return VesselType.OTHER
    
    # ITU-R M.1371-5 Classification
    if 0 <= type_code <= 19:
        # Reserved for future use
        return VesselType.OTHER
    
    # 20-29: Wing in ground (WIG)
    elif 20 <= type_code <= 29:
        return VesselType.WIG
    
    # 30-39: Fishing
    elif 30 <= type_code <= 39:
        if type_code == 31:
            return VesselType.TUG  # Towing
        return VesselType.FISHING
    
    # 40-49: Diving / Dredger / Military
    elif 40 <= type_code <= 49:
        if type_code == 40:
            return VesselType.DIVING
        elif type_code in [41, 42, 43, 44, 45]:
            return VesselType.DIVING
        elif type_code in [46, 47, 48, 49]:
            return VesselType.DREDGER
        return VesselType.OTHER
    
    # 50-59: Pilot / SAR / Tug / Port Tender
    elif 50 <= type_code <= 59:
        if type_code == 50:
            return VesselType.PILOT
        elif type_code == 51:
            return VesselType.SAR
        elif type_code in [52, 53, 54, 55, 56, 57, 58, 59]:
            return VesselType.TUG
        return VesselType.OTHER
    
    # 60-69: Passenger
    elif 60 <= type_code <= 69:
        return VesselType.PASSENGER
    
    # 70-79: Cargo
    elif 70 <= type_code <= 79:
        if type_code == 79:
            return VesselType.PLEASURE
        elif type_code in [71, 72, 73, 74, 75, 76, 77, 78]:
            return VesselType.CARGO
        return VesselType.CARGO
    
    # 80-89: Tanker
    elif 80 <= type_code <= 89:
        return VesselType.TANKER
    
    # 90-99: Other
    elif 90 <= type_code <= 99:
        return VesselType.OTHER
    
    # 100-199: Reserved
    elif 100 <= type_code <= 199:
        return VesselType.OTHER
    
    # 200-201: Wing in ground (WIG)
    elif type_code in [200, 201]:
        return VesselType.WIG
    
    # 202-207: Reserved
    elif 202 <= type_code <= 207:
        return VesselType.OTHER
    
    # Default
    return VesselType.OTHER

async def import_ais():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    file_path = "processed_AIS_dataset.csv"
    target_vessel_count = 500
    max_positions_per_vessel = 30
    
    print(f"🚀 Загрузка {target_vessel_count} случайных судов из {file_path}")
    
    # Шаг 1: собираем все уникальные MMSI из файла
    print("📊 Сбор уникальных MMSI...")
    all_mmsi = set()
    chunk_size = 100000
    for chunk in pd.read_csv(file_path, chunksize=chunk_size, usecols=['MMSI']):
        all_mmsi.update(chunk['MMSI'].unique())
        print(f"   Найдено MMSI: {len(all_mmsi)}", end='\r')
    print(f"\n✅ Всего уникальных судов в файле: {len(all_mmsi)}")
    
    # Шаг 2: выбираем случайные 500 MMSI
    selected_mmsi = random.sample(list(all_mmsi), min(target_vessel_count, len(all_mmsi)))
    selected_set = set(selected_mmsi)
    print(f"🎲 Выбрано {len(selected_mmsi)} случайных судов")
    
    # Шаг 3: собираем позиции для выбранных судов
    print("📖 Сбор позиций для выбранных судов...")
    vessels_data = {}
    
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        chunk_filtered = chunk[chunk['MMSI'].isin(selected_set)]
        
        for _, row in chunk_filtered.iterrows():
            mmsi = int(row['MMSI'])
            
            if mmsi not in vessels_data:
                # Получаем имя
                raw_name = row.get('VesselName')
                if pd.isna(raw_name) or raw_name is None:
                    vessel_name = f"Ship_{mmsi}"
                else:
                    vessel_name = str(raw_name)[:100]
                
                # Получаем тип судна
                raw_type = row.get('VesselType')
                vessel_type = map_vessel_type(raw_type)
                
                vessels_data[mmsi] = {
                    'positions': [],
                    'dest_lat': row.get('dest_lat'),
                    'dest_lon': row.get('dest_lon'),
                    'name': vessel_name,
                    'vessel_type': vessel_type.value,  # Сохраняем строковое значение
                    'length': row.get('Length', 0) if pd.notna(row.get('Length', 0)) else 0
                }
            
            if len(vessels_data[mmsi]['positions']) < max_positions_per_vessel:
                vessels_data[mmsi]['positions'].append({
                    'timestamp': row['BaseDateTime'],
                    'lat': row['LAT'],
                    'lon': row['LON'],
                    'sog': row.get('SOG', 0) if pd.notna(row.get('SOG', 0)) else 0,
                    'cog': row.get('COG', 0) if pd.notna(row.get('COG', 0)) else 0
                })
        
        print(f"   Собрано судов: {len(vessels_data)}", end='\r')
    
    print(f"\n✅ Собрано {len(vessels_data)} судов, всего позиций: {sum(len(v['positions']) for v in vessels_data.values())}")
    
    # Добавляем колонки destination в таблицу vessels (если нет)
    async with async_session() as session:
        try:
            await session.execute(text("ALTER TABLE vessels ADD COLUMN IF NOT EXISTS destination_lat FLOAT"))
            await session.execute(text("ALTER TABLE vessels ADD COLUMN IF NOT EXISTS destination_lon FLOAT"))
            await session.commit()
            print("✅ Колонки destination добавлены")
        except Exception as e:
            print(f"⚠️ Колонки уже существуют или ошибка: {e}")
    
    async with async_session() as session:
        print("🗑️ Очистка БД...")
        
        # Проверка, есть ли маршруты в БД
        result = await session.execute(text("SELECT COUNT(*) FROM routes"))
        routes_count = result.scalar()
        
        if routes_count > 0:
            print(f"⚠️ ВНИМАНИЕ: Найдено {routes_count} исторических маршрутов!")
            print("⚠️ Они будут СОХРАНЕНЫ!")
        
        # Очищаем только нужные таблицы
        await session.execute(text("TRUNCATE vessel_positions, vessels, alerts CASCADE"))
        await session.commit()
        print("✅ Очищены: vessels, vessel_positions, alerts")
        print(f"✅ Исторические маршруты сохранены: {routes_count} шт.")
    
    # Вставка судов с правильными типами
    async with async_session() as session:
        print("🚢 Добавление судов...")
        type_stats = {}
        
        for mmsi, data in vessels_data.items():
            vessel = Vessel(
                mmsi=mmsi,
                name=data['name'],
                vessel_type=data['vessel_type'],  # Используем правильный тип
                length=float(data['length']) if data['length'] else 0,
                destination_lat=float(data['dest_lat']) if data['dest_lat'] and pd.notna(data['dest_lat']) else None,
                destination_lon=float(data['dest_lon']) if data['dest_lon'] and pd.notna(data['dest_lon']) else None
            )
            session.add(vessel)
            
            # Статистика по типам
            vessel_type = data['vessel_type']
            type_stats[vessel_type] = type_stats.get(vessel_type, 0) + 1
        
        await session.commit()
        print(f"✅ Добавлено {len(vessels_data)} судов")
        print("\n📊 Статистика по типам судов:")
        for vtype, count in sorted(type_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {vtype}: {count}")
    
    # Вставка позиций из CSV
    async with async_session() as session:
        print("📍 Добавление позиций...")
        total_pos = 0
        for mmsi, data in vessels_data.items():
            for pos in data['positions']:
                ts = pd.to_datetime(pos['timestamp'])
                vp = VesselPosition(
                    mmsi=mmsi,
                    timestamp=ts.to_pydatetime(),
                    latitude=float(pos['lat']),
                    longitude=float(pos['lon']),
                    speed=float(pos['sog']),
                    course=float(pos['cog'])
                )
                session.add(vp)
                total_pos += 1
            
            if total_pos % 1000 == 0:
                await session.commit()
        await session.commit()
        print(f"✅ Добавлено {total_pos} позиций из CSV")
    
    await engine.dispose()
    print("\n🎉 Импорт завершён!")

if __name__ == "__main__":
    asyncio.run(import_ais())