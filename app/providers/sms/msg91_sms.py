import logging
import httpx
from app.providers.sms.interface import SMSProvider

logger = logging.getLogger("doom_ott.sms.msg91")


class MSG91Provider(SMSProvider):
    """MSG91 SMS Provider implementation stub."""

    def __init__(self, api_key: str = "", template_id: str = ""):
        self.api_key = api_key
        self.template_id = template_id

    async def send_otp(self, phone: str, otp: str) -> bool:
        # TODO: Replace with live MSG91 API credentials and endpoint call
        logger.info(f"[MSG91 STUB] Preparing to send OTP {otp} to {phone}")
        """
        async with httpx.AsyncClient() as client:
            url = "https://control.msg91.com/api/v5/otp"
            headers = {"authkey": self.api_key, "Content-Type": "application/json"}
            payload = {
                "template_id": self.template_id,
                "mobile": phone,
                "otp": otp,
            }
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code == 200
        """
        return True
