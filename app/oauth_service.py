"""OAuth integration service for email collection."""

import secrets
from typing import Optional, Dict, Any
from datetime import datetime
from app.models import User, OAuthAccount, OAuthProvider, UserCreate
from app.database import get_session
from sqlmodel import select


class OAuthService:
    """Service for handling OAuth authentication and user creation."""

    def __init__(self):
        # In production, these would come from environment variables
        self.google_client_id = "demo-client-id"
        self.google_client_secret = "demo-client-secret"
        self.redirect_uri = "http://localhost:8080/auth/callback"

    def get_google_auth_url(self, state: Optional[str] = None) -> str:
        """Generate Google OAuth authorization URL."""
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        from urllib.parse import urlencode

        query_string = urlencode(params)
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"

    async def exchange_code_for_tokens(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange OAuth code for access tokens."""
        # In a real implementation, this would make HTTP requests to Google's token endpoint
        # For demo purposes, we'll simulate the response
        return {
            "access_token": f"demo_access_token_{secrets.token_hex(16)}",
            "refresh_token": f"demo_refresh_token_{secrets.token_hex(16)}",
            "expires_in": 3600,
            "scope": "openid email profile",
            "id_token": f"demo_id_token_{secrets.token_hex(32)}",
        }

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Fetch user information from Google's userinfo endpoint."""
        # In a real implementation, this would make HTTP requests to Google's userinfo API
        # For demo purposes, we'll simulate the response
        return {
            "id": f"google_user_{secrets.token_hex(8)}",
            "email": "demo.user@example.com",
            "given_name": "Demo",
            "family_name": "User",
            "name": "Demo User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True,
        }

    def create_or_update_user(
        self, oauth_data: Dict[str, Any], provider: OAuthProvider = OAuthProvider.GOOGLE
    ) -> Optional[User]:
        """Create or update user from OAuth data."""
        with get_session() as session:
            # Check if user already exists by email
            statement = select(User).where(User.email == oauth_data["email"])
            existing_user = session.exec(statement).first()

            if existing_user:
                # Update existing user's first name if it has changed
                if existing_user.first_name != oauth_data.get("given_name", ""):
                    existing_user.first_name = oauth_data.get("given_name", existing_user.first_name)
                    existing_user.updated_at = datetime.utcnow()
                    session.add(existing_user)
                    session.commit()
                    session.refresh(existing_user)
                # Return fresh instance to avoid DetachedInstanceError
                return session.get(User, existing_user.id)

            # Create new user
            user_create = UserCreate(email=oauth_data["email"], first_name=oauth_data.get("given_name", ""))

            new_user = User(
                email=user_create.email,
                first_name=user_create.first_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            # Create OAuth account record
            if new_user.id is not None:
                oauth_account = OAuthAccount(
                    user_id=new_user.id,
                    provider=provider,
                    provider_user_id=oauth_data["id"],
                    provider_email=oauth_data["email"],
                    profile_data=oauth_data,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(oauth_account)
                session.commit()

            # Return fresh instance to avoid DetachedInstanceError
            return session.get(User, new_user.id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        with get_session() as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).first()


# Global service instance
oauth_service = OAuthService()
