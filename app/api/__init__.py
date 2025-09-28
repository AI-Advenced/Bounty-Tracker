# API routers initialization
from .auth import router as auth_router
from .issues import router as issues_router  
from .bounties import router as bounties_router
from .repositories import router as repositories_router
from .users import router as users_router
from .search import router as search_router
from .analytics import router as analytics_router
from .notifications import router as notifications_router

__all__ = [
    "auth_router",
    "issues_router", 
    "bounties_router",
    "repositories_router",
    "users_router",
    "search_router",
    "analytics_router", 
    "notifications_router"
]