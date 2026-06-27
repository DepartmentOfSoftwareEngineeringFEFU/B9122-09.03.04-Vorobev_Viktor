# backend/import_gpkg_tracks.py
import asyncio
import geopandas as gpd
import json
import os
from shapely.geometry import LineString, Polygon, Point
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.route import Route
from app.services.route_service import route_service

# Координаты квадрата Мексиканского залива
POLYGON_COORDS = [
    (-94.9290, 30.3364),
    (-88.5240, 30.9728),
    (-87.6890, 27.9935),
    (-94.2918, 27.8959),
    (-94.9290, 30.3364)  # замыкаем
]

def create_filter_polygon():
    """Создает полигон для фильтрации маршрутов"""
    return Polygon(POLYGON_COORDS)

def check_route_in_polygon(geom, polygon):
    """Проверяет, находится ли маршрут внутри полигона"""
    if geom is None or geom.is_empty:
        return False
    
    try:
        if geom.geom_type == 'LineString':
            # Проверяем любую точку маршрута
            for coord in geom.coords:
                point = Point(coord[0], coord[1])
                if polygon.contains(point) or polygon.intersects(point):
                    return True
            return polygon.intersects(geom)
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                if polygon.intersects(line):
                    return True
        return False
    except Exception as e:
        print(f"Ошибка проверки полигона: {e}")
        return False

async def import_gpkg_tracks():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    file_path = r"C:\Users\Vivorik\Desktop\ВКР\Monitoring_system\backend\AISVesselTracks2023.gpkg"
    
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        return
    
    print(f"Чтение GeoPackage: {file_path}")
    print(f"Фильтр по квадрату: {POLYGON_COORDS}")
    
    # Читаем файл
    gdf = gpd.read_file(file_path)
    print(f"Загружено {len(gdf)} треков")
    
    # Создаем полигон для фильтрации
    filter_polygon = create_filter_polygon()
    print(f"Полигон создан")
    
    async with async_session() as session:
        # Удаляем старые исторические маршруты
        print("Удаление старых исторических маршрутов...")
        await session.execute(text("DELETE FROM routes WHERE route_type = 'historical'"))
        await session.commit()
        print("Старые маршруты удалены")
        
        count = 0
        skipped = 0
        
        for idx, row in gdf.iterrows():
            geom = row['geometry']
            if geom is None or geom.is_empty:
                skipped += 1
                continue
            
            # Проверяем, находится ли маршрут в нашем квадрате
            if not check_route_in_polygon(geom, filter_polygon):
                skipped += 1
                continue
            
            # Получаем координаты
            if geom.geom_type == 'LineString':
                coords = list(geom.coords)
            elif geom.geom_type == 'MultiLineString':
                coords = []
                for line in geom.geoms:
                    coords.extend(list(line.coords))
            else:
                skipped += 1
                continue
            
            if len(coords) < 2:
                skipped += 1
                continue
            
            # Первая и последняя точки
            start_lon, start_lat = coords[0]
            end_lon, end_lat = coords[-1]
            
            # Находим ближайшие порты
            start_port = await route_service.find_nearest_port(start_lat, start_lon, session)
            end_port = await route_service.find_nearest_port(end_lat, end_lon, session)
            
            # Преобразуем координаты в (lat, lon) для waypoints
            waypoints = [[lat, lon] for lon, lat in coords]
            
            # Создаём геометрию LINESTRING
            line_geom = LineString(coords)
            
            # Сохраняем маршрут
            route = Route(
                vessel_mmsi=None,
                route_type="historical",
                waypoints=waypoints,
                geom=f"SRID=4326;{line_geom.wkt}",
                port_origin=start_port['name'] if start_port else None,
                port_destination=end_port['name'] if end_port else None
            )
            session.add(route)
            count += 1
            
            if count % 100 == 0:
                await session.commit()
                print(f"   Добавлено {count} маршрутов...")
        
        await session.commit()
        print(f"\nРезультаты импорта:")
        print(f"   Добавлено: {count} маршрутов")
        print(f"   Пропущено (вне квадрата или ошибки): {skipped}")
        print(f"   Всего обработано: {count + skipped}")
    
    await engine.dispose()
    print("\nИмпорт завершён!")

if __name__ == "__main__":
    asyncio.run(import_gpkg_tracks())