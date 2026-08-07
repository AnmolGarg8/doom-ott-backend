import enum


class AuthProvider(str, enum.Enum):
    PHONE = "phone"
    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"


class ContentType(str, enum.Enum):
    MOVIE = "movie"
    SHORT = "short"
    SERIES = "series"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class VideoAssetStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class CouponDiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FLAT = "flat"
