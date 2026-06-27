from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vessel_monitor:secure_password_123@localhost:5432/vessel_monitoring"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Application
    APP_NAME: str = "Vessel Monitoring System"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AIS Settings
    AIS_UDP_PORT: int = 33333
    AIS_TCP_HOST: Optional[str] = None
    AIS_TCP_PORT: Optional[int] = None

    # JWT Settings (если есть)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Admin API Key
    ADMIN_API_KEY: str = "default-admin-key-change-me"
    
    # Rule Engine Settings
    RULE_CHECK_INTERVAL_SECONDS: int = 5
    MIN_CPA_DISTANCE_NAUTICAL_MILES: float = 0.5
    MIN_CPA_TIME_MINUTES: float = 10.0
    
    class Config:
        env_file = ".env"

settings = Settings()