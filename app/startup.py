import logging
from app.database import create_tables
from nicegui import ui
import app.mobile_auth
import app.mobile_phone_verification

logger = logging.getLogger(__name__)


def startup() -> None:
    """Initialize the application - called before the first request"""
    logger.info("Starting application initialization...")

    try:
        # Initialize database tables
        logger.info("Creating database tables...")
        create_tables()

        # Register all UI modules
        logger.info("Registering UI modules...")
        app.mobile_auth.create()
        app.mobile_phone_verification.create()

        # Root page redirect
        @ui.page("/")
        def index():
            """Root page redirects to auth."""
            ui.navigate.to("/auth")

        logger.info("Application initialization completed successfully")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        # Re-raise to prevent app from starting with broken state
        raise
