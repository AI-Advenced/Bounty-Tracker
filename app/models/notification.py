"""
Notification system for real-time updates
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .base import BaseModel

class NotificationChannel(PyEnum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    BROWSER = "browser"
    WEBHOOK = "webhook"
    SMS = "sms"

class NotificationType(PyEnum):
    NEW_BOUNTY = "new_bounty"
    BOUNTY_CLAIMED = "bounty_claimed"
    BOUNTY_COMPLETED = "bounty_completed"
    BOUNTY_PAYMENT = "bounty_payment"
    ISSUE_UPDATED = "issue_updated"
    COMMENT_ADDED = "comment_added"
    DEADLINE_REMINDER = "deadline_reminder"
    SYSTEM_ALERT = "system_alert"

class NotificationPriority(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Notification(BaseModel):
    __tablename__ = "notifications"
    
    # Recipient
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    
    # Notification content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.MEDIUM)
    
    # Delivery channels
    channels = Column(String(200), nullable=False)  # Comma-separated list of channels
    
    # Related entities
    issue_id = Column(String(36), ForeignKey('issues.id'), nullable=True)
    bounty_id = Column(String(36), ForeignKey('bounties.id'), nullable=True)
    repository_id = Column(String(36), ForeignKey('repositories.id'), nullable=True)
    
    # Delivery status
    is_read = Column(Boolean, default=False, index=True)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Delivery tracking per channel
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    telegram_sent = Column(Boolean, default=False)
    telegram_sent_at = Column(DateTime, nullable=True)
    browser_sent = Column(Boolean, default=False)
    webhook_sent = Column(Boolean, default=False)
    
    # Action URLs and metadata
    action_url = Column(String(500), nullable=True)
    action_text = Column(String(100), nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string for additional data
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    issue = relationship("Issue")
    bounty = relationship("Bounty")
    repository = relationship("Repository")
    
    @property
    def is_expired(self) -> bool:
        """Check if notification is expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    @property
    def channel_list(self) -> list:
        """Get list of delivery channels"""
        return [channel.strip() for channel in self.channels.split(",") if channel.strip()]
    
    @property
    def age_minutes(self) -> int:
        """Get notification age in minutes"""
        return int((datetime.utcnow() - self.created_at).total_seconds() / 60)
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def mark_as_sent(self, channel: str = None):
        """Mark notification as sent for a specific channel"""
        self.is_sent = True
        self.sent_at = datetime.utcnow()
        
        if channel == "email":
            self.email_sent = True
            self.email_sent_at = datetime.utcnow()
        elif channel == "telegram":
            self.telegram_sent = True
            self.telegram_sent_at = datetime.utcnow()
        elif channel == "browser":
            self.browser_sent = True
    
    @classmethod
    def create_bounty_notification(
        cls, 
        user_id: str, 
        bounty, 
        notification_type: NotificationType,
        channels: list = None
    ):
        """Create a bounty-related notification"""
        if channels is None:
            channels = ["browser", "email"]
        
        title_map = {
            NotificationType.NEW_BOUNTY: f"New Bounty: {bounty.title}",
            NotificationType.BOUNTY_CLAIMED: f"Bounty Claimed: {bounty.title}",
            NotificationType.BOUNTY_COMPLETED: f"Bounty Completed: {bounty.title}",
            NotificationType.BOUNTY_PAYMENT: f"Payment Processed: {bounty.title}",
        }
        
        message_map = {
            NotificationType.NEW_BOUNTY: f"A new bounty worth {bounty.amount_formatted} has been posted.",
            NotificationType.BOUNTY_CLAIMED: f"Your bounty has been claimed by a hunter.",
            NotificationType.BOUNTY_COMPLETED: f"Bounty work has been completed and is ready for review.",
            NotificationType.BOUNTY_PAYMENT: f"Payment of {bounty.amount_formatted} has been processed.",
        }
        
        return cls(
            user_id=user_id,
            title=title_map.get(notification_type, "Bounty Update"),
            message=message_map.get(notification_type, "Your bounty has been updated."),
            notification_type=notification_type,
            channels=",".join(channels),
            bounty_id=bounty.id,
            issue_id=bounty.issue_id,
            action_url=f"/bounties/{bounty.id}",
            action_text="View Bounty"
        )
    
    @classmethod
    def create_issue_notification(
        cls, 
        user_id: str, 
        issue, 
        notification_type: NotificationType,
        channels: list = None
    ):
        """Create an issue-related notification"""
        if channels is None:
            channels = ["browser"]
        
        title_map = {
            NotificationType.ISSUE_UPDATED: f"Issue Updated: {issue.title}",
            NotificationType.COMMENT_ADDED: f"New Comment: {issue.title}",
        }
        
        message_map = {
            NotificationType.ISSUE_UPDATED: f"Issue #{issue.github_number} has been updated.",
            NotificationType.COMMENT_ADDED: f"A new comment was added to issue #{issue.github_number}.",
        }
        
        return cls(
            user_id=user_id,
            title=title_map.get(notification_type, "Issue Update"),
            message=message_map.get(notification_type, "An issue has been updated."),
            notification_type=notification_type,
            channels=",".join(channels),
            issue_id=issue.id,
            repository_id=issue.repository_id,
            action_url=f"/issues/{issue.id}",
            action_text="View Issue"
        )
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.notification_type.value}, user_id={self.user_id})>"

