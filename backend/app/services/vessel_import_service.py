# app/services/vessel_import_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import pandas as pd

class VesselImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def map_vessel_type(self, vessel_type_value) -> str:
        """Маппинг типов судов по стандарту ITU-R M.1371-5"""
        try:
            type_code = int(float(vessel_type_value))
        except (ValueError, TypeError):
            return 'OTHER'
        
        type_map = {
            **dict.fromkeys(range(20, 30), 'WIG'),
            **dict.fromkeys([30, 32, 33, 34, 35, 36, 37, 38, 39], 'FISHING'),
            31: 'TUG',
            **dict.fromkeys(range(40, 46), 'DIVING'),
            **dict.fromkeys(range(46, 50), 'DREDGER'),
            50: 'PILOT',
            51: 'SAR',
            **dict.fromkeys(range(52, 60), 'TUG'),
            **dict.fromkeys(range(60, 70), 'PASSENGER'),
            **dict.fromkeys(range(70, 79), 'CARGO'),
            79: 'PLEASURE',
            **dict.fromkeys(range(80, 90), 'TANKER'),
            **dict.fromkeys(range(90, 100), 'OTHER'),
            200: 'WIG',
            201: 'WIG',
        }
        
        return type_map.get(type_code, 'OTHER')
    
    async def import_vessels_from_df(self, df: pd.DataFrame, user_id: int = None) -> dict:
        """Импорт судов и позиций из DataFrame"""
        
        print(f"🔄 Importing...")
        
        # Очищаем таблицы перед импортом (так как user_id больше нет)
        await self.db.execute(text("DELETE FROM vessel_positions"))
        await self.db.execute(text("DELETE FROM vessels"))
        await self.db.commit()
        print("🧹 Cleared existing data")
        
        vessels_imported = 0
        positions_imported = 0
        
        for mmsi, group in df.groupby('MMSI'):
            mmsi_int = int(mmsi)
            first_row = group.iloc[0]
            
            vessel_name = first_row.get('VesselName')
            if pd.isna(vessel_name) or not vessel_name:
                vessel_name = f"Ship_{mmsi_int}"
            else:
                vessel_name = str(vessel_name)[:100]
            
            vessel_type_code = first_row.get('VesselType', 'OTHER')
            vessel_type = self.map_vessel_type(vessel_type_code)
            
            length = first_row.get('Length', 0)
            if pd.isna(length):
                length = 0
            else:
                length = float(length)
            
            dest_lat = first_row.get('dest_lat')
            dest_lon = first_row.get('dest_lon')
            if pd.isna(dest_lat):
                dest_lat = None
            else:
                dest_lat = float(dest_lat)
            
            if pd.isna(dest_lon):
                dest_lon = None
            else:
                dest_lon = float(dest_lon)
            
            # ВСТАВКА СУДНА (БЕЗ user_id)
            await self.db.execute(
                text("""
                    INSERT INTO vessels (mmsi, name, vessel_type, length, destination_lat, destination_lon, created_at, updated_at)
                    VALUES (:mmsi, :name, :type, :length, :dest_lat, :dest_lon, NOW(), NOW())
                """),
                {
                    "mmsi": mmsi_int,
                    "name": vessel_name,
                    "type": vessel_type,
                    "length": length,
                    "dest_lat": dest_lat,
                    "dest_lon": dest_lon
                }
            )
            vessels_imported += 1
            
            # ВСТАВКА ПОЗИЦИЙ (БЕЗ user_id)
            for _, row in group.iterrows():
                try:
                    timestamp = pd.to_datetime(row['BaseDateTime'])
                    
                    lat = float(row['LAT'])
                    lon = float(row['LON'])
                    if abs(lat) > 90 or abs(lon) > 180:
                        continue
                    
                    speed = float(row['SOG']) if pd.notna(row['SOG']) else 0
                    course = float(row['COG']) if pd.notna(row['COG']) else 0
                    
                    await self.db.execute(
                        text("""
                            INSERT INTO vessel_positions (mmsi, timestamp, latitude, longitude, speed, course)
                            VALUES (:mmsi, :timestamp, :lat, :lon, :speed, :course)
                        """),
                        {
                            "mmsi": mmsi_int,
                            "timestamp": timestamp.to_pydatetime(),
                            "lat": lat,
                            "lon": lon,
                            "speed": speed,
                            "course": course
                        }
                    )
                    positions_imported += 1
                    
                except Exception as e:
                    print(f"Error importing position for {mmsi}: {e}")
                    continue
            
            if vessels_imported % 10 == 0:
                await self.db.commit()
                print(f"  Progress: {vessels_imported} vessels, {positions_imported} positions")
        
        await self.db.commit()
        
        print(f"✅ Imported: {vessels_imported} vessels, {positions_imported} positions")
        
        return {
            "vessels_imported": vessels_imported,
            "positions_imported": positions_imported,
            "note": "Historical routes were NOT affected"
        }