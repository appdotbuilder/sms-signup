"""Tests for phone verification service."""

import pytest
from datetime import datetime, timedelta
from app.phone_verification_service import phone_verification_service
from app.models import User, VerificationStatus, PhoneVerification
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
            email="test@example.com", first_name="Test", created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


class TestPhoneVerificationService:
    """Test phone verification service functionality."""

    def test_generate_verification_code(self):
        """Test verification code generation."""
        code = phone_verification_service.generate_verification_code()

        assert len(code) == 6
        assert code.isdigit()

    def test_clean_phone_number_us_with_plus(self):
        """Test phone number cleaning for US numbers with +."""
        service = phone_verification_service

        # Test various formats
        assert service._clean_phone_number("+1 (555) 123-4567") == "+15551234567"
        assert service._clean_phone_number("+1-555-123-4567") == "+15551234567"
        assert service._clean_phone_number("+1 555 123 4567") == "+15551234567"

    def test_clean_phone_number_us_without_plus(self):
        """Test phone number cleaning for US numbers without +."""
        service = phone_verification_service

        assert service._clean_phone_number("15551234567") == "+15551234567"
        assert service._clean_phone_number("5551234567") == "+15551234567"
        assert service._clean_phone_number("(555) 123-4567") == "+15551234567"

    def test_clean_phone_number_international(self):
        """Test phone number cleaning for international numbers."""
        service = phone_verification_service

        assert service._clean_phone_number("44 20 7123 4567") == "+442071234567"
        assert service._clean_phone_number("+44 20 7123 4567") == "+442071234567"

    def test_send_verification_code_success(self, sample_user):
        """Test successful verification code sending."""
        phone_number = "+1 (555) 123-4567"

        verification = phone_verification_service.send_verification_code(sample_user, phone_number)

        assert verification is not None
        assert verification.user_id == sample_user.id
        assert verification.phone_number == "+15551234567"  # Cleaned format
        assert verification.status == VerificationStatus.PENDING
        assert len(verification.verification_code) == 6
        assert verification.verification_code.isdigit()
        assert verification.sms_service_id is not None
        assert verification.sms_service_status == "sent"

    def test_send_verification_code_user_without_id(self):
        """Test sending code to user without ID."""
        user = User(email="test@example.com", first_name="Test")  # No ID

        verification = phone_verification_service.send_verification_code(user, "+15551234567")

        assert verification is None

    def test_verify_code_success(self, sample_user):
        """Test successful code verification."""
        phone_number = "+1 (555) 123-4567"

        # Send verification code
        verification = phone_verification_service.send_verification_code(sample_user, phone_number)
        assert verification is not None

        # Verify the code
        user_id = sample_user.id  # Store ID to avoid detached instance issues
        success, result, message = phone_verification_service.verify_code(
            sample_user, phone_number, verification.verification_code
        )

        assert success
        assert result is not None
        assert result.status == VerificationStatus.VERIFIED
        assert result.verified_at is not None
        assert message == "Phone number verified successfully"

        # Check that user was updated
        with get_session() as session:
            updated_user = session.get(User, user_id)
            assert updated_user is not None
            assert updated_user.phone_number == "+15551234567"
            assert updated_user.is_phone_verified

    def test_verify_code_wrong_code(self, sample_user):
        """Test verification with wrong code."""
        phone_number = "+1 (555) 123-4567"

        # Send verification code
        verification = phone_verification_service.send_verification_code(sample_user, phone_number)
        assert verification is not None

        # Try wrong code
        wrong_code = "999999" if verification.verification_code != "999999" else "000000"
        success, result, message = phone_verification_service.verify_code(sample_user, phone_number, wrong_code)

        assert not success
        assert result is not None
        assert result.status == VerificationStatus.PENDING
        assert result.attempts == 1
        assert "Invalid code" in message
        assert "attempts remaining" in message

    def test_verify_code_max_attempts_exceeded(self, sample_user):
        """Test verification when max attempts are exceeded."""
        phone_number = "+1 (555) 123-4567"

        # Send verification code
        verification = phone_verification_service.send_verification_code(sample_user, phone_number)
        assert verification is not None

        # Make maximum attempts with wrong code
        wrong_code = "999999" if verification.verification_code != "999999" else "000000"

        for attempt in range(3):  # max_attempts = 3
            success, result, message = phone_verification_service.verify_code(sample_user, phone_number, wrong_code)
            assert not success
            assert result is not None

            if attempt < 2:  # First 2 attempts
                assert result.status == VerificationStatus.PENDING
            else:  # Final attempt
                assert result.status == VerificationStatus.FAILED
                assert "Maximum attempts exceeded" in message

    def test_verify_code_expired(self, sample_user):
        """Test verification with expired code."""
        phone_number = "+1 (555) 123-4567"

        # Send verification code
        verification = phone_verification_service.send_verification_code(sample_user, phone_number)
        assert verification is not None

        # Manually expire the verification
        verification_id = verification.id  # Store ID to avoid detached instance
        with get_session() as session:
            ver = session.get(PhoneVerification, verification_id)
            if ver:
                ver.expires_at = datetime.utcnow() - timedelta(minutes=1)
                session.add(ver)
                session.commit()

        # Try to verify expired code
        success, result, message = phone_verification_service.verify_code(
            sample_user, phone_number, verification.verification_code
        )

        assert not success
        assert result is not None
        assert result.status == VerificationStatus.EXPIRED
        assert message == "Verification code has expired"

    def test_verify_code_no_verification_found(self, sample_user):
        """Test verification when no pending verification exists."""
        phone_number = "+1 (555) 123-4567"

        success, result, message = phone_verification_service.verify_code(sample_user, phone_number, "123456")

        assert not success
        assert result is None
        assert message == "No verification request found"

    def test_verify_code_user_without_id(self):
        """Test verification with user without ID."""
        user = User(email="test@example.com", first_name="Test")  # No ID

        success, result, message = phone_verification_service.verify_code(user, "+15551234567", "123456")

        assert not success
        assert result is None
        assert message == "Invalid user"

    def test_get_verification_status(self, sample_user):
        """Test getting verification status."""
        phone_number = "+1 (555) 123-4567"

        # Initially no verification
        status = phone_verification_service.get_verification_status(sample_user, phone_number)
        assert status is None

        # Send verification code
        verification = phone_verification_service.send_verification_code(sample_user, phone_number)
        assert verification is not None

        # Get status
        status = phone_verification_service.get_verification_status(sample_user, phone_number)
        assert status is not None
        assert status.id == verification.id
        assert status.status == VerificationStatus.PENDING

    def test_get_verification_status_user_without_id(self):
        """Test getting status for user without ID."""
        user = User(email="test@example.com", first_name="Test")  # No ID

        status = phone_verification_service.get_verification_status(user, "+15551234567")
        assert status is None

    def test_can_send_new_code_timing(self, sample_user):
        """Test timing restrictions for sending new codes."""
        service = phone_verification_service
        phone_number = "+1 (555) 123-4567"

        # Send first code
        verification1 = service.send_verification_code(sample_user, phone_number)
        assert verification1 is not None

        # Try to send another immediately (should return same verification)
        verification2 = service.send_verification_code(sample_user, phone_number)
        assert verification2 is not None
        assert verification2.id == verification1.id  # Same verification returned

        # Manually advance time for the verification
        verification1_id = verification1.id  # Store ID to avoid detached instance
        with get_session() as session:
            ver = session.get(PhoneVerification, verification1_id)
            if ver:
                ver.created_at = datetime.utcnow() - timedelta(minutes=2)
                session.add(ver)
                session.commit()

        # Now should be able to send new code
        verification3 = service.send_verification_code(sample_user, phone_number)
        assert verification3 is not None
        assert verification3.id != verification1.id  # New verification

    def test_multiple_phone_numbers_per_user(self, sample_user):
        """Test that user can verify different phone numbers."""
        phone1 = "+1 (555) 123-4567"
        phone2 = "+1 (555) 987-6543"

        # Send codes to both numbers
        verification1 = phone_verification_service.send_verification_code(sample_user, phone1)
        verification2 = phone_verification_service.send_verification_code(sample_user, phone2)

        assert verification1 is not None
        assert verification2 is not None
        assert verification1.phone_number != verification2.phone_number

        # Verify first phone
        user_id = sample_user.id  # Store ID before verification to avoid detached instance issues
        success1, _, _ = phone_verification_service.verify_code(sample_user, phone1, verification1.verification_code)
        assert success1

        # User should have the first phone number verified
        with get_session() as session:
            user = session.get(User, user_id)
            assert user is not None
            assert user.phone_number == "+15551234567"  # phone1 cleaned
            assert user.is_phone_verified
