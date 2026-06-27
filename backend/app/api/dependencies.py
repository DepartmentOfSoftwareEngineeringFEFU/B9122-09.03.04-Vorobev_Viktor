# app/api/dependencies.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

# Временный файл, можно оставить пустым или добавить общие зависимости