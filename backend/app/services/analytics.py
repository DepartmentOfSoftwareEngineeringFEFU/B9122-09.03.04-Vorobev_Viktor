import math
import numpy as np
from typing import Tuple, Optional
from datetime import datetime
from geopy.distance import distance as geopy_distance

class AnalyticsService:
    
    @staticmethod
    def calculate_distance_nautical_miles(lat1: float, lon1: float, 
                                          lat2: float, lon2: float) -> float:
        """Расчет расстояния между двумя точками в морских милях"""
        dist_km = geopy_distance((lat1, lon1), (lat2, lon2)).kilometers
        return dist_km * 0.539957  # перевод км в морские мили
    
    @staticmethod
    def calculate_cpa(lat1: float, lon1: float, speed1: float, course1: float,
                     lat2: float, lon2: float, speed2: float, course2: float) -> Tuple[float, float]:
        """
        Расчет DCPA (Distance to Closest Point of Approach) и TCPA (Time to CPA)
        Возвращает (dcpa_nautical_miles, tcpa_minutes)
        """
        # Перевод курса из градусов в радианы
        course1_rad = math.radians(course1)
        course2_rad = math.radians(course2)
        
        # Векторы скорости в узлах -> мили/минуту
        v1x = speed1 * math.sin(course1_rad) / 60
        v1y = speed1 * math.cos(course1_rad) / 60
        v2x = speed2 * math.sin(course2_rad) / 60
        v2y = speed2 * math.cos(course2_rad) / 60
        
        # Относительная скорость
        rel_vx = v2x - v1x
        rel_vy = v2y - v1y
        
        # Текущее относительное положение (в милях)
        # Упрощенное преобразование градусов в морские мили
        dx = (lon2 - lon1) * 60 * math.cos(math.radians((lat1 + lat2) / 2))
        dy = (lat2 - lat1) * 60
        
        # Время до ближайшей точки (в минутах)
        speed_rel_sq = rel_vx**2 + rel_vy**2
        if speed_rel_sq < 0.01:  # суда движутся синхронно
            tcpa = 0
            dcpa = math.sqrt(dx**2 + dy**2)
        else:
            tcpa = -(dx*rel_vx + dy*rel_vy) / speed_rel_sq
            if tcpa < 0:
                tcpa = 0
            dcpa = abs( (dx*rel_vy - dy*rel_vx) / math.sqrt(speed_rel_sq) )
        
        return dcpa, tcpa
    
    @staticmethod
    def calculate_speed_from_positions(lat1: float, lon1: float, time1: datetime,
                                       lat2: float, lon2: float, time2: datetime) -> float:
        """Расчет скорости по двум позициям (узлы)"""
        distance_nm = AnalyticsService.calculate_distance_nautical_miles(lat1, lon1, lat2, lon2)
        delta_time_hours = (time2 - time1).total_seconds() / 3600
        
        if delta_time_hours > 0:
            return distance_nm / delta_time_hours
        return 0.0
    
    @staticmethod
    def is_point_in_polygon(lat: float, lon: float, polygon_coords: list) -> bool:
        """Проверка, находится ли точка внутри полигона (алгоритм пересечения лучей)"""
        # Упрощенная реализация, в production использовать shapely
        from shapely.geometry import Point, Polygon
        
        point = Point(lon, lat)  # shapely принимает (x, y) -> (lon, lat)
        polygon = Polygon(polygon_coords)
        return polygon.contains(point)
    
    @staticmethod
    def calculate_cluster_statistics(positions: list) -> dict:
        """
        Расчет метрик для кластера судов
        positions: список словарей с latitude, longitude, speed
        """
        if not positions:
            return {}
        
        speeds = [p.get('speed', 0) for p in positions]
        courses = [p.get('course', 0) for p in positions]
        
        return {
            'vessel_count': len(positions),
            'avg_speed': np.mean(speeds),
            'std_speed': np.std(speeds),
            'avg_course': np.mean(courses),
            'std_course': np.std(courses),
            'min_speed': min(speeds),
            'max_speed': max(speeds)
        }