"""
Repositories API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Repository

router = APIRouter()

@router.get("/")
async def list_repositories(db: Session = Depends(get_db)):
    """Get all repositories"""
    repositories = db.query(Repository).limit(50).all()
    return {"items": repositories}