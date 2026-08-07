import logging
from app.providers.sms.interface import SMSProvider

logger = logging.getLogger("doom_ott.sms")


class MockSMSProvider(SMSProvider):
    """Mock SMS Provider logging OTPs to console/logger."""

    async def send_otp(self, phone: str, otp: str) -> bool:
        message = f"========================================\n[MOCK SMS] Sent to {phone}: Your OTP is {otp}\n========================================"
        print(message)
        logger.info(message)
        return True
