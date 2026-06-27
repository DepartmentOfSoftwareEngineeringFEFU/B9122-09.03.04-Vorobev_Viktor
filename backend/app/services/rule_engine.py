import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rule import NavigationRule
from app.services.analytics import AnalyticsService

class RuleEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics = AnalyticsService()
    
    async def load_active_rules(self, water_area_id: Optional[int] = None) -> List[NavigationRule]:
        """Загрузка активных правил для акватории"""
        query = select(NavigationRule).where(NavigationRule.is_active == True)
        
        if water_area_id is not None:
            # Фильтр по акватории (упрощенно, проверяем JSON поле)
            pass
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def check_speed_rule(self, rule: NavigationRule, vessel_data: Dict[str, Any],
                               water_area: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Проверка правила скорости"""
        condition = rule.condition
        speed_limit = condition.get('value', 10)  # узлов по умолчанию
        vessel_speed = vessel_data.get('speed_over_ground', 0)
        
        if vessel_speed > speed_limit:
            return {
                'rule_id': rule.id,
                'rule_name': rule.name,
                'violation_type': 'speed_violation',
                'severity': rule.action_type,
                'description': rule.message_template.format(
                    vessel_name=vessel_data.get('name', 'Unknown'),
                    speed=vessel_speed,
                    limit=speed_limit
                ),
                'parameters': {
                    'actual_speed': vessel_speed,
                    'speed_limit': speed_limit,
                    'exceed_by': vessel_speed - speed_limit
                }
            }
        return None
    
    async def check_collision_rule(self, rule: NavigationRule, vessel1: Dict[str, Any],
                                   vessel2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Проверка правила опасного сближения"""
        condition = rule.condition
        min_cpa = condition.get('min_cpa_distance', 0.5)  # морские мили
        min_tcpa = condition.get('min_tcpa_time', 10)  # минут
        
        # Расчет DCPA и TCPA
        dcpa, tcpa = self.analytics.calculate_cpa(
            vessel1['latitude'], vessel1['longitude'], vessel1['speed_over_ground'], vessel1['course_over_ground'],
            vessel2['latitude'], vessel2['longitude'], vessel2['speed_over_ground'], vessel2['course_over_ground']
        )
        
        if dcpa < min_cpa and 0 < tcpa < min_tcpa:
            return {
                'rule_id': rule.id,
                'rule_name': rule.name,
                'violation_type': 'collision_risk',
                'severity': rule.action_type,
                'description': f"Риск столкновения между судами {vessel1.get('mmsi')} и {vessel2.get('mmsi')}. "
                              f"DCPA: {dcpa:.2f} миль, TCPA: {tcpa:.1f} мин",
                'parameters': {
                    'vessel1_mmsi': vessel1.get('mmsi'),
                    'vessel2_mmsi': vessel2.get('mmsi'),
                    'dcpa': dcpa,
                    'tcpa': tcpa,
                    'min_cpa': min_cpa
                },
                'related_vessels': [vessel1.get('mmsi'), vessel2.get('mmsi')]
            }
        return None
    
    async def check_waterway_deviation(self, rule: NavigationRule, vessel_data: Dict[str, Any],
                                       fairway_polygon: List) -> Optional[Dict[str, Any]]:
        """Проверка отклонения от фарватера"""
        is_inside = self.analytics.is_point_in_polygon(
            vessel_data['latitude'], 
            vessel_data['longitude'], 
            fairway_polygon
        )
        
        if not is_inside:
            return {
                'rule_id': rule.id,
                'rule_name': rule.name,
                'violation_type': 'fairway_deviation',
                'severity': rule.action_type,
                'description': f"Судно {vessel_data.get('name', 'Unknown')} отклонилось от фарватера",
                'parameters': {
                    'mmsi': vessel_data.get('mmsi'),
                    'latitude': vessel_data['latitude'],
                    'longitude': vessel_data['longitude']
                }
            }
        return None
    
    async def evaluate_all_rules(self, vessel_data: Dict[str, Any], 
                                 water_area: Dict[str, Any],
                                 other_vessels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Оценка всех правил для судна"""
        alerts = []
        rules = await self.load_active_rules(water_area.get('id'))
        
        for rule in rules:
            rule_type = rule.rule_category
            
            if rule_type == 'speed':
                alert = await self.check_speed_rule(rule, vessel_data, water_area)
                if alert:
                    alerts.append(alert)
            
            elif rule_type == 'distance':
                # Проверка сближения с каждым другим судном
                for other in other_vessels:
                    if other['mmsi'] != vessel_data['mmsi']:
                        alert = await self.check_collision_rule(rule, vessel_data, other)
                        if alert:
                            alerts.append(alert)
            
            elif rule_type == 'navigation':
                if water_area.get('fairway_polygon'):
                    alert = await self.check_waterway_deviation(rule, vessel_data, water_area.get('fairway_polygon'))
                    if alert:
                        alerts.append(alert)
        
        return alerts