"""
Issue model for GitHub issues and bounties tracking
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime  
from .base import BaseModel, Base

# Many-to-many table for issue labels  
issue_labels_table = Table(
    'issue_labels',
    Base.metadata,
    Column('issue_id', String(36), ForeignKey('issues.id')),
    Column('label_id', String(36), ForeignKey('labels.id'))
)

class IssueStatus(PyEnum):
    OPEN = "open"
    CLOSED = "closed" 
    MERGED = "merged"
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"

class IssuePriority(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Issue(BaseModel):
    __tablename__ = "issues"
    
    # GitHub data
    github_id = Column(String(50), unique=True, nullable=False, index=True)
    github_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False, index=True)
    body = Column(Text, nullable=True)
    html_url = Column(String(500), nullable=False)
    api_url = Column(String(500), nullable=False)
    
    # Repository info
    repository_id = Column(String(36), ForeignKey('repositories.id'), nullable=False, index=True)
    repository_full_name = Column(String(200), nullable=False, index=True)
    repository_owner = Column(String(100), nullable=False)
    repository_name = Column(String(100), nullable=False)
    
    # Issue details
    status = Column(SQLEnum(IssueStatus), default=IssueStatus.OPEN, index=True)
    priority = Column(SQLEnum(IssuePriority), default=IssuePriority.MEDIUM)
    is_pull_request = Column(Boolean, default=False)
    
    # Bounty info
    bounty_amount = Column(Integer, default=0)  # In cents
    has_bounty = Column(Boolean, default=False, index=True)
    bounty_source = Column(String(100), nullable=True)  # "github", "bountysource", "custom"
    
    # GitHub user data
    author_username = Column(String(100), nullable=False)
    author_avatar_url = Column(String(500), nullable=True)
    assignee_username = Column(String(100), nullable=True)
    
    # Metrics
    comments_count = Column(Integer, default=0)
    reactions_count = Column(Integer, default=0)
    thumbs_up_count = Column(Integer, default=0)
    thumbs_down_count = Column(Integer, default=0)
    
    # Dates from GitHub
    github_created_at = Column(DateTime, nullable=False)
    github_updated_at = Column(DateTime, nullable=False)
    github_closed_at = Column(DateTime, nullable=True)
    
    # Tracking
    last_fetched_at = Column(DateTime, nullable=True)
    fetch_count = Column(Integer, default=1)
    is_featured = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    
    # Language and technology tags
    primary_language = Column(String(50), nullable=True, index=True)
    difficulty_level = Column(String(20), nullable=True)  # "beginner", "intermediate", "advanced"
    
    # Relationships
    repository = relationship("Repository", back_populates="issues")
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan")
    labels = relationship("IssueLabel", secondary=issue_labels_table, back_populates="issues")
    bounties = relationship("Bounty", back_populates="issue")
    
    @property
    def bounty_formatted(self) -> str:
        """Format bounty amount as currency"""
        if self.bounty_amount > 0:
            return f"${self.bounty_amount / 100:.2f}"
        return "$0.00"
    
    @property
    def is_high_value(self) -> bool:
        """Check if this is a high-value bounty (>$100)"""
        return self.bounty_amount >= 10000  # $100 in cents
    
    @property
    def github_short_url(self) -> str:
        """Get short GitHub URL"""
        return f"github.com/{self.repository_full_name}/issues/{self.github_number}"
    
    @property
    def age_days(self) -> int:
        """Get issue age in days"""
        return (datetime.utcnow() - self.github_created_at).days
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
    
    def update_from_github(self, github_data: dict):
        """Update issue data from GitHub API response"""
        self.title = github_data.get("title", self.title)
        self.body = github_data.get("body", self.body)
        self.status = IssueStatus.CLOSED if github_data.get("state") == "closed" else IssueStatus.OPEN
        self.comments_count = github_data.get("comments", 0)
        
        # Update timestamps
        if github_data.get("updated_at"):
            self.github_updated_at = datetime.fromisoformat(
                github_data["updated_at"].replace("Z", "+00:00")
            )
        
        if github_data.get("closed_at"):
            self.github_closed_at = datetime.fromisoformat(
                github_data["closed_at"].replace("Z", "+00:00")
            )
            
        self.last_fetched_at = datetime.utcnow()
        self.fetch_count += 1
    
    def __repr__(self):
        return f"<Issue(id={self.id}, github_id={self.github_id}, title={self.title[:50]}...)>"

class IssueLabel(BaseModel):
    __tablename__ = "labels"
    
    name = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(7), nullable=False)  # Hex color code
    description = Column(Text, nullable=True)
    
    # Relationships
    issues = relationship("Issue", secondary=issue_labels_table, back_populates="labels")
    
    def __repr__(self):
        return f"<IssueLabel(name={self.name}, color={self.color})>"

class IssueComment(BaseModel):
    __tablename__ = "issue_comments"
    
    # GitHub data
    github_id = Column(String(50), unique=True, nullable=False)
    issue_id = Column(String(36), ForeignKey('issues.id'), nullable=False)
    
    # Comment content
    body = Column(Text, nullable=False)
    html_url = Column(String(500), nullable=False)
    
    # Author info
    author_username = Column(String(100), nullable=False)
    author_avatar_url = Column(String(500), nullable=True)
    author_association = Column(String(50), nullable=True)  # "OWNER", "MEMBER", "CONTRIBUTOR", etc.
    
    # Timestamps
    github_created_at = Column(DateTime, nullable=False)
    github_updated_at = Column(DateTime, nullable=False)
    
    # Relationships
    issue = relationship("Issue", back_populates="comments")
    
    def __repr__(self):
        return f"<IssueComment(id={self.id}, issue_id={self.issue_id}, author={self.author_username})>"