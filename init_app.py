#!/usr/bin/env python3
"""
Initialize the Bounty Tracker application
"""
import asyncio
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def initialize_application():
    """Initialize the application with database setup and sample data"""
    
    logger.info("Starting Bounty Tracker initialization...")
    
    try:
        # Import after setting up logging
        from app.db import init_db, get_db_context
        from app.models import User, Repository, Issue
        from app.models.user import UserRole
        from app.services import AuthService, GitHubService
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
        
        # Create admin user if not exists
        logger.info("Creating admin user...")
        with get_db_context() as db:
            auth_service = AuthService()
            
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                admin_user = auth_service.create_user(
                    db,
                    username="admin",
                    email="admin@bountytracker.com",
                    password="admin123",
                    full_name="Administrator",
                    role=UserRole.ADMIN
                )
                if admin_user:
                    admin_user.is_superuser = True
                    admin_user.is_verified = True
                    db.commit()
                    logger.info("Admin user created successfully")
                else:
                    logger.error("Failed to create admin user")
            else:
                logger.info("Admin user already exists")
        
        # Fetch initial bounty data if GitHub token is available
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            logger.info("GitHub token found, fetching initial bounty data...")
            
            github_service = GitHubService()
            
            with get_db_context() as db:
                try:
                    # Search for Python bounties
                    python_issues = await github_service.search_bounty_issues(
                        db,
                        query="python bounty OR reward",
                        language="python",
                        min_amount=2500,  # $25 minimum
                        per_page=20,
                        max_pages=2
                    )
                    
                    # Search for JavaScript bounties
                    js_issues = await github_service.search_bounty_issues(
                        db,
                        query="javascript bounty OR reward",
                        language="javascript", 
                        min_amount=2500,
                        per_page=20,
                        max_pages=2
                    )
                    
                    total_issues = len(python_issues) + len(js_issues)
                    logger.info(f"Fetched {total_issues} initial bounty issues")
                    
                except Exception as e:
                    logger.error(f"Error fetching initial bounties: {e}")
                    
        else:
            logger.warning("No GitHub token provided, skipping initial data fetch")
            logger.info("Set GITHUB_TOKEN environment variable to enable GitHub API access")
        
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        logger.info("Bounty Tracker initialization completed successfully!")
        logger.info("You can now start the application with: pm2 start ecosystem.config.cjs")
        
        return True
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return False

def create_sample_data():
    """Create sample data for development/testing"""
    logger.info("Creating sample data...")
    
    try:
        from app.db import get_db_context
        from app.models import User, Repository, Issue, Bounty
        from app.models.user import UserRole
        from app.models.issue import IssueStatus
        from app.models.bounty import BountyStatus, BountyType
        from app.services import AuthService
        from datetime import datetime, timedelta
        
        with get_db_context() as db:
            auth_service = AuthService()
            
            # Create sample users
            sample_users = [
                {
                    "username": "hunter1",
                    "email": "hunter1@example.com", 
                    "password": "password123",
                    "full_name": "Alice Hunter",
                    "role": UserRole.HUNTER
                },
                {
                    "username": "maintainer1",
                    "email": "maintainer1@example.com",
                    "password": "password123", 
                    "full_name": "Bob Maintainer",
                    "role": UserRole.MAINTAINER
                }
            ]
            
            created_users = []
            for user_data in sample_users:
                existing_user = db.query(User).filter(User.username == user_data["username"]).first()
                if not existing_user:
                    user = auth_service.create_user(db, **user_data)
                    if user:
                        user.is_verified = True
                        created_users.append(user)
                        logger.info(f"Created sample user: {user.username}")
                else:
                    created_users.append(existing_user)
            
            # Create sample repository
            sample_repo = Repository(
                github_id="12345",
                full_name="example/sample-project",
                name="sample-project",
                owner="example",
                description="A sample project for demonstrating bounties",
                html_url="https://github.com/example/sample-project",
                clone_url="https://github.com/example/sample-project.git",
                ssh_url="git@github.com:example/sample-project.git",
                primary_language="Python",
                stars_count=150,
                forks_count=25,
                watchers_count=45,
                open_issues_count=8,
                github_created_at=datetime.utcnow() - timedelta(days=365),
                github_updated_at=datetime.utcnow() - timedelta(days=1),
                github_pushed_at=datetime.utcnow() - timedelta(hours=2)
            )
            
            existing_repo = db.query(Repository).filter(Repository.full_name == sample_repo.full_name).first()
            if not existing_repo:
                db.add(sample_repo)
                db.commit()
                logger.info(f"Created sample repository: {sample_repo.full_name}")
            else:
                sample_repo = existing_repo
            
            # Create sample issues
            sample_issues = [
                {
                    "github_id": "issue_1",
                    "github_number": 42,
                    "title": "Add dark mode support - $150 Bounty",
                    "body": "We need to implement dark mode support for the application. This includes updating the CSS, adding a toggle switch, and persisting user preference.",
                    "bounty_amount": 15000,  # $150
                    "has_bounty": True,
                    "bounty_source": "custom"
                },
                {
                    "github_id": "issue_2", 
                    "github_number": 43,
                    "title": "Fix memory leak in data processing - $75 Bounty",
                    "body": "There's a memory leak in the data processing module that causes the application to crash after processing large datasets.",
                    "bounty_amount": 7500,  # $75
                    "has_bounty": True,
                    "bounty_source": "github"
                },
                {
                    "github_id": "issue_3",
                    "github_number": 44, 
                    "title": "Add API documentation - $50 Bounty",
                    "body": "Need comprehensive API documentation with examples and usage guidelines.",
                    "bounty_amount": 5000,  # $50
                    "has_bounty": True,
                    "bounty_source": "bountysource"
                }
            ]
            
            for issue_data in sample_issues:
                existing_issue = db.query(Issue).filter(Issue.github_id == issue_data["github_id"]).first()
                if not existing_issue:
                    issue = Issue(
                        repository_id=sample_repo.id,
                        repository_full_name=sample_repo.full_name,
                        repository_owner=sample_repo.owner,
                        repository_name=sample_repo.name,
                        html_url=f"https://github.com/{sample_repo.full_name}/issues/{issue_data['github_number']}",
                        api_url=f"https://api.github.com/repos/{sample_repo.full_name}/issues/{issue_data['github_number']}",
                        status=IssueStatus.OPEN,
                        author_username="example-user",
                        author_avatar_url="https://github.com/identicons/example-user.png",
                        comments_count=3,
                        primary_language=sample_repo.primary_language,
                        github_created_at=datetime.utcnow() - timedelta(days=7),
                        github_updated_at=datetime.utcnow() - timedelta(hours=12),
                        **issue_data
                    )
                    db.add(issue)
                    logger.info(f"Created sample issue: {issue.title}")
            
            db.commit()
            logger.info("Sample data created successfully!")
            
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--sample-data":
        # Create sample data
        create_sample_data()
    else:
        # Full initialization
        success = asyncio.run(initialize_application())
        
        if success:
            print("\n" + "="*60)
            print("🎉 Bounty Tracker initialized successfully!")
            print("="*60)
            print("\n📋 Next steps:")
            print("1. Set environment variables (optional):")
            print("   export GITHUB_TOKEN='your_github_token'")
            print("   export TELEGRAM_BOT_TOKEN='your_telegram_token'")
            print("\n2. Start the application:")
            print("   pm2 start ecosystem.config.cjs")
            print("\n3. Access the application:")
            print("   http://localhost:3000")
            print("\n4. Admin login:")
            print("   Username: admin")
            print("   Password: admin123")
            print("\n🔧 Additional commands:")
            print("   python init_app.py --sample-data  # Create sample data")
            print("   pm2 logs bounty-tracker          # View logs")
            print("   pm2 restart bounty-tracker       # Restart app")
            print("="*60)
        else:
            print("\n❌ Initialization failed. Check the logs above.")
            sys.exit(1)