"""
Payment Provider abstraction module (Stripe / Razorpay / etc.).
"""
from app.core.config import settings


async def create_payment_intent(amount: int, currency: str = "usd") -> dict:
    """Create payment intent via configured provider (mock or live)."""
    if settings.PAYMENT_PROVIDER == "mock":
        print(f"[MOCK PAYMENT] Creating payment intent for {amount} {currency}")
        return {
            "status": "success",
            "transaction_id": "mock_tx_12345",
            "amount": amount,
            "currency": currency,
            "provider": "mock",
        }
    else:
        raise NotImplementedError(f"Payment Provider '{settings.PAYMENT_PROVIDER}' not implemented.")
