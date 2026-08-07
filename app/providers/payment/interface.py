from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    """Abstract Base Class for Payment Gateway Providers."""

    @abstractmethod
    async def create_order(self, amount: float, currency: str = "INR") -> dict:
        """Create a new payment order with the provider and return order_id and checkout details."""
        pass

    @abstractmethod
    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify payment signature / status with the payment provider."""
        pass
