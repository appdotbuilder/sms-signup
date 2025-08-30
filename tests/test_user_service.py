"""Tests for user service."""

import pytest
from datetime import datetime
from app.user_service import user_service
from app.models import User, VerificationStatus
from app.database import reset_db, get_session


@pytest.fixture()
def clean_db():
    """Clean database for testing."""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def sample_user(clean_db):
    """Create a sample user for testing."""
    with get_session() as session:
        user = User(
            email="test@example.com",
            first_name="Test",
            phone_number="+15551234567",
            is_phone_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture()
def unverified_user(clean_db):
    """Create an unverified user for testing."""
    with get_session() as session:
        user = User(
            email="unverified@example.com",
            first_name="Unverified",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


class TestUserService:
    """Test user service functionality."""

    def test_get_user_by_id_found(self, sample_user):
        """Test getting existing user by ID."""
        found_user = user_service.get_user_by_id(sample_user.id)

        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email
        assert found_user.first_name == sample_user.first_name

    def test_get_user_by_id_not_found(self, clean_db):
        """Test getting non-existent user by ID."""
        user = user_service.get_user_by_id(999999)
        assert user is None

    def test_get_user_by_email_found(self, sample_user):
        """Test getting existing user by email."""
        found_user = user_service.get_user_by_email(sample_user.email)

        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email

    def test_get_user_by_email_not_found(self, clean_db):
        """Test getting non-existent user by email."""
        user = user_service.get_user_by_email("notfound@example.com")
        assert user is None

    def test_update_user_phone_verified(self, unverified_user):
        """Test updating user phone number with verification."""
        new_phone = "+15559876543"

        updated_user = user_service.update_user_phone(unverified_user.id, new_phone, is_verified=True)

        assert updated_user is not None
        assert updated_user.phone_number == new_phone
        assert updated_user.is_phone_verified
        assert updated_user.updated_at > unverified_user.updated_at

    def test_update_user_phone_unverified(self, unverified_user):
        """Test updating user phone number without verification."""
        new_phone = "+15559876543"

        updated_user = user_service.update_user_phone(unverified_user.id, new_phone, is_verified=False)

        assert updated_user is not None
        assert updated_user.phone_number == new_phone
        assert not updated_user.is_phone_verified

    def test_update_user_phone_nonexistent_user(self, clean_db):
        """Test updating phone for non-existent user."""
        updated_user = user_service.update_user_phone(999999, "+15551234567", True)
        assert updated_user is None

    def test_get_mobile_user_profile_verified(self, sample_user):
        """Test getting mobile profile for verified user."""
        profile = user_service.get_mobile_user_profile(sample_user)

        assert profile.first_name == sample_user.first_name
        assert profile.email == sample_user.email
        assert profile.phone_number == sample_user.phone_number
        assert profile.verification_status == VerificationStatus.VERIFIED
        assert profile.signup_completed
        assert profile.created_date == sample_user.created_at.isoformat()

    def test_get_mobile_user_profile_unverified(self, unverified_user):
        """Test getting mobile profile for unverified user."""
        profile = user_service.get_mobile_user_profile(unverified_user)

        assert profile.first_name == unverified_user.first_name
        assert profile.email == unverified_user.email
        assert profile.phone_number is None
        assert profile.verification_status == VerificationStatus.PENDING
        assert not profile.signup_completed

    def test_get_mobile_user_profile_phone_not_verified(self, clean_db):
        """Test getting mobile profile for user with phone but not verified."""
        with get_session() as session:
            user = User(
                email="partial@example.com",
                first_name="Partial",
                phone_number="+15551234567",
                is_phone_verified=False,  # Phone number but not verified
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        profile = user_service.get_mobile_user_profile(user)

        assert profile.phone_number == "+15551234567"
        assert profile.verification_status == VerificationStatus.PENDING
        assert not profile.signup_completed  # Not complete without verification

    def test_is_signup_complete_fully_verified(self, sample_user):
        """Test signup completion check for fully verified user."""
        is_complete = user_service.is_signup_complete(sample_user)
        assert is_complete

    def test_is_signup_complete_unverified(self, unverified_user):
        """Test signup completion check for unverified user."""
        is_complete = user_service.is_signup_complete(unverified_user)
        assert not is_complete

    def test_is_signup_complete_no_phone(self, clean_db):
        """Test signup completion check for user without phone."""
        with get_session() as session:
            user = User(
                email="nophone@example.com",
                first_name="NoPhone",
                phone_number=None,
                is_phone_verified=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        is_complete = user_service.is_signup_complete(user)
        assert not is_complete

    def test_is_signup_complete_phone_not_verified(self, clean_db):
        """Test signup completion check for user with unverified phone."""
        with get_session() as session:
            user = User(
                email="unverified@example.com",
                first_name="Unverified",
                phone_number="+15551234567",
                is_phone_verified=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        is_complete = user_service.is_signup_complete(user)
        assert not is_complete

    def test_is_signup_complete_missing_email(self, clean_db):
        """Test signup completion check for user without email."""
        # This is an edge case that shouldn't happen in normal flow
        # but we should handle it gracefully
        with get_session() as session:
            user = User(
                email="",  # Empty email
                first_name="NoEmail",
                phone_number="+15551234567",
                is_phone_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        is_complete = user_service.is_signup_complete(user)
        assert not is_complete  # Should require non-empty email

    def test_is_signup_complete_missing_first_name(self, clean_db):
        """Test signup completion check for user without first name."""
        with get_session() as session:
            user = User(
                email="noname@example.com",
                first_name="",  # Empty first name
                phone_number="+15551234567",
                is_phone_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        is_complete = user_service.is_signup_complete(user)
        assert not is_complete  # Should require non-empty first name
