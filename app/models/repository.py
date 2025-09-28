"""
Repository model for GitHub repositories tracking
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .base import BaseModel

class RepositoryType(PyEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    FORK = "fork"

class RepositoryStatus(PyEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISABLED = "disabled"
    SUSPENDED = "suspended"

class Repository(BaseModel):
    __tablename__ = "repositories"
    
    # GitHub data
    github_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(200), unique=True, nullable=False, index=True)  # "owner/repo"
    name = Column(String(100), nullable=False, index=True)
    owner = Column(String(100), nullable=False, index=True)
    
    # Repository info
    description = Column(Text, nullable=True)
    html_url = Column(String(500), nullable=False)
    clone_url = Column(String(500), nullable=False)
    ssh_url = Column(String(500), nullable=False)
    
    # Repository type and status
    repository_type = Column(SQLEnum(RepositoryType), default=RepositoryType.PUBLIC)
    status = Column(SQLEnum(RepositoryStatus), default=RepositoryStatus.ACTIVE)
    is_fork = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_disabled = Column(Boolean, default=False)
    
    # Languages and topics
    primary_language = Column(String(50), nullable=True, index=True)
    languages_json = Column(Text, nullable=True)  # JSON string of languages
    topics_json = Column(Text, nullable=True)  # JSON string of topics
    
    # Statistics
    stars_count = Column(Integer, default=0, index=True)
    forks_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)
    open_issues_count = Column(Integer, default=0)
    size_kb = Column(Integer, default=0)
    
    # Activity metrics
    total_bounties = Column(Integer, default=0)
    total_bounty_amount = Column(Integer, default=0)  # In cents
    active_bounties = Column(Integer, default=0)
    completed_bounties = Column(Integer, default=0)
    
    # Dates from GitHub
    github_created_at = Column(DateTime, nullable=False)
    github_updated_at = Column(DateTime, nullable=False)
    github_pushed_at = Column(DateTime, nullable=True)
    
    # Tracking
    last_fetched_at = Column(DateTime, nullable=True)
    fetch_count = Column(Integer, default=1)
    last_issues_sync_at = Column(DateTime, nullable=True)
    
    # License and README
    license_name = Column(String(100), nullable=True)
    license_spdx_id = Column(String(50), nullable=True)
    has_readme = Column(Boolean, default=False)
    readme_content = Column(Text, nullable=True)
    
    # Quality metrics
    code_quality_score = Column(Float, nullable=True)  # 0-100 score
    maintainer_response_time = Column(Integer, nullable=True)  # Average response time in hours
    issue_resolution_rate = Column(Float, nullable=True)  # Percentage of issues resolved
    
    # Relationships
    issues = relationship("Issue", back_populates="repository", cascade="all, delete-orphan")
    stats = relationship("RepositoryStats", back_populates="repository", cascade="all, delete-orphan")
    
    @property
    def bounty_total_formatted(self) -> str:
        """Format total bounty amount as currency"""
        return f"${self.total_bounty_amount / 100:.2f}"
    
    @property
    def github_short_url(self) -> str:
        """Get short GitHub URL"""
        return f"github.com/{self.full_name}"
    
    @property
    def is_popular(self) -> bool:
        """Check if repository is popular (>1000 stars)"""
        return self.stars_count >= 1000
    
    @property
    def is_active_project(self) -> bool:
        """Check if project is actively maintained (pushed within 30 days)"""
        if not self.github_pushed_at:
            return False
        days_since_push = (datetime.utcnow() - self.github_pushed_at).days
        return days_since_push <= 30
    
    def update_from_github(self, github_data: dict):
        """Update repository data from GitHub API response"""
        self.name = github_data.get("name", self.name)
        self.description = github_data.get("description", self.description)
        self.primary_language = github_data.get("language")
        self.stars_count = github_data.get("stargazers_count", 0)
        self.forks_count = github_data.get("forks_count", 0)
        self.watchers_count = github_data.get("watchers_count", 0)
        self.open_issues_count = github_data.get("open_issues_count", 0)
        self.size_kb = github_data.get("size", 0)
        self.is_fork = github_data.get("fork", False)
        self.is_archived = github_data.get("archived", False)
        self.is_disabled = github_data.get("disabled", False)
        
        # Update timestamps
        if github_data.get("updated_at"):
            self.github_updated_at = datetime.fromisoformat(
                github_data["updated_at"].replace("Z", "+00:00")
            )
        
        if github_data.get("pushed_at"):
            self.github_pushed_at = datetime.fromisoformat(
                github_data["pushed_at"].replace("Z", "+00:00")
            )
            
        # License info
        license_info = github_data.get("license")
        if license_info:
            self.license_name = license_info.get("name")
            self.license_spdx_id = license_info.get("spdx_id")
            
        self.last_fetched_at = datetime.utcnow()
        self.fetch_count += 1
    
    def update_bounty_stats(self, db_session):
        """Update bounty-related statistics"""
        from . import Issue, Bounty
        
        # Count total bounties
        total_bounties = db_session.query(Issue).filter(
            Issue.repository_id == self.id,
            Issue.has_bounty == True
        ).count()
        
        # Sum total bounty amounts
        total_amount = db_session.query(
            db_session.func.sum(Issue.bounty_amount)
        ).filter(
            Issue.repository_id == self.id,
            Issue.has_bounty == True
        ).scalar() or 0
        
        # Count active bounties (open issues with bounties)
        active_bounties = db_session.query(Issue).filter(
            Issue.repository_id == self.id,
            Issue.has_bounty == True,
            Issue.status == "open"
        ).count()
        
        # Count completed bounties (closed issues with bounties)
        completed_bounties = db_session.query(Issue).filter(
            Issue.repository_id == self.id,
            Issue.has_bounty == True,
            Issue.status == "closed"
        ).count()
        
        self.total_bounties = total_bounties
        self.total_bounty_amount = total_amount
        self.active_bounties = active_bounties
        self.completed_bounties = completed_bounties
    
    def __repr__(self):
        return f"<Repository(id={self.id}, full_name={self.full_name}, stars={self.stars_count})>"

class RepositoryStats(BaseModel):
    __tablename__ = "repository_stats"
    
    repository_id = Column(String(36), ForeignKey('repositories.id'), nullable=False, index=True)
    
    # Date for this stats snapshot
    stats_date = Column(DateTime, nullable=False, index=True)
    
    # GitHub stats at this date
    stars_count = Column(Integer, default=0)
    forks_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)
    open_issues_count = Column(Integer, default=0)
    
    # Bounty stats at this date
    total_bounties = Column(Integer, default=0)
    active_bounties = Column(Integer, default=0)
    total_bounty_amount = Column(Integer, default=0)
    
    # Activity metrics
    commits_last_week = Column(Integer, default=0)
    prs_opened_last_week = Column(Integer, default=0)
    issues_opened_last_week = Column(Integer, default=0)
    issues_closed_last_week = Column(Integer, default=0)
    
    # Relationships
    repository = relationship("Repository", back_populates="stats")
    
    def __repr__(self):
        return f"<RepositoryStats(repo_id={self.repository_id}, date={self.stats_date})>"