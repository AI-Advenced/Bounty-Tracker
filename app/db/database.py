"""
Enhanced database configuration with connection pooling and monitoring
"""
import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
from app.models.base import Base

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bounty_tracker.db")
DATABASE_ECHO = os.getenv("DATABASE_ECHO", "false").lower() == "true"

# Create engine with optimizations for SQLite
engine_kwargs = {
    "echo": DATABASE_ECHO,
    "future": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "connect_args": {
            "check_same_thread": False,
            "timeout": 30,
        },
        "poolclass": StaticPool,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session configuration
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)

# Logging setup
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO if DATABASE_ECHO else logging.WARNING)

# Database event listeners for SQLite optimizations
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Optimize SQLite settings"""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        
        # Performance optimizations
        cursor.execute("PRAGMA journal_mode=WAL")          # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")        # Faster than FULL
        cursor.execute("PRAGMA cache_size=-64000")         # 64MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")         # Temp tables in memory
        cursor.execute("PRAGMA mmap_size=268435456")       # 256MB memory map
        
        # Foreign key enforcement
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Automatic index creation
        cursor.execute("PRAGMA automatic_index=ON")
        
        cursor.close()

# Connection monitoring
@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log database connections"""
    logging.debug("Connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log database disconnections"""
    logging.debug("Connection checked in to pool")

# Dependency injection for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logging.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logging.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db() -> None:
    """
    Initialize database with all tables
    """
    try:
        # Import all models to ensure they're registered
        from app.models import (
            User, Issue, Repository, Bounty, Notification,
            SearchQuery, AnalyticsEvent, AnalyticsSummary
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logging.info("Database initialized successfully")
        
        # Create indexes for better performance
        create_indexes()
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise

def create_tables() -> None:
    """
    Create all tables (alias for init_db for compatibility)
    """
    init_db()

def create_indexes() -> None:
    """
    Create additional indexes for better query performance
    """
    try:
        with engine.connect() as connection:
            # Composite indexes for common queries
            indexes = [
                # Issues indexes
                "CREATE INDEX IF NOT EXISTS idx_issues_repo_status ON issues(repository_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_issues_bounty_amount ON issues(bounty_amount DESC) WHERE has_bounty = 1",
                "CREATE INDEX IF NOT EXISTS idx_issues_created_date ON issues(github_created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_issues_language_bounty ON issues(primary_language, has_bounty)",
                
                # Bounties indexes  
                "CREATE INDEX IF NOT EXISTS idx_bounties_status_amount ON bounties(status, amount DESC)",
                "CREATE INDEX IF NOT EXISTS idx_bounties_deadline ON bounties(deadline_at) WHERE deadline_at IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_bounties_hunter_status ON bounties(hunter_id, status)",
                
                # Users indexes
                "CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_users_github_username ON users(github_username) WHERE github_username IS NOT NULL",
                
                # Repositories indexes
                "CREATE INDEX IF NOT EXISTS idx_repositories_language_stars ON repositories(primary_language, stars_count DESC)",
                "CREATE INDEX IF NOT EXISTS idx_repositories_bounty_stats ON repositories(total_bounties DESC, active_bounties DESC)",
                
                # Notifications indexes
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_notifications_type_priority ON notifications(notification_type, priority)",
                
                # Analytics indexes
                "CREATE INDEX IF NOT EXISTS idx_analytics_events_type_date ON analytics_events(event_type, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_events_user_session ON analytics_events(user_id, session_id)",
                
                # Search indexes
                "CREATE INDEX IF NOT EXISTS idx_search_queries_user_date ON search_queries(user_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_search_queries_text ON search_queries(query_text)",
            ]
            
            for index_sql in indexes:
                try:
                    connection.execute(text(index_sql))
                    logging.debug(f"Created index: {index_sql}")
                except Exception as e:
                    logging.warning(f"Failed to create index: {e}")
            
            connection.commit()
            logging.info("Database indexes created successfully")
            
    except Exception as e:
        logging.error(f"Failed to create indexes: {e}")

def drop_tables() -> None:
    """
    Drop all tables (use with caution!)
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logging.info("All tables dropped successfully")
    except Exception as e:
        logging.error(f"Failed to drop tables: {e}")
        raise

def get_db_stats() -> dict:
    """
    Get database statistics and health information
    """
    try:
        with engine.connect() as connection:
            stats = {}
            
            # Get table row counts
            tables = [
                'users', 'issues', 'repositories', 'bounties', 
                'notifications', 'analytics_events', 'search_queries'
            ]
            
            for table in tables:
                try:
                    result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    stats[f"{table}_count"] = result.scalar()
                except:
                    stats[f"{table}_count"] = 0
            
            # Get database size (SQLite specific)
            if DATABASE_URL.startswith("sqlite"):
                try:
                    result = connection.execute(text("SELECT page_count * page_size AS size FROM pragma_page_count(), pragma_page_size()"))
                    stats["database_size_bytes"] = result.scalar()
                except:
                    stats["database_size_bytes"] = 0
            
            # Get connection pool stats
            stats["pool_size"] = engine.pool.size()
            stats["pool_checked_in"] = engine.pool.checkedin()
            stats["pool_checked_out"] = engine.pool.checkedout()
            
            return stats
            
    except Exception as e:
        logging.error(f"Failed to get database stats: {e}")
        return {}

def vacuum_database() -> None:
    """
    Optimize SQLite database by running VACUUM
    """
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as connection:
                connection.execute(text("VACUUM"))
                connection.commit()
                logging.info("Database vacuumed successfully")
        except Exception as e:
            logging.error(f"Failed to vacuum database: {e}")

def backup_database(backup_path: str) -> None:
    """
    Create a backup of the SQLite database
    """
    if DATABASE_URL.startswith("sqlite"):
        import shutil
        try:
            # Extract the database file path from URL
            db_file = DATABASE_URL.replace("sqlite:///", "")
            shutil.copy2(db_file, backup_path)
            logging.info(f"Database backed up to {backup_path}")
        except Exception as e:
            logging.error(f"Failed to backup database: {e}")
            raise