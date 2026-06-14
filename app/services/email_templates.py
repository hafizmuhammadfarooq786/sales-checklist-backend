"""
Transactional email templates — aligned with frontend brand tokens (brand-tokens.css).

Colors: navy #0b2e59, intel #0550c3, strong #198754, warn #f59e0b, critical #b91c1c,
        appbg #f5f6f8, surface #ffffff, line #d7dce3, ink #0b1220, ink-muted #5b6473
"""

EMAIL_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body, table, td, p, a, li, h1, span, div {
  font-family: 'Inter', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
}

body {
  background-color: #f5f6f8 !important;
  color: #0b1220 !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
  padding: 32px 16px !important;
  line-height: 1.6 !important;
}

.email-wrapper { max-width: 600px; margin: 0 auto !important; }

.pre-header {
  padding: 0 4px 20px;
  border-bottom: 1px solid #d7dce3;
  margin-bottom: 0;
}

.pre-header-table { width: 100%; border-collapse: collapse; }
.pre-header-table td { vertical-align: middle; }

.wordmark {
  font-size: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #0b2e59 !important;
}

.badge {
  display: inline-block;
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  border-radius: 999px !important;
  padding: 4px 10px !important;
  white-space: nowrap;
}
.badge-intel { color: #0550c3 !important; background: #e5f1fd !important; border: 1px solid #b8d4f8 !important; }
.badge-strong { color: #198754 !important; background: #eaf7f0 !important; border: 1px solid #b8e6cc !important; }
.badge-warn { color: #b45309 !important; background: #fff4e5 !important; border: 1px solid #fcd9a8 !important; }
.badge-critical { color: #b91c1c !important; background: #fdecec !important; border: 1px solid #f5c2c2 !important; }

.card {
  background: #ffffff !important;
  border: 1px solid #d7dce3 !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  box-shadow: 0 1px 2px rgba(11, 46, 89, 0.06) !important;
}

.header {
  background: linear-gradient(135deg, #001a41 0%, #0b2e59 100%) !important;
  padding: 36px 32px 32px !important;
  position: relative;
}

.header-accent {
  display: inline-block;
  width: 40px;
  height: 3px;
  background: #0550c3 !important;
  border-radius: 2px;
  margin-bottom: 16px;
}

.header-eyebrow {
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: #7eb3ff !important;
  margin-bottom: 10px !important;
}

.header h1 {
  font-size: 26px !important;
  font-weight: 700 !important;
  color: #ffffff !important;
  line-height: 1.25 !important;
  letter-spacing: -0.02em !important;
  margin-bottom: 8px !important;
}

.header h1 .accent { color: #ffd526 !important; }

.header-sub {
  font-size: 15px !important;
  color: #e5f1fd !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
}

.content { padding: 32px !important; }

.intro-text {
  font-size: 15px !important;
  color: #5b6473 !important;
  line-height: 1.65 !important;
  margin-bottom: 24px !important;
}
.intro-text strong { color: #0b1220 !important; font-weight: 600 !important; }

.section-label {
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #5b6473 !important;
  margin-bottom: 10px !important;
}

.details-grid {
  display: table;
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid #d7dce3 !important;
  border-radius: 8px !important;
  overflow: hidden;
  margin-bottom: 24px !important;
}
.detail-cell {
  display: table-cell;
  width: 50%;
  padding: 16px 18px !important;
  background: #f5f6f8 !important;
  border-right: 1px solid #d7dce3 !important;
  vertical-align: top;
}
.detail-cell:last-child { border-right: none !important; }
.detail-label {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #5b6473 !important;
  margin-bottom: 6px !important;
}
.detail-value {
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #0b1220 !important;
}

.role-pill {
  display: inline-block;
  font-size: 12px !important;
  font-weight: 600 !important;
  color: #198754 !important;
  background: #eaf7f0 !important;
  border: 1px solid #b8e6cc !important;
  border-radius: 999px !important;
  padding: 2px 10px !important;
}

.creds-box {
  background: #e5f1fd !important;
  border-radius: 8px !important;
  padding: 18px 20px !important;
  margin-bottom: 20px !important;
  border: 1px solid #b8d4f8 !important;
}
.cred-row { margin-bottom: 14px !important; }
.cred-row:last-child { margin-bottom: 0 !important; }
.cred-key {
  display: block;
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #5b6473 !important;
  margin-bottom: 6px !important;
}
.cred-value {
  font-size: 15px !important;
  font-weight: 600 !important;
  color: #0b1220 !important;
  word-break: break-all !important;
  text-decoration: none !important;
}
.cred-value a {
  color: #0b1220 !important;
  text-decoration: none !important;
  pointer-events: none !important;
}
.cred-password {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  letter-spacing: 0.04em !important;
  color: #0b1220 !important;
}

.banner {
  border-radius: 8px !important;
  padding: 14px 16px !important;
  margin-bottom: 24px !important;
  font-size: 14px !important;
  line-height: 1.55 !important;
}
.banner-strong { background: #eaf7f0 !important; border: 1px solid #b8e6cc !important; color: #166534 !important; }
.banner-warn { background: #fff4e5 !important; border: 1px solid #fcd9a8 !important; color: #92400e !important; }
.banner-critical { background: #fdecec !important; border: 1px solid #f5c2c2 !important; color: #991b1b !important; }
.banner strong { font-weight: 600 !important; }

.notice {
  background: #fff4e5 !important;
  border: 1px solid #fcd9a8 !important;
  border-radius: 8px !important;
  padding: 14px 16px !important;
  margin-bottom: 24px !important;
}
.notice-text { font-size: 13px !important; color: #92400e !important; line-height: 1.55 !important; }

.cta-section { text-align: center; margin: 28px 0 !important; }
.cta-button {
  display: inline-block;
  background: #0550c3 !important;
  color: #ffffff !important;
  text-decoration: none !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  padding: 13px 28px !important;
  border-radius: 8px !important;
  border: 1px solid #0446a8 !important;
}
.cta-sub {
  margin-top: 10px !important;
  font-size: 12px !important;
  color: #5b6473 !important;
}

.divider { height: 1px; background: #d7dce3; margin: 24px 0 !important; }

.fallback-url {
  background: #f5f6f8 !important;
  border: 1px solid #d7dce3 !important;
  border-radius: 8px !important;
  padding: 14px 16px !important;
  margin-bottom: 24px !important;
}
.fallback-label {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #5b6473 !important;
  margin-bottom: 6px !important;
}
.fallback-link {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  font-size: 11px !important;
  color: #0550c3 !important;
  word-break: break-all !important;
  line-height: 1.6 !important;
}

.steps-table {
  width: 100% !important;
  border-collapse: collapse !important;
  margin: 0 !important;
}
.step-row td {
  padding: 12px 0 !important;
  border-bottom: 1px solid #d7dce3 !important;
  vertical-align: middle !important;
}
.step-row:last-child td { border-bottom: none !important; }
.step-num-cell {
  width: 36px !important;
  padding-right: 14px !important;
  vertical-align: middle !important;
}
.step-num-badge {
  width: 28px !important;
  height: 28px !important;
  min-width: 28px !important;
  min-height: 28px !important;
  background: #e5f1fd !important;
  color: #0550c3 !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  border-radius: 6px !important;
  text-align: center !important;
  vertical-align: middle !important;
  padding: 0 !important;
  mso-line-height-rule: exactly;
}
.step-text {
  font-size: 14px !important;
  color: #5b6473 !important;
  line-height: 1.5 !important;
  vertical-align: middle !important;
}

.features-grid {
  border: 1px solid #d7dce3 !important;
  border-radius: 8px !important;
  overflow: hidden;
  margin-bottom: 24px !important;
}
.feature-cell {
  padding: 16px 18px !important;
  background: #ffffff !important;
  border-bottom: 1px solid #d7dce3 !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #0b1220 !important;
}
.feature-cell:nth-child(odd) { background: #f5f6f8 !important; }

.body-text {
  font-size: 14px !important;
  color: #5b6473 !important;
  line-height: 1.65 !important;
}

.footer {
  padding: 20px 4px 0 !important;
  border-top: 1px solid #d7dce3;
  margin-top: 20px;
}
.footer-copy {
  font-size: 12px !important;
  color: #5b6473 !important;
  line-height: 1.55 !important;
}
.footer-aside {
  font-size: 12px !important;
  color: #5b6473 !important;
  line-height: 1.55 !important;
  margin-top: 8px !important;
}

@media (max-width: 520px) {
  .header, .content { padding: 24px 20px !important; }
  .header h1 { font-size: 22px !important; }
  .detail-cell { display: block !important; width: 100% !important; border-right: none !important; border-bottom: 1px solid #d7dce3 !important; }
  .detail-cell:last-child { border-bottom: none !important; }
}
"""


def _shell(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
<style>{EMAIL_BASE_CSS}</style>
</head>
<body style="margin:0;padding:32px 16px;background-color:#f5f6f8;font-family:'Inter',Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0b1220;">
{body}
</body>
</html>"""


EMAIL_TEMPLATES = {
    "email_verification": _shell(
        "Verify Your Email — {{ project_name }}",
        """
<div class="email-wrapper">
  <div class="pre-header">
    <table class="pre-header-table" role="presentation">
      <tr>
        <td><span class="wordmark">{{ project_name }}</span></td>
        <td align="right"><span class="badge badge-intel">Verification</span></td>
      </tr>
    </table>
  </div>

  <div class="card">
    <div class="header">
      <div class="header-accent"></div>
      <h1>Confirm your <span class="accent">email</span></h1>
      <p class="header-sub">Verify your address to activate your account.</p>
    </div>
    <div class="content">
      <p class="intro-text">
        Hello <strong>{{ user_name }}</strong>, thanks for signing up for
        <strong>{{ project_name }}</strong>. Verify your email to unlock your account
        and access all features.
      </p>

      <div class="cta-section">
        <a href="{{ verification_url }}" class="cta-button">Verify email address &rarr;</a>
      </div>

      <div class="notice">
        <div class="notice-text">
          This link expires in <strong>24 hours</strong>. If you did not create an account,
          you can safely ignore this email.
        </div>
      </div>

      <p class="body-text">Best regards,<br />The {{ project_name }} Team</p>
    </div>
  </div>

  <div class="footer">
    <div class="footer-copy">
      &copy; {{ current_year }} {{ company_name }}. All rights reserved.<br />
      Sent to {{ user_email }}
    </div>
    <div class="footer-aside">Didn't sign up? You can safely ignore this email.</div>
  </div>
</div>
""",
    ),
    "password_reset": _shell(
        "Reset Your Password — {{ project_name }}",
        """
<div class="email-wrapper">
  <div class="pre-header">
    <table class="pre-header-table" role="presentation">
      <tr>
        <td><span class="wordmark">{{ project_name }}</span></td>
        <td align="right"><span class="badge badge-critical">Security</span></td>
      </tr>
    </table>
  </div>

  <div class="card">
    <div class="header">
      <div class="header-accent"></div>
      <div class="header-eyebrow">Password reset</div>
      <h1>Reset your <span class="accent">password</span></h1>
      <p class="header-sub">A reset was requested for your {{ project_name }} account.</p>
    </div>
    <div class="content">
      <p class="intro-text">
        Hello <strong>{{ user_name }}</strong>, we received a request to reset the password
        on your account. Click below to choose a new one.
      </p>

      <div class="banner banner-critical">
        This link expires in <strong>1 hour</strong>. After that you will need to request a new reset.
      </div>

      <div class="cta-section">
        <a href="{{ reset_url }}" class="cta-button">Reset password &rarr;</a>
        <p class="cta-sub">Expires in 1 hour</p>
      </div>

      <div class="divider"></div>

      <div class="fallback-url">
        <div class="fallback-label">Or open this link</div>
        <div class="fallback-link">{{ reset_url }}</div>
      </div>

      <div class="notice">
        <div class="notice-text">
          Didn't request this? Ignore this email — your password will not change.
        </div>
      </div>

      <p class="body-text">Best regards,<br />The {{ project_name }} Team</p>
    </div>
  </div>

  <div class="footer">
    <div class="footer-copy">
      &copy; {{ current_year }} {{ company_name }}. All rights reserved.<br />
      Sent to {{ user_email }}
    </div>
    <div class="footer-aside">Didn't request a reset? Ignore this email safely.</div>
  </div>
</div>
""",
    ),
    "welcome": _shell(
        "Welcome to {{ project_name }}",
        """
<div class="email-wrapper">
  <div class="pre-header">
    <table class="pre-header-table" role="presentation">
      <tr>
        <td><span class="wordmark">{{ project_name }}</span></td>
        <td align="right"><span class="badge badge-strong">Welcome</span></td>
      </tr>
    </table>
  </div>

  <div class="card">
    <div class="header">
      <div class="header-accent"></div>
      <div class="header-eyebrow">Account activated</div>
      <h1>Welcome to <span class="accent">{{ project_name }}</span></h1>
      <p class="header-sub">Your account is live and ready to go.</p>
    </div>
    <div class="content">
      <p class="intro-text">
        Hello <strong>{{ user_name }}</strong>, your email has been verified and your
        account is fully active. Here is what you can do from day one.
      </p>

      <div class="banner banner-strong">
        <strong>Account verified and active</strong>
      </div>

      <div class="section-label">What you have access to</div>
      <div class="features-grid">
        <div class="feature-cell">Sales session analysis</div>
        <div class="feature-cell">Checklist scoring</div>
        <div class="feature-cell">Performance tracking</div>
        <div class="feature-cell">Detailed reports</div>
      </div>

      <div class="cta-section">
        <a href="{{ dashboard_url }}" class="cta-button">Go to dashboard &rarr;</a>
      </div>

      <p class="body-text">Best regards,<br />The {{ project_name }} Team</p>
    </div>
  </div>

  <div class="footer">
    <div class="footer-copy">
      &copy; {{ current_year }} {{ company_name }}. All rights reserved.<br />
      Sent to {{ user_email }}
    </div>
    <div class="footer-aside">You're receiving this because you created an account.</div>
  </div>
</div>
""",
    ),
    "invitation": _shell(
        "Invitation — {{ project_name }}",
        """
<div class="email-wrapper">
  <div class="pre-header">
    <table class="pre-header-table" role="presentation">
      <tr>
        <td><span class="wordmark">{{ project_name }}</span></td>
        <td align="right"><span class="badge badge-intel">Invitation</span></td>
      </tr>
    </table>
  </div>

  <div class="card">
    <div class="header">
      <div class="header-accent"></div>
      <h1>Join <span class="accent">{{ organization_name }}</span></h1>
      <p class="header-sub">You've been invited to collaborate on {{ project_name }}.</p>
    </div>
    <div class="content">
      <p class="intro-text">
        <strong>{{ inviter_name }}</strong> has invited you to join
        <strong>{{ organization_name }}</strong>.
      </p>

      <div class="details-grid">
        <div class="detail-cell">
          <div class="detail-label">Team</div>
          <div class="detail-value">{{ team_name if team_name else '—' }}</div>
        </div>
        <div class="detail-cell">
          <div class="detail-label">Role</div>
          <div class="detail-value"><span class="role-pill">{{ role|capitalize }}</span></div>
        </div>
      </div>

      {% if temp_password %}
      <div class="section-label">Your login credentials</div>
      <table class="creds-box" role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#e5f1fd" style="background-color:#e5f1fd;border:1px solid #b8d4f8;border-radius:8px;">
        <tr>
          <td style="padding:18px 20px;">
            <div class="cred-row">
              <span class="cred-key">Email</span>
              <span class="cred-value" style="color:#0b1220;text-decoration:none;">{{ user_email }}</span>
            </div>
            <div class="cred-row">
              <span class="cred-key">Temporary password</span>
              <span class="cred-value cred-password" style="color:#0b1220;">{{ temp_password }}</span>
            </div>
          </td>
        </tr>
      </table>

      <div class="notice">
        <div class="notice-text">
          This is a temporary password. You will be prompted to set a new password after signing in.
        </div>
      </div>
      {% endif %}

      <div class="cta-section">
        <a href="{{ invite_url }}" class="cta-button">Accept invitation &rarr;</a>
        <p class="cta-sub">This invitation expires in 7 days</p>
      </div>

      <div class="section-label">What to do next</div>
      <table class="steps-table" role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr class="step-row">
          <td class="step-num-cell" width="36" valign="middle">
            <table role="presentation" width="28" height="28" cellpadding="0" cellspacing="0" border="0" bgcolor="#e5f1fd" style="width:28px;height:28px;background-color:#e5f1fd;border-radius:6px;">
              <tr>
                <td width="28" height="28" align="center" valign="middle" bgcolor="#e5f1fd" style="width:28px;height:28px;background-color:#e5f1fd;color:#0550c3;font-size:13px;font-weight:700;font-family:Arial,Helvetica,sans-serif;text-align:center;vertical-align:middle;border-radius:6px;">1</td>
              </tr>
            </table>
          </td>
          <td class="step-text" valign="middle">Click &ldquo;Accept invitation&rdquo; above</td>
        </tr>
        <tr class="step-row">
          <td class="step-num-cell" width="36" valign="middle">
            <table role="presentation" width="28" height="28" cellpadding="0" cellspacing="0" border="0" bgcolor="#e5f1fd" style="width:28px;height:28px;background-color:#e5f1fd;border-radius:6px;">
              <tr>
                <td width="28" height="28" align="center" valign="middle" bgcolor="#e5f1fd" style="width:28px;height:28px;background-color:#e5f1fd;color:#0550c3;font-size:13px;font-weight:700;font-family:Arial,Helvetica,sans-serif;text-align:center;vertical-align:middle;border-radius:6px;">2</td>
              </tr>
            </table>
          </td>
          <td class="step-text" valign="middle">Sign in with your email and temporary password</td>
        </tr>
        <tr class="step-row">
          <td class="step-num-cell" width="36" valign="middle">
            <table role="presentation" width="28" height="28" cellpadding="0" cellspacing="0" border="0" bgcolor="#e5f1fd" style="width:28px;height:28px;background-color:#e5f1fd;border-radius:6px;">
              <tr>
                <td width="28" height="28" align="center" valign="middle" bgcolor="#e5f1fd" style="width:28px;height:28px;background-color:#e5f1fd;color:#0550c3;font-size:13px;font-weight:700;font-family:Arial,Helvetica,sans-serif;text-align:center;vertical-align:middle;border-radius:6px;">3</td>
              </tr>
            </table>
          </td>
          <td class="step-text" valign="middle">Complete the invitation acceptance flow</td>
        </tr>
      </table>
    </div>
  </div>

  <div class="footer">
    <div class="footer-copy">
      &copy; {{ current_year }} {{ company_name }}. All rights reserved.
    </div>
    <div class="footer-aside">Sent to {{ user_email }}</div>
  </div>
</div>
""",
    ),
}


def get_email_templates() -> dict[str, str]:
    return EMAIL_TEMPLATES
