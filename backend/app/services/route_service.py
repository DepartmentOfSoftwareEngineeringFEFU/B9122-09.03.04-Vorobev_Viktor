import math
import random
import json
from typing import List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.route import Route, Port
from app.models.vessel import VesselPosition
from functools import lru_cache

class RouteService:
    def __init__(self):
        self.waypoints = {
            "port_entry": {"lat": 43.1120, "lon": 131.8900},
            "fairway_center": {"lat": 43.1150, "lon": 131.8880},
            "fairway_north": {"lat": 43.1180, "lon": 131.8850},
            "fairway_south": {"lat": 43.1090, "lon": 131.8930},
            "anchorage": {"lat": 43.1080, "lon": 131.8950},
            "turning_basin": {"lat": 43.1130, "lon": 131.8880},
        }
        
        self.obstacles = [
            {"lat_min": 43.122, "lat_max": 43.128, "lon_min": 131.885, "lon_max": 131.895},
            {"lat_min": 43.005, "lat_max": 43.080, "lon_min": 131.850, "lon_max": 131.885},
            {"lat_min": 43.135, "lat_max": 43.150, "lon_min": 131.865, "lon_max": 131.880},
            {"lat_min": 43.102, "lat_max": 43.108, "lon_min": 131.896, "lon_max": 131.905},
            {"lat_min": 43.115, "lat_max": 43.122, "lon_min": 131.873, "lon_max": 131.878},
        ]
        
        self.base_routes = {
            "tanker": [
                {"lat": 43.120, "lon": 131.878},
                {"lat": 43.118, "lon": 131.882},
                {"lat": 43.115, "lon": 131.885},
                {"lat": 43.112, "lon": 131.890},
            ],
            "container": [
                {"lat": 43.108, "lon": 131.892},
                {"lat": 43.110, "lon": 131.890},
                {"lat": 43.112, "lon": 131.890},
            ],
            "passenger": [
                {"lat": 43.112, "lon": 131.890},
                {"lat": 43.114, "lon": 131.888},
                {"lat": 43.115, "lon": 131.885},
            ],
            "fishing": [
                {"lat": 43.125, "lon": 131.882},
                {"lat": 43.120, "lon": 131.885},
                {"lat": 43.115, "lon": 131.885},
            ],
            "tug": [
                {"lat": 43.112, "lon": 131.890},
                {"lat": 43.115, "lon": 131.885},
                {"lat": 43.113, "lon": 131.888},
            ],
        }
        
        self.water_zones = []
        self.land_check_cache = {}
        self.line_water_cache = {}  # Новый кеш для is_line_on_water
        
    def _is_in_vladivostok_bay(self, lat: float, lon: float) -> bool:
        if 43.105 <= lat <= 43.125 and 131.875 <= lon <= 131.895:
            return True
        if 43.09 <= lat <= 43.14 and 131.70 <= lon <= 131.82:
            return True
        if 43.10 <= lat <= 43.18 and 131.89 <= lon <= 132.05:
            return True
        return False
    
    def _point_in_polygon(self, lat: float, lon: float, polygon: List[Tuple]) -> bool:
        inside = False
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            if ((y1 > lon) != (y2 > lon)) and (lat < (x2 - x1) * (lon - y1) / (y2 - y1) + x1):
                inside = not inside
        return inside
    
    def is_point_in_water(self, lat: float, lon: float) -> bool:
        if self._is_in_vladivostok_bay(lat, lon):
            return True
        for polygon in self.water_zones:
            if self._point_in_polygon(lat, lon, polygon):
                return True
        return False
        
    async def is_point_on_land(self, lat: float, lon: float, db: AsyncSession, 
                            precision: int = 4, skip_ports: bool = True) -> bool:
        cache_key = (round(lat, precision), round(lon, precision))
        
        if cache_key in self.land_check_cache:
            return self.land_check_cache[cache_key]
        
        try:
            query = text("""
                SELECT EXISTS (
                    SELECT 1 FROM land_polygons
                    WHERE ST_DWithin(
                        geom, 
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 
                        0.01
                    )
                    AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    LIMIT 1
                ) as is_on_land
            """)
            result = await db.execute(query, {"lat": lat, "lon": lon})
            is_on_land = result.scalar()
            
            result_bool = bool(is_on_land) if is_on_land is not None else False
            
            if result_bool and skip_ports:
                port_query = text("""
                    SELECT EXISTS (
                        SELECT 1 FROM ports_global
                        WHERE ST_DWithin(
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                            ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                            0.02
                        )
                        LIMIT 1
                    ) as is_near_port
                """)
                port_result = await db.execute(port_query, {"lat": lat, "lon": lon})
                is_near_port = port_result.scalar()
                
                if is_near_port:
                    print(f"Точка на суше, но рядом порт — считаем водой")
                    result_bool = False
            
            self.land_check_cache[cache_key] = result_bool
            return result_bool
            
        except Exception as e:
            print(f"Ошибка в is_point_on_land: {e}")
            return False
    
    async def is_line_on_water(self, start_lat: float, start_lon: float,
                                end_lat: float, end_lon: float,
                                db: AsyncSession) -> bool:
        
        cache_key = (round(start_lat, 5), round(start_lon, 5), 
                     round(end_lat, 5), round(end_lon, 5))
        
        if cache_key in self.line_water_cache:
            return self.line_water_cache[cache_key]
        
        try:
            query = text("""
                SELECT NOT EXISTS (
                    SELECT 1 FROM land_polygons
                    WHERE ST_Intersects(
                        ST_SetSRID(ST_MakeLine(
                            ST_MakePoint(:lon1, :lat1),
                            ST_MakePoint(:lon2, :lat2)
                        ), 4326),
                        geom
                    )
                    LIMIT 1
                ) as is_on_water
            """)
            result = await db.execute(query, {
                "lat1": start_lat, "lon1": start_lon,
                "lat2": end_lat, "lon2": end_lon
            })
            is_water = result.scalar() or False
            
            self.line_water_cache[cache_key] = is_water
            return is_water
        except Exception as e:
            print(f"Ошибка проверки линии: {e}")
            return await self._check_line_by_points(start_lat, start_lon, end_lat, end_lon, db)

    async def _check_line_by_points(self, start_lat: float, start_lon: float,
                                    end_lat: float, end_lon: float,
                                    db: AsyncSession, steps: int = 20) -> bool:
        for i in range(steps + 1):
            t = i / steps
            mid_lat = start_lat + (end_lat - start_lat) * t
            mid_lon = start_lon + (end_lon - start_lon) * t
            
            if await self.is_point_on_land(mid_lat, mid_lon, db):
                return False
        return True

    async def build_optimal_route(self, historical_route: List[Tuple[float, float]], db: AsyncSession) -> Dict[str, Any]:

        if not historical_route or len(historical_route) < 3:
            return {
                "route": [[lat, lon] for lat, lon in historical_route] if historical_route else [],
                "type": "optimal",
                "distance_km": 0,
                "points_count": len(historical_route),
                "message": "Not enough points for optimization"
            }
        
        optimized = []
        i = 0
        
        while i < len(historical_route):
            optimized.append(historical_route[i])
            
            if i < len(historical_route) - 1:
                furthest = i + 1
                
                for j in range(len(historical_route) - 1, i, -1):
                    start = historical_route[i]
                    end = historical_route[j]
                    
                    is_water = await self.is_line_on_water(
                        start[0], start[1],
                        end[0], end[1],
                        db
                    )
                    
                    if is_water:
                        furthest = j
                        break
                
                if furthest > i + 1:
                    i = furthest
                else:
                    i += 1
            else:
                i += 1
        
        unique_route = []
        for point in optimized:
            if not unique_route or unique_route[-1] != point:
                unique_route.append(point)
        
        original_distance = 0
        for i in range(1, len(historical_route)):
            original_distance += self.calculate_distance(
                historical_route[i-1][0], historical_route[i-1][1],
                historical_route[i][0], historical_route[i][1]
            )
        
        optimal_distance = 0
        for i in range(1, len(unique_route)):
            optimal_distance += self.calculate_distance(
                unique_route[i-1][0], unique_route[i-1][1],
                unique_route[i][0], unique_route[i][1]
            )
        
        return {
            "route": [[lat, lon] for lat, lon in unique_route],
            "type": "optimal",
            "distance_km": round(optimal_distance, 2),
            "original_distance_km": round(original_distance, 2),
            "points_count": len(unique_route),
            "original_points": len(historical_route),
            "reduction_percent": round((1 - optimal_distance / original_distance) * 100, 1) if original_distance > 0 else 0,
            "savings_km": round(original_distance - optimal_distance, 2)
        }

    def _calculate_angle(self, a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
        import math
        
        ba_x = a[0] - b[0]
        ba_y = a[1] - b[1]
        
        bc_x = c[0] - b[0]
        bc_y = c[1] - b[1]
        
        ba_len = math.sqrt(ba_x**2 + ba_y**2)
        bc_len = math.sqrt(bc_x**2 + bc_y**2)
        
        if ba_len < 0.0001 or bc_len < 0.0001:
            return 0
        
        dot = ba_x * bc_x + ba_y * bc_y
        
        cos_angle = dot / (ba_len * bc_len)
        cos_angle = max(-1, min(1, cos_angle))
        
        angle_rad = math.acos(cos_angle)
        
        return angle_rad * 180 / math.pi

    async def check_if_over_land(self, start_lat: float, start_lon: float,
                                end_lat: float, end_lon: float,
                                db: AsyncSession, steps: int = 5) -> bool:

        print(f"\nПроверка сегмента на водность...")
        
        distance = self.calculate_distance(start_lat, start_lon, end_lat, end_lon)
        if distance > 5000:  # >5000 км
            actual_steps = max(steps, 10)
        elif distance > 1000:
            actual_steps = max(steps, 7)
        else:
            actual_steps = steps
        
        print(f"   Расстояние: {distance:.0f} км, шагов: {actual_steps}")
        
        for i in range(1, actual_steps):
            t = i / actual_steps
            mid_lat = start_lat + (end_lat - start_lat) * t
            mid_lon = start_lon + (end_lon - start_lon) * t
            
            if await self.is_point_on_land(mid_lat, mid_lon, db):
                print(f"Сегмент проходит через сушу (точка {i}/{actual_steps-1})")
                return False
        
        print(f"Быстрая проверка пройдена")
        
        is_water = await self.is_line_on_water(start_lat, start_lon, end_lat, end_lon, db)
        
        if is_water:
            print(f"Весь сегмент на воде")
        else:
            print(f"Сегмент пересекает сушу (проверка линии)")
        
        return is_water

    async def _does_line_cross_land(self, lat1: float, lon1: float,
                                    lat2: float, lon2: float,
                                    db: AsyncSession) -> bool:

        query = text("""
            SELECT EXISTS (
                SELECT 1 FROM land_polygons
                WHERE ST_Intersects(
                    ST_SetSRID(ST_MakeLine(
                        ST_MakePoint(:lon1, :lat1),
                        ST_MakePoint(:lon2, :lat2)
                    ), 4326),
                    geom
                )
                LIMIT 1
            ) as crosses
        """)
        result = await db.execute(query, {
            "lat1": lat1, "lon1": lon1,
            "lat2": lat2, "lon2": lon2
        })
        return result.scalar() or False
        

    async def build_direct_route_simple(self, start_lat: float, start_lon: float,
                                            end_lat: float, end_lon: float,
                                            db: AsyncSession) -> Dict[str, Any]:

        print(f"\n{'='*60}")
        print(f"Построение маршрута: ({start_lat}, {start_lon}) -> ({end_lat}, {end_lon})")
        
        call_count = 0
        visited_points = set()

        bypass_cache = {}
        
        async def get_bypass_cache_key(p1_lat, p1_lon, p2_lat, p2_lon):
            return (round(p1_lat, 4), round(p1_lon, 4), round(p2_lat, 4), round(p2_lon, 4))
        
        async def find_bypass_point_fast(p1_lat, p1_lon, p2_lat, p2_lon, depth):
            cache_key = await get_bypass_cache_key(p1_lat, p1_lon, p2_lat, p2_lon)
            if cache_key in bypass_cache:
                return bypass_cache[cache_key]
            
            mid_lat = (p1_lat + p2_lat) / 2
            mid_lon = (p1_lon + p2_lon) / 2
            
            for radius in [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]:
                for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
                    rad = math.radians(angle)
                    test_lat = mid_lat + radius * math.cos(rad)
                    test_lon = mid_lon + radius * math.sin(rad)
                    
                    point_key = (round(test_lat, 4), round(test_lon, 4))
                    if point_key in visited_points:
                        continue
                    
                    if await self.is_point_on_land(test_lat, test_lon, db):
                        continue
                    
                    seg1_ok = await self.is_line_on_water(p1_lat, p1_lon, test_lat, test_lon, db)
                    seg2_ok = await self.is_line_on_water(test_lat, test_lon, p2_lat, p2_lon, db)
                    
                    if seg1_ok and seg2_ok:
                        result = (test_lat, test_lon)
                        bypass_cache[cache_key] = result
                        return result
            
            for radius in [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]:
                for angle in [0, 90, 180, 270]: 
                    rad = math.radians(angle)
                    test_lat = mid_lat + radius * math.cos(rad)
                    test_lon = mid_lon + radius * math.sin(rad)
                    
                    point_key = (round(test_lat, 4), round(test_lon, 4))
                    if point_key in visited_points:
                        continue
                    
                    if await self.is_point_on_land(test_lat, test_lon, db):
                        continue
                    
                    if await self.is_line_on_water(p1_lat, p1_lon, test_lat, test_lon, db):
                        result = (test_lat, test_lon)
                        bypass_cache[cache_key] = result
                        return result
                    
                    if await self.is_line_on_water(test_lat, test_lon, p2_lat, p2_lon, db):
                        result = (test_lat, test_lon)
                        bypass_cache[cache_key] = result
                        return result
            
            bypass_cache[cache_key] = None
            return None
        
        async def build_route_recursive(p1_lat, p1_lon, p2_lat, p2_lon, depth=0):
            nonlocal call_count
            call_count += 1
            
            if depth > 30: 
                return [(p1_lat, p1_lon), (p2_lat, p2_lon)]
            
            distance = self.calculate_distance(p1_lat, p1_lon, p2_lat, p2_lon)
            if distance < 0.3:
                return [(p1_lat, p1_lon), (p2_lat, p2_lon)]
            
            is_water = await self.is_line_on_water(p1_lat, p1_lon, p2_lat, p2_lon, db)
            
            if is_water:
                if depth == 0:  
                    print(f"Прямой путь по воде ({distance:.1f} км)")
                return [(p1_lat, p1_lon), (p2_lat, p2_lon)]
            
            if depth == 0:
                print(f"Нужен объезд ({distance:.1f} км)")
            
            waypoint = await find_bypass_point_fast(p1_lat, p1_lon, p2_lat, p2_lon, depth)
            
            if waypoint is None:
                return [(p1_lat, p1_lon), (p2_lat, p2_lon)]
            
            visited_points.add((round(waypoint[0], 4), round(waypoint[1], 4)))
            
            part1 = await build_route_recursive(p1_lat, p1_lon, waypoint[0], waypoint[1], depth + 1)
            part2 = await build_route_recursive(waypoint[0], waypoint[1], p2_lat, p2_lon, depth + 1)
            
            return part1 + part2[1:]
        
        full_route = await build_route_recursive(start_lat, start_lon, end_lat, end_lon)
        
        unique_route = []
        for point in full_route:
            if not unique_route:
                unique_route.append(point)
            else:
                last = unique_route[-1]
                if self.calculate_distance(last[0], last[1], point[0], point[1]) > 0.1:
                    unique_route.append(point)
        
        if unique_route[-1] != (end_lat, end_lon):
            unique_route.append((end_lat, end_lon))
        
        total_distance = 0
        for i in range(1, len(unique_route)):
            total_distance += self.calculate_distance(
                unique_route[i-1][0], unique_route[i-1][1],
                unique_route[i][0], unique_route[i][1]
            )
        
        print(f"Статистика: {call_count} итераций, {len(unique_route)} точек, {total_distance:.0f} км")
        
        return {
            "route": [[lat, lon] for lat, lon in unique_route],
            "type": "direct_simple",
            "distance_km": round(total_distance, 2),
            "points_count": len(unique_route),
            "start": {"lat": start_lat, "lon": start_lon},
            "destination": {"lat": end_lat, "lon": end_lon}
        }
    
    def calculate_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        R = 6371
        lat1, lat2 = math.radians(lat1), math.radians(lat2)
        lon1, lon2 = math.radians(lon1), math.radians(lon2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(min(1, math.sqrt(a)))
        return R * c
    
    def is_in_obstacle(self, lat: float, lon: float) -> bool:
        for obs in self.obstacles:
            if (obs["lat_min"] <= lat <= obs["lat_max"] and 
                obs["lon_min"] <= lon <= obs["lon_max"]):
                return True
        return False
    
    def is_in_water(self, lat: float, lon: float) -> bool:
        if 43.105 <= lat <= 43.125 and 131.875 <= lon <= 131.895:
            return not self.is_in_obstacle(lat, lon)
        if 43.09 <= lat <= 43.14 and 131.70 <= lon <= 131.82:
            return True
        if 43.10 <= lat <= 43.18 and 131.89 <= lon <= 132.05:
            return True
        return False
    
    def correct_to_water(self, lat: float, lon: float) -> Tuple[float, float]:
        if self.is_in_water(lat, lon):
            return (lat, lon)
        
        best_lat, best_lon = lat, lon
        min_dist = float('inf')
        
        for name, wp in self.waypoints.items():
            dist = self.calculate_distance(lat, lon, wp["lat"], wp["lon"])
            if dist < min_dist:
                min_dist = dist
                best_lat, best_lon = wp["lat"], wp["lon"]
        
        for obs in self.obstacles:
            corners = [
                (obs["lat_min"], obs["lon_min"]), (obs["lat_min"], obs["lon_max"]),
                (obs["lat_max"], obs["lon_min"]), (obs["lat_max"], obs["lon_max"])
            ]
            for c_lat, c_lon in corners:
                dist = self.calculate_distance(lat, lon, c_lat, c_lon)
                if dist < min_dist:
                    min_dist = dist
                    best_lat, best_lon = c_lat, c_lon
        
        return (best_lat, best_lon)
        
    def build_direct_route(self, start: Tuple[float, float], 
                           destination: Tuple[float, float],
                           vessel_type: str = None) -> List[Tuple[float, float]]:
        s_lat, s_lon = self.correct_to_water(start[0], start[1])
        d_lat, d_lon = self.correct_to_water(destination[0], destination[1])
        
        route = [(s_lat, s_lon)]
        
        steps = 10
        need_waypoint = False
        
        for i in range(1, steps):
            t = i / steps
            mid_lat = s_lat + (d_lat - s_lat) * t
            mid_lon = s_lon + (d_lon - s_lon) * t
            
            if not self.is_in_water(mid_lat, mid_lon):
                need_waypoint = True
                break
        
        if need_waypoint:
            waypoint = self.waypoints["fairway_center"]
            route.append((waypoint["lat"], waypoint["lon"]))
        
        route.append((d_lat, d_lon))
        return route
    
    def build_safe_route(self, start: Tuple[float, float], 
                         destination: Tuple[float, float],
                         vessel_type: str = None) -> List[Tuple[float, float]]:
        s_lat, s_lon = self.correct_to_water(start[0], start[1])
        d_lat, d_lon = self.correct_to_water(destination[0], destination[1])
        
        route = [(s_lat, s_lon)]
        
        base_route = []
        if vessel_type and vessel_type in self.base_routes:
            base_route = self.base_routes[vessel_type]
        else:
            base_route = [
                {"lat": 43.115, "lon": 131.885},
                {"lat": 43.112, "lon": 131.890},
            ]
        
        for point in reversed(base_route):
            dist_to_start = self.calculate_distance(s_lat, s_lon, point["lat"], point["lon"])
            dist_to_dest = self.calculate_distance(d_lat, d_lon, point["lat"], point["lon"])
            
            if dist_to_start < self.calculate_distance(s_lat, s_lon, d_lat, d_lon) * 1.2:
                route.append((point["lat"], point["lon"]))
        
        route.append((d_lat, d_lon))
        
        unique_route = []
        for point in route:
            if point not in unique_route:
                unique_route.append(point)
        
        return unique_route
    
    async def build_historical_route(self, mmsi: int, db: AsyncSession) -> List[Tuple[float, float]]:

        result = await db.execute(
            select(VesselPosition)
            .where(VesselPosition.mmsi == mmsi)
            .order_by(VesselPosition.timestamp.desc())
            .limit(20)
        )
        positions = result.scalars().all()
        
        if not positions:
            return []
        
        route = []
        for pos in positions:
            point = (pos.latitude, pos.longitude)
            if point not in route:
                route.append(point)
        
        min_distance = 0.3
        smoothed = [route[0]] if route else []
        
        for point in route[1:]:
            last = smoothed[-1]
            dist = self.calculate_distance(last[0], last[1], point[0], point[1])
            if dist > min_distance:
                smoothed.append(point)
        
        return smoothed
    
    def build_route_to_port(self, vessel_lat: float, vessel_lon: float,
                            port_lat: float = None, port_lon: float = None,
                            port_name: str = None,
                            route_type: str = "safe",
                            vessel_type: str = None) -> Dict[str, Any]:
        if port_lat is None or port_lon is None:
            if port_name:
                default_ports = {
                    "центр": (43.115, 131.885),
                    "феско": (43.108, 131.892),
                    "пассажирский": (43.112, 131.890),
                    "нефтяной": (43.120, 131.878),
                    "рыбный": (43.125, 131.882),
                }
                port_lat, port_lon = default_ports.get(port_name.lower(), (43.115, 131.885))
            else:
                port_lat, port_lon = 43.115, 131.885
        
        start = (vessel_lat, vessel_lon)
        destination = (port_lat, port_lon)
        
        if route_type == "direct":
            route = self.build_direct_route(start, destination, vessel_type)
        elif route_type == "safe":
            route = self.build_safe_route(start, destination, vessel_type)
        else:
            route = [start, destination]
        
        total_distance = 0
        for i in range(1, len(route)):
            total_distance += self.calculate_distance(
                route[i-1][0], route[i-1][1],
                route[i][0], route[i][1]
            )
        
        return {
            "route": [[lat, lon] for lat, lon in route],
            "type": route_type,
            "distance_km": round(total_distance, 2),
            "points_count": len(route),
            "start": {"lat": start[0], "lon": start[1]},
            "destination": {"lat": destination[0], "lon": destination[1]}
        }
    
    def get_waypoints_info(self) -> List[Dict]:
        return [
            {"name": name, "lat": wp["lat"], "lon": wp["lon"]}
            for name, wp in self.waypoints.items()
        ]
    
    def get_obstacles_info(self) -> List[Dict]:
        return self.obstacles
    
    async def find_nearest_port(self, lat: float, lon: float, db: AsyncSession):
        query = text("""
            SELECT 
                port_name,
                country,
                latitude,
                longitude,
                (6371 * acos(
                    cos(radians(:lat)) * cos(radians(latitude)) *
                    cos(radians(longitude) - radians(:lon)) +
                    sin(radians(:lat)) * sin(radians(latitude))
                )) AS distance_km
            FROM ports_global
            ORDER BY distance_km
            LIMIT 1
        """)
        
        result = await db.execute(query, {"lat": lat, "lon": lon})
        port = result.fetchone()
        
        if port:
            return {
                "name": port[0],
                "country": port[1],
                "latitude": port[2],
                "longitude": port[3],
                "distance_km": round(port[4], 2)
            }
        return None
    
    async def find_water_waypoint(self, lat: float, lon: float, db: AsyncSession) -> Tuple[float, float]:
        
        print(f"Поиск водной точки рядом с ({lat:.4f}, {lon:.4f})")
        
        radii = [0.05, 0.1, 0.2, 0.3, 0.5, 1.0]
        
        for radius in radii:
            for angle in range(0, 360, 45):  
                rad = math.radians(angle)
                test_lat = lat + radius * math.cos(rad)
                test_lon = lon + radius * math.sin(rad)
                
                if not await self.is_point_on_land(test_lat, test_lon, db, precision=4):
                    print(f"Найдена водная точка: ({test_lat:.4f}, {test_lon:.4f})")
                    return (test_lat, test_lon)
        
        print(f"Водная точка не найдена, возвращаем исходную")
        return (lat, lon)
    
    async def find_historical_route_by_position(self, current_lat: float, current_lon: float, destination_port: str = None,db: AsyncSession = None,radius_km: float = 5.0) -> Dict[str, Any]:
        """
        Ищет исторический маршрут, проходящий рядом с текущей позицией судна
        
        Args:
            current_lat, current_lon: текущая позиция судна
            destination_port: порт назначения (опционально)
            db: сессия БД
            radius_km: радиус поиска в км (по умолчанию 5 км)
        
        Returns:
            dict: маршрут или сообщение об отсутствии
        """
        # Конвертируем км в градусы (приблизительно)
        radius_deg = radius_km / 111.0
        
        query = text("""
            SELECT 
                id, 
                waypoints, 
                port_origin, 
                port_destination,
                ST_Distance(
                    geom,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                ) as distance
            FROM routes
            WHERE route_type = 'historical'
            AND ST_DWithin(
                geom,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                :radius
            )
        """)
        
        params = {"lat": current_lat, "lon": current_lon, "radius": radius_deg}
        
        if destination_port:
            query = text(str(query) + " AND port_destination = :dest_port")
            params["dest_port"] = destination_port
        
        query = text(str(query) + " ORDER BY distance LIMIT 1")
        
        result = await db.execute(query, params)
        row = result.fetchone()
        
        if row:
            return {
                "route": row[1] if isinstance(row[1], list) else json.loads(row[1]),
                "type": "historical",
                "port_origin": row[2],
                "port_destination": row[3],
                "distance_km": round(row[4] * 111.0, 2)
            }
        
        return {
            "route": [],
            "type": "historical",
            "message": "Historical route not found near current position"
        }


route_service = RouteService()