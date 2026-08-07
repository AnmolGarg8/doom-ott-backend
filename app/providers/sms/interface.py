from abc import ABC, abstractmethod


class SMSProvider(ABC):
    """Abstract Base Class for SMS Providers."""

    @abstractmethod
    async def send_otp(self, phone: str, otp: str) -> bool:
        """Send OTP to the given phone number."""
        pass
