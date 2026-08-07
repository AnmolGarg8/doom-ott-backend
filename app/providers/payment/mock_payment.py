import uuid
from app.providers.payment.interface import PaymentProvider


class MockPaymentProvider(PaymentProvider):
    """Mock Payment Provider for testing instant payment checkout & verification without a live account."""

    async def create_order(self, amount: float, currency: str = "INR") -> dict:
        mock_order_id = f"mock_order_{uuid.uuid4().hex[:12]}"
        return {
            "order_id": mock_order_id,
            "amount": amount,
            "currency": currency,
            "provider": "mock",
        }

    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        # Mock payment verification always succeeds in mock mode
        return True
