"""
Issues API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db import get_db
from app.models import Issue, Repository, IssueComment, User
from app.services import SearchService, GitHubService
from app.schemas.issues import IssueResponse, IssueListResponse, IssueCreate, IssueUpdate

router = APIRouter()

@router.get("/", response_model=IssueListResponse)
async def list_issues(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    language: Optional[str] = None,
    min_amount: Optional[int] = None,
    status: Optional[str] = None,
    repository: Optional[str] = None,
    has_bounty: Optional[bool] = None,
    sort_by: str = Query("updated", regex="^(created|updated|bounty|stars)$"),
    order: str = Query("desc", regex="^(asc|desc)$")
):
    """Get paginated list of issues with filters"""
    
    query = db.query(Issue).filter(Issue.is_active == True)
    
    # Apply filters
    if language:
        query = query.filter(Issue.primary_language == language)
    
    if min_amount:
        query = query.filter(Issue.bounty_amount >= min_amount * 100)  # Convert to cents
    
    if status:
        query = query.filter(Issue.status == status)
    
    if repository:
        query = query.filter(Issue.repository_full_name.ilike(f"%{repository}%"))
    
    if has_bounty is not None:
        query = query.filter(Issue.has_bounty == has_bounty)
    
    # Apply sorting
    sort_column = {
        "created": Issue.github_created_at,
        "updated": Issue.github_updated_at, 
        "bounty": Issue.bounty_amount,
        "stars": Issue.repository.has(Repository.stars_count)
    }.get(sort_by, Issue.github_updated_at)
    
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    issues = query.offset(offset).limit(per_page).all()
    
    # Calculate pagination metadata
    total_pages = (total + per_page - 1) // per_page
    
    return IssueListResponse(
        items=issues,
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    )

@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed issue information"""
    
    issue = db.query(Issue).filter(
        Issue.id == issue_id,
        Issue.is_active == True
    ).first()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Increment view count
    issue.increment_view_count()
    
    try:
        db.commit()
    except:
        db.rollback()
    
    return IssueResponse.from_orm(issue)

@router.get("/{issue_id}/comments")
async def get_issue_comments(
    issue_id: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Get issue comments with pagination"""
    
    # Verify issue exists
    issue = db.query(Issue).filter(
        Issue.id == issue_id,
        Issue.is_active == True
    ).first()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Get comments
    query = db.query(IssueComment).filter(
        IssueComment.issue_id == issue_id
    ).order_by(IssueComment.github_created_at)
    
    total = query.count()
    offset = (page - 1) * per_page
    comments = query.offset(offset).limit(per_page).all()
    
    return {
        "items": comments,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
            "has_next": page * per_page < total,
            "has_prev": page > 1
        }
    }

@router.post("/{issue_id}/sync")
async def sync_issue_from_github(
    issue_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync issue data from GitHub API"""
    
    issue = db.query(Issue).filter(
        Issue.id == issue_id,
        Issue.is_active == True
    ).first()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Check permissions (admin or moderator)
    if not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        github_service = GitHubService()
        
        # Fetch issue data from GitHub
        url = issue.api_url
        github_data = await github_service.make_request(url)
        
        if not github_data:
            raise HTTPException(status_code=404, detail="Issue not found on GitHub")
        
        # Update issue
        issue.update_from_github(github_data)
        
        # Fetch comments
        await github_service.fetch_issue_comments(db, issue)
        
        db.commit()
        
        return {"message": "Issue synced successfully", "issue_id": issue_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/statistics/summary")
async def get_issues_statistics(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get issues statistics for the specified period"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Total issues
    total_issues = db.query(Issue).filter(Issue.is_active == True).count()
    
    # Issues with bounties
    bounty_issues = db.query(Issue).filter(
        Issue.is_active == True,
        Issue.has_bounty == True
    ).count()
    
    # Recent issues
    recent_issues = db.query(Issue).filter(
        Issue.is_active == True,
        Issue.github_created_at >= cutoff_date
    ).count()
    
    # Total bounty value
    total_bounty_value = db.query(db.func.sum(Issue.bounty_amount)).filter(
        Issue.is_active == True,
        Issue.has_bounty == True
    ).scalar() or 0
    
    # Average bounty value
    avg_bounty_value = db.query(db.func.avg(Issue.bounty_amount)).filter(
        Issue.is_active == True,
        Issue.has_bounty == True,
        Issue.bounty_amount > 0
    ).scalar() or 0
    
    # Language distribution
    language_stats = db.query(
        Issue.primary_language,
        db.func.count(Issue.id).label('count')
    ).filter(
        Issue.is_active == True,
        Issue.primary_language.isnot(None)
    ).group_by(Issue.primary_language).order_by(
        db.func.count(Issue.id).desc()
    ).limit(10).all()
    
    # Status distribution
    status_stats = db.query(
        Issue.status,
        db.func.count(Issue.id).label('count')
    ).filter(
        Issue.is_active == True
    ).group_by(Issue.status).all()
    
    return {
        "total_issues": total_issues,
        "bounty_issues": bounty_issues,
        "recent_issues": recent_issues,
        "total_bounty_value": total_bounty_value / 100,  # Convert to dollars
        "average_bounty_value": avg_bounty_value / 100,
        "language_distribution": [
            {"language": lang, "count": count}
            for lang, count in language_stats
        ],
        "status_distribution": [
            {"status": status.value if hasattr(status, 'value') else status, "count": count}
            for status, count in status_stats
        ],
        "period_days": days
    }

@router.get("/trending/weekly")
async def get_trending_issues(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100)
):
    """Get trending issues from the past week"""
    
    one_week_ago = datetime.utcnow() - timedelta(weeks=1)
    
    issues = db.query(Issue).filter(
        Issue.is_active == True,
        Issue.has_bounty == True,
        Issue.github_created_at >= one_week_ago
    ).order_by(
        Issue.bounty_amount.desc(),
        Issue.view_count.desc()
    ).limit(limit).all()
    
    return {
        "items": issues,
        "period": "weekly",
        "total": len(issues)
    }

@router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=20)
):
    """Get search suggestions for issues"""
    
    # Search in titles
    title_matches = db.query(Issue.title).filter(
        Issue.is_active == True,
        Issue.title.ilike(f"%{query}%")
    ).distinct().limit(limit // 2).all()
    
    # Search in repository names
    repo_matches = db.query(Issue.repository_full_name).filter(
        Issue.is_active == True,
        Issue.repository_full_name.ilike(f"%{query}%")
    ).distinct().limit(limit // 2).all()
    
    suggestions = []
    suggestions.extend([title[0] for title in title_matches])
    suggestions.extend([repo[0] for repo in repo_matches])
    
    return {
        "query": query,
        "suggestions": suggestions[:limit]
    }