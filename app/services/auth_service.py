"""
Authentication and authorization service
"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models import User
from app.models.user import UserRole

class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = os.getenv("SECRET_KEY", "bounty-tracker-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password"""
        # Try to find user by username or email
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return None
        
        if not user.verify_password(password):
            return None
        
        # Update login stats
        user.update_login()
        db.commit()
        
        return user
    
    def create_user(
        self, 
        db: Session, 
        username: str, 
        email: str, 
        password: str,
        full_name: str = None,
        role: UserRole = UserRole.USER
    ) -> Optional[User]:
        """Create a new user"""
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return None
        
        # Create new user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role
        )
        user.set_password(password)
        
        db.add(user)
        try:
            db.commit()
            return user
        except Exception:
            db.rollback()
            return None
    
    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        payload = self.decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.update_activity()
            db.commit()
        
        return user
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from refresh token"""
        payload = self.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Create new access token
        access_token_data = {"sub": user_id}
        return self.create_access_token(access_token_data)
    
    def create_tokens_for_user(self, user: User) -> Dict[str, str]:
        """Create both access and refresh tokens for user"""
        token_data = {"sub": user.id}
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def check_permission(self, user: User, required_role: UserRole) -> bool:
        """Check if user has required role or higher"""
        role_hierarchy = {
            UserRole.USER: 1,
            UserRole.HUNTER: 2,
            UserRole.MAINTAINER: 3,
            UserRole.MODERATOR: 4,
            UserRole.ADMIN: 5
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level or user.is_superuser
    
    def update_user_profile(
        self, 
        db: Session, 
        user: User, 
        profile_data: Dict
    ) -> User:
        """Update user profile"""
        allowed_fields = [
            'full_name', 'bio', 'location', 'website',
            'email_notifications', 'telegram_notifications', 
            'browser_notifications'
        ]
        
        for field, value in profile_data.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        try:
            db.commit()
            return user
        except Exception:
            db.rollback()
            raise
    
    def change_password(
        self, 
        db: Session, 
        user: User, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """Change user password"""
        if not user.verify_password(current_password):
            return False
        
        user.set_password(new_password)
        
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    def link_github_account(
        self, 
        db: Session, 
        user: User, 
        github_username: str, 
        github_id: str, 
        access_token: str = None
    ) -> bool:
        """Link GitHub account to user"""
        user.github_username = github_username
        user.github_id = github_id
        if access_token:
            user.github_access_token = access_token
        
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    def link_telegram_account(
        self, 
        db: Session, 
        user: User, 
        telegram_chat_id: str, 
        telegram_username: str = None
    ) -> bool:
        """Link Telegram account to user"""
        user.telegram_chat_id = telegram_chat_id
        if telegram_username:
            user.telegram_username = telegram_username
        user.telegram_notifications = True
        
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    def verify_email(self, db: Session, user: User) -> bool:
        """Mark user email as verified"""
        user.is_verified = True
        
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    def create_password_reset_token(self, user: User) -> str:
        """Create password reset token"""
        token_data = {
            "sub": user.id,
            "type": "password_reset",
            "email": user.email
        }
        expire = datetime.utcnow() + timedelta(hours=1)
        token_data.update({"exp": expire})
        
        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
    
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """Verify password reset token and return user ID"""
        payload = self.decode_token(token)
        if not payload or payload.get("type") != "password_reset":
            return None
        
        return payload.get("sub")
    
    def reset_password(
        self, 
        db: Session, 
        token: str, 
        new_password: str
    ) -> bool:
        """Reset user password with token"""
        user_id = self.verify_password_reset_token(token)
        if not user_id:
            return False
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.set_password(new_password)
        
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False