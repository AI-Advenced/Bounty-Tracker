"""
Bounty schemas
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BountyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    amount: int
    issue_id: str

class BountyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[int] = None

class BountyResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    amount: int
    created_at: datetime
    
    class Config:
        from_attributes = True