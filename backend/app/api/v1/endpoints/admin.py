# app/api/v1/endpoints/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.core.database import get_db
from app.services.settings_service import SettingsService
from app.services.alerting import AlertingService
from sqlalchemy import select, text
from app.models.alert import Alert
from app.utils.admin_auth import require_admin

router = APIRouter()  # ЭТА СТРОКА БЫЛА ПРОПУЩЕНА!

# Модели для запросов
class SpeedLimitsUpdate(BaseModel):
    speed_limits: Dict[str, float]

class CourseDeviationUpdate(BaseModel):
    allowed_degrees: float

class SpeedMultiplierUpdate(BaseModel):
    multiplier: float

class CreateAlertRequest(BaseModel):
    mmsi: int
    alert_type: str
    severity: str
    title: str
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None


# ========== Управление настройками ==========

@router.get("/settings/speed-limits", dependencies=[Depends(require_admin)])
async def get_speed_limits(db: AsyncSession = Depends(get_db)):
    """Получение скоростных лимитов"""
    settings_service = SettingsService(db)
    return await settings_service.get_setting("speed_limits")


@router.put("/settings/speed-limits", dependencies=[Depends(require_admin)])
async def update_speed_limits(
    data: SpeedLimitsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление скоростных лимитов"""
    settings_service = SettingsService(db)
    await settings_service.set_setting("speed_limits", data.speed_limits)
    return {"status": "success", "message": "Speed limits updated"}


@router.get("/settings/course-deviation", dependencies=[Depends(require_admin)])
async def get_course_deviation_settings(db: AsyncSession = Depends(get_db)):
    """Получение настроек допустимого отклонения по курсу"""
    settings_service = SettingsService(db)
    allowed = await settings_service.get_setting("course_deviation_allowed", 30.0)
    return {"allowed_degrees": allowed}


@router.put("/settings/course-deviation", dependencies=[Depends(require_admin)])
async def update_course_deviation_settings(
    data: CourseDeviationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление настроек допустимого отклонения по курсу"""
    if data.allowed_degrees < 0 or data.allowed_degrees > 180:
        raise HTTPException(status_code=400, detail="Допустимое отклонение должно быть от 0 до 180 градусов")
    settings_service = SettingsService(db)
    await settings_service.set_setting("course_deviation_allowed", data.allowed_degrees)
    return {"status": "success", "message": "Настройки отклонения по курсу обновлены"}


@router.get("/settings/speed-multiplier", dependencies=[Depends(require_admin)])
async def get_speed_multiplier(db: AsyncSession = Depends(get_db)):
    """Получение множителя для критического превышения скорости"""
    settings_service = SettingsService(db)
    multiplier = await settings_service.get_setting("speed_multiplier_critical", 1.5)
    return {"multiplier": multiplier}


@router.put("/settings/speed-multiplier", dependencies=[Depends(require_admin)])
async def update_speed_multiplier(
    data: SpeedMultiplierUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление множителя для критического превышения скорости"""
    if data.multiplier < 1.0:
        raise HTTPException(status_code=400, detail="Множитель должен быть >= 1.0")
    settings_service = SettingsService(db)
    await settings_service.set_setting("speed_multiplier_critical", data.multiplier)
    return {"status": "success", "message": "Множитель критической скорости обновлён"}


# ========== Управление предупреждениями ==========

@router.get("/alerts", dependencies=[Depends(require_admin)])
async def get_all_alerts(
    limit: int = 100,
    severity: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Получение всех предупреждений с фильтрацией"""
    query = select(Alert).order_by(Alert.timestamp.desc())
    
    if severity:
        query = query.where(Alert.severity == severity)
    
    query = query.limit(limit)
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "description": a.description,
            "mmsi": a.mmsi,
            "timestamp": a.timestamp.isoformat(),
            "parameters": a.parameters,
            "is_acknowledged": a.is_acknowledged
        }
        for a in alerts
    ]


@router.post("/alerts", dependencies=[Depends(require_admin)])
async def create_manual_alert(
    alert_data: CreateAlertRequest,
    db: AsyncSession = Depends(get_db)
):
    """Создание ручного предупреждения администратором"""
    from app.services.alerting import AlertingService
    
    alert_service = AlertingService(db)
    
    new_alert_data = {
        "violation_type": alert_data.alert_type,
        "severity": alert_data.severity,
        "title": alert_data.title,
        "description": alert_data.description,
        "mmsi": alert_data.mmsi,
        "parameters": alert_data.parameters or {
            "latitude": alert_data.latitude,
            "longitude": alert_data.longitude,
            "created_by_admin": True
        }
    }
    
    try:
        alert = await alert_service.create_alert(new_alert_data)
        return {
            "status": "success",
            "message": "Alert created successfully",
            "alert_id": alert.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")


@router.delete("/alerts/{alert_id}", dependencies=[Depends(require_admin)])
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Удаление предупреждения"""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
    return {"status": "success", "message": "Alert deleted"}


@router.delete("/alerts", dependencies=[Depends(require_admin)])
async def clear_all_alerts(db: AsyncSession = Depends(get_db)):
    """Очистка всех предупреждений"""
    await db.execute(text("DELETE FROM alerts"))
    await db.commit()
    return {"status": "success", "message": "All alerts cleared"}


# ========== Статистика ==========

@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    """Получение статистики системы"""
    vessels_count = await db.execute(text("SELECT COUNT(*) FROM vessels"))
    positions_count = await db.execute(text("SELECT COUNT(*) FROM vessel_positions"))
    routes_count = await db.execute(text("SELECT COUNT(*) FROM routes WHERE route_type = 'historical'"))
    alerts_count = await db.execute(text("SELECT COUNT(*) FROM alerts"))
    unacknowledged_alerts = await db.execute(text("SELECT COUNT(*) FROM alerts WHERE is_acknowledged = false"))
    
    return {
        "vessels": vessels_count.scalar(),
        "positions": positions_count.scalar(),
        "historical_routes": routes_count.scalar(),
        "total_alerts": alerts_count.scalar(),
        "unacknowledged_alerts": unacknowledged_alerts.scalar()
    }


# ========== Список судов для админ-панели ==========

@router.get("/vessels", dependencies=[Depends(require_admin)])
async def get_all_vessels_for_admin(
    db: AsyncSession = Depends(get_db),
    limit: int = 100
):
    """Получение списка всех судов для выбора в админ-панели"""
    result = await db.execute(
        text("SELECT mmsi, name, vessel_type FROM vessels LIMIT :limit"),
        {"limit": limit}
    )
    vessels = result.fetchall()
    return [
        {"mmsi": v[0], "name": v[1], "vessel_type": v[2]}
        for v in vessels
    ]


# ========== Инициализация ==========

@router.post("/init-settings", dependencies=[Depends(require_admin)])
async def init_settings(db: AsyncSession = Depends(get_db)):
    """Инициализация настроек по умолчанию"""
    settings_service = SettingsService(db)
    await settings_service.init_default_settings()
    return {"status": "success", "message": "Default settings initialized"}