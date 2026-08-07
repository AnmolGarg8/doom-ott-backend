import hmac
import hashlib
import logging
import httpx
from app.core.config import settings
from app.providers.payment.interface import PaymentProvider

logger = logging.getLogger("doom_ott.payment.razorpay")


class RazorpayProvider(PaymentProvider):
    """Razorpay Gateway Integration Provider."""

    def __init__(self, key_id: str = "", key_secret: str = ""):
        self.key_id = key_id or getattr(settings, "RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret or getattr(settings, "RAZORPAY_KEY_SECRET", "")

    async def create_order(self, amount: float, currency: str = "INR") -> dict:
        url = "https://api.razorpay.com/v1/orders"
        # Razorpay amount is in smallest currency sub-unit (paise for INR)
        amount_in_subunits = int(round(amount * 100))
        payload = {
            "amount": amount_in_subunits,
            "currency": currency,
            "payment_capture": 1,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, json=payload, auth=(self.key_id, self.key_secret)
            )
            response.raise_for_status()
            data = response.json()

        return {
            "order_id": data.get("id"),
            "amount": amount,
            "currency": currency,
            "key_id": self.key_id,
            "provider": "razorpay",
        }

    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify Razorpay payment signature per Razorpay documentation."""
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        generated_signature = hmac.new(
            self.key_secret.encode("utf-8"), msg, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature)
