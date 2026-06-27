from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)  # speed_violation, collision_risk, etc.
    severity = Column(String(20), nullable=False)  # info, warning, critical
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Участники инцидента
    mmsi = Column(Integer, index=True)
    mmsi_other = Column(Integer, nullable=True)  # для парных нарушений
    
    # Место и время
    latitude = Column(Float)
    longitude = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Данные нарушения
    parameters = Column(JSONB) 
    rule_id = Column(Integer, nullable=True)
    
    # Статус обработки
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)