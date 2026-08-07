"""
SMS Provider abstraction module.
"""
from app.core.config import settings


async def send_sms(phone_number: str, message: str) -> bool:
    """Send SMS via configured provider (mock or live)."""
    if settings.SMS_PROVIDER == "mock":
        # Mock provider logic
        print(f"[MOCK SMS] Sending to {phone_number}: {message}")
        return True
    else:
        # Live provider integration placeholder
        raise NotImplementedError(f"SMS Provider '{settings.SMS_PROVIDER}' not implemented.")
