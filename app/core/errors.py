from typing import Any, Dict, Optional


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="RESOURCE_NOT_FOUND", message=message, status_code=404, details=details)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="AUTHENTICATION_FAILED", message=message, status_code=401, details=details)


class AuthorizationError(AppError):
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="PERMISSION_DENIED", message=message, status_code=403, details=details)


class DuplicateResourceError(AppError):
    def __init__(self, message: str = "Resource already exists", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="DUPLICATE_RESOURCE", message=message, status_code=409, details=details)


class UnsupportedMediaTypeError(AppError):
    def __init__(self, message: str = "Unsupported media type", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="UNSUPPORTED_MEDIA_TYPE", message=message, status_code=415, details=details)


class PayloadTooLargeError(AppError):
    def __init__(self, message: str = "Payload exceeds maximum allowed size", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="PAYLOAD_TOO_LARGE", message=message, status_code=413, details=details)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


class RateLimitExceededError(AppError):
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="RATE_LIMIT_EXCEEDED", message=message, status_code=429, details=details)


class PipelineError(AppError):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code=code, message=message, status_code=500, details=details)
