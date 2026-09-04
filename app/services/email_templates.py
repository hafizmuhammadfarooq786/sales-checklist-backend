"""
Transactional email templates.

Visual system matches Fortune 50 / enterprise mail (Apple, IBM, JPMorgan, Stripe):
white canvas, no fills, no tinted banners. Hierarchy comes from type and color only.

  Navy     #0b2e59  wordmark, headings, primary action
  Ink      #111111  body copy
  Muted    #5b6473  labels, supporting text, footer
  Intel    #0550c3  secondary links (fallback URLs)
  Critical #b91c1c  expiry / security — text only
  Line     #d7dce3  hairlines
"""

# Email-safe stack. Google Fonts are stripped by Outlook and many webmail clients.
FONT = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
)

EMAIL_BASE_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body, table, td, p, a, li, h1, span, div {{
  font-family: {FONT} !important;
}}
body {{
  background: #ffffff !important;
  color: #111111 !important;
  -webkit-font-smoothing: antialiased !important;
  margin: 0 !important;
  padding: 0 !important;
}}
a {{ color: #0550c3; }}
"""


def _preheader(text: str) -> str:
    return (
        f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;'
        f'font-size:1px;line-height:1px;color:#ffffff;opacity:0;">{text}&nbsp;&zwnj;'
        f'&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>'
    )


def _brand_bar() -> str:
    return f"""
<p style="margin:0;font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#0b2e59;font-family:{FONT};">{{{{ project_name }}}}</p>
<div style="height:1px;background:#d7dce3;line-height:1px;font-size:1px;margin:20px 0 32px;">&nbsp;</div>
"""


def _h1(text: str) -> str:
    return (
        f'<h1 style="margin:0 0 16px;font-size:22px;line-height:1.3;font-weight:600;'
        f'letter-spacing:-0.02em;color:#0b2e59;font-family:{FONT};">{text}</h1>'
    )


def _p(text: str, *, margin: str = "0 0 16px") -> str:
    return (
        f'<p style="margin:{margin};font-size:15px;line-height:1.65;color:#111111;'
        f'font-family:{FONT};">{text}</p>'
    )


def _muted(text: str, *, margin: str = "0 0 16px") -> str:
    return (
        f'<p style="margin:{margin};font-size:14px;line-height:1.6;color:#5b6473;'
        f'font-family:{FONT};">{text}</p>'
    )


def _critical(text: str) -> str:
    return (
        f'<p style="margin:0 0 8px;font-size:14px;line-height:1.6;color:#b91c1c;'
        f'font-family:{FONT};">{text}</p>'
    )


def _cta(href: str, label: str) -> str:
    return f"""
<p style="margin:28px 0 8px;font-family:{FONT};">
  <a href="{href}" style="display:inline-block;padding:4px 0;font-size:16px;line-height:1.4;font-weight:600;color:#0b2e59;text-decoration:underline;text-underline-offset:3px;">{label}</a>
</p>
"""


def _fallback(href: str) -> str:
    return f"""
<p style="margin:16px 0 0;font-size:13px;line-height:1.55;color:#5b6473;font-family:{FONT};">
  If the link does not open, copy this URL into your browser:<br />
  <a href="{href}" style="color:#0550c3;word-break:break-all;text-decoration:underline;">{href}</a>
</p>
"""


def _kv(label: str, value: str) -> str:
    return f"""
<p style="margin:0 0 16px;font-family:{FONT};">
  <span style="display:block;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#5b6473;">{label}</span>
  <span style="display:block;margin-top:4px;font-size:15px;font-weight:600;color:#111111;">{value}</span>
</p>
"""


def _steps(items: list[str]) -> str:
    lis = "".join(
        f'<li style="margin:0 0 8px;padding:0;">{item}</li>' for item in items
    )
    return (
        f'<ol style="margin:8px 0 0;padding-left:20px;font-size:15px;line-height:1.55;'
        f'color:#111111;font-family:{FONT};">{lis}</ol>'
    )


def _signoff() -> str:
    return _p("Thank you,<br />{{ project_name }}", margin="32px 0 0")


def _footer(reason: str, sent_to: str = "{{ user_email }}") -> str:
    return f"""
<div style="height:1px;background:#d7dce3;line-height:1px;font-size:1px;margin:40px 0 16px;">&nbsp;</div>
<p style="margin:0;font-size:12px;line-height:1.55;color:#5b6473;font-family:{FONT};">
  &copy; {{{{ current_year }}}} {{{{ company_name }}}}<br />
  Sent to {sent_to}
</p>
<p style="margin:8px 0 0;font-size:12px;line-height:1.55;color:#5b6473;font-family:{FONT};">{reason}</p>
"""


def _shell(title: str, inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<title>{title}</title>
<style>{EMAIL_BASE_CSS}</style>
</head>
<body style="margin:0;padding:0;background:#ffffff;color:#111111;font-family:{FONT};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;">
  <tr>
    <td align="center" style="padding:32px 20px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
        <tr>
          <td style="font-family:{FONT};color:#111111;">
{inner}
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


EMAIL_TEMPLATES = {
    "email_verification": _shell(
        "Verify your email — {{ project_name }}",
        f"""
{_preheader("Confirm your email to activate your account. This link expires in 24 hours.")}
{_brand_bar()}
{_h1("Confirm your email")}
{_p("Hello <strong>{{ user_name }}</strong>,")}
{_p("Please verify <strong>{{ user_email }}</strong> to activate your {{ project_name }} account and start using the platform.")}
{_cta("{{ verification_url }}", "Verify email address &rarr;")}
{_critical("This link expires in 24 hours.")}
{_muted("If you did not create an account, you can ignore this email. No account will be activated.")}
{_fallback("{{ verification_url }}")}
{_signoff()}
{_footer("You received this because an account was created with this address.")}
""",
    ),
    "password_reset": _shell(
        "Reset your password — {{ project_name }}",
        f"""
{_preheader("Reset the password for your account. This link expires in 1 hour.")}
{_brand_bar()}
{_h1("Reset your password")}
{_p("Hello <strong>{{ user_name }}</strong>,")}
{_p("We received a request to reset the password for <strong>{{ user_email }}</strong> on {{ project_name }}.")}
{_cta("{{ reset_url }}", "Choose a new password &rarr;")}
{_critical("This link expires in 1 hour. After that you will need to request a new reset.")}
{_muted("If you did not request this, ignore this email. Your password will not change.")}
{_fallback("{{ reset_url }}")}
{_signoff()}
{_footer("You received this because a password reset was requested for this address.")}
""",
    ),
    "welcome": _shell(
        "Welcome to {{ project_name }}",
        f"""
{_preheader("Your account is active. Here is how to get started.")}
{_brand_bar()}
{_h1("Your account is ready")}
{_p("Hello <strong>{{ user_name }}</strong>,")}
{_p("Your email is verified and your {{ project_name }} account is active. Use the dashboard to run checklists, review scores, and track deal evidence.")}
{_cta("{{ dashboard_url }}", "Open your dashboard &rarr;")}
{_p("<strong>Suggested first steps</strong>", margin="28px 0 0")}
{_steps([
    "Start a sales checklist for an active deal",
    "Review scoring and coaching notes after the session",
    "Invite managers and reps from organization settings",
])}
{_fallback("{{ dashboard_url }}")}
{_signoff()}
{_footer("You received this because you created an account.")}
""",
    ),
    "registration_approved": _shell(
        "Registration approved — {{ project_name }}",
        f"""
{_preheader("{{ organization_name }} is approved. Sign in with the temporary password below.")}
{_brand_bar()}
{_h1("{{ organization_name }} is approved")}
{_p("Hello <strong>{{ user_name }}</strong>,")}
{_p("<strong>{{ approver_name }}</strong> approved your organization on {{ project_name }}. Sign in with the credentials below, then set a permanent password.")}
{_kv("Organization", "{{ organization_name }}")}
{_kv("Role", "Admin")}
{_kv("Email", "{{ user_email }}")}
{_kv("Temporary password", '<span style="font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:0.02em;">{{ temp_password }}</span>')}
{_critical("Do not share this password. You will be asked to set a new one after you sign in.")}
{_cta("{{ sign_in_url }}", "Sign in &rarr;")}
{_p("<strong>What to do next</strong>", margin="28px 0 0")}
{_steps([
    "Sign in with your email and temporary password",
    "Set a new password when prompted",
    "Invite managers and salespeople from Users",
])}
{_fallback("{{ sign_in_url }}")}
{_signoff()}
{_footer("You received this because your organization registration was approved.")}
""",
    ),
    "invitation": _shell(
        "Invitation — {{ project_name }}",
        f"""
{_preheader("{{ inviter_name }} invited you to {{ organization_name }}. This invitation expires in 7 days.")}
{_brand_bar()}
{_h1("Join {{ organization_name }}")}
{_p("<strong>{{ inviter_name }}</strong> invited you to {{ project_name }}. Accept below to access your workspace.")}
{_kv("Organization", "{{ organization_name }}")}
{_kv("Team", "{{ team_name if team_name else '&mdash;' }}")}
{_kv("Role", "{{ role|capitalize }}")}
{{% if temp_password %}}
{_kv("Email", "{{ user_email }}")}
{_kv("Temporary password", '<span style="font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:0.02em;">{{ temp_password }}</span>')}
{_muted("This is a temporary password. You will set a new one after you sign in.")}
{{% endif %}}
{_cta("{{ invite_url }}", "Accept invitation &rarr;")}
{_critical("This invitation expires in 7 days.")}
{_p("<strong>What to do next</strong>", margin="28px 0 0")}
{_steps([
    "Accept the invitation using the link above",
    "Sign in with your email and temporary password",
    "Complete setup and open your first checklist",
])}
{_fallback("{{ invite_url }}")}
{_signoff()}
{_footer("You received this because you were invited to an organization.")}
""",
    ),
    "notification": _shell(
        "{{ subject }} — {{ project_name }}",
        f"""
{_preheader("{{ subject }}")}
{_brand_bar()}
{_h1("{{ subject }}")}
{_p("{{ greeting }}")}
{_p("{{ message|safe }}")}
{_signoff()}
{_footer("This is a notification from {{ project_name }}.")}
""",
    ),
    "manager_note": _shell(
        "Coaching note — {{ project_name }}",
        f"""
{_preheader("{{ manager_name }} left coaching feedback on {{ customer_name }} — {{ opportunity_name }}.")}
{_brand_bar()}
{_h1("New coaching note")}
{_p("Hello <strong>{{ rep_name }}</strong>,")}
{_p("<strong>{{ manager_name }}</strong> left {% if note_type == 'audio' %}an audio coaching note{% else %}a coaching note{% endif %} on your session.")}
{_kv("Customer", "{{ customer_name }}")}
{_kv("Opportunity", "{{ opportunity_name }}")}
{{% if note_type == 'text' and note_preview %}}
{_p("<strong>Note</strong>", margin="8px 0 8px")}
<p style="margin:0 0 16px;padding:0 0 0 12px;border-left:2px solid #0b2e59;font-size:15px;line-height:1.65;color:#111111;font-family:{FONT};">{{{{ note_preview }}}}</p>
{{% elif note_type == 'audio' %}}
{_muted("Open the session to listen to the audio note.")}
{{% endif %}}
{_cta("{{ session_url }}", "View session &rarr;")}
{_muted("Coaching notes appear on the session results page.")}
{_fallback("{{ session_url }}")}
{_signoff()}
{_footer("You received this because a manager left coaching feedback on your deal.", sent_to="{{ rep_email }}")}
""",
    ),
}


def get_email_templates() -> dict[str, str]:
    return EMAIL_TEMPLATES


COMMON_TEMPLATE_VARIABLES = ("project_name", "company_name", "current_year")

EMAIL_TEMPLATE_DEFAULT_SUBJECTS: dict[str, str] = {
    "email_verification": "Verify your email for {{ project_name }}",
    "password_reset": "Reset your {{ project_name }} password",
    "welcome": "Your {{ project_name }} account is ready",
    "registration_approved": (
        "{{ organization_name }} is approved — sign in to {{ project_name }}"
    ),
    "invitation": (
        "{% if is_resend %}Reminder: {{ inviter_name }} invited you to "
        "{{ organization_name }}{% else %}{{ inviter_name }} invited you to "
        "{{ organization_name }}{% endif %}"
    ),
    "manager_note": (
        "{% if note_type == 'audio' %}Audio coaching note: {{ customer_name }} "
        "— {{ opportunity_name }}{% else %}Coaching note: {{ customer_name }} "
        "— {{ opportunity_name }}{% endif %}"
    ),
    "notification": "{{ subject }}",
}

EMAIL_TEMPLATE_META: dict[str, dict] = {
    "email_verification": {
        "name": "Email verification",
        "description": "Sent when a user needs to verify their email address.",
        "variables": ("user_name", "user_email", "verification_url"),
    },
    "password_reset": {
        "name": "Password reset",
        "description": "Sent when a user requests a password reset.",
        "variables": ("user_name", "user_email", "reset_url"),
    },
    "welcome": {
        "name": "Welcome",
        "description": "Sent after a user successfully activates their account.",
        "variables": ("user_name", "user_email", "dashboard_url"),
    },
    "registration_approved": {
        "name": "Registration approved",
        "description": "Sent to the applicant when Super Admin approves an organization.",
        "variables": (
            "user_name",
            "user_email",
            "organization_name",
            "approver_name",
            "temp_password",
            "sign_in_url",
        ),
    },
    "invitation": {
        "name": "Organization invitation",
        "description": "Sent when an admin invites a user to join an organization.",
        "variables": (
            "user_email",
            "organization_name",
            "inviter_name",
            "invite_url",
            "role",
            "team_name",
            "temp_password",
            "is_resend",
        ),
    },
    "manager_note": {
        "name": "Manager coaching note",
        "description": "Sent to a rep when a manager leaves coaching feedback.",
        "variables": (
            "rep_email",
            "rep_name",
            "manager_name",
            "customer_name",
            "opportunity_name",
            "session_url",
            "note_type",
            "note_preview",
        ),
    },
    "notification": {
        "name": "Generic notification",
        "description": "Used for registration received, rejection, and admin alerts.",
        "variables": ("subject", "greeting", "message", "user_name"),
    },
}

TEMPLATE_SLUG_ORDER = (
    "invitation",
    "registration_approved",
    "email_verification",
    "password_reset",
    "welcome",
    "manager_note",
    "notification",
)


def list_template_slugs() -> list[str]:
    known = [slug for slug in TEMPLATE_SLUG_ORDER if slug in EMAIL_TEMPLATES]
    extras = sorted(slug for slug in EMAIL_TEMPLATES if slug not in known)
    return known + extras


def get_template_variables(slug: str) -> list[str]:
    extra = EMAIL_TEMPLATE_META.get(slug, {}).get("variables", ())
    return list(COMMON_TEMPLATE_VARIABLES) + list(extra)


def get_default_subject(slug: str) -> str:
    if slug not in EMAIL_TEMPLATES:
        raise KeyError(f"Unknown email template: {slug}")
    return EMAIL_TEMPLATE_DEFAULT_SUBJECTS.get(slug, "{{ project_name }}")


def get_default_html(slug: str) -> str:
    if slug not in EMAIL_TEMPLATES:
        raise KeyError(f"Unknown email template: {slug}")
    return EMAIL_TEMPLATES[slug]
