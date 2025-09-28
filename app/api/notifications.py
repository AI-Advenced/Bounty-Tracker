"""
Notifications API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Notification

router = APIRouter()

@router.get("/")
async def list_notifications(db: Session = Depends(get_db)):
    """Get all notifications"""
    notifications = db.query(Notification).limit(50).all()
    return {"items": notifications}