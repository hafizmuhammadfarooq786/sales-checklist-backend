"""
Login OTP codes — passwordless email verification for sign-in.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class LoginOtp(Base):
    """
    One active login OTP per user at a time.

    A code remains valid until it expires (24 hours) or is revoked by a resend.
    The same code can be verified on multiple devices during that window.
    """

    __tablename__ = "login_otp_codes"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)

    user = relationship("User", backref="login_otp_codes")
