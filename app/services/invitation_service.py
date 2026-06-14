"""
Invitation Service
Handles user invitation logic, token generation, and email sending
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import exists, func, select
from sqlalchemy.orm import selectinload

from app.models.invitation import Invitation
from app.models.user import User, UserRole, Organization, Team
from app.services.email_service import get_email_service
from app.services.auth_service import auth_service


def exclude_users_with_pending_invitations(organization_id: int, user_email_column):
    """Users with an active, unaccepted invitation belong on Pending Invitations only."""
    return ~exists().where(
        Invitation.organization_id == organization_id,
        Invitation.accepted_at.is_(None),
        Invitation.expires_at > datetime.utcnow(),
        func.lower(Invitation.email) == func.lower(user_email_column),
    )


class InvitationService:
    """Service for managing user invitations"""

    def __init__(self):
        self.email_service = get_email_service()
        self.token_expiry_days = 7  # Invitations expire after 7 days

    def generate_token(self) -> str:
        """
        Generate a cryptographically secure invitation token.

        Returns:
            URL-safe token string (43 characters)
        """
        return secrets.token_urlsafe(32)

    def generate_temp_password(self) -> str:
        """
        Generate a secure temporary password.

        Returns:
            12-character password with mix of uppercase, lowercase, digits, and symbols
        """
        # Ensure password has at least one of each type
        password_chars = [
            secrets.choice(string.ascii_uppercase),  # At least one uppercase
            secrets.choice(string.ascii_lowercase),  # At least one lowercase
            secrets.choice(string.digits),           # At least one digit
            secrets.choice('!@#$%^&*'),              # At least one special char
        ]

        # Fill remaining 8 characters randomly
        all_chars = string.ascii_letters + string.digits + '!@#$%^&*'
        password_chars.extend(secrets.choice(all_chars) for _ in range(8))

        # Shuffle to avoid predictable pattern
        secrets.SystemRandom().shuffle(password_chars)

        return ''.join(password_chars)

    async def create_invitation(
        self,
        db: AsyncSession,
        email: str,
        organization_id: int,
        role: str,
        invited_by: int,
        team_id: Optional[int] = None,
        frontend_url: str = "http://localhost:3000",
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        job_title: Optional[str] = None,
        direct_dial: Optional[str] = None,
        cell_phone: Optional[str] = None,
        auto_commit: bool = True,
    ) -> Invitation:
        """
        Create a new invitation, create user account with temporary password, and send invitation email.

        Args:
            db: Database session
            email: Email address to invite
            organization_id: Organization ID
            role: User role (rep, manager, admin)
            invited_by: User ID of the inviter
            team_id: Optional team ID
            frontend_url: Frontend base URL for invitation link

        Returns:
            Created Invitation object

        Raises:
            ValueError: If invitation already exists or email is invalid
        """
        # Check if user already exists in this organization
        existing_user = await db.execute(
            select(User).where(
                User.email == email,
                User.organization_id == organization_id
            )
        )
        if existing_user.scalar_one_or_none():
            raise ValueError(f"User with email {email} already exists in this organization")

        # Check if there's already a pending invitation
        existing_invitation = await db.execute(
            select(Invitation).where(
                Invitation.email == email,
                Invitation.organization_id == organization_id,
                Invitation.accepted_at.is_(None),
                Invitation.expires_at > datetime.utcnow()
            )
        )
        existing_inv = existing_invitation.scalar_one_or_none()
        if existing_inv:
            raise ValueError(f"An active invitation already exists for {email}")

        # Generate temporary password and token
        temp_password = self.generate_temp_password()
        token = self.generate_token()
        expires_at = datetime.utcnow() + timedelta(days=self.token_expiry_days)

        # Create user account immediately with temporary password
        # DB userrole enum expects uppercase (REP, MANAGER, ADMIN)
        user_role = UserRole(role.upper())
        new_user = User(
            email=email,
            password_hash=auth_service.hash_password(temp_password),
            first_name=(first_name or "").strip() or None,
            last_name=(last_name or "").strip() or None,
            job_title=(job_title or "").strip() or None,
            direct_dial=(direct_dial or "").strip() or None,
            cell_phone=(cell_phone or "").strip() or None,
            organization_id=organization_id,
            team_id=team_id,
            role=user_role,
            is_active=True,
            is_verified=False,  # Verified when the invite is accepted
            must_change_password=True  # Force password change on first login
        )
        db.add(new_user)
        await db.flush()

        # Create invitation
        invitation = Invitation(
            email=email,
            organization_id=organization_id,
            team_id=team_id,
            role=role,
            token=token,
            invited_by=invited_by,
            expires_at=expires_at
        )

        db.add(invitation)
        await db.flush()
        await db.refresh(invitation)

        await self._send_invitation_email_for_record(
            db, invitation, temp_password, frontend_url
        )

        if auto_commit:
            await db.commit()
        return invitation

    async def _send_invitation_email_for_record(
        self,
        db: AsyncSession,
        invitation: Invitation,
        temp_password: str,
        frontend_url: str,
        *,
        is_resend: bool = False,
    ) -> None:
        org_result = await db.execute(
            select(Organization).where(Organization.id == invitation.organization_id)
        )
        organization = org_result.scalar_one()

        inviter_result = await db.execute(
            select(User).where(User.id == invitation.invited_by)
        )
        inviter = inviter_result.scalar_one_or_none()
        inviter_name = (
            f"{inviter.first_name} {inviter.last_name}".strip()
            if inviter and (inviter.first_name or inviter.last_name)
            else "Your administrator"
        )

        team_name = None
        if invitation.team_id:
            team_result = await db.execute(
                select(Team).where(Team.id == invitation.team_id)
            )
            team = team_result.scalar_one_or_none()
            if team:
                team_name = team.name

        invite_url = f"{frontend_url}/accept-invite?token={invitation.token}"
        email_sent = await self.email_service.send_invitation_email(
            to_email=invitation.email,
            organization_name=organization.name,
            inviter_name=inviter_name,
            invite_url=invite_url,
            role=invitation.role,
            team_name=team_name,
            temp_password=temp_password,
            is_resend=is_resend,
        )
        if not email_sent:
            raise ValueError(f"Failed to send invitation email to {invitation.email}")

    async def resend_invitation(
        self,
        db: AsyncSession,
        invitation_id: int,
        organization_id: int,
        frontend_url: str,
    ) -> Invitation:
        """Regenerate invite token + temp password and resend the invitation email."""
        result = await db.execute(
            select(Invitation).where(Invitation.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        if not invitation:
            raise ValueError("Invitation not found")
        if invitation.organization_id != organization_id:
            raise PermissionError("Invitation does not belong to this organization")
        if invitation.accepted_at is not None:
            raise ValueError("Invitation has already been accepted")

        user_result = await db.execute(
            select(User).where(
                User.email == invitation.email,
                User.organization_id == invitation.organization_id,
            )
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("Invited user account not found")

        temp_password = self.generate_temp_password()
        user.password_hash = auth_service.hash_password(temp_password)
        user.must_change_password = True
        user.is_active = True

        invitation.token = self.generate_token()
        invitation.expires_at = datetime.utcnow() + timedelta(days=self.token_expiry_days)

        await self._send_invitation_email_for_record(
            db, invitation, temp_password, frontend_url, is_resend=True
        )
        await db.commit()
        await db.refresh(invitation)
        return invitation

    async def resend_pending_invitations_for_organization(
        self,
        db: AsyncSession,
        organization_id: int,
        frontend_url: str,
    ) -> int:
        """Resend all pending invitations for an organization. Returns count sent."""
        invitations = await self.get_pending_invitations(db, organization_id)
        if not invitations:
            return 0

        sent = 0
        for invitation in invitations:
            await self.resend_invitation(
                db,
                invitation.id,
                organization_id,
                frontend_url,
            )
            sent += 1
        return sent

    async def verify_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[Dict]:
        """
        Verify an invitation token and return invitation details.

        Args:
            db: Database session
            token: Invitation token

        Returns:
            Dictionary with invitation details if valid, None otherwise
        """
        result = await db.execute(
            select(Invitation)
            .options(selectinload(Invitation.organization))
            .options(selectinload(Invitation.team))
            .where(Invitation.token == token)
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            return None

        if not invitation.is_valid:
            return None

        return {
            "valid": True,
            "email": invitation.email,
            "organization_id": invitation.organization_id,
            "organization_name": invitation.organization.name,
            "team_id": invitation.team_id,
            "team_name": invitation.team.name if invitation.team else None,
            "role": invitation.role,
            "expires_at": invitation.expires_at
        }

    async def accept_invitation(
        self,
        db: AsyncSession,
        token: str,
        user_id: int
    ) -> bool:
        """
        Accept an invitation and verify user account.

        Args:
            db: Database session
            token: Invitation token
            user_id: User ID accepting the invitation

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If token invalid, expired, or user mismatch
        """
        result = await db.execute(
            select(Invitation).where(Invitation.token == token)
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            raise ValueError("Invalid invitation token")

        if not invitation.is_valid:
            if invitation.is_expired:
                raise ValueError("Invitation has expired")
            if invitation.is_accepted:
                raise ValueError("Invitation has already been accepted")
            raise ValueError("Invalid invitation")

        # Get user
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Verify email matches
        if user.email.lower() != invitation.email.lower():
            raise ValueError("Email address does not match invitation")

        # Mark user as verified (they successfully logged in with temp password)
        user.is_verified = True
        # Mark user as active once the invitation is accepted.
        # This keeps the "already members" view consistent with invitation lifecycle.
        user.is_active = True

        # Mark invitation as accepted
        invitation.accepted_at = datetime.utcnow()

        await db.commit()
        return True

    async def get_pending_invitations(
        self,
        db: AsyncSession,
        organization_id: int
    ) -> list[Invitation]:
        """
        Get all pending invitations for an organization.

        Args:
            db: Database session
            organization_id: Organization ID

        Returns:
            List of pending invitations
        """
        result = await db.execute(
            select(Invitation)
            .options(selectinload(Invitation.inviter))
            .options(selectinload(Invitation.team))
            .where(
                Invitation.organization_id == organization_id,
                Invitation.accepted_at.is_(None),
                Invitation.expires_at > datetime.utcnow()
            )
            .order_by(Invitation.created_at.desc())
        )
        return result.scalars().all()

    async def cancel_invitation(
        self,
        db: AsyncSession,
        invitation_id: int,
        organization_id: int
    ) -> bool:
        """
        Cancel (hard-delete) a pending invitation.
        Also hard-deletes the corresponding invited user account (if still unverified).

        Args:
            db: Database session
            invitation_id: Invitation ID
            organization_id: Organization ID (for authorization)

        Returns:
            True if successful, False if not found

        Raises:
            PermissionError: If invitation doesn't belong to organization
        """
        result = await db.execute(
            select(Invitation).where(Invitation.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            return False

        if invitation.organization_id != organization_id:
            raise PermissionError("Invitation does not belong to this organization")

        if invitation.accepted_at is not None:
            raise ValueError("Accepted invitations cannot be deleted")

        invited_user_result = await db.execute(
            select(User).where(
                User.email == invitation.email,
                User.organization_id == invitation.organization_id
            )
        )
        invited_user = invited_user_result.scalar_one_or_none()

        await db.delete(invitation)

        # Hard-delete the placeholder invited user account as part of invite cancellation.
        # Only remove users who have not completed invite acceptance.
        if invited_user and not invited_user.is_verified:
            await db.delete(invited_user)

        await db.commit()
        return True


# Singleton instance
_invitation_service: Optional[InvitationService] = None


def get_invitation_service() -> InvitationService:
    """Get or create the invitation service singleton"""
    global _invitation_service
    if _invitation_service is None:
        _invitation_service = InvitationService()
    return _invitation_service
