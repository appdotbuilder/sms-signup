import os
import logging
from sqlmodel import SQLModel, create_engine, Session

# Import all models to ensure they're registered. ToDo: replace with specific imports when possible.
from app.models import *  # noqa: F401, F403

logger = logging.getLogger(__name__)

# Try PostgreSQL first, fallback to SQLite for local development
DATABASE_URL = os.environ.get("APP_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/postgres")


def create_engine_with_fallback():
    """Create database engine with fallback to SQLite for local development"""
    try:
        # Try PostgreSQL first
        engine = create_engine(
            DATABASE_URL, connect_args={"connect_timeout": 15, "options": "-c statement_timeout=1000"}
        )
        # Test connection
        with engine.connect():
            logger.info("Connected to PostgreSQL database")
        return engine
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")
        logger.info("Falling back to SQLite for local development")

        # Fallback to SQLite
        sqlite_url = "sqlite:///./app.db"
        engine = create_engine(sqlite_url, echo=False)
        logger.info("Connected to SQLite database")
        return engine


ENGINE = create_engine_with_fallback()


def create_tables():
    """Create all tables in the database"""
    try:
        SQLModel.metadata.create_all(ENGINE)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_session():
    return Session(ENGINE)


def reset_db():
    """Wipe all tables in the database. Use with caution - for testing only!"""
    try:
        SQLModel.metadata.drop_all(ENGINE)
        SQLModel.metadata.create_all(ENGINE)
        logger.info("Database reset completed")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise
