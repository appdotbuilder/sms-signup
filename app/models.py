from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# Enums for status tracking
class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    MICROSOFT = "microsoft"
    APPLE = "apple"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    first_name: str = Field(max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    is_phone_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    oauth_accounts: List["OAuthAccount"] = Relationship(back_populates="user")
    phone_verifications: List["PhoneVerification"] = Relationship(back_populates="user")


class OAuthAccount(SQLModel, table=True):
    __tablename__ = "oauth_accounts"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    provider: OAuthProvider = Field()
    provider_user_id: str = Field(max_length=255)
    provider_email: str = Field(max_length=255)
    access_token: Optional[str] = Field(default=None, max_length=1000)
    refresh_token: Optional[str] = Field(default=None, max_length=1000)
    token_expires_at: Optional[datetime] = Field(default=None)
    profile_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Unique constraint on provider + provider_user_id
    __table_args__ = {"extend_existing": True}

    # Relationships
    user: User = Relationship(back_populates="oauth_accounts")


class PhoneVerification(SQLModel, table=True):
    __tablename__ = "phone_verifications"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    phone_number: str = Field(max_length=20)
    verification_code: str = Field(max_length=10)
    status: VerificationStatus = Field(default=VerificationStatus.PENDING)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)
    expires_at: datetime = Field()
    verified_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # SMS service metadata
    sms_service_id: Optional[str] = Field(default=None, max_length=100)
    sms_service_status: Optional[str] = Field(default=None, max_length=50)
    error_message: Optional[str] = Field(default=None, max_length=500)

    # Relationships
    user: User = Relationship(back_populates="phone_verifications")


class SMSServiceConfig(SQLModel, table=True):
    __tablename__ = "sms_service_configs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    service_name: str = Field(max_length=50)  # e.g., "twilio", "aws_sns"
    is_active: bool = Field(default=True)
    config_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    rate_limit_per_minute: int = Field(default=10)
    rate_limit_per_hour: int = Field(default=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    session_token: str = Field(unique=True, max_length=255)
    device_info: Optional[str] = Field(default=None, max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=45)  # IPv6 compatible
    expires_at: datetime = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = Field(default_factory=datetime.utcnow)


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    email: str = Field(max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    first_name: str = Field(max_length=100)


class UserResponse(SQLModel, table=False):
    id: int
    email: str
    first_name: str
    phone_number: Optional[str] = None
    is_phone_verified: bool
    is_active: bool
    created_at: str  # Will be serialized as ISO format


class OAuthCallbackData(SQLModel, table=False):
    provider: OAuthProvider
    code: str
    state: Optional[str] = None
    redirect_uri: str


class PhoneVerificationRequest(SQLModel, table=False):
    phone_number: str = Field(max_length=20, regex=r"^\+?1?[0-9]{10,15}$")


class PhoneVerificationCodeSubmit(SQLModel, table=False):
    phone_number: str = Field(max_length=20)
    verification_code: str = Field(max_length=10)


class PhoneVerificationResponse(SQLModel, table=False):
    id: int
    phone_number: str
    status: VerificationStatus
    attempts: int
    max_attempts: int
    expires_at: str  # ISO format
    created_at: str  # ISO format


class SMSServiceResponse(SQLModel, table=False):
    success: bool
    message: str
    service_id: Optional[str] = None
    error_code: Optional[str] = None


class UserSessionCreate(SQLModel, table=False):
    user_id: int
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    expires_in_hours: int = Field(default=24)


class UserSessionResponse(SQLModel, table=False):
    session_token: str
    expires_at: str  # ISO format
    user: UserResponse


# Mobile-optimized data transfer objects
class MobileSignupRequest(SQLModel, table=False):
    email: str = Field(max_length=255)
    first_name: str = Field(max_length=100)
    phone_number: str = Field(max_length=20, regex=r"^\+?1?[0-9]{10,15}$")
    oauth_provider: OAuthProvider
    oauth_code: str


class MobileVerificationStatus(SQLModel, table=False):
    is_verified: bool
    phone_number: str
    attempts_remaining: int
    expires_in_minutes: int
    next_step: str  # "enter_code", "resend_code", "verification_complete"


class MobileUserProfile(SQLModel, table=False):
    first_name: str
    email: str
    phone_number: Optional[str] = None
    verification_status: VerificationStatus
    signup_completed: bool
    created_date: str  # ISO format
