# app/api/v1/endpoints/routes.py
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.database import get_db
from app.models.vessel import Vessel, VesselPosition
from app.services.route_service import route_service
from pydantic import BaseModel
from typing import List

router = APIRouter()

class OptimizeRouteRequest(BaseModel):
    waypoints: List[List[float]]  # [[lat, lon], [lat, lon], ...]

@router.post("/optimize")
async def optimize_route(
    request: OptimizeRouteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Оптимизация маршрута - сокращение точек на основе полученных waypoints"""
    try:
        waypoints = request.waypoints
        if not waypoints or len(waypoints) < 3:
            return {
                "route": waypoints,
                "type": "optimal",
                "distance_km": 0,
                "points_count": len(waypoints),
                "message": "Not enough points for optimization"
            }
        
        # Преобразуем в кортежи
        route_tuples = [(point[0], point[1]) for point in waypoints]
        
        # Строим оптимальный маршрут
        optimal_result = await route_service.build_optimal_route(route_tuples, db)
        return optimal_result
        
    except Exception as e:
        print(f"Error in optimize route: {e}")
        return {
            "route": request.waypoints,
            "type": "optimal",
            "distance_km": 0,
            "points_count": len(request.waypoints),
            "error": str(e)
        }

@router.get("/optimal")
async def get_optimal_route(
    mmsi: int,
    db: AsyncSession = Depends(get_db)
):
    """Идеальный маршрут - оптимизированная версия исторического маршрута для данного судна"""
    try:
        # 1. Получаем текущую позицию судна
        pos_result = await db.execute(
            text("""
                SELECT latitude, longitude 
                FROM vessel_positions 
                WHERE mmsi = :mmsi 
                ORDER BY timestamp DESC 
                LIMIT 1
            """),
            {"mmsi": mmsi}
        )
        current_pos = pos_result.fetchone()
        
        if not current_pos:
            return {
                "route": [],
                "type": "optimal",
                "distance_km": 0,
                "points_count": 0,
                "mmsi": mmsi,
                "message": "Current position not found"
            }
        
        current_lat = current_pos[0]
        current_lon = current_pos[1]
        
        # 2. Получаем порт назначения судна
        vessel_result = await db.execute(
            text("""
                SELECT destination_lat, destination_lon, name
                FROM vessels 
                WHERE mmsi = :mmsi
            """),
            {"mmsi": mmsi}
        )
        vessel = vessel_result.fetchone()
        
        dest_lat = None
        dest_lon = None
        if vessel and vessel[0] and vessel[1]:
            dest_lat = vessel[0]
            dest_lon = vessel[1]
        
        # 3. Ищем исторический маршрут (как в /historical)
        radius_deg = 10.0 / 111.0  # 10 км в градусах
        
        # Строим запрос для поиска маршрута рядом с текущей позицией
        query = text("""
            SELECT id, waypoints, port_origin, port_destination, geom
            FROM routes
            WHERE route_type = 'historical'
            AND ST_DWithin(
                geom,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                :radius
            )
            ORDER BY ST_Distance(
                geom,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            )
            LIMIT 1
        """)
        
        result = await db.execute(query, {
            "lat": current_lat,
            "lon": current_lon,
            "radius": radius_deg
        })
        row = result.fetchone()
        
        # Если не нашли по позиции, пробуем найти по порту назначения
        if not row and dest_lat and dest_lon:
            result = await db.execute(query, {
                "lat": dest_lat,
                "lon": dest_lon,
                "radius": radius_deg
            })
            row = result.fetchone()
        
        if not row:
            return {
                "route": [],
                "type": "optimal",
                "distance_km": 0,
                "points_count": 0,
                "mmsi": mmsi,
                "message": "No historical route found near vessel position or destination"
            }
        
        # 4. Получаем waypoints исторического маршрута
        waypoints = row[1]
        if isinstance(waypoints, str):
            waypoints = json.loads(waypoints)
        
        if not waypoints or len(waypoints) < 2:
            return {
                "route": [],
                "type": "optimal",
                "distance_km": 0,
                "points_count": 0,
                "mmsi": mmsi,
                "message": "Historical route has insufficient points"
            }
        
        # 5. Преобразуем в кортежи для обработки
        route_tuples = [(float(point[0]), float(point[1])) for point in waypoints]
        
        # 6. Строим идеальный (оптимизированный) маршрут
        optimal_result = await route_service.build_optimal_route(route_tuples, db)
        optimal_result["mmsi"] = mmsi
        optimal_result["port_origin"] = row[2]
        optimal_result["port_destination"] = row[3]
        
        return optimal_result
        
    except Exception as e:
        print(f"Error in optimal route: {e}")
        return {
            "route": [],
            "type": "optimal",
            "distance_km": 0,
            "points_count": 0,
            "mmsi": mmsi,
            "error": str(e)
        }

@router.get("/direct")
async def get_direct_route(
    mmsi: int,
    db: AsyncSession = Depends(get_db)
):
    return {"status": "disabled", "message": "Direct route temporarily unavailable"}
    # Получаем позицию судна
    pos_result = await db.execute(
        select(VesselPosition)
        .where(VesselPosition.mmsi == mmsi)
        .order_by(VesselPosition.timestamp.desc())
        .limit(1)
    )
    current_pos = pos_result.scalar_one_or_none()
    if not current_pos:
        raise HTTPException(status_code=404, detail="Current position not found")
    
    # Получаем судно
    vessel_result = await db.execute(select(Vessel).where(Vessel.mmsi == mmsi))
    vessel = vessel_result.scalar_one_or_none()
    if not vessel or not vessel.destination_lat or not vessel.destination_lon:
        raise HTTPException(status_code=404, detail="No destination for this vessel")
    
    # Находим ближайший порт к точке назначения
    nearest_port = await route_service.find_nearest_port(
        vessel.destination_lat, vessel.destination_lon, db
    )
    if not nearest_port:
        raise HTTPException(status_code=404, detail="No port found near destination")
    
    # Строим маршрут
    result = await route_service.build_direct_route_simple(
        start_lat=current_pos.latitude,
        start_lon=current_pos.longitude,
        end_lat=nearest_port["latitude"],
        end_lon=nearest_port["longitude"],
        db=db
    )
    
    result["mmsi"] = mmsi
    result["port"] = nearest_port
    return result


@router.get("/direct_simple")
async def get_direct_route_simple(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Простой прямой маршрут с обходом суши (только по координатам)
    """
    result = await route_service.build_direct_route_simple(
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
        db=db
    )
    return result


@router.get("/historical")
async def get_historical_route(
    mmsi: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Исторический маршрут, проходящий рядом с текущей позицией судна
    """
    # Получаем текущую позицию судна
    pos_result = await db.execute(
        select(VesselPosition)
        .where(VesselPosition.mmsi == mmsi)
        .order_by(VesselPosition.timestamp.desc())
        .limit(1)
    )
    current_pos = pos_result.scalar_one_or_none()
    
    if not current_pos:
        raise HTTPException(status_code=404, detail="Current position not found")
    
    # Получаем порт назначения судна (если есть)
    vessel_result = await db.execute(
        select(Vessel).where(Vessel.mmsi == mmsi)
    )
    vessel = vessel_result.scalar_one_or_none()
    
    destination_port = None
    if vessel and vessel.destination_lat and vessel.destination_lon:
        nearest_port = await route_service.find_nearest_port(
            vessel.destination_lat, vessel.destination_lon, db
        )
        if nearest_port:
            destination_port = nearest_port["name"]
    
    # Ищем исторический маршрут
    result = await route_service.find_historical_route_by_position(
        current_lat=current_pos.latitude,
        current_lon=current_pos.longitude,
        destination_port=destination_port,
        db=db,
        radius_km=10.0  # радиус 10 км
    )
    
    result["mmsi"] = mmsi
    return result


@router.get("/by_mmsi")
async def get_direct_route_by_mmsi(
    mmsi: int,
    dest_lat: float = None,
    dest_lon: float = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Прямой маршрут от текущей позиции судна до указанного порта
    """
    # Получаем текущую позицию судна
    pos_result = await db.execute(
        select(VesselPosition)
        .where(VesselPosition.mmsi == mmsi)
        .order_by(VesselPosition.timestamp.desc())
        .limit(1)
    )
    current_pos = pos_result.scalar_one_or_none()
    
    if not current_pos:
        raise HTTPException(status_code=404, detail="Current position not found")
    
    # Если координаты порта не указаны — пытаемся найти из данных судна
    if dest_lat is None or dest_lon is None:
        vessel_result = await db.execute(
            select(Vessel).where(Vessel.mmsi == mmsi)
        )
        vessel = vessel_result.scalar_one_or_none()
        
        if vessel and vessel.destination_lat and vessel.destination_lon:
            dest_lat = vessel.destination_lat
            dest_lon = vessel.destination_lon
        else:
            # По умолчанию — порт Владивосток
            dest_lat = 43.112
            dest_lon = 131.890
    
    # Строим маршрут с проверкой на сушу
    result = await route_service.build_direct_route_simple(
        start_lat=current_pos.latitude,
        start_lon=current_pos.longitude,
        end_lat=dest_lat,
        end_lon=dest_lon,
        db=db
    )
    
    # Добавляем информацию о судне
    result["mmsi"] = mmsi
    result["vessel_position"] = {"lat": current_pos.latitude, "lon": current_pos.longitude}
    
    return result


@router.get("/ports/near")
async def get_nearest_port(
    lat: float,
    lon: float,
    db: AsyncSession = Depends(get_db)
):
    nearest = await route_service.find_nearest_port(lat, lon, db)
    if not nearest:
        raise HTTPException(status_code=404, detail="No ports found")
    return nearest
