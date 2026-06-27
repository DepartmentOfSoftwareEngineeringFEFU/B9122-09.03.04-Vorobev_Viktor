import redis.asyncio as redis
from app.core.config import settings

class RedisClient:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        self.client = await redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding="utf-8"
        )
        return self.client
    
    async def disconnect(self):
        if self.client:
            await self.client.close()
    
    async def get_client(self):
        if not self.client:
            await self.connect()
        return self.client

redis_client = RedisClient()

class RedisChannels:
    VESSEL_POSITIONS = "vessel:positions"  
    ALERTS = "alerts:new" 
    RULES_UPDATE = "rules:update"  