# app/services/alerting.py
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.alert import Alert
from app.core.redis_client import redis_client, RedisChannels
import json
import math

class AlertingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Скоростные лимиты для разных типов судов (узлы)
        self.SPEED_LIMITS = {
            "tanker": 12.0,
            "container": 18.0,
            "passenger": 15.0,
            "tug": 10.0,
            "fishing": 8.0,
            "cargo": 14.0,
            "wig": 50.0,
            "hsc": 40.0,
            "military": 30.0,
            "sailing": 6.0,
            "pleasure": 10.0,
            "pilot": 12.0,
            "sar": 25.0,
            "dredger": 6.0,
            "diving": 4.0,
            "fire": 20.0,
            "port_tender": 8.0,
            "other": 12.0,
        }
        
        # Расстояния для отклонения от маршрута (в км)
        self.COURSE_DEVIATION_ALLOWED = 30.0
        self.speed_multiplier_critical = 1.5
    
    async def close(self):
        """Закрытие сессии"""
        await self.db.close()
    
    async def refresh_settings_from_db(self):
        """Обновление настроек из БД"""
        try:
            from app.services.settings_service import SettingsService
            settings_service = SettingsService(self.db)
            
            self.SPEED_LIMITS = await settings_service.get_setting("speed_limits", self.SPEED_LIMITS)
            self.COURSE_DEVIATION_ALLOWED = await settings_service.get_setting("course_deviation_allowed", 30.0)
            self.speed_multiplier_critical = await settings_service.get_setting("speed_multiplier_critical", 1.5)
        except Exception as e:
            print(f"Ошибка обновления настроек: {e}")
    
    async def check_route_deviation(self, vessel_mmsi: int, current_course: float, current_lat: float, current_lon: float) -> Optional[Dict[str, Any]]:
        """
        Проверка отклонения судна от маршрута по КУРСУ
        """
        await self.refresh_settings_from_db()
        
        try:
            # Ищем исторические маршруты рядом с позицией судна
            radius_deg = 5.0 / 111.0  # 5 км в градусах
            
            query = text("""
                SELECT id, waypoints, port_destination, port_origin, geom
                FROM routes 
                WHERE route_type = 'historical'
                AND ST_DWithin(
                    geom,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                    :radius
                )
                ORDER BY ST_Distance(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                LIMIT 10
            """)
            
            result = await self.db.execute(query, {
                "lat": current_lat,
                "lon": current_lon,
                "radius": radius_deg
            })
            nearby_routes = result.fetchall()
            
            if not nearby_routes:
                return None
            
            for route in nearby_routes:
                waypoints = route[1]
                if isinstance(waypoints, str):
                    waypoints = json.loads(waypoints)
                
                if not waypoints or len(waypoints) < 2:
                    continue
                
                # Находим ближайшую точку на маршруте
                min_dist = float('inf')
                nearest_idx = 0
                for i, point in enumerate(waypoints):
                    dist = self.calculate_distance(current_lat, current_lon, point[0], point[1])
                    if dist < min_dist:
                        min_dist = dist
                        nearest_idx = i
                
                # Определяем направление маршрута в ближайшей точке
                route_course = None
                if nearest_idx == 0 and len(waypoints) > 1:
                    route_course = self._calculate_course_between_points(
                        waypoints[0][0], waypoints[0][1],
                        waypoints[1][0], waypoints[1][1]
                    )
                elif nearest_idx == len(waypoints) - 1 and len(waypoints) > 1:
                    route_course = self._calculate_course_between_points(
                        waypoints[-2][0], waypoints[-2][1],
                        waypoints[-1][0], waypoints[-1][1]
                    )
                elif 0 < nearest_idx < len(waypoints) - 1:
                    course_to_next = self._calculate_course_between_points(
                        waypoints[nearest_idx][0], waypoints[nearest_idx][1],
                        waypoints[nearest_idx + 1][0], waypoints[nearest_idx + 1][1]
                    )
                    route_course = course_to_next
                
                if route_course is None:
                    continue
                
                # Вычисляем разницу курсов
                course_diff = abs(current_course - route_course)
                course_diff = min(course_diff, 360 - course_diff)
                
                if course_diff <= self.COURSE_DEVIATION_ALLOWED:
                    return None
            
            # Если ни один маршрут не подошел - отклонение
            return {
                "violation_type": "route_deviation",
                "severity": "warning",
                "title": "Отклонение от маршрута",
                "description": f"Курс судна {current_course:.0f}° не соответствует ни одному маршруту (допустимое отклонение: {self.COURSE_DEVIATION_ALLOWED:.0f}°)",
                "mmsi": vessel_mmsi,
                "parameters": {
                    "current_course": round(current_course, 1),
                    "allowed_deviation": self.COURSE_DEVIATION_ALLOWED,
                    "nearby_routes_count": len(nearby_routes),
                    "current_lat": current_lat,
                    "current_lon": current_lon
                }
            }
            
        except Exception as e:
            print(f"Ошибка проверки отклонения по курсу: {e}")
            return None
    
    def _calculate_course_between_points(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Расчёт курса между двумя точками"""
        import math
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        
        course_rad = math.atan2(x, y)
        course_deg = math.degrees(course_rad)
        
        if course_deg < 0:
            course_deg += 360
        
        return course_deg

    async def _get_distance_to_route(self, lat: float, lon: float, route_geom) -> float:
        """Вычисляет расстояние от точки до маршрута в км"""
        try:
            query = text("""
                SELECT ST_Distance(
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :geom::geography
                ) / 1000.0 as distance_km
            """)
            result = await self.db.execute(query, {"lat": lat, "lon": lon, "geom": route_geom})
            distance = result.scalar()
            return distance if distance else 999.0
        except Exception as e:
            print(f"Ошибка расчета расстояния: {e}")
            return 999.0
    
    async def check_speed_violation(self, vessel_mmsi: int, current_speed: float, vessel_type: str) -> Optional[Dict[str, Any]]:
        """Проверка превышения скоростного лимита"""
        await self.refresh_settings_from_db()
        
        speed_limit = self.SPEED_LIMITS.get(vessel_type, 12.0)
        
        if current_speed > speed_limit * self.speed_multiplier_critical:
            return {
                "violation_type": "speed_violation",
                "severity": "critical",
                "title": "Критическое превышение скорости",
                "description": f"Скорость {current_speed:.1f} уз (лимит: {speed_limit:.1f} уз)",
                "mmsi": vessel_mmsi,
                "parameters": {
                    "current_speed": round(current_speed, 1),
                    "speed_limit": speed_limit,
                    "excess_percent": round((current_speed / speed_limit - 1) * 100, 1),
                    "vessel_type": vessel_type
                }
            }
        elif current_speed > speed_limit:
            return {
                "violation_type": "speed_violation",
                "severity": "warning",
                "title": "Превышение скорости",
                "description": f"Скорость {current_speed:.1f} уз (лимит: {speed_limit:.1f} уз)",
                "mmsi": vessel_mmsi,
                "parameters": {
                    "current_speed": round(current_speed, 1),
                    "speed_limit": speed_limit,
                    "excess_percent": round((current_speed / speed_limit - 1) * 100, 1),
                    "vessel_type": vessel_type
                }
            }
        
        return None
    
    async def check_vessel_alerts(self, vessel_mmsi: int, current_lat: float, current_lon: float, 
                                current_speed: float, current_course: float, vessel_type: str) -> List[Alert]:
        """Полная проверка судна по всем критериям"""
        alerts = []
        
        try:
            # Проверка скорости
            speed_alert = await self.check_speed_violation(vessel_mmsi, current_speed, vessel_type)
            if speed_alert:
                alert = await self.create_alert(speed_alert)
                alerts.append(alert)
            
            # Проверка отклонения по КУРСУ (передаём current_course)
            route_alert = await self.check_route_deviation(vessel_mmsi, current_course, current_lat, current_lon)
            if route_alert:
                alert = await self.create_alert(route_alert)
                alerts.append(alert)
        except Exception as e:
            print(f"Ошибка проверки предупреждений: {e}")
        
        return alerts
    
    async def create_alert(self, alert_data: Dict[str, Any]) -> Alert:
        """Создание и сохранение предупреждения"""
        alert = Alert(
            alert_type=alert_data['violation_type'],
            severity=alert_data['severity'],
            title=alert_data['title'],
            description=alert_data['description'],
            mmsi=alert_data.get('mmsi'),
            latitude=alert_data.get('parameters', {}).get('current_lat'),
            longitude=alert_data.get('parameters', {}).get('current_lon'),
            parameters=alert_data.get('parameters', {}),
            is_acknowledged=False
        )
        
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        
        # Отправка в Redis (если Redis недоступен, не падаем)
        try:
            await self._publish_alert(alert)
        except Exception as e:
            print(f"Ошибка публикации в Redis: {e}")
        
        return alert
    
    async def _publish_alert(self, alert: Alert):
        """Публикация предупреждения через Redis Pub/Sub"""
        try:
            redis = await redis_client.get_client()
            alert_message = {
                'id': alert.id,
                'type': alert.alert_type,
                'severity': alert.severity,
                'title': alert.title,
                'description': alert.description,
                'mmsi': alert.mmsi,
                'timestamp': alert.timestamp.isoformat(),
                'parameters': alert.parameters
            }
            await redis.publish(RedisChannels.ALERTS, json.dumps(alert_message))
        except Exception as e:
            print(f"Ошибка публикации: {e}")
    
    async def acknowledge_alert(self, alert_id: int, user_id: int) -> bool:
        """Подтверждение предупреждения оператором"""
        try:
            alert = await self.db.get(Alert, alert_id)
            if alert and not alert.is_acknowledged:
                alert.is_acknowledged = True
                alert.acknowledged_by = user_id
                alert.acknowledged_at = datetime.utcnow()
                await self.db.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка подтверждения: {e}")
            await self.db.rollback()
            return False
    
    async def get_active_alerts(self, limit: int = 100) -> List[Alert]:
        """Получение активных (неподтвержденных) предупреждений"""
        try:
            query = select(Alert).where(
                Alert.is_acknowledged == False
            ).order_by(Alert.timestamp.desc()).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Ошибка получения предупреждений: {e}")
            return []
    
    async def get_alerts_by_vessel(self, mmsi: int, limit: int = 50) -> List[Alert]:
        """Получение предупреждений для конкретного судна"""
        try:
            query = select(Alert).where(
                Alert.mmsi == mmsi,
                Alert.is_acknowledged == False
            ).order_by(Alert.timestamp.desc()).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Ошибка получения предупреждений для судна {mmsi}: {e}")
            return []