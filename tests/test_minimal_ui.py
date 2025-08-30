"""Minimal UI test to verify the application works"""

import pytest
from nicegui.testing import User


@pytest.mark.asyncio
async def test_root_page_redirects_to_auth(user: User) -> None:
    """Test that root page redirects to /auth"""
    await user.open("/")

    # Should redirect to /auth page
    await user.should_see("Join Our SMS Service")

    # Verify the auth page components are present
    await user.should_see("Sign in with your account")
    await user.should_see("Continue with Google")


@pytest.mark.asyncio
async def test_auth_page_loads_correctly(user: User) -> None:
    """Test that /auth page loads with expected content"""
    await user.open("/auth")

    # Check main elements are present
    await user.should_see("Join Our SMS Service")
    await user.should_see("Sign in to get started")
    await user.should_see("Continue with Google")
    await user.should_see("Demo Mode")


@pytest.mark.asyncio
async def test_auth_callback_without_code_shows_error(user: User) -> None:
    """Test that auth callback without code shows error page"""
    await user.open("/auth/callback")

    # Should show error message
    await user.should_see("Authentication Failed")
    await user.should_see("Try Again")


@pytest.mark.asyncio
async def test_phone_verification_redirects_when_not_authenticated(user: User) -> None:
    """Test that phone verification redirects to auth when not authenticated"""
    await user.open("/phone-verification")

    # Should redirect to auth page since no user is in tab storage
    await user.should_see("Join Our SMS Service")
