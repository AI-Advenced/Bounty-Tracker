"""
Search and analytics models
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .base import BaseModel

class SearchType(PyEnum):
    ISSUES = "issues"
    BOUNTIES = "bounties"
    REPOSITORIES = "repositories"
    USERS = "users"

class SearchQuery(BaseModel):
    __tablename__ = "search_queries"
    
    # Query details
    query_text = Column(String(500), nullable=False, index=True)
    search_type = Column(SQLEnum(SearchType), nullable=False, index=True)
    
    # User who performed the search
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True, index=True)
    
    # Search filters applied
    filters_json = Column(Text, nullable=True)  # JSON string of applied filters
    sort_by = Column(String(50), nullable=True)
    sort_order = Column(String(10), default="desc")  # "asc" or "desc"
    
    # Results
    results_count = Column(Integer, default=0)
    execution_time_ms = Column(Integer, nullable=True)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    referer_url = Column(String(500), nullable=True)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<SearchQuery(query={self.query_text[:50]}, type={self.search_type.value})>"

class SearchResult(BaseModel):
    __tablename__ = "search_results"
    
    # Associated search query
    search_query_id = Column(String(36), ForeignKey('search_queries.id'), nullable=False, index=True)
    
    # Result details
    result_type = Column(SQLEnum(SearchType), nullable=False)
    result_id = Column(String(36), nullable=False)  # ID of the found entity
    result_title = Column(String(500), nullable=True)
    result_url = Column(String(500), nullable=True)
    
    # Ranking
    relevance_score = Column(Float, nullable=True)
    position = Column(Integer, nullable=False)  # Position in search results (1, 2, 3, ...)
    
    # User interaction
    clicked = Column(Boolean, default=False)
    clicked_at = Column(DateTime, nullable=True)
    
    # Relationships
    search_query = relationship("SearchQuery")
    
    def mark_clicked(self):
        """Mark result as clicked"""
        self.clicked = True
        self.clicked_at = datetime.utcnow()
    
    def __repr__(self):
        return f"<SearchResult(query_id={self.search_query_id}, position={self.position})>"

class AnalyticsEvent(BaseModel):
    __tablename__ = "analytics_events"
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    event_category = Column(String(50), nullable=True, index=True)
    event_action = Column(String(100), nullable=True)
    event_label = Column(String(200), nullable=True)
    
    # User and session
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    
    # Related entities
    issue_id = Column(String(36), ForeignKey('issues.id'), nullable=True)
    bounty_id = Column(String(36), ForeignKey('bounties.id'), nullable=True)
    repository_id = Column(String(36), ForeignKey('repositories.id'), nullable=True)
    
    # Event data
    properties_json = Column(Text, nullable=True)  # JSON string of additional properties
    value = Column(Float, nullable=True)  # Numeric value (e.g., bounty amount, time spent)
    
    # Request context
    page_url = Column(String(500), nullable=True)
    referer_url = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Geographic data
    country = Column(String(2), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User")
    issue = relationship("Issue")
    bounty = relationship("Bounty") 
    repository = relationship("Repository")
    
    @classmethod
    def create_page_view(cls, page_url: str, user_id: str = None, **kwargs):
        """Create a page view event"""
        return cls(
            event_type="page_view",
            event_category="navigation",
            page_url=page_url,
            user_id=user_id,
            **kwargs
        )
    
    @classmethod
    def create_bounty_view(cls, bounty_id: str, user_id: str = None, **kwargs):
        """Create a bounty view event"""
        return cls(
            event_type="bounty_view",
            event_category="engagement",
            bounty_id=bounty_id,
            user_id=user_id,
            **kwargs
        )
    
    @classmethod
    def create_search_event(cls, query: str, results_count: int, user_id: str = None, **kwargs):
        """Create a search event"""
        return cls(
            event_type="search",
            event_category="discovery",
            event_action="search_performed",
            event_label=query,
            value=results_count,
            user_id=user_id,
            **kwargs
        )
    
    def __repr__(self):
        return f"<AnalyticsEvent(type={self.event_type}, category={self.event_category})>"

class AnalyticsSummary(BaseModel):
    __tablename__ = "analytics_summary"
    
    # Time period
    date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # "daily", "weekly", "monthly"
    
    # Overall metrics
    total_page_views = Column(Integer, default=0)
    unique_visitors = Column(Integer, default=0)
    total_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    
    # Bounty metrics
    new_bounties = Column(Integer, default=0)
    bounties_claimed = Column(Integer, default=0)
    bounties_completed = Column(Integer, default=0)
    total_bounty_value = Column(Integer, default=0)  # In cents
    
    # Issue metrics
    new_issues = Column(Integer, default=0)
    issues_closed = Column(Integer, default=0)
    issues_with_bounties = Column(Integer, default=0)
    
    # Repository metrics
    new_repositories = Column(Integer, default=0)
    active_repositories = Column(Integer, default=0)
    
    # Search metrics
    total_searches = Column(Integer, default=0)
    unique_search_queries = Column(Integer, default=0)
    avg_results_per_search = Column(Float, default=0)
    
    # Engagement metrics
    avg_session_duration_seconds = Column(Integer, default=0)
    bounce_rate = Column(Float, default=0)  # Percentage
    pages_per_session = Column(Float, default=0)
    
    # Top content
    top_repositories_json = Column(Text, nullable=True)  # JSON array of top repositories
    top_bounties_json = Column(Text, nullable=True)      # JSON array of top bounties
    top_search_terms_json = Column(Text, nullable=True)  # JSON array of top search terms
    
    @property
    def bounty_value_formatted(self) -> str:
        """Format total bounty value as currency"""
        return f"${self.total_bounty_value / 100:.2f}"
    
    @property
    def avg_bounty_value_formatted(self) -> str:
        """Calculate and format average bounty value"""
        if self.new_bounties > 0:
            avg_value = self.total_bounty_value / self.new_bounties
            return f"${avg_value / 100:.2f}"
        return "$0.00"
    
    def __repr__(self):
        return f"<AnalyticsSummary(date={self.date}, period={self.period_type})>"