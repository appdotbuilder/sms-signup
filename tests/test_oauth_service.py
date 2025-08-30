"""Tests for OAuth service."""

import pytest
from app.oauth_service import oauth_service
from app.models import OAuthProvider
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database for testing."""
    reset_db()
    yield
    reset_db()


class TestOAuthService:
    """Test OAuth service functionality."""

    def test_get_google_auth_url(self):
        """Test Google OAuth URL generation."""
        url = oauth_service.get_google_auth_url(state="test_state")

        assert "accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=demo-client-id" in url
        assert "state=test_state" in url
        assert "scope=openid%20email%20profile" in url or "scope=openid+email+profile" in url
        assert "response_type=code" in url

    def test_get_google_auth_url_without_state(self):
        """Test Google OAuth URL generation without explicit state."""
        url = oauth_service.get_google_auth_url()

        assert "accounts.google.com/o/oauth2/v2/auth" in url
        assert "state=" in url  # Should have generated a state

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self):
        """Test OAuth code exchange (mocked)."""
        tokens = await oauth_service.exchange_code_for_tokens("test_code")

        assert tokens is not None
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "expires_in" in tokens
        assert tokens["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test getting user info from OAuth provider (mocked)."""
        user_info = await oauth_service.get_user_info("test_token")

        assert user_info is not None
        assert "id" in user_info
        assert "email" in user_info
        assert "given_name" in user_info
        assert user_info["email"] == "demo.user@example.com"
        assert user_info["given_name"] == "Demo"

    def test_create_new_user(self, clean_db):
        """Test creating a new user from OAuth data."""
        oauth_data = {
            "id": "google_123",
            "email": "newuser@example.com",
            "given_name": "New",
            "family_name": "User",
            "verified_email": True,
        }

        user = oauth_service.create_or_update_user(oauth_data, OAuthProvider.GOOGLE)

        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.first_name == "New"
        assert not user.is_phone_verified
        assert user.phone_number is None

    def test_update_existing_user(self, clean_db):
        """Test updating an existing user from OAuth data."""
        # Create initial user
        initial_oauth_data = {
            "id": "google_123",
            "email": "existing@example.com",
            "given_name": "Old",
            "family_name": "Name",
        }

        user1 = oauth_service.create_or_update_user(initial_oauth_data, OAuthProvider.GOOGLE)
        assert user1 is not None
        assert user1.first_name == "Old"

        # Update with new name
        updated_oauth_data = {
            "id": "google_123",
            "email": "existing@example.com",
            "given_name": "New",
            "family_name": "Name",
        }

        user2 = oauth_service.create_or_update_user(updated_oauth_data, OAuthProvider.GOOGLE)
        assert user2 is not None
        assert user2.id == user1.id  # Same user
        assert user2.first_name == "New"  # Updated name

    def test_get_user_by_email(self, clean_db):
        """Test getting user by email."""
        # Create user first
        oauth_data = {"id": "google_123", "email": "findme@example.com", "given_name": "Find", "family_name": "Me"}

        created_user = oauth_service.create_or_update_user(oauth_data, OAuthProvider.GOOGLE)
        assert created_user is not None

        # Find user by email
        found_user = oauth_service.get_user_by_email("findme@example.com")
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "findme@example.com"

    def test_get_user_by_email_not_found(self, clean_db):
        """Test getting non-existent user by email."""
        user = oauth_service.get_user_by_email("notfound@example.com")
        assert user is None

    def test_create_user_with_empty_name(self, clean_db):
        """Test creating user when OAuth data has empty given_name."""
        oauth_data = {"id": "google_123", "email": "noname@example.com", "given_name": "", "family_name": "User"}

        user = oauth_service.create_or_update_user(oauth_data, OAuthProvider.GOOGLE)

        assert user is not None
        assert user.email == "noname@example.com"
        assert user.first_name == ""  # Should handle empty name gracefully

    def test_create_user_missing_given_name(self, clean_db):
        """Test creating user when OAuth data is missing given_name."""
        oauth_data = {
            "id": "google_123",
            "email": "missing@example.com",
            "family_name": "User",
            # No 'given_name' key
        }

        user = oauth_service.create_or_update_user(oauth_data, OAuthProvider.GOOGLE)

        assert user is not None
        assert user.email == "missing@example.com"
        assert user.first_name == ""  # Should default to empty string
