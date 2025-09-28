"""
Search service for advanced filtering and searching
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.models import Issue, Repository, User, Bounty, SearchQuery

class SearchService:
    def search_issues(
        self, 
        db: Session,
        query: str = "",
        filters: Dict[str, Any] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict:
        """Search issues with advanced filtering"""
        
        if filters is None:
            filters = {}
        
        # Start with base query
        base_query = db.query(Issue).filter(Issue.is_active == True)
        
        # Apply text search
        if query:
            search_terms = query.split()
            for term in search_terms:
                base_query = base_query.filter(
                    or_(
                        Issue.title.ilike(f"%{term}%"),
                        Issue.body.ilike(f"%{term}%"),
                        Issue.repository_full_name.ilike(f"%{term}%")
                    )
                )
        
        # Apply filters
        if filters.get("language"):
            base_query = base_query.filter(Issue.primary_language == filters["language"])
        
        if filters.get("min_amount"):
            base_query = base_query.filter(Issue.bounty_amount >= filters["min_amount"])
        
        if filters.get("status"):
            base_query = base_query.filter(Issue.status == filters["status"])
        
        if filters.get("has_bounty") is not None:
            base_query = base_query.filter(Issue.has_bounty == filters["has_bounty"])
        
        # Get total count
        total = base_query.count()
        
        # Apply pagination and sorting
        offset = (page - 1) * per_page
        issues = base_query.order_by(
            Issue.github_updated_at.desc()
        ).offset(offset).limit(per_page).all()
        
        return {
            "items": issues,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
                "has_prev": page > 1,
                "has_next": page * per_page < total
            }
        }