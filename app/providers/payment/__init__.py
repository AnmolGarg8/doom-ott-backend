from app.core.config import settings
from app.providers.payment.interface import PaymentProvider
from app.providers.payment.mock_payment import MockPaymentProvider
from app.providers.payment.razorpay_payment import RazorpayProvider


def get_payment_provider() -> PaymentProvider:
    """Factory function returning PaymentProvider implementation based on PAYMENT_PROVIDER setting."""
    provider_name = settings.PAYMENT_PROVIDER.lower()
    if provider_name == "razorpay":
        return RazorpayProvider()
    return MockPaymentProvider()


__all__ = [
    "PaymentProvider",
    "MockPaymentProvider",
    "RazorpayProvider",
    "get_payment_provider",
]
