from datetime import timedelta

from app.core.config import settings
from app.services.email_templates import EMAIL_TEMPLATES, get_default_html
from app.services.otp_service import OtpService


def test_otp_is_valid_for_24_hours():
    assert settings.OTP_EXPIRE_HOURS == 24
    assert timedelta(hours=settings.OTP_EXPIRE_HOURS) == timedelta(hours=24)


def test_generate_code_is_six_digits():
    service = OtpService()
    codes = {service.generate_code() for _ in range(30)}
    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert len(codes) > 1


def test_hash_is_deterministic_and_does_not_store_plaintext():
    service = OtpService()
    code = "482917"
    hashed = service.hash_code(code)
    assert hashed != code
    assert len(hashed) == 64
    assert service.codes_match(code, hashed)
    assert not service.codes_match("000000", hashed)


def test_normalize_code_keeps_digits_only():
    service = OtpService()
    assert service.normalize_code("12 34-56") == "123456"
    assert service.normalize_code("abc") == ""
    assert len(service.normalize_code("12 34")) != 6


def test_login_otp_email_mentions_24_hours_and_resend_revoke():
    html = get_default_html("login_otp")
    assert "login_otp" in EMAIL_TEMPLATES
    assert "{{ otp_code }}" in html
    assert "24 hours" in html
    assert "invalidates" in html.lower()
