# app/models/vessel.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.core.database import Base
from datetime import datetime
import enum

class VesselType(str, enum.Enum):
    TANKER = "tanker"
    CONTAINER = "container"
    PASSENGER = "passenger"
    TUG = "tug"
    FISHING = "fishing"
    CARGO = "cargo"
    WIG = "wig"
    HSC = "hsc"
    MILITARY = "military"
    SAILING = "sailing"
    PLEASURE = "pleasure"
    PILOT = "pilot"
    SAR = "sar"
    DREDGER = "dredger"
    DIVING = "diving"
    FIRE = "fire"
    PORT_TENDER = "port_tender"
    OTHER = "other"

class Vessel(Base):
    __tablename__ = "vessels"
    
    id = Column(Integer, primary_key=True)
    mmsi = Column(Integer, nullable=False)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # УДАЛЕНО
    name = Column(String(100))
    vessel_type = Column(String(50), default=VesselType.OTHER.value)
    length = Column(Float, default=0)
    width = Column(Float, nullable=True)
    draft = Column(Float, nullable=True)
    destination = Column(String(100), nullable=True)
    eta = Column(DateTime, nullable=True)
    destination_lat = Column(Float, nullable=True)
    destination_lon = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VesselPosition(Base):
    __tablename__ = "vessel_positions"
    
    id = Column(Integer, primary_key=True)
    mmsi = Column(Integer, nullable=False)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # УДАЛЕНО
    timestamp = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, default=0)
    course = Column(Float, default=0)
    heading = Column(Integer, nullable=True)
    rate_of_turn = Column(Integer, nullable=True)
    navigation_status = Column(Integer, nullable=True)
    raw_data = Column(JSONB, nullable=True)

class VesselTrajectory(Base):
    __tablename__ = "vessel_trajectories"
    
    id = Column(Integer, primary_key=True)
    mmsi = Column(Integer, nullable=False)
    trajectory = Column(Geometry('LINESTRING', srid=4326))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)