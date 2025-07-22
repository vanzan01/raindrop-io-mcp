"""Configuration management utilities."""

import os
from typing import Optional
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings for the Raindrop.io MCP server."""

    # API Configuration
    RAINDROP_API_TOKEN: Optional[str] = os.getenv("RAINDROP_API_TOKEN")
    RAINDROP_API_BASE_URL: str = os.getenv(
        "RAINDROP_API_BASE_URL", "https://api.raindrop.io/rest/v1"
    )

    # Server Configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "3000"))

    # Rate Limiting Configuration
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # HTTP Client Configuration
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.RAINDROP_API_TOKEN:
            raise ValueError(
                "RAINDROP_API_TOKEN is required. Please set it in your .env file."
            )

        if len(cls.RAINDROP_API_TOKEN) < 10:
            raise ValueError("RAINDROP_API_TOKEN appears to be invalid (too short).")

    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development mode."""
        return cls.ENVIRONMENT.lower() == "development"

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode."""
        return cls.ENVIRONMENT.lower() == "production"
