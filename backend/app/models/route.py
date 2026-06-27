# app/models/route.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.core.database import Base
from datetime import datetime

class Port(Base):
    __tablename__ = "ports"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    boundary = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Route(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True)
    vessel_mmsi = Column(Integer, nullable=True)
    route_type = Column(String(50))  # 'historical', 'direct', 'safe'
    waypoints = Column(JSONB)  # точки маршрута [[lat, lon], ...]
    geom = Column(Geometry('LINESTRING', srid=4326))  # геометрия для быстрого поиска
    port_origin = Column(String(100), nullable=True)
    port_destination = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)