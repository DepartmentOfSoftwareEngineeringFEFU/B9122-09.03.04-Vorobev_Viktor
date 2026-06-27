# app/services/overpass_service.py
import requests
import json
from typing import List, Tuple, Dict, Any
import math

class OverpassService:
    def __init__(self):
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.water_zones = []  # Полигоны воды
        self.land_zones = []   # Полигоны суши
        self.fairways = []     # Фарватеры
        self.ports = []        # Пирсы и портовые сооружения
        
    def fetch_vladivostok_data(self):
        """Загрузка данных по акватории Владивостока"""
        bbox = "43.00,131.80,43.20,132.00"  # Юг,Запад,Север,Восток
        
        query = f"""
        [out:json][timeout:60];
        (
          // Береговая линия
          way["natural"="coastline"]({bbox});
          
          // Водные объекты
          way["natural"="water"]({bbox});
          way["waterway"]({bbox});
          relation["natural"="water"]({bbox});
          
          // Пирсы и причалы
          way["man_made"="pier"]({bbox});
          way["waterway"="dock"]({bbox});
          
          // Портовые сооружения
          way["building"]({bbox});
          node["seamark:type"]({bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        try:
            response = requests.get(self.base_url, params={'data': query}, timeout=90)
            response.raise_for_status()
            data = response.json()
            
            self._parse_osm_data(data)
            return True
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            return False
    
    def _parse_osm_data(self, data: Dict):
        """Парсинг OSM данных"""
        nodes = {}
        ways = {}
        
        # Сначала собираем все узлы
        for element in data.get('elements', []):
            if element.get('type') == 'node':
                nodes[element['id']] = (element.get('lat', 0), element.get('lon', 0))
        
        # Затем обрабатываем пути (полигоны)
        for element in data.get('elements', []):
            if element.get('type') == 'way':
                tags = element.get('tags', {})
                node_ids = element.get('nodes', [])
                
                # Собираем координаты пути
                coords = []
                for nid in node_ids:
                    if nid in nodes:
                        coords.append(nodes[nid])
                
                if len(coords) < 3:
                    continue
                
                # Определяем тип объекта
                if 'natural' in tags:
                    if tags['natural'] in ['water', 'coastline']:
                        self.water_zones.append(coords)
                
                if tags.get('man_made') == 'pier':
                    self.ports.append({'type': 'pier', 'coords': coords})
                
                if tags.get('waterway') in ['river', 'canal', 'fairway']:
                    self.fairways.append(coords)
        
        print(f"Загружено: {len(self.water_zones)} водных зон, {len(self.ports)} пирсов, {len(self.fairways)} фарватеров")
    
    def is_point_in_water(self, lat: float, lon: float) -> bool:
        """Проверка, находится ли точка в воде"""
        # Точка в воде, если:
        # 1. Внутри водной зоны
        # 2. Не на суше
        # 3. Близко к фарватеру
        
        for water_zone in self.water_zones:
            if self._point_in_polygon(lat, lon, water_zone):
                return True
        
        # Если нет данных от OSM, используем запасной вариант
        # Проверяем по координатам бухты Владивостока
        return self._is_in_vladivostok_bay(lat, lon)
    
    def _is_in_vladivostok_bay(self, lat: float, lon: float) -> bool:
        """Запасная проверка — зоны акватории Владивостока"""
        # Бухта Золотой Рог
        if 43.105 <= lat <= 43.125 and 131.875 <= lon <= 131.895:
            return True
        # Амурский залив (западнее)
        if 43.09 <= lat <= 43.14 and 131.70 <= lon <= 131.82:
            return True
        # Уссурийский залив (восточнее)
        if 43.10 <= lat <= 43.18 and 131.89 <= lon <= 132.05:
            return True
        return False
    
    def _point_in_polygon(self, lat: float, lon: float, polygon: List[Tuple]) -> bool:
        """Алгоритм проверки точки в полигоне (ray casting)"""
        inside = False
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            if ((y1 > lon) != (y2 > lon)) and (lat < (x2 - x1) * (lon - y1) / (y2 - y1) + x1):
                inside = not inside
        return inside
    
    def get_nearest_fairway(self, lat: float, lon: float) -> Tuple[float, float]:
        """Найти ближайшую точку на фарватере"""
        if not self.fairways:
            return (lat, lon)
        
        min_dist = float('inf')
        nearest = (lat, lon)
        
        for fairway in self.fairways:
            for point in fairway:
                dist = math.hypot(point[0] - lat, point[1] - lon)
                if dist < min_dist:
                    min_dist = dist
                    nearest = point
        
        return nearest

# Глобальный экземпляр сервиса
overpass_service = OverpassService()