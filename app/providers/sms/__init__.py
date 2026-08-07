from app.core.config import settings
from app.providers.sms.interface import SMSProvider
from app.providers.sms.mock_sms import MockSMSProvider
from app.providers.sms.msg91_sms import MSG91Provider


def get_sms_provider() -> SMSProvider:
    """Factory function returning SMSProvider based on SMS_PROVIDER setting."""
    provider_name = settings.SMS_PROVIDER.lower()
    if provider_name == "msg91":
        return MSG91Provider()
    return MockSMSProvider()


__all__ = ["SMSProvider", "MockSMSProvider", "MSG91Provider", "get_sms_provider"]
