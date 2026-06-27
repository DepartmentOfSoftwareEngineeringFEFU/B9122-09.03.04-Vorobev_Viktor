# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text  # <-- ДОБАВИТЬ ЭТУ СТРОКУ
from typing import Optional
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserResponse, UserUpdate, Token
from app.utils.auth import get_current_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            vessel_mmsi=user_data.vessel_mmsi
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему"""
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_service.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление профиля пользователя"""
    auth_service = AuthService(db)
    
    update_data = {}
    if user_update.email:
        update_data["email"] = user_update.email
    if user_update.first_name:
        update_data["first_name"] = user_update.first_name
    if user_update.last_name:
        update_data["last_name"] = user_update.last_name
    if user_update.vessel_mmsi:
        update_data["vessel_mmsi"] = user_update.vessel_mmsi
    if user_update.password:
        update_data["hashed_password"] = auth_service.get_password_hash(user_update.password)
    
    user = await auth_service.update_profile(current_user.id, **update_data)
    return user

@router.post("/clear-guest-data")
async def clear_guest_data(db: AsyncSession = Depends(get_db)):
    """Очистка гостевых данных (user_id IS NULL)"""
    try:
        # Удаляем гостевые позиции
        await db.execute(text("DELETE FROM vessel_positions WHERE user_id IS NULL"))
        # Удаляем гостевые суда
        await db.execute(text("DELETE FROM vessels WHERE user_id IS NULL"))
        await db.commit()
        return {"status": "success", "message": "Guest data cleared"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-vessel-mmsi")
async def get_my_vessel_mmsi(current_user = Depends(get_current_user)):
    """Получение MMSI судна пользователя"""
    return {"vessel_mmsi": current_user.vessel_mmsi}