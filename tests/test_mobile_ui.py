"""Mobile UI smoke tests - basic functionality only."""

import pytest
from nicegui.testing import User
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database for testing."""
    reset_db()
    yield
    reset_db()


async def test_root_redirects_to_auth(user: User, clean_db) -> None:
    """Test that root page redirects to auth page."""
    await user.open("/")
    # Should eventually land on auth page
    await user.should_see("Join Our SMS Service")


async def test_auth_page_basic_elements(user: User, clean_db) -> None:
    """Test that auth page has essential elements."""
    await user.open("/auth")
    await user.should_see("Join Our SMS Service")
    await user.should_see("Sign in to get started")
    await user.should_see("Continue with Google")
    await user.should_see("Demo Mode")


async def test_phone_verification_requires_auth(user: User, clean_db) -> None:
    """Test that phone verification redirects unauthenticated users."""
    await user.open("/phone-verification")
    # Should redirect to auth since no authentication
    await user.should_see("Join Our SMS Service")


async def test_completion_page_requires_auth(user: User, clean_db) -> None:
    """Test that completion page redirects unauthenticated users."""
    await user.open("/verification-complete")
    # Should redirect to auth
    await user.should_see("Join Our SMS Service")


async def test_dashboard_requires_auth(user: User, clean_db) -> None:
    """Test that dashboard redirects unauthenticated users."""
    await user.open("/dashboard")
    # Should redirect to auth
    await user.should_see("Join Our SMS Service")


async def test_logout_redirects_to_auth(user: User, clean_db) -> None:
    """Test that logout redirects to auth page."""
    await user.open("/auth/logout")
    # Should redirect to auth
    await user.should_see("Join Our SMS Service")


async def test_oauth_callback_without_code(user: User, clean_db) -> None:
    """Test OAuth callback without code shows error."""
    await user.open("/auth/callback")
    # Should show error page
    await user.should_see("Authentication Failed")
    await user.should_see("Try Again")


async def test_basic_page_accessibility(user: User, clean_db) -> None:
    """Test that pages have basic accessibility elements."""
    await user.open("/auth")

    # Should have proper headings and labels
    await user.should_see("Join Our SMS Service")
    await user.should_see("Sign in with your account")
    await user.should_see("Continue with Google")


async def test_error_handling_pages_exist(user: User, clean_db) -> None:
    """Test that error handling pages are accessible."""
    # Test OAuth callback error page
    await user.open("/auth/callback?error=access_denied")
    await user.should_see("Authentication Failed")
    await user.should_see("Try Again")

    # Test callback without parameters shows error
    await user.open("/auth/callback")
    await user.should_see("Authentication Failed")
