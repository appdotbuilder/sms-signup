"""User management service."""

from typing import Optional
from datetime import datetime
from app.models import User, MobileUserProfile, VerificationStatus
from app.database import get_session
from sqlmodel import select


class UserService:
    """Service for user management operations."""

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with get_session() as session:
            return session.get(User, user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        with get_session() as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).first()

    def update_user_phone(self, user_id: int, phone_number: str, is_verified: bool = False) -> Optional[User]:
        """Update user's phone number and verification status."""
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                return None

            user.phone_number = phone_number
            user.is_phone_verified = is_verified
            user.updated_at = datetime.utcnow()

            session.add(user)
            session.commit()
            session.refresh(user)
            # Return fresh instance to avoid DetachedInstanceError
            return session.get(User, user.id)

    def get_mobile_user_profile(self, user: User) -> MobileUserProfile:
        """Get mobile-optimized user profile."""
        verification_status = VerificationStatus.VERIFIED if user.is_phone_verified else VerificationStatus.PENDING
        signup_completed = user.is_phone_verified and user.phone_number is not None

        return MobileUserProfile(
            first_name=user.first_name,
            email=user.email,
            phone_number=user.phone_number,
            verification_status=verification_status,
            signup_completed=signup_completed,
            created_date=user.created_at.isoformat(),
        )

    def is_signup_complete(self, user: User) -> bool:
        """Check if user has completed the full signup process."""
        return bool(
            user.email
            and user.email.strip()
            and user.first_name
            and user.first_name.strip()
            and user.phone_number
            and user.phone_number.strip()
            and user.is_phone_verified
        )


# Global service instance
user_service = UserService()
