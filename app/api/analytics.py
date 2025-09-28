"""
Analytics API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db

router = APIRouter()

@router.get("/summary")
async def get_analytics_summary(db: Session = Depends(get_db)):
    """Get analytics summary"""
    return {"message": "Analytics summary endpoint"}