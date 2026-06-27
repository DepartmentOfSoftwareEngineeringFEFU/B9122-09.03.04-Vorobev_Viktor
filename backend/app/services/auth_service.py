# app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.models.user import User
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _truncate_password(self, password: str) -> str:
        """Обрезает пароль до 72 байт для bcrypt"""
        # bcrypt ограничение - 72 байта
        password_bytes = password.encode('utf-8')[:72]
        return password_bytes.decode('utf-8', errors='ignore')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        plain_password = self._truncate_password(plain_password)
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        password = self._truncate_password(password)
        return pwd_context.hash(password)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    async def register_user(self, username: str, email: str, password: str, 
                           first_name: str = None, last_name: str = None, 
                           vessel_mmsi: int = None) -> User:
        # Проверка на существование
        existing = await self.get_user_by_username(username)
        if existing:
            raise ValueError("Username already exists")
        
        existing_email = await self.get_user_by_email(email)
        if existing_email:
            raise ValueError("Email already exists")
        
        hashed = self.get_password_hash(password)
        
        user = User(
            username=username,
            email=email,
            hashed_password=hashed,
            first_name=first_name,
            last_name=last_name,
            vessel_mmsi=vessel_mmsi
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_profile(self, user_id: int, **kwargs) -> User:
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                if key == "hashed_password" and isinstance(value, str):
                    # Если передан пароль, хешируем его
                    value = self.get_password_hash(value)
                setattr(user, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user