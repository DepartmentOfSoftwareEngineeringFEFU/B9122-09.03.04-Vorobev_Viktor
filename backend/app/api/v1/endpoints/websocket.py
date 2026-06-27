# app/api/v1/endpoints/websocket.py
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.websocket_manager import manager
import random
import asyncio
from datetime import datetime

router = APIRouter()

# Базовые координаты судов (правильный синтаксис словаря)
vessel_coords = {
    273210001: {"lat": 43.115, "lon": 131.885},
    273210002: {"lat": 43.108, "lon": 131.892},
    273210003: {"lat": 43.120, "lon": 131.878},
    273210004: {"lat": 43.112, "lon": 131.890},
    273210005: {"lat": 43.125, "lon": 131.882},
}

async def send_updates(websocket: WebSocket):
    """Отправка обновлений позиций"""
    while True:
        try:
            updates = []
            for mmsi, coords in vessel_coords.items():
                # Обновляем координаты с небольшим случайным смещением
                lat = coords["lat"] + random.uniform(-0.001, 0.001)
                lon = coords["lon"] + random.uniform(-0.001, 0.001)
                
                # Ограничиваем, чтобы не уходили далеко
                lat = max(43.10, min(43.13, lat))
                lon = max(131.87, min(131.90, lon))
                
                vessel_coords[mmsi] = {"lat": lat, "lon": lon}
                
                updates.append({
                    "mmsi": mmsi,
                    "latitude": lat,
                    "longitude": lon,
                    "speed": random.uniform(5, 15),
                    "course": random.uniform(0, 360),
                    "timestamp": datetime.now().isoformat()
                })
            
            await websocket.send_json({
                "type": "positions_update",
                "data": updates
            })
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Send updates error: {e}")
            break

@router.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        # Запускаем отправку обновлений
        await send_updates(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client {client_id} disconnected")