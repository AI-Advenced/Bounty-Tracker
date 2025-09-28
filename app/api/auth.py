"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.db import get_db
from app.services import AuthService
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """User login"""
    auth_service = AuthService()
    
    user = auth_service.authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    tokens = auth_service.create_tokens_for_user(user)
    return TokenResponse(**tokens)

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """User registration"""
    auth_service = AuthService()
    
    user = auth_service.create_user(
        db,
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    tokens = auth_service.create_tokens_for_user(user)
    return TokenResponse(**tokens)