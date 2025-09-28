"""
Advanced Bounty Tracker - Main FastAPI application
Enhanced version with comprehensive features and real-time capabilities
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import asyncio

# Import database and models
from app.db import get_db, init_db
from app.models import (
    User, Issue, Repository, Bounty, Notification,
    AnalyticsEvent, SearchQuery
)

# Import services
from app.services import (
    GitHubService, NotificationService, TelegramService,
    SearchService, AnalyticsService, AuthService, BountyService
)

# Import API routers
from app.api import (
    auth_router, issues_router, bounties_router, 
    repositories_router, users_router, search_router,
    analytics_router, notifications_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, user_id: str = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def send_to_user(self, message: dict, user_id: str):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
    
    async def broadcast(self, message: dict):
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.active_connections.remove(connection)

# Global connection manager instance
connection_manager = ConnectionManager()

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info("Starting Bounty Tracker application...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Initialize services
    app.state.github_service = GitHubService()
    app.state.notification_service = NotificationService()
    app.state.telegram_service = TelegramService()
    app.state.search_service = SearchService()
    app.state.analytics_service = AnalyticsService()
    app.state.auth_service = AuthService()
    app.state.bounty_service = BountyService()
    
    logger.info("Services initialized successfully")
    
    # Start background tasks
    asyncio.create_task(periodic_github_sync())
    asyncio.create_task(periodic_notifications_cleanup())
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down Bounty Tracker application...")

# Create FastAPI app
app = FastAPI(
    title="Advanced Bounty Tracker",
    description="Comprehensive GitHub bounty tracking system with real-time notifications",
    version="2.0.0",
    lifespan=lifespan
)

# Security
security = HTTPBearer()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Templates and static files
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(issues_router, prefix="/api/issues", tags=["issues"])
app.include_router(bounties_router, prefix="/api/bounties", tags=["bounties"])
app.include_router(repositories_router, prefix="/api/repositories", tags=["repositories"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])

# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    auth_service: AuthService = app.state.auth_service
    
    user = auth_service.get_current_user(db, credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    return user

# Optional authentication (for public endpoints that show more info when authenticated)
async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        auth_service: AuthService = app.state.auth_service
        return auth_service.get_current_user(db, token)
    except:
        return None

# Analytics middleware
@app.middleware("http")
async def analytics_middleware(request: Request, call_next):
    """Track page views and user activity"""
    start_time = datetime.utcnow()
    
    response = await call_next(request)
    
    # Track analytics for successful requests
    if response.status_code < 400:
        try:
            analytics_service: AnalyticsService = app.state.analytics_service
            
            # Get user if authenticated
            user_id = None
            try:
                if hasattr(request.state, 'user'):
                    user_id = request.state.user.id
            except:
                pass
            
            # Create analytics event
            event = AnalyticsEvent.create_page_view(
                page_url=str(request.url),
                user_id=user_id,
                ip_address=request.client.host,
                user_agent=request.headers.get("User-Agent"),
                referer_url=request.headers.get("Referer")
            )
            
            # Save to database in background
            asyncio.create_task(analytics_service.save_event(event))
            
        except Exception as e:
            logger.error(f"Analytics tracking error: {e}")
    
    return response

# Main routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Main dashboard with recent bounties and statistics"""
    try:
        # Get recent high-value bounties
        recent_bounties = db.query(Issue).filter(
            Issue.has_bounty == True,
            Issue.bounty_amount >= 5000  # $50+
        ).order_by(Issue.github_updated_at.desc()).limit(20).all()
        
        # Get statistics
        total_bounties = db.query(Issue).filter(Issue.has_bounty == True).count()
        total_value = db.query(db.func.sum(Issue.bounty_amount)).filter(
            Issue.has_bounty == True
        ).scalar() or 0
        
        active_bounties = db.query(Issue).filter(
            Issue.has_bounty == True,
            Issue.status == "open"
        ).count()
        
        total_repositories = db.query(Repository).count()
        
        stats = {
            "total_bounties": total_bounties,
            "total_value": total_value / 100,  # Convert cents to dollars
            "active_bounties": active_bounties,
            "total_repositories": total_repositories
        }
        
        return templates.TemplateResponse("dashboard/index.html", {
            "request": request,
            "issues": recent_bounties,
            "stats": stats,
            "user": user
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load dashboard"
        })

@app.get("/issues", response_class=HTMLResponse)
async def issues_page(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    page: int = 1,
    per_page: int = 50,
    language: Optional[str] = None,
    min_amount: Optional[int] = None,
    status: Optional[str] = None
):
    """Issues listing page with filters"""
    try:
        search_service: SearchService = app.state.search_service
        
        # Build filters
        filters = {}
        if language:
            filters["language"] = language
        if min_amount:
            filters["min_amount"] = min_amount * 100  # Convert to cents
        if status:
            filters["status"] = status
        
        # Search issues
        results = search_service.search_issues(
            db, 
            query="",
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        # Get available languages for filter
        languages = db.query(Issue.primary_language).filter(
            Issue.primary_language.isnot(None)
        ).distinct().all()
        languages = [lang[0] for lang in languages if lang[0]]
        
        return templates.TemplateResponse("issues/list.html", {
            "request": request,
            "issues": results["items"],
            "pagination": results["pagination"],
            "languages": languages,
            "filters": {
                "language": language,
                "min_amount": min_amount,
                "status": status
            },
            "user": user
        })
        
    except Exception as e:
        logger.error(f"Issues page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load issues"
        })

@app.get("/issues/{issue_id}", response_class=HTMLResponse)
async def issue_detail(
    issue_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Individual issue detail page"""
    try:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        # Increment view count
        issue.increment_view_count()
        
        # Get related bounties
        bounties = db.query(Bounty).filter(Bounty.issue_id == issue_id).all()
        
        # Get comments
        comments = db.query(IssueComment).filter(
            IssueComment.issue_id == issue_id
        ).order_by(IssueComment.github_created_at).all()
        
        # Get repository
        repository = db.query(Repository).filter(
            Repository.id == issue.repository_id
        ).first()
        
        try:
            db.commit()  # Save view count update
        except:
            db.rollback()
        
        return templates.TemplateResponse("issues/detail.html", {
            "request": request,
            "issue": issue,
            "bounties": bounties,
            "comments": comments,
            "repository": repository,
            "user": user
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Issue detail error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load issue details"
        })

@app.get("/repositories", response_class=HTMLResponse)
async def repositories_page(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    page: int = 1,
    per_page: int = 30,
    language: Optional[str] = None,
    sort_by: str = "stars"
):
    """Repositories listing page"""
    try:
        query = db.query(Repository).filter(Repository.is_active == True)
        
        if language:
            query = query.filter(Repository.primary_language == language)
        
        # Sorting
        if sort_by == "stars":
            query = query.order_by(Repository.stars_count.desc())
        elif sort_by == "bounties":
            query = query.order_by(Repository.total_bounties.desc())
        elif sort_by == "recent":
            query = query.order_by(Repository.github_updated_at.desc())
        
        # Pagination
        total = query.count()
        offset = (page - 1) * per_page
        repositories = query.offset(offset).limit(per_page).all()
        
        # Get available languages
        languages = db.query(Repository.primary_language).filter(
            Repository.primary_language.isnot(None)
        ).distinct().all()
        languages = [lang[0] for lang in languages if lang[0]]
        
        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
            "has_prev": page > 1,
            "has_next": page * per_page < total
        }
        
        return templates.TemplateResponse("repositories/list.html", {
            "request": request,
            "repositories": repositories,
            "pagination": pagination,
            "languages": languages,
            "filters": {
                "language": language,
                "sort_by": sort_by
            },
            "user": user
        })
        
    except Exception as e:
        logger.error(f"Repositories page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load repositories"
        })

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time updates"""
    await connection_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await connection_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                        websocket
                    )
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

# Broadcast functions for real-time updates
async def broadcast_new_issue(issue: Issue):
    """Broadcast new issue to all connected clients"""
    message = {
        "type": "new_issue",
        "data": {
            "id": issue.id,
            "title": issue.title,
            "bounty_amount": issue.bounty_amount,
            "repository": issue.repository_full_name,
            "created_at": issue.github_created_at.isoformat(),
            "html_url": issue.html_url
        }
    }
    await connection_manager.broadcast(message)

async def broadcast_bounty_update(bounty: Bounty):
    """Broadcast bounty update to all connected clients"""
    message = {
        "type": "bounty_update",
        "data": {
            "id": bounty.id,
            "title": bounty.title,
            "amount": bounty.amount,
            "status": bounty.status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
    }
    await connection_manager.broadcast(message)

# Background tasks
async def periodic_github_sync():
    """Periodically sync with GitHub API"""
    while True:
        try:
            logger.info("Starting periodic GitHub sync...")
            
            github_service: GitHubService = app.state.github_service
            
            # Use database context
            from app.db import get_db_context
            
            with get_db_context() as db:
                # Search for new bounties
                new_issues = await github_service.search_bounty_issues(
                    db,
                    query="bounty OR reward OR prize",
                    min_amount=5000,  # $50 minimum
                    per_page=50,
                    max_pages=5
                )
                
                # Broadcast new issues
                for issue in new_issues:
                    await broadcast_new_issue(issue)
                
                logger.info(f"GitHub sync completed. Found {len(new_issues)} new issues")
            
        except Exception as e:
            logger.error(f"GitHub sync error: {e}")
        
        # Wait 6 hours before next sync
        await asyncio.sleep(6 * 60 * 60)

async def periodic_notifications_cleanup():
    """Clean up old notifications and analytics"""
    while True:
        try:
            logger.info("Starting periodic cleanup...")
            
            from app.db import get_db_context
            
            with get_db_context() as db:
                # Delete old read notifications (older than 30 days)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                old_notifications = db.query(Notification).filter(
                    Notification.is_read == True,
                    Notification.created_at < cutoff_date
                ).delete()
                
                # Delete old analytics events (older than 90 days)
                analytics_cutoff = datetime.utcnow() - timedelta(days=90)
                
                old_events = db.query(AnalyticsEvent).filter(
                    AnalyticsEvent.created_at < analytics_cutoff
                ).delete()
                
                logger.info(f"Cleanup completed. Removed {old_notifications} notifications and {old_events} analytics events")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        # Wait 24 hours before next cleanup
        await asyncio.sleep(24 * 60 * 60)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Application health check"""
    try:
        from app.db import get_db_stats
        
        stats = get_db_stats()
        github_service: GitHubService = app.state.github_service
        rate_limit = github_service.get_rate_limit_info()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": stats,
            "github_rate_limit": rate_limit,
            "websocket_connections": len(connection_manager.active_connections)
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "Page not found"
    }, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    logger.error(f"Server error: {exc}")
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "Internal server error"
    }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )