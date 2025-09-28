"""
Notification service for multi-channel notifications
"""
import asyncio
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import Notification, User

class NotificationService:
    async def send_notification(
        self, 
        db: Session, 
        user_id: str, 
        title: str, 
        message: str,
        channels: List[str] = None
    ) -> Notification:
        """Send a notification to user"""
        
        if channels is None:
            channels = ["browser"]
        
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            channels=",".join(channels)
        )
        
        db.add(notification)
        db.commit()
        
        return notification