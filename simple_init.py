#!/usr/bin/env python3
"""
Simple initialization for Bounty Tracker
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Simple database setup
DATABASE_URL = "sqlite:///./bounty_tracker.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def create_simple_tables():
    """Create basic tables"""
    
    sql_commands = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS repositories (
            id TEXT PRIMARY KEY,
            github_id TEXT UNIQUE NOT NULL,
            full_name TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            owner TEXT NOT NULL,
            description TEXT,
            html_url TEXT NOT NULL,
            primary_language TEXT,
            stars_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS issues (
            id TEXT PRIMARY KEY,
            github_id TEXT UNIQUE NOT NULL,
            github_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            html_url TEXT NOT NULL,
            repository_full_name TEXT NOT NULL,
            repository_owner TEXT NOT NULL,
            repository_name TEXT NOT NULL,
            bounty_amount INTEGER DEFAULT 0,
            has_bounty INTEGER DEFAULT 0,
            author_username TEXT NOT NULL,
            comments_count INTEGER DEFAULT 0,
            primary_language TEXT,
            github_created_at DATETIME NOT NULL,
            github_updated_at DATETIME NOT NULL,
            view_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    with engine.connect() as conn:
        for sql in sql_commands:
            conn.execute(text(sql))
        conn.commit()
    
    print("✅ Basic database tables created successfully!")

def insert_sample_data():
    """Insert sample data"""
    
    import uuid
    from datetime import datetime
    
    sample_data = [
        # Sample issues
        """
        INSERT OR IGNORE INTO issues 
        (id, github_id, github_number, title, body, html_url, repository_full_name, 
         repository_owner, repository_name, bounty_amount, has_bounty, author_username,
         comments_count, primary_language, github_created_at, github_updated_at)
        VALUES 
        ('{}', 'issue_1', 42, 'Add dark mode support - $150 Bounty',
         'We need to implement dark mode support for the application.',
         'https://github.com/example/repo/issues/42',
         'example/sample-repo', 'example', 'sample-repo', 15000, 1, 'developer1',
         3, 'JavaScript', '{}', '{}')
        """.format(str(uuid.uuid4()), datetime.now(), datetime.now()),
        
        """
        INSERT OR IGNORE INTO issues 
        (id, github_id, github_number, title, body, html_url, repository_full_name,
         repository_owner, repository_name, bounty_amount, has_bounty, author_username,
         comments_count, primary_language, github_created_at, github_updated_at)
        VALUES 
        ('{}', 'issue_2', 43, 'Fix memory leak - $75 Bounty',
         'There is a memory leak in the data processing module.',
         'https://github.com/example/repo/issues/43',
         'example/sample-repo', 'example', 'sample-repo', 7500, 1, 'developer2',
         1, 'Python', '{}', '{}')
        """.format(str(uuid.uuid4()), datetime.now(), datetime.now()),
        
        """
        INSERT OR IGNORE INTO issues 
        (id, github_id, github_number, title, body, html_url, repository_full_name,
         repository_owner, repository_name, bounty_amount, has_bounty, author_username,
         comments_count, primary_language, github_created_at, github_updated_at)
        VALUES 
        ('{}', 'issue_3', 44, 'Add API documentation - $50 Bounty',
         'Need comprehensive API documentation with examples.',
         'https://github.com/example/repo/issues/44',
         'example/sample-repo', 'example', 'sample-repo', 5000, 1, 'developer3',
         0, 'TypeScript', '{}', '{}')
        """.format(str(uuid.uuid4()), datetime.now(), datetime.now())
    ]
    
    with engine.connect() as conn:
        for sql in sample_data:
            conn.execute(text(sql))
        conn.commit()
    
    print("✅ Sample data inserted successfully!")

if __name__ == "__main__":
    print("🚀 Initializing Bounty Tracker (Simple Version)...")
    
    create_simple_tables()
    insert_sample_data()
    
    print("\n" + "="*60)
    print("🎉 Bounty Tracker initialized successfully!")
    print("="*60)
    print("\n📋 Next steps:")
    print("1. Start the application:")
    print("   pm2 start ecosystem.config.cjs")
    print("\n2. Access the application:")
    print("   http://localhost:3000")
    print("="*60)