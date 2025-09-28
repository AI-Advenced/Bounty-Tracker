"""
Users API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User

router = APIRouter()

@router.get("/")
async def list_users(db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(User).limit(50).all()
    return {"items": users}