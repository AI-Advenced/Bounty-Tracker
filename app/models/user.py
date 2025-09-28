"""
User model with authentication and profile management
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
from enum import Enum as PyEnum
from .base import BaseModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(PyEnum):
    ADMIN = "admin"
    MODERATOR = "moderator" 
    USER = "user"
    HUNTER = "hunter"  # Bounty hunter
    MAINTAINER = "maintainer"  # Repository maintainer

class User(BaseModel):
    __tablename__ = "users"
    
    # Basic info
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    
    # Profile
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    website = Column(String(200), nullable=True)
    
    # GitHub integration
    github_username = Column(String(100), nullable=True, index=True)
    github_id = Column(String(50), nullable=True, unique=True)
    github_access_token = Column(String(500), nullable=True)
    
    # Telegram integration
    telegram_chat_id = Column(String(50), nullable=True)
    telegram_username = Column(String(100), nullable=True)
    
    # Preferences
    email_notifications = Column(Boolean, default=True)
    telegram_notifications = Column(Boolean, default=False)
    browser_notifications = Column(Boolean, default=True)
    
    # Stats
    bounties_submitted = Column(Integer, default=0)
    bounties_completed = Column(Integer, default=0)
    total_earnings = Column(Integer, default=0)  # In cents
    reputation_score = Column(Integer, default=0)
    
    # Activity tracking
    last_login_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    # Relationships
    # issues = relationship("Issue", back_populates="creator")
    # comments = relationship("IssueComment", back_populates="author")
    # bounties = relationship("Bounty", back_populates="hunter")
    # notifications = relationship("Notification", back_populates="user")
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(password, self.hashed_password)
    
    def update_activity(self):
        """Update last activity timestamp"""
        from datetime import datetime
        self.last_activity_at = datetime.utcnow()
    
    def update_login(self):
        """Update login stats"""
        from datetime import datetime
        self.last_login_at = datetime.utcnow()
        self.login_count += 1
    
    def add_earnings(self, amount: int):
        """Add to total earnings"""
        self.total_earnings += amount
        self.bounties_completed += 1
        self.reputation_score += amount // 100  # 1 point per dollar
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_superuser
    
    @property
    def is_moderator(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.MODERATOR] or self.is_superuser
    
    @property
    def display_name(self) -> str:
        return self.full_name or self.username
    
    @property
    def earnings_formatted(self) -> str:
        """Format earnings as currency"""
        return f"${self.total_earnings / 100:.2f}"
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role.value})>"