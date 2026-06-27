# app/api/v1/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class VesselPositionBase(BaseModel):
    mmsi: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_over_ground: Optional[float] = Field(None, ge=0, le=120)
    course_over_ground: Optional[float] = Field(None, ge=0, le=360)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class VesselPositionResponse(VesselPositionBase):
    id: int
    
    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    id: int
    alert_type: str
    severity: str
    title: str
    description: str
    mmsi: Optional[int]
    timestamp: datetime
    is_acknowledged: bool
    
    class Config:
        from_attributes = True

class VesselTrajectoryResponse(BaseModel):
    mmsi: int
    start_time: datetime
    end_time: datetime
    path: List[List[float]]  # список точек [[lat, lon], ...]
    avg_speed: float
    distance_nautical_miles: float