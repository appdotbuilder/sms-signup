"""Phone verification service for SMS validation."""

import random
import string
from typing import Optional, Tuple
from datetime import datetime, timedelta
from app.models import User, PhoneVerification, VerificationStatus
from app.database import get_session
from sqlmodel import select, and_, desc


class PhoneVerificationService:
    """Service for handling phone number verification via SMS."""

    def __init__(self):
        self.code_length = 6
        self.expiry_minutes = 15
        self.max_attempts = 3

    def generate_verification_code(self) -> str:
        """Generate a random verification code."""
        return "".join(random.choices(string.digits, k=self.code_length))

    def send_verification_code(self, user: User, phone_number: str) -> Optional[PhoneVerification]:
        """Send verification code to user's phone number."""
        if user.id is None:
            return None

        # Clean phone number (remove spaces, dashes, etc.)
        cleaned_phone = self._clean_phone_number(phone_number)

        with get_session() as session:
            # Check if there's a recent pending verification
            recent_verification = self._get_recent_verification(session, user.id, cleaned_phone)
            if recent_verification and not self._can_send_new_code(recent_verification):
                # Too soon to send another code
                # Return a fresh instance
                return session.get(PhoneVerification, recent_verification.id)

            # Generate new verification code
            verification_code = self.generate_verification_code()
            expires_at = datetime.utcnow() + timedelta(minutes=self.expiry_minutes)

            # Create verification record
            verification = PhoneVerification(
                user_id=user.id,
                phone_number=cleaned_phone,
                verification_code=verification_code,
                status=VerificationStatus.PENDING,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # In a real implementation, this would send the SMS
            # For demo purposes, we'll simulate success
            verification.sms_service_id = f"demo_sms_{random.randint(10000, 99999)}"
            verification.sms_service_status = "sent"

            session.add(verification)
            session.commit()
            session.refresh(verification)

            # Return fresh instance to avoid DetachedInstanceError
            return session.get(PhoneVerification, verification.id)

    def verify_code(self, user: User, phone_number: str, code: str) -> Tuple[bool, Optional[PhoneVerification], str]:
        """
        Verify the submitted code.

        Returns:
            (success, verification_record, message)
        """
        if user.id is None:
            return False, None, "Invalid user"

        cleaned_phone = self._clean_phone_number(phone_number)

        with get_session() as session:
            # Find the most recent pending verification for this user and phone
            statement = (
                select(PhoneVerification)
                .where(
                    and_(
                        PhoneVerification.user_id == user.id,
                        PhoneVerification.phone_number == cleaned_phone,
                        PhoneVerification.status == VerificationStatus.PENDING,
                    )
                )
                .order_by(desc(PhoneVerification.created_at))
            )

            verification = session.exec(statement).first()

            if not verification:
                return False, None, "No verification request found"

            # Check if expired
            if datetime.utcnow() > verification.expires_at:
                verification.status = VerificationStatus.EXPIRED
                verification.updated_at = datetime.utcnow()
                session.add(verification)
                session.commit()
                session.refresh(verification)
                fresh_verification = session.get(PhoneVerification, verification.id)
                return False, fresh_verification, "Verification code has expired"

            # Check attempts
            if verification.attempts >= verification.max_attempts:
                verification.status = VerificationStatus.FAILED
                verification.updated_at = datetime.utcnow()
                session.add(verification)
                session.commit()
                session.refresh(verification)
                fresh_verification = session.get(PhoneVerification, verification.id)
                return False, fresh_verification, "Maximum attempts exceeded"

            # Increment attempts
            verification.attempts += 1
            verification.updated_at = datetime.utcnow()

            # Check if code matches
            if verification.verification_code == code:
                # Success!
                verification.status = VerificationStatus.VERIFIED
                verification.verified_at = datetime.utcnow()

                # Update user's phone verification status
                user.phone_number = cleaned_phone
                user.is_phone_verified = True
                user.updated_at = datetime.utcnow()

                session.add(verification)
                session.add(user)
                session.commit()
                session.refresh(verification)

                # Return fresh instance to avoid DetachedInstanceError
                fresh_verification = session.get(PhoneVerification, verification.id)
                return True, fresh_verification, "Phone number verified successfully"
            else:
                # Wrong code
                if verification.attempts >= verification.max_attempts:
                    verification.status = VerificationStatus.FAILED
                    message = "Maximum attempts exceeded"
                else:
                    remaining = verification.max_attempts - verification.attempts
                    message = f"Invalid code. {remaining} attempts remaining"

                session.add(verification)
                session.commit()
                session.refresh(verification)

                # Return fresh instance to avoid DetachedInstanceError
                fresh_verification = session.get(PhoneVerification, verification.id)
                return False, fresh_verification, message

    def get_verification_status(self, user: User, phone_number: str) -> Optional[PhoneVerification]:
        """Get the current verification status for a phone number."""
        if user.id is None:
            return None

        cleaned_phone = self._clean_phone_number(phone_number)

        with get_session() as session:
            statement = (
                select(PhoneVerification)
                .where(and_(PhoneVerification.user_id == user.id, PhoneVerification.phone_number == cleaned_phone))
                .order_by(desc(PhoneVerification.created_at))
            )

            return session.exec(statement).first()

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number."""
        # Remove all non-digit characters except +
        cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

        # If it starts with 1 and is 11 digits, add + prefix
        if len(cleaned) == 11 and cleaned.startswith("1"):
            cleaned = "+" + cleaned
        elif len(cleaned) == 10:
            # Assume US number, add +1 prefix
            cleaned = "+1" + cleaned
        elif not cleaned.startswith("+"):
            # Add + if not present
            cleaned = "+" + cleaned

        return cleaned

    def _get_recent_verification(self, session, user_id: int, phone_number: str) -> Optional[PhoneVerification]:
        """Get recent verification within the last minute."""
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)

        statement = (
            select(PhoneVerification)
            .where(
                and_(
                    PhoneVerification.user_id == user_id,
                    PhoneVerification.phone_number == phone_number,
                    PhoneVerification.created_at > one_minute_ago,
                    PhoneVerification.status == VerificationStatus.PENDING,
                )
            )
            .order_by(desc(PhoneVerification.created_at))
        )

        return session.exec(statement).first()

    def _can_send_new_code(self, verification: PhoneVerification) -> bool:
        """Check if enough time has passed to send a new code."""
        # Allow new code if more than 1 minute has passed
        return datetime.utcnow() > (verification.created_at + timedelta(minutes=1))


# Global service instance
phone_verification_service = PhoneVerificationService()
