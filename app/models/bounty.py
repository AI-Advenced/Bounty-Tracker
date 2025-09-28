"""
Bounty model for tracking bounty payments and hunters
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .base import BaseModel

class BountyStatus(PyEnum):
    OPEN = "open"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    PAID = "paid"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"

class BountyType(PyEnum):
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    TEST = "test"
    REFACTOR = "refactor"
    SECURITY = "security"
    PERFORMANCE = "performance"
    OTHER = "other"

class PaymentStatus(PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class Bounty(BaseModel):
    __tablename__ = "bounties"
    
    # Associated issue
    issue_id = Column(String(36), ForeignKey('issues.id'), nullable=False, index=True)
    
    # Bounty details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Integer, nullable=False)  # In cents
    currency = Column(String(3), default="USD")
    
    # Type and status
    bounty_type = Column(SQLEnum(BountyType), default=BountyType.BUG_FIX)
    status = Column(SQLEnum(BountyStatus), default=BountyStatus.OPEN, index=True)
    
    # People involved
    creator_id = Column(String(36), ForeignKey('users.id'), nullable=True)  # Who posted the bounty
    hunter_id = Column(String(36), ForeignKey('users.id'), nullable=True)   # Who claimed it
    reviewer_id = Column(String(36), ForeignKey('users.id'), nullable=True) # Who reviews the work
    
    # External bounty platforms
    external_platform = Column(String(50), nullable=True)  # "bountysource", "gitcoin", "algora", etc.
    external_id = Column(String(100), nullable=True)
    external_url = Column(String(500), nullable=True)
    
    # Requirements and criteria
    acceptance_criteria = Column(Text, nullable=True)
    skills_required = Column(String(500), nullable=True)  # Comma-separated
    experience_level = Column(String(20), nullable=True)  # "beginner", "intermediate", "advanced"
    estimated_hours = Column(Integer, nullable=True)
    
    # Deadlines
    deadline_at = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Work tracking
    work_description = Column(Text, nullable=True)  # Description of work done
    pull_request_url = Column(String(500), nullable=True)
    submission_notes = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Metrics
    view_count = Column(Integer, default=0)
    applicants_count = Column(Integer, default=0)
    time_to_complete_hours = Column(Integer, nullable=True)
    
    # Relationships
    issue = relationship("Issue", back_populates="bounties")
    creator = relationship("User", foreign_keys=[creator_id])
    hunter = relationship("User", foreign_keys=[hunter_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    payments = relationship("BountyPayment", back_populates="bounty", cascade="all, delete-orphan")
    
    @property
    def amount_formatted(self) -> str:
        """Format bounty amount as currency"""
        return f"${self.amount / 100:.2f}"
    
    @property
    def hourly_rate_formatted(self) -> str:
        """Calculate and format hourly rate if estimated hours is available"""
        if self.estimated_hours and self.estimated_hours > 0:
            rate = (self.amount / 100) / self.estimated_hours
            return f"${rate:.2f}/hr"
        return "N/A"
    
    @property
    def is_high_value(self) -> bool:
        """Check if this is a high-value bounty (>$200)"""
        return self.amount >= 20000
    
    @property
    def is_urgent(self) -> bool:
        """Check if bounty has a deadline within 7 days"""
        if not self.deadline_at:
            return False
        days_until_deadline = (self.deadline_at - datetime.utcnow()).days
        return days_until_deadline <= 7
    
    @property
    def days_until_deadline(self) -> int:
        """Get days until deadline"""
        if not self.deadline_at:
            return -1
        return (self.deadline_at - datetime.utcnow()).days
    
    def claim_bounty(self, hunter_id: str):
        """Claim bounty for a hunter"""
        self.hunter_id = hunter_id
        self.status = BountyStatus.CLAIMED
        self.claimed_at = datetime.utcnow()
    
    def start_work(self):
        """Mark work as started"""
        self.status = BountyStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
    
    def submit_work(self, pull_request_url: str = None, notes: str = None):
        """Submit work for review"""
        self.status = BountyStatus.UNDER_REVIEW
        self.submitted_at = datetime.utcnow()
        if pull_request_url:
            self.pull_request_url = pull_request_url
        if notes:
            self.submission_notes = notes
    
    def complete_bounty(self, reviewer_id: str = None, review_notes: str = None):
        """Complete bounty and mark for payment"""
        self.status = BountyStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if reviewer_id:
            self.reviewer_id = reviewer_id
        if review_notes:
            self.review_notes = review_notes
            
        # Calculate time to complete
        if self.started_at:
            hours = (self.completed_at - self.started_at).total_seconds() / 3600
            self.time_to_complete_hours = int(hours)
    
    def cancel_bounty(self, reason: str = None):
        """Cancel bounty"""
        self.status = BountyStatus.CANCELLED
        if reason:
            self.review_notes = reason
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
    
    def __repr__(self):
        return f"<Bounty(id={self.id}, amount={self.amount_formatted}, status={self.status.value})>"

class BountyPayment(BaseModel):
    __tablename__ = "bounty_payments"
    
    # Associated bounty
    bounty_id = Column(String(36), ForeignKey('bounties.id'), nullable=False, index=True)
    
    # Payment details
    amount = Column(Integer, nullable=False)  # In cents
    currency = Column(String(3), default="USD")
    payment_method = Column(String(50), nullable=True)  # "paypal", "stripe", "crypto", etc.
    
    # Payment status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    
    # External payment data
    external_payment_id = Column(String(200), nullable=True)
    external_platform = Column(String(50), nullable=True)
    transaction_hash = Column(String(200), nullable=True)  # For crypto payments
    
    # Recipients
    recipient_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    recipient_address = Column(String(500), nullable=True)  # Email, wallet address, etc.
    
    # Payment tracking
    initiated_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Notes and metadata
    payment_notes = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    fees_amount = Column(Integer, default=0)  # Platform fees in cents
    
    # Relationships
    bounty = relationship("Bounty", back_populates="payments")
    recipient = relationship("User")
    
    @property
    def amount_formatted(self) -> str:
        """Format payment amount as currency"""
        return f"${self.amount / 100:.2f}"
    
    @property
    def net_amount_formatted(self) -> str:
        """Format net amount (after fees) as currency"""
        net_amount = self.amount - self.fees_amount
        return f"${net_amount / 100:.2f}"
    
    @property
    def fees_formatted(self) -> str:
        """Format fees as currency"""
        return f"${self.fees_amount / 100:.2f}"
    
    def initiate_payment(self):
        """Initiate payment processing"""
        self.status = PaymentStatus.PROCESSING
        self.initiated_at = datetime.utcnow()
    
    def complete_payment(self, transaction_id: str = None):
        """Mark payment as completed"""
        self.status = PaymentStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if transaction_id:
            self.external_payment_id = transaction_id
    
    def fail_payment(self, reason: str = None):
        """Mark payment as failed"""
        self.status = PaymentStatus.FAILED
        self.failed_at = datetime.utcnow()
        if reason:
            self.failure_reason = reason
    
    def __repr__(self):
        return f"<BountyPayment(id={self.id}, bounty_id={self.bounty_id}, amount={self.amount_formatted})>"