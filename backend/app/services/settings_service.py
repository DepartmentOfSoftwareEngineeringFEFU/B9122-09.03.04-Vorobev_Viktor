# app/services/settings_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import json
from app.models.settings import SystemSettings

class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_setting(self, key: str, default=None):
        result = await self.db.execute(
            select(SystemSettings).where(SystemSettings.setting_key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            try:
                return json.loads(setting.setting_value)
            except:
                return setting.setting_value
        return default
    
    async def set_setting(self, key: str, value, description: str = None):
        # Преобразуем значение в JSON, если это не строка
        if not isinstance(value, str):
            value = json.dumps(value)
        
        # Проверяем, существует ли уже настройка
        result = await self.db.execute(
            select(SystemSettings).where(SystemSettings.setting_key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.setting_value = value
            if description:
                setting.description = description
        else:
            setting = SystemSettings(
                setting_key=key,
                setting_value=value,
                description=description
            )
            self.db.add(setting)
        
        await self.db.commit()
        return setting
    
    async def get_all_settings(self):
        result = await self.db.execute(select(SystemSettings))
        settings = result.scalars().all()
        return {
            s.setting_key: json.loads(s.setting_value) if s.setting_value.startswith('{') or s.setting_value.startswith('[') else s.setting_value
            for s in settings
        }

    async def init_default_settings(self):
        """Инициализация настроек по умолчанию"""
        default_settings = {
            "speed_limits": {
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
            },
            "course_deviation_allowed": 30.0,  # Допустимое отклонение по курсу в градусах
            "speed_multiplier_critical": 1.5,
        }
        
        for key, value in default_settings.items():
            await self.set_setting(key, value, f"Default setting for {key}")