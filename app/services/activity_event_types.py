"""
Activity event types — starter catalog for Super Admin observability (P2).
"""

# Auth
AUTH_LOGIN = "auth.login"
AUTH_LOGOUT = "auth.logout"
AUTH_OTP_REQUESTED = "auth.otp_requested"
AUTH_OTP_FAILED = "auth.otp_failed"

# Org lifecycle
ORG_APPROVED = "org.approved"
ORG_REJECTED = "org.rejected"
INVITE_CREATED = "invite.created"
INVITE_ACCEPTED = "invite.accepted"
INVITE_RESENT = "invite.resent"

# Deal session
SESSION_CREATED = "session.created"
SESSION_SUBMITTED = "session.submitted"
SESSION_COMPLETED = "session.completed"
SESSION_FAILED = "session.failed"

# Admin
ADMIN_AUTH_SESSION_REVOKED = "admin.auth_session.revoked"

# Shared checklists — a contributor from a partner organization is editing
# someone else's checklist, so every change is attributable.
SHARE_GRANTED = "share.granted"
SHARE_REVOKED = "share.revoked"
SHARE_EDIT_APPLIED = "share.edit_applied"
