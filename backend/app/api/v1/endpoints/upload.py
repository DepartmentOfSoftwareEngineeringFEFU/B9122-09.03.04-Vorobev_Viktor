# app/api/v1/endpoints/upload.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.services.vessel_import_service import VesselImportService
# from app.utils.auth import get_current_user_optional  # Временно отключаем
import pandas as pd
import io

router = APIRouter()

@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Загрузка CSV файла с данными судов"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        required_columns = [
            'MMSI', 'BaseDateTime', 'LAT', 'LON', 'SOG', 'COG', 'Heading',
            'VesselName', 'IMO', 'CallSign', 'VesselType', 'Status', 'Length',
            'Width', 'Draft', 'Cargo', 'TransceiverClass', 'dest_cluster',
            'dest_lat', 'dest_lon', 'dist_km', 'SOG_kmh', 'ETA_min',
            'VesselType_enc', 'Status_enc', 'Cargo_enc', 'ETA_hours', 'Speed_Category'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # user_id = current_user.id if current_user else None
        # import_service = VesselImportService(db)
        # result = await import_service.import_vessels_from_df(df, user_id=user_id)
        
        import_service = VesselImportService(db)
        result = await import_service.import_vessels_from_df(df, user_id=None) # Всегда None
        
        return {
            "status": "success",
            "message": f"Imported {result['vessels_imported']} vessels with {result['positions_imported']} positions",
            "details": result
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))