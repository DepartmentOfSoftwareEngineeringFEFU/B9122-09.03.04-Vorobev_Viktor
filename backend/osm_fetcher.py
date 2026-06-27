import requests
import json
from typing import List, Tuple

class OSMAdapter:
    def __init__(self):
        self.cache_file = "osm_cache.json"
        self._load_cache()

    def _load_cache(self):
        try:
            with open(self.cache_file, "r") as f:
                self.cache = json.load(f)
        except:
            self.cache = {"water_areas": None, "timestamp": 0}

    def fetch_vladivostok(self, force: bool = False):
        if not force and self.cache["water_areas"]:
            print("📦 Возвращаем кэшированные данные")
            return self.cache["water_areas"]

        print("🌍 Запрашиваем свежие данные через Overpass API...")
        bbox = "43.00,131.80,43.20,132.00"
        
        # Компактный запрос без лишних переносов
        query = f"""[out:json][timeout:25];(way["natural"="water"]({bbox});way["waterway"="riverbank"]({bbox}););out geom;"""
        
        # Пробуем разные зеркала Overpass API
        servers = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.openstreetmap.fr/api/interpreter",
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 VesselMonitor/1.0",
            "Accept": "application/json",
        }
        
        for url in servers:
            try:
                response = requests.get(url, params={"data": query}, headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    water_areas = []
                    for element in data.get("elements", []):
                        if element.get("type") == "way" and "geometry" in element:
                            coords = [(node["lat"], node["lon"]) for node in element["geometry"]]
                            if len(coords) >= 3:
                                water_areas.append(coords)
                    print(f"✅ Загружено {len(water_areas)} водных полигонов с сервера {url}")
                    self.cache["water_areas"] = water_areas
                    with open(self.cache_file, "w") as f:
                        json.dump(self.cache, f)
                    return water_areas
                else:
                    print(f"⚠️ Сервер {url} вернул {response.status_code}")
            except Exception as e:
                print(f"⚠️ Ошибка при запросе к {url}: {e}")
        
        print("🔄 Все серверы недоступны. Используем резервные зоны воды.")
        return self._get_fallback_data()

    def _get_fallback_data(self):
        """Резервные зоны воды — покрывают акваторию Владивостока"""
        return [
            # Бухта Золотой Рог
            [(43.105, 131.875), (43.125, 131.875), (43.125, 131.895), (43.105, 131.895)],
            # Амурский залив
            [(43.090, 131.740), (43.140, 131.740), (43.140, 131.820), (43.090, 131.820)],
            # Уссурийский залив (северная часть)
            [(43.080, 131.900), (43.120, 131.900), (43.120, 132.000), (43.080, 132.000)],
            # Уссурийский залив (южная часть, для рыбака)
            [(43.100, 131.960), (43.115, 131.960), (43.115, 132.000), (43.100, 132.000)],
            # Дополнительная зона для контейнеровоза
            [(43.090, 131.930), (43.100, 131.930), (43.100, 131.950), (43.090, 131.950)],
        ]