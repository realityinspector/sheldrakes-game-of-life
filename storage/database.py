#!/usr/bin/env python3
"""
Database Configuration and Connection Management

Supports both SQLite and PostgreSQL databases with automatic detection
and appropriate engine configuration.
"""

import os
import logging
from typing import Optional, Union
from pathlib import Path
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, continue without it
    pass

logger = logging.getLogger(__name__)

# Base for SQLAlchemy models
Base = declarative_base()
metadata = MetaData()

class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///emergence.db")
        self.is_sqlite = self._is_sqlite_url(self.database_url)
        self.is_postgres = self._is_postgres_url(self.database_url)
        
        # Configure engines
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        
        self._setup_engines()
        
    def _is_sqlite_url(self, url: str) -> bool:
        """Check if database URL is for SQLite"""
        return url.startswith("sqlite:")
        
    def _is_postgres_url(self, url: str) -> bool:
        """Check if database URL is for PostgreSQL"""
        return (url.startswith("postgresql:") or 
                url.startswith("postgres:") or 
                url.startswith("postgresql+") or
                url.startswith("postgres+"))
        
    def _setup_engines(self):
        """Set up synchronous and asynchronous database engines"""
        
        if self.is_sqlite:
            self._setup_sqlite()
        elif self.is_postgres:
            self._setup_postgres()
        else:
            raise ValueError(f"Unsupported database URL: {self.database_url}")
            
    def _setup_sqlite(self):
        """Configure SQLite engines"""
        logger.info(f"Configuring SQLite database: {self.database_url}")
        
        # Synchronous SQLite engine
        self.engine = create_engine(
            self.database_url,
            echo=False,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,  # Allow SQLite to be used across threads
            }
        )
        
        # Async SQLite engine (using aiosqlite)
        async_url = self.database_url.replace("sqlite:", "sqlite+aiosqlite:")
        self.async_engine = create_async_engine(
            async_url,
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        
        # Session makers
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.AsyncSessionLocal = sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )
        
    def _setup_postgres(self):
        """Configure PostgreSQL engines"""
        logger.info(f"Configuring PostgreSQL database: {self.database_url}")
        
        # Synchronous PostgreSQL engine  
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600
        )
        
        # Async PostgreSQL engine (using asyncpg)
        if "postgresql+psycopg:" in self.database_url:
            async_url = self.database_url.replace("postgresql+psycopg:", "postgresql+asyncpg:")
        elif "postgresql:" in self.database_url:
            async_url = self.database_url.replace("postgresql:", "postgresql+asyncpg:")
        elif "postgres:" in self.database_url:
            async_url = self.database_url.replace("postgres:", "postgresql+asyncpg:")
        else:
            async_url = self.database_url.replace("postgresql+", "postgresql+asyncpg:")
            
        self.async_engine = create_async_engine(
            async_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600
        )
        
        # Session makers
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.AsyncSessionLocal = sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )
        
    def create_tables(self):
        """Create all database tables"""
        logger.info("Creating database tables...")
        
        if self.is_sqlite:
            # Ensure directory exists for SQLite
            db_path = Path(self.database_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
        
    async def create_tables_async(self):
        """Create all database tables asynchronously"""
        logger.info("Creating database tables (async)...")
        
        if self.is_sqlite:
            # Ensure directory exists for SQLite
            db_path = Path(self.database_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
        # Create tables
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully (async)")
        
    def get_session(self):
        """Get a synchronous database session"""
        return self.SessionLocal()
        
    def get_async_session(self):
        """Get an asynchronous database session"""
        return self.AsyncSessionLocal()
        
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            self.async_engine.sync_engine.dispose()
            
    @property
    def database_type(self) -> str:
        """Get the database type name"""
        if self.is_sqlite:
            return "SQLite"
        elif self.is_postgres:
            return "PostgreSQL"
        else:
            return "Unknown"
            
    @property 
    def database_info(self) -> dict:
        """Get database configuration information"""
        return {
            "type": self.database_type,
            "url": self.database_url,
            "is_sqlite": self.is_sqlite,
            "is_postgres": self.is_postgres,
            "supports_async": True
        }


# Global database configuration instance
db_config = DatabaseConfig()

# Convenience functions
def get_engine():
    """Get the synchronous database engine"""
    return db_config.engine

def get_async_engine():
    """Get the asynchronous database engine"""
    return db_config.async_engine
    
def get_session():
    """Get a synchronous database session"""
    return db_config.get_session()
    
def get_async_session():
    """Get an asynchronous database session"""
    return db_config.get_async_session()
    
def create_tables():
    """Create all database tables"""
    return db_config.create_tables()
    
async def create_tables_async():
    """Create all database tables asynchronously"""
    return await db_config.create_tables_async()

def get_database_info() -> dict:
    """Get database configuration information"""
    return db_config.database_info


if __name__ == "__main__":
    # Quick test of database configuration
    print("🗄️  Database Configuration Test")
    print("=" * 40)
    
    info = get_database_info()
    print(f"Database Type: {info['type']}")
    print(f"Database URL: {info['url']}")
    print(f"SQLite: {info['is_sqlite']}")
    print(f"PostgreSQL: {info['is_postgres']}")
    print(f"Async Support: {info['supports_async']}")
    
    print("\nTesting table creation...")
    try:
        create_tables()
        print("✅ Tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")