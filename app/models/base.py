"""
Base model with common fields and functionality
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class BaseModel(Base):
    """Base model with common fields for all tables"""
    __abstract__ = True
    
    # UUID primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Soft delete
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata_json = Column(JSON, nullable=True)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def soft_delete(self):
        """Soft delete the record"""
        self.is_active = False
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore soft deleted record"""
        self.is_active = True
        self.deleted_at = None
    
    @classmethod
    def get_active_query(cls, session):
        """Get query for active records only"""
        return session.query(cls).filter(cls.is_active == True)
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"