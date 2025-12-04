"""
User and Organization models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """User roles for RBAC"""
    SYSTEM_ADMIN = "system_admin"  # Product admin - view only, no sessions
    ADMIN = "admin"  # Organization admin
    MANAGER = "manager"  # Team manager/coach
    REP = "rep"  # Sales representative


class Organization(Base, TimestampMixin):
    """Organization/Company table"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization")


class Team(Base, TimestampMixin):
    """Teams within an organization"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    users = relationship("User", back_populates="team")


class User(Base, TimestampMixin):
    """
    User table - custom JWT authentication system
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Role & Organization
    role = Column(SQLEnum(UserRole), default=UserRole.REP, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Status & Security
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)

    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    team = relationship("Team", back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
