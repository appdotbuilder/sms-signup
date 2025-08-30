#!/usr/bin/env python3
"""Test script to debug startup issues"""

import traceback
from app.database import create_tables, reset_db
from logging import getLogger

logger = getLogger(__name__)


def test_startup_components():
    """Test if startup components work correctly"""
    logger.info("Testing startup components...")

    try:
        # Test database initialization
        logger.info("1. Testing database initialization...")
        reset_db()  # Use reset_db for tests
        create_tables()
        logger.info("   ✓ Database tables created successfully")

        # Test module imports
        logger.info("2. Testing module imports...")
        import app.mobile_auth
        import app.mobile_phone_verification

        logger.info("   ✓ Modules imported successfully")

        # Test module create functions exist
        logger.info("3. Testing module create functions...")
        assert hasattr(app.mobile_auth, "create"), "mobile_auth missing create() function"
        assert hasattr(app.mobile_phone_verification, "create"), "mobile_phone_verification missing create() function"
        logger.info("   ✓ Create functions found")

        logger.info("🎉 All startup components working correctly!")

    except Exception as e:
        logger.error(f"❌ Error during startup test: {e}")
        logger.error("Full traceback:")
        traceback.print_exc()
        raise  # Re-raise for pytest to catch


def test_module_imports():
    """Test that modules can be imported without issues"""
    try:
        import app.mobile_auth
        import app.mobile_phone_verification

        # Verify create functions exist
        assert hasattr(app.mobile_auth, "create")
        assert hasattr(app.mobile_phone_verification, "create")

        logger.info("✓ Module import test passed")
    except Exception as e:
        logger.error(f"Module import failed: {e}")
        raise
