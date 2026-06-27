# app/api/v1/endpoints/alerts.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.alerting import AlertingService
from pydantic import BaseModel
# from app.utils.auth import get_current_user_optional  # Временно отключаем

router = APIRouter()

@router.get("/")
async def get_alerts(
    mmsi: int = Query(None, description="MMSI судна для фильтрации"),
    db: AsyncSession = Depends(get_db),
    # current_user = Depends(get_current_user_optional)  # Временно отключаем
):
    """Получение активных предупреждений"""
    alert_service = AlertingService(db)
    try:
        if mmsi:
            alerts = await alert_service.get_alerts_by_vessel(mmsi)
        else:
            alerts = await alert_service.get_active_alerts()
        
        return [
            {
                "id": a.id,
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "mmsi": a.mmsi,
                "timestamp": a.timestamp.isoformat(),
                "parameters": a.parameters
            }
            for a in alerts
        ]
    finally:
        await alert_service.close()

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    user_id: int = Query(1, description="ID пользователя"),
    db: AsyncSession = Depends(get_db),
    # current_user = Depends(get_current_user_optional)  # Временно отключаем
):
    """Подтверждение предупреждения"""
    alert_service = AlertingService(db)
    try:
        success = await alert_service.acknowledge_alert(alert_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
        return {"status": "success", "message": "Alert acknowledged"}
    finally:
        await alert_service.close()

class VesselCheck(BaseModel):
    mmsi: int
    latitude: float
    longitude: float
    speed: float
    course: float
    vessel_type: str

@router.post("/check")
async def check_vessel_alerts(
    vessel_data: VesselCheck,
    db: AsyncSession = Depends(get_db)
):
    """Проверка судна на нарушения"""
    alert_service = AlertingService(db)
    try:
        alerts = await alert_service.check_vessel_alerts(
            vessel_data.mmsi,
            vessel_data.latitude,
            vessel_data.longitude,
            vessel_data.speed,
            vessel_data.course,  # Передаём course
            vessel_data.vessel_type
        )
        return {"alerts_created": len(alerts)}
    finally:
        await alert_service.close()