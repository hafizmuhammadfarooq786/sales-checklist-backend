"""
User and Organization models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    MANAGER = "manager"
    REP = "rep"


class Organization(Base, TimestampMixin):
    """Organization/Company table"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=True)  # Email domain restriction
    is_active = Column(Boolean, default=True, nullable=False)

    # Settings
    scoring_mode = Column(String(50), default="equal_weight")  # equal_weight, weighted, custom
    max_users = Column(Integer, default=10000)

    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization")


class Team(Base, TimestampMixin):
    """Teams within an organization"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    users = relationship("User", back_populates="team")


class User(Base, TimestampMixin):
    """
    User table - synced from Clerk via webhook
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Role & Organization
    role = Column(SQLEnum(UserRole), default=UserRole.REP, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    team = relationship("Team", back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
