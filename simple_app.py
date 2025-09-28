"""
Simple Bounty Tracker Application
"""
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os

# Database setup
DATABASE_URL = "sqlite:///./bounty_tracker.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(title="Bounty Tracker", description="GitHub Bounty Tracking System", version="1.0.0")

# Static files and templates
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard"""
    try:
        # Get recent issues with bounties
        result = db.execute(text("""
            SELECT * FROM issues 
            WHERE has_bounty = 1 AND is_active = 1 
            ORDER BY github_updated_at DESC 
            LIMIT 20
        """))
        issues = result.fetchall()
        
        # Convert to dict format for template
        issues_list = []
        for issue in issues:
            issues_list.append({
                'id': issue.id,
                'github_id': issue.github_id,
                'github_number': issue.github_number,
                'title': issue.title,
                'body': issue.body,
                'html_url': issue.html_url,
                'repository_full_name': issue.repository_full_name,
                'repository_owner': issue.repository_owner,
                'repository_name': issue.repository_name,
                'bounty_amount': issue.bounty_amount,
                'bounty_formatted': f"${issue.bounty_amount / 100:.2f}",
                'has_bounty': issue.has_bounty,
                'author_username': issue.author_username,
                'comments_count': issue.comments_count,
                'primary_language': issue.primary_language,
                'github_created_at': issue.github_created_at,
                'github_updated_at': issue.github_updated_at,
                'view_count': issue.view_count
            })
        
        # Get statistics
        stats_result = db.execute(text("""
            SELECT 
                COUNT(*) as total_bounties,
                SUM(bounty_amount) as total_value,
                COUNT(CASE WHEN has_bounty = 1 THEN 1 END) as active_bounties,
                COUNT(DISTINCT repository_full_name) as total_repositories
            FROM issues 
            WHERE is_active = 1
        """))
        stats_row = stats_result.fetchone()
        
        stats = {
            "total_bounties": stats_row.total_bounties or 0,
            "total_value": (stats_row.total_value or 0) / 100,  # Convert cents to dollars
            "active_bounties": stats_row.active_bounties or 0,
            "total_repositories": stats_row.total_repositories or 0
        }
        
        return templates.TemplateResponse("dashboard/simple.html", {
            "request": request,
            "issues": issues_list,
            "stats": stats
        })
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        return templates.TemplateResponse("dashboard/simple.html", {
            "request": request,
            "issues": [],
            "stats": {
                "total_bounties": 0,
                "total_value": 0,
                "active_bounties": 0,
                "total_repositories": 0
            },
            "error": "Failed to load dashboard data"
        })

@app.get("/issues", response_class=HTMLResponse)  
async def issues_page(request: Request, db: Session = Depends(get_db)):
    """Issues listing page"""
    try:
        result = db.execute(text("""
            SELECT * FROM issues 
            WHERE is_active = 1 
            ORDER BY github_updated_at DESC 
            LIMIT 50
        """))
        issues = result.fetchall()
        
        issues_list = []
        for issue in issues:
            issues_list.append({
                'id': issue.id,
                'title': issue.title,
                'repository_full_name': issue.repository_full_name,
                'bounty_formatted': f"${issue.bounty_amount / 100:.2f}" if issue.bounty_amount > 0 else "$0.00",
                'has_bounty': issue.has_bounty,
                'author_username': issue.author_username,
                'primary_language': issue.primary_language,
                'html_url': issue.html_url,
                'github_created_at': issue.github_created_at,
                'comments_count': issue.comments_count
            })
        
        return templates.TemplateResponse("issues/simple.html", {
            "request": request,
            "issues": issues_list
        })
        
    except Exception as e:
        print(f"Issues page error: {e}")
        return templates.TemplateResponse("issues/simple.html", {
            "request": request,
            "issues": [],
            "error": "Failed to load issues"
        })

@app.get("/api/issues")
async def api_issues(db: Session = Depends(get_db)):
    """API endpoint for issues"""
    try:
        result = db.execute(text("""
            SELECT * FROM issues 
            WHERE is_active = 1 
            ORDER BY github_updated_at DESC 
            LIMIT 50
        """))
        issues = result.fetchall()
        
        issues_list = []
        for issue in issues:
            issues_list.append({
                'id': issue.id,
                'github_id': issue.github_id,
                'title': issue.title,
                'repository_full_name': issue.repository_full_name,
                'bounty_amount': issue.bounty_amount,
                'has_bounty': issue.has_bounty,
                'author_username': issue.author_username,
                'html_url': issue.html_url
            })
        
        return {"items": issues_list, "total": len(issues_list)}
        
    except Exception as e:
        return {"error": str(e), "items": [], "total": 0}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)