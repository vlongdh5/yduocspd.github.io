import pytest
from accounts.otp import TOTPManager, is_otp_enabled, set_otp_enabled


def test_totp_generate_secret():
    secret = TOTPManager.generate_secret()
    assert len(secret) == 32


def test_totp_generate_provisioning_uri():
    secret = TOTPManager.generate_secret()
    uri = TOTPManager.get_provisioning_uri(secret, 'test@example.com')
    assert 'test@example.com' in uri
    assert 'HR System' in uri


def test_totp_verify_valid_code():
    import pyotp
    secret = TOTPManager.generate_secret()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    assert TOTPManager.verify(secret, current_code) is True


def test_totp_verify_invalid_code():
    secret = TOTPManager.generate_secret()
    assert TOTPManager.verify(secret, '000000') is False


def test_otp_enabled_default_false():
    assert is_otp_enabled() is False


@pytest.mark.django_db
def test_otp_toggle():
    set_otp_enabled(True)
    assert is_otp_enabled() is True
    set_otp_enabled(False)
    assert is_otp_enabled() is False
