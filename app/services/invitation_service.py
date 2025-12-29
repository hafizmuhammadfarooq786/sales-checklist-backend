"""
Invitation Service
Handles user invitation logic, token generation, and email sending
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.invitation import Invitation
from app.models.user import User, Organization, Team
from app.services.email_service import get_email_service


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

    async def create_invitation(
        self,
        db: AsyncSession,
        email: str,
        organization_id: int,
        role: str,
        invited_by: int,
        team_id: Optional[int] = None,
        frontend_url: str = "http://localhost:3000"
    ) -> Invitation:
        """
        Create a new invitation and send invitation email.

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

        # Generate token and expiry
        token = self.generate_token()
        expires_at = datetime.utcnow() + timedelta(days=self.token_expiry_days)

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

        # Get organization and inviter details for email
        org_result = await db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = org_result.scalar_one()

        inviter_result = await db.execute(
            select(User).where(User.id == invited_by)
        )
        inviter = inviter_result.scalar_one()

        # Get team name if team_id provided
        team_name = None
        if team_id:
            team_result = await db.execute(
                select(Team).where(Team.id == team_id)
            )
            team = team_result.scalar_one_or_none()
            if team:
                team_name = team.name

        # Send invitation email
        invite_url = f"{frontend_url}/accept-invite?token={token}"
        inviter_name = f"{inviter.first_name} {inviter.last_name}"

        await self.email_service.send_invitation_email(
            to_email=email,
            organization_name=organization.name,
            inviter_name=inviter_name,
            invite_url=invite_url,
            role=role,
            team_name=team_name
        )

        await db.commit()
        return invitation

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
        Accept an invitation and add user to organization/team.

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

        # Update user with organization and team
        user.organization_id = invitation.organization_id
        user.team_id = invitation.team_id
        user.role = invitation.role

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
        Cancel (delete) a pending invitation.

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

        await db.delete(invitation)
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
