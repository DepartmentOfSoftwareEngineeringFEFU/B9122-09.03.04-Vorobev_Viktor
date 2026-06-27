# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import vessels, positions, routes, alerts, upload, auth, admin

api_router = APIRouter()

api_router.include_router(vessels.router, prefix="/vessels", tags=["vessels"])
api_router.include_router(positions.router, prefix="/positions", tags=["positions"])
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"]) 