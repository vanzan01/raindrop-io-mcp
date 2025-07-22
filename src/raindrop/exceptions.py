"""Custom exceptions for Raindrop.io API interactions."""

from typing import Optional, Dict, Any


class RaindropError(Exception):
    """Base exception for Raindrop.io API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(RaindropError):
    """Authentication-related errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: Optional[int] = 401,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

    @property
    def recovery_suggestion(self) -> str:
        """Provide recovery suggestions for authentication errors."""
        return (
            "Please check your RAINDROP_API_TOKEN in the .env file. "
            "You can generate a new token at https://app.raindrop.io/settings/integrations"
        )


class InvalidTokenError(AuthenticationError):
    """Invalid API token error."""

    def __init__(self, message: str = "Invalid API token provided"):
        super().__init__(message, 401)

    @property
    def recovery_suggestion(self) -> str:
        """Recovery suggestion for invalid token."""
        return (
            "The provided API token is invalid or malformed. "
            "Please verify your RAINDROP_API_TOKEN in the .env file. "
            "Generate a new token at https://app.raindrop.io/settings/integrations"
        )


class TokenExpiredError(AuthenticationError):
    """Expired API token error."""

    def __init__(self, message: str = "API token has expired"):
        super().__init__(message, 401)

    @property
    def recovery_suggestion(self) -> str:
        """Recovery suggestion for expired token."""
        return (
            "Your API token has expired. "
            "Please generate a new token at https://app.raindrop.io/settings/integrations "
            "and update your .env file"
        )


class MissingTokenError(AuthenticationError):
    """Missing API token error."""

    def __init__(self, message: str = "API token is required but not configured"):
        super().__init__(message, 401)

    @property
    def recovery_suggestion(self) -> str:
        """Recovery suggestion for missing token."""
        return (
            "No API token is configured. "
            "Please add your RAINDROP_API_TOKEN to the .env file. "
            "Generate a token at https://app.raindrop.io/settings/integrations"
        )


class RateLimitError(RaindropError):
    """Rate limiting error."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None
    ):
        super().__init__(message, 429)
        self.retry_after = retry_after

    @property
    def recovery_suggestion(self) -> str:
        """Recovery suggestion for rate limit errors."""
        retry_msg = ""
        if self.retry_after:
            retry_msg = f" Please retry after {self.retry_after} seconds."
        return f"You have exceeded the API rate limit.{retry_msg}"


class ValidationError(RaindropError):
    """Data validation error."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, 400)
        self.field = field


class NotFoundError(RaindropError):
    """Resource not found error."""

    def __init__(self, resource: str, resource_id: Optional[int] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, 404)
        self.resource = resource
        self.resource_id = resource_id


class PermissionError(RaindropError):
    """Permission denied error."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, 403)


class ServerError(RaindropError):
    """Server-side error."""

    def __init__(self, message: str = "Server error occurred", status_code: int = 500):
        super().__init__(message, status_code)


class NetworkError(RaindropError):
    """Network-related error."""

    def __init__(self, message: str = "Network error occurred"):
        super().__init__(message)
