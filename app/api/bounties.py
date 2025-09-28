"""
Bounties API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Bounty

router = APIRouter()

@router.get("/")
async def list_bounties(db: Session = Depends(get_db)):
    """Get all bounties"""
    bounties = db.query(Bounty).limit(50).all()
    return {"items": bounties}