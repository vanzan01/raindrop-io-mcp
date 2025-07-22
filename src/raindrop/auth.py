"""Authentication and token validation for Raindrop.io API."""

import asyncio
import time
from typing import Optional, Dict, Any
import aiohttp
from .exceptions import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    MissingTokenError,
    NetworkError,
)
from ..utils.config import Config


class TokenValidator:
    """Handles API token validation and management."""

    def __init__(self, token: str, base_url: Optional[str] = None) -> None:
        self.token = token
        self.base_url = base_url or Config.RAINDROP_API_BASE_URL
        self._validation_cache: Dict[str, tuple[bool, float]] = {}
        self._cache_duration = 300  # 5 minutes

    async def validate_token(self, force_refresh: bool = False) -> bool:
        """
        Validate the API token against Raindrop.io API.

        Args:
            force_refresh: Skip cache and force fresh validation

        Returns:
            True if token is valid, False otherwise

        Raises:
            AuthenticationError: If token validation fails
            NetworkError: If unable to connect to API
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_result = self._get_cached_validation()
            if cached_result is not None:
                return cached_result

        try:
            is_valid = await self._validate_against_api()
            self._cache_validation_result(is_valid)
            return is_valid

        except aiohttp.ClientError as e:
            raise NetworkError(f"Failed to connect to Raindrop.io API: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")

    async def _validate_against_api(self) -> bool:
        """Validate token by making a test API call."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Use the user endpoint for validation - it's lightweight
            url = f"{self.base_url}/user"

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    response_text = await response.text()
                    if "expired" in response_text.lower():
                        raise TokenExpiredError()
                    else:
                        raise InvalidTokenError()
                elif response.status == 403:
                    raise AuthenticationError("Token lacks required permissions")
                else:
                    raise AuthenticationError(
                        f"Unexpected response status: {response.status}"
                    )

    def _get_cached_validation(self) -> Optional[bool]:
        """Get cached validation result if still valid."""
        if self.token not in self._validation_cache:
            return None

        is_valid, timestamp = self._validation_cache[self.token]

        # Check if cache is still valid
        if time.time() - timestamp < self._cache_duration:
            return is_valid

        # Cache expired, remove it
        del self._validation_cache[self.token]
        return None

    def _cache_validation_result(self, is_valid: bool) -> None:
        """Cache validation result with timestamp."""
        self._validation_cache[self.token] = (is_valid, time.time())

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def validate_token_format(token: str) -> bool:
        """Basic token format validation."""
        if not isinstance(token, str):
            return False

        # Remove whitespace
        token = token.strip()

        # Basic checks
        if len(token) < 10:  # Raindrop tokens are typically longer
            return False

        # Should contain only valid characters (alphanumeric and some special chars)
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        )
        if not all(c in allowed_chars for c in token):
            return False

        return True


class AuthenticationManager:
    """Manages authentication for the Raindrop.io MCP server."""

    def __init__(self) -> None:
        self.config = Config
        self._validator: Optional[TokenValidator] = None
        self._authenticated = False

    async def initialize(self) -> None:
        """Initialize authentication system."""
        # Validate configuration
        self.config.validate()

        # Check for valid token
        if not self.config.RAINDROP_API_TOKEN:
            raise MissingTokenError("API token not configured")

        # Create token validator
        self._validator = TokenValidator(self.config.RAINDROP_API_TOKEN)

        # Validate token format
        if not TokenValidator.validate_token_format(self.config.RAINDROP_API_TOKEN):
            raise InvalidTokenError("Token format is invalid")

        # Validate token against API
        try:
            await self._validator.validate_token()
            self._authenticated = True
        except AuthenticationError:
            # Re-raise authentication errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions
            raise AuthenticationError(f"Authentication initialization failed: {str(e)}")

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._authenticated

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self._authenticated or not self._validator:
            raise AuthenticationError("Not authenticated. Call initialize() first.")

        return self._validator.get_auth_headers()

    async def refresh_token_validation(self) -> None:
        """Refresh token validation (force check against API)."""
        if not self._validator:
            raise AuthenticationError("Authentication not initialized")

        try:
            is_valid = await self._validator.validate_token(force_refresh=True)
            self._authenticated = is_valid
            if not is_valid:
                raise AuthenticationError("Token validation failed")
        except AuthenticationError:
            self._authenticated = False
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform authentication health check."""
        result: Dict[str, Any] = {
            "authenticated": self._authenticated,
            "token_configured": bool(self.config.RAINDROP_API_TOKEN),
            "timestamp": time.time(),
        }

        if self._authenticated and self._validator:
            try:
                # Quick validation check
                is_valid = await self._validator.validate_token()
                result["token_valid"] = is_valid
                if not is_valid:
                    self._authenticated = False
                    result["authenticated"] = False
            except Exception as e:
                result["token_valid"] = False
                result["error"] = str(e)
                self._authenticated = False
                result["authenticated"] = False

        return result