class NotificationPreference(BaseModel):
    __tablename__ = "notification_preferences"
    
    # User preferences
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    
    # Channel preferences
    email_enabled = Column(Boolean, default=True)
    telegram_enabled = Column(Boolean, default=False)
    browser_enabled = Column(Boolean, default=True)
    webhook_enabled = Column(Boolean, default=False)
    
    # Notification type preferences
    new_bounties = Column(Boolean, default=True)
    bounty_updates = Column(Boolean, default=True)
    issue_updates = Column(Boolean, default=False)
    comments = Column(Boolean, default=False)
    system_alerts = Column(Boolean, default=True)
    
    # Frequency settings
    email_frequency = Column(String(20), default="immediate")  # "immediate", "daily", "weekly"
    telegram_frequency = Column(String(20), default="immediate")
    
    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(5), nullable=True)  # "22:00"
    quiet_hours_end = Column(String(5), nullable=True)    # "08:00"
    quiet_hours_timezone = Column(String(50), nullable=True)
    
    # Keywords and filters
    keyword_filters = Column(Text, nullable=True)  # JSON string of keywords to watch
    minimum_bounty_amount = Column(Integer, default=0)  # Only notify for bounties above this amount
    preferred_languages = Column(String(200), nullable=True)  # Comma-separated list
    
    # Relationships
    user = relationship("User")
    
    def should_notify(self, notification_type: NotificationType, channel: NotificationChannel) -> bool:
        """Check if user should receive notification based on preferences"""
        # Check channel preference
        channel_enabled = {
            NotificationChannel.EMAIL: self.email_enabled,
            NotificationChannel.TELEGRAM: self.telegram_enabled,
            NotificationChannel.BROWSER: self.browser_enabled,
            NotificationChannel.WEBHOOK: self.webhook_enabled,
        }
        
        if not channel_enabled.get(channel, False):
            return False
        
        # Check notification type preference
        type_enabled = {
            NotificationType.NEW_BOUNTY: self.new_bounties,
            NotificationType.BOUNTY_CLAIMED: self.bounty_updates,
            NotificationType.BOUNTY_COMPLETED: self.bounty_updates,
            NotificationType.BOUNTY_PAYMENT: self.bounty_updates,
            NotificationType.ISSUE_UPDATED: self.issue_updates,
            NotificationType.COMMENT_ADDED: self.comments,
            NotificationType.SYSTEM_ALERT: self.system_alerts,
        }
        
        return type_enabled.get(notification_type, True)
    
    def is_in_quiet_hours(self) -> bool:
        """Check if current time is in user's quiet hours"""
        if not self.quiet_hours_enabled:
            return False
        
        # Implementation would check current time against quiet hours
        # This is a simplified version
        return False
    
    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id})>"