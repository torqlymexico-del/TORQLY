class ServiceError(Exception):
    """Base domain exception."""


class NotFoundError(ServiceError):
    """Raised when an entity cannot be found."""


class ConflictError(ServiceError):
    """Raised when a resource would violate a unique/business constraint."""


class ValidationError(ServiceError):
    """Raised when business validation fails."""

