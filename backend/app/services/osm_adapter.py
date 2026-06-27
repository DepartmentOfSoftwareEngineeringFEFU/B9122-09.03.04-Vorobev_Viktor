# app/services/osm_adapter.py
import overpy
import json
from typing import List, Tuple, Dict, Any
from app.core.config import settings

class OSMAdapter:
    def __init__(self):
        self.api = overpy.Overpass()
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
            print("Возвращаем кэшированные данные")
            return self.cache["water_areas"]

        print("Запрашиваем свежие данные через Overpass API...")
        bbox = "43.00,131.80,43.20,132.00"
        # Упрощенный и быстрый запрос, который гарантированно вернет результат
        query = f"""
        [out:json][timeout:25][maxsize:16000000];
        (
          way["natural"="water"]({bbox});
          way["waterway"="riverbank"]({bbox});
          relation["natural"="water"]({bbox});
        );
        out geom;
        """
        try:
            # Выполняем запрос к публичному API (опционально с кэшем)
            result = self.api.query(query)
            water_areas = []
            for way in result.ways:
                if way.geometry:
                    nodes = [(node.lat, node.lon) for node in way.geometry]
                    water_areas.append(nodes)
            print(f"✅ Загружено {len(water_areas)} водоемов")
            # Кэшируем и сохраняем в файл
            self.cache["water_areas"] = water_areas
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f)
            return water_areas
        except Exception as e:
            print(f"⚠️ Ошибка Overpass API: {e}. Используем резервные данные.")
            return self._get_fallback_data()

    def _get_fallback_data(self):
        # Твои резервные зоны (без которых никуда)
        return [
            [(43.115, 131.885), (43.108, 131.892), (43.112, 131.890)],
            [(43.090, 131.770), (43.095, 131.810), (43.100, 131.850)]
        ]