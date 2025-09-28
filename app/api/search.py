"""
Search API endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.services import SearchService

router = APIRouter()

@router.get("/issues")
async def search_issues(
    query: str = Query("", description="Search query"),
    db: Session = Depends(get_db)
):
    """Search issues"""
    search_service = SearchService()
    results = search_service.search_issues(db, query)
    return results