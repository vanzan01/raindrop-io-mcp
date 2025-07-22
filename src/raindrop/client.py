"""Raindrop.io API client with connection pooling, rate limiting, and retry logic."""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError, ClientResponseError

from .models import BookmarkModel, CollectionModel, UserModel
from .auth import AuthenticationManager
from .rate_limiter import RateLimiter
from .exceptions import (
    RaindropError,
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    PermissionError,
    ServerError,
    NetworkError,
)
from ..utils.config import Config
from ..utils.logging import get_logger


logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.base_delay * (2**attempt)
        return min(delay, self.max_delay)


class RaindropClient:
    """
    HTTP client for Raindrop.io API with comprehensive error handling,
    rate limiting, and retry logic.
    """

    def __init__(
        self,
        auth_manager: Optional[AuthenticationManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        """
        Initialize Raindrop API client.

        Args:
            auth_manager: Authentication manager instance
            rate_limiter: Rate limiter instance
        """
        self.auth_manager = auth_manager or AuthenticationManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.base_url = Config.RAINDROP_API_BASE_URL

        # HTTP client configuration
        self.timeout = ClientTimeout(total=Config.REQUEST_TIMEOUT)
        self.retry_config = RetryConfig(
            max_retries=Config.MAX_RETRIES, base_delay=Config.RETRY_DELAY
        )

        # Connection pooling
        self.connector = aiohttp.TCPConnector(
            limit=10,  # Total connection pool size
            limit_per_host=5,  # Max connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )

        self.session: Optional[ClientSession] = None
        self._closed = False

    async def __aenter__(self) -> "RaindropClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize the client and its dependencies."""
        if self._closed:
            raise RaindropError("Client has been closed")

        # Initialize authentication
        await self.auth_manager.initialize()

        # Start rate limiter
        await self.rate_limiter.start()

        # Create HTTP session
        self.session = ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers={"User-Agent": "Raindrop-MCP-Client/0.1.0"},
        )

        logger.info("Raindrop API client initialized")

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        if self._closed:
            return

        self._closed = True

        # Stop rate limiter
        await self.rate_limiter.stop()

        # Close HTTP session
        if self.session and not self.session.closed:
            await self.session.close()

        # Close connector
        if self.connector and not self.connector.closed:
            await self.connector.close()

        logger.info("Raindrop API client closed")

    async def cleanup(self) -> None:
        """Alias for close() method for consistent API."""
        await self.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting, retries, and error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            priority: Request priority for rate limiting

        Returns:
            Response data as dictionary

        Raises:
            Various Raindrop exceptions based on error type
        """
        if self._closed:
            raise RaindropError("Client has been closed")

        if not self.session:
            raise RaindropError("Client not initialized. Call initialize() first.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Acquire rate limit permission
        if not await self.rate_limiter.acquire(priority=priority):
            raise RateLimitError("Rate limit exceeded and request timed out")

        # Prepare headers
        headers = self.auth_manager.get_auth_headers()

        # Retry loop
        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                async with self.session.request(
                    method=method, url=url, params=params, json=data, headers=headers
                ) as response:
                    # Handle response
                    response_data = await self._handle_response(response)

                    # Record success for rate limiter
                    self.rate_limiter.record_success()

                    return response_data

            except (ClientError, asyncio.TimeoutError) as e:
                last_exception = e

                # Record failure for rate limiter
                self.rate_limiter.record_failure()

                # Don't retry authentication errors
                if isinstance(
                    e,
                    (
                        AuthenticationError,
                        InvalidTokenError,
                        TokenExpiredError,
                        PermissionError,
                    ),
                ):
                    raise

                # Don't retry validation errors
                if isinstance(e, ValidationError):
                    raise

                # Don't retry on last attempt
                if attempt == self.retry_config.max_retries:
                    break

                # Calculate delay
                delay = self.retry_config.get_delay(attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        if last_exception:
            if isinstance(last_exception, asyncio.TimeoutError):
                raise NetworkError("Request timed out after multiple retries")
            else:
                raise NetworkError(
                    f"Request failed after {self.retry_config.max_retries} retries: {last_exception}"
                )

        raise NetworkError("Request failed for unknown reason")

    async def _handle_response(
        self, response: aiohttp.ClientResponse
    ) -> Dict[str, Any]:
        """
        Handle HTTP response and convert errors to appropriate exceptions.

        Args:
            response: aiohttp response object

        Returns:
            Response data as dictionary

        Raises:
            Various Raindrop exceptions based on response status
        """
        try:
            # Try to parse JSON response
            response_data = await response.json()
        except Exception:
            # If JSON parsing fails, use text
            response_text = await response.text()
            response_data = {"message": response_text}

        # Handle different status codes
        if response.status == 200 or response.status == 201:
            return response_data

        elif response.status == 400:
            error_message = response_data.get("error", "Bad request")
            raise ValidationError(error_message)

        elif response.status == 401:
            error_message = response_data.get("error", "Unauthorized")
            if "token" in error_message.lower():
                if "expired" in error_message.lower():
                    raise TokenExpiredError(error_message)
                else:
                    raise InvalidTokenError(error_message)
            else:
                raise AuthenticationError(error_message)

        elif response.status == 403:
            error_message = response_data.get("error", "Forbidden")
            raise PermissionError(error_message)

        elif response.status == 404:
            error_message = response_data.get("error", "Not found")
            raise NotFoundError("Resource", None)

        elif response.status == 429:
            error_message = response_data.get("error", "Too many requests")
            retry_after = response.headers.get("Retry-After")
            retry_seconds = int(retry_after) if retry_after else None
            raise RateLimitError(error_message, retry_seconds)

        elif response.status >= 500:
            error_message = response_data.get("error", "Server error")
            raise ServerError(error_message, response.status)

        else:
            error_message = response_data.get(
                "error", f"Unexpected status code: {response.status}"
            )
            raise RaindropError(error_message, response.status)

    # User API methods
    async def get_user(self) -> UserModel:
        """Get current user information."""
        data = await self._make_request("GET", "/user")
        return UserModel.from_dict(data["user"])

    # Bookmark API methods
    async def search_bookmarks(self, **params: Any) -> Dict[str, Any]:
        """
        Search bookmarks with filters.

        Args:
            **params: Search parameters (search, type, tag, sort, etc.)

        Returns:
            Search results with items and metadata
        """
        collection_id = params.pop("collection", 0)  # Default to all bookmarks
        endpoint = f"/raindrops/{collection_id}"

        data = await self._make_request("GET", endpoint, params=params)

        # Parse bookmarks
        bookmarks = []
        for item in data.get("items", []):
            try:
                bookmarks.append(BookmarkModel.from_dict(item))
            except Exception as e:
                logger.warning(f"Failed to parse bookmark: {e}")

        return {
            "items": bookmarks,
            "count": data.get("count", 0),
            "total": data.get("total", 0),
            "result": data.get("result", True),
        }

    async def get_bookmark(self, bookmark_id: int) -> BookmarkModel:
        """Get bookmark by ID."""
        data = await self._make_request("GET", f"/raindrop/{bookmark_id}")
        return BookmarkModel.from_dict(data["item"])

    async def create_bookmark(self, bookmark_data: Dict[str, Any]) -> BookmarkModel:
        """Create a new bookmark."""
        data = await self._make_request("POST", "/raindrop", data=bookmark_data)
        return BookmarkModel.from_dict(data["item"])

    async def update_bookmark(
        self, bookmark_id: int, bookmark_data: Dict[str, Any]
    ) -> BookmarkModel:
        """Update an existing bookmark."""
        data = await self._make_request(
            "PUT", f"/raindrop/{bookmark_id}", data=bookmark_data
        )
        return BookmarkModel.from_dict(data["item"])

    async def delete_bookmark(self, bookmark_id: int) -> bool:
        """Delete a bookmark."""
        await self._make_request("DELETE", f"/raindrop/{bookmark_id}")
        return True

    # Collection API methods
    async def list_collections(self) -> List[CollectionModel]:
        """List all collections (both root and child collections)."""
        collections = []
        
        # Get root collections
        try:
            root_data = await self._make_request("GET", "/collections")
            for item in root_data.get("items", []):
                try:
                    collections.append(CollectionModel.from_dict(item))
                except Exception as e:
                    logger.warning(f"Failed to parse root collection: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch root collections: {e}")
        
        # Get child collections (subcollections)
        try:
            child_data = await self._make_request("GET", "/collections/childrens")
            for item in child_data.get("items", []):
                try:
                    collections.append(CollectionModel.from_dict(item))
                except Exception as e:
                    logger.warning(f"Failed to parse child collection: {e}")
        except Exception as e:
            logger.warning(f"Failed to fetch child collections: {e}")

        return collections

    async def get_collection(self, collection_id: int) -> CollectionModel:
        """Get collection by ID."""
        data = await self._make_request("GET", f"/collection/{collection_id}")
        return CollectionModel.from_dict(data["item"])

    async def create_collection(
        self, collection_data: Dict[str, Any]
    ) -> CollectionModel:
        """Create a new collection."""
        data = await self._make_request("POST", "/collection", data=collection_data)
        return CollectionModel.from_dict(data["item"])

    async def update_collection(
        self, collection_id: int, collection_data: Dict[str, Any]
    ) -> CollectionModel:
        """Update an existing collection."""
        data = await self._make_request(
            "PUT", f"/collection/{collection_id}", data=collection_data
        )
        return CollectionModel.from_dict(data["item"])

    async def delete_collection(self, collection_id: int) -> bool:
        """Delete a collection."""
        await self._make_request("DELETE", f"/collection/{collection_id}")
        return True

    # Health and status methods
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the client and API."""
        health_info = {
            "client_status": "healthy" if not self._closed else "closed",
            "session_status": (
                "active" if self.session and not self.session.closed else "inactive"
            ),
            "auth_status": await self.auth_manager.health_check(),
            "rate_limiter_status": self.rate_limiter.get_status(),
            "timestamp": time.time(),
        }

        try:
            # Test API connectivity
            user = await self.get_user()
            health_info["api_status"] = "connected"
            health_info["user_id"] = user.id
        except Exception as e:
            health_info["api_status"] = "error"
            health_info["api_error"] = str(e)

        return health_info
