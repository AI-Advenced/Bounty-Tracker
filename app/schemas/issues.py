"""
Pydantic schemas for issues
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class IssueStatusEnum(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"

class IssuePriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IssueBase(BaseModel):
    title: str = Field(..., max_length=500)
    body: Optional[str] = None
    bounty_amount: int = Field(0, ge=0)
    has_bounty: bool = False
    bounty_source: Optional[str] = None
    priority: IssuePriorityEnum = IssuePriorityEnum.MEDIUM
    primary_language: Optional[str] = None
    difficulty_level: Optional[str] = None

class IssueCreate(IssueBase):
    github_id: str
    github_number: int
    html_url: str
    api_url: str
    repository_full_name: str
    repository_owner: str
    repository_name: str
    author_username: str
    github_created_at: datetime
    github_updated_at: datetime

class IssueUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    bounty_amount: Optional[int] = None
    has_bounty: Optional[bool] = None
    bounty_source: Optional[str] = None
    priority: Optional[IssuePriorityEnum] = None
    difficulty_level: Optional[str] = None
    is_featured: Optional[bool] = None

class RepositoryInfo(BaseModel):
    id: str
    full_name: str
    name: str
    owner: str
    description: Optional[str]
    html_url: str
    primary_language: Optional[str]
    stars_count: int
    is_fork: bool
    
    class Config:
        from_attributes = True

class IssueResponse(IssueBase):
    id: str
    github_id: str
    github_number: int
    html_url: str
    api_url: str
    repository_id: str
    repository_full_name: str
    repository_owner: str
    repository_name: str
    status: IssueStatusEnum
    is_pull_request: bool
    author_username: str
    author_avatar_url: Optional[str]
    assignee_username: Optional[str]
    comments_count: int
    reactions_count: int
    thumbs_up_count: int
    thumbs_down_count: int
    github_created_at: datetime
    github_updated_at: datetime
    github_closed_at: Optional[datetime]
    last_fetched_at: Optional[datetime]
    fetch_count: int
    is_featured: bool
    view_count: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    # Computed properties
    bounty_formatted: str
    is_high_value: bool
    github_short_url: str
    age_days: int
    
    # Related data
    repository: Optional[RepositoryInfo] = None
    
    class Config:
        from_attributes = True

class IssueListItem(BaseModel):
    id: str
    github_id: str
    github_number: int
    title: str
    html_url: str
    repository_full_name: str
    repository_owner: str
    repository_name: str
    status: IssueStatusEnum
    is_pull_request: bool
    bounty_amount: int
    has_bounty: bool
    bounty_formatted: str
    is_high_value: bool
    author_username: str
    author_avatar_url: Optional[str]
    comments_count: int
    primary_language: Optional[str]
    github_created_at: datetime
    github_updated_at: datetime
    view_count: int
    is_featured: bool
    
    class Config:
        from_attributes = True

class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class IssueListResponse(BaseModel):
    items: List[IssueListItem]
    pagination: PaginationInfo

class IssueCommentResponse(BaseModel):
    id: str
    github_id: str
    body: str
    html_url: str
    author_username: str
    author_avatar_url: Optional[str]
    author_association: Optional[str]
    github_created_at: datetime
    github_updated_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class IssueLabelResponse(BaseModel):
    id: str
    name: str
    color: str
    description: Optional[str]
    
    class Config:
        from_attributes = True

class IssueStatistics(BaseModel):
    total_issues: int
    bounty_issues: int
    recent_issues: int
    total_bounty_value: float
    average_bounty_value: float
    language_distribution: List[Dict[str, Any]]
    status_distribution: List[Dict[str, Any]]
    period_days: int

class TrendingIssuesResponse(BaseModel):
    items: List[IssueListItem]
    period: str
    total: int

class SearchSuggestionsResponse(BaseModel):
    query: str
    suggestions: List[str]