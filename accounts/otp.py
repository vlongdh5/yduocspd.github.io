import pyotp
import qrcode
import io
import base64

TOTP_ISSUER = 'HR System'


class TOTPManager:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, email: str) -> str:
        from urllib.parse import unquote
        totp = pyotp.TOTP(secret)
        return unquote(totp.provisioning_uri(name=email, issuer_name=TOTP_ISSUER))

    @staticmethod
    def verify(secret: str, code: str) -> bool:
        from django.core.cache import cache
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            return False
        # Prevent replay within the 90-second validity window
        replay_key = f'totp_used_{secret[-8:]}_{code}'
        if cache.get(replay_key):
            return False
        cache.set(replay_key, True, timeout=90)
        return True

    @staticmethod
    def generate_qr_code_base64(secret: str, email: str) -> str:
        uri = TOTPManager.get_provisioning_uri(secret, email)
        img = qrcode.make(uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()


def is_otp_enabled() -> bool:
    from accounts.models import SystemConfig
    try:
        return SystemConfig.get('otp_enabled', False)
    except Exception:
        return False


def set_otp_enabled(enabled: bool):
    from accounts.models import SystemConfig
    SystemConfig.set('otp_enabled', enabled)
