from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

class NavigationRule(Base):
    __tablename__ = "navigation_rules"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(50))  
    rule_category = Column(String(50))  
    
    # Условие в формате JSON
    condition = Column(JSONB, nullable=False)
    
    # Действие
    action_type = Column(String(50))
    message_template = Column(Text)
    
    # Применение
    applicable_water_areas = Column(JSONB)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)