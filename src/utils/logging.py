"""Logging configuration for the Raindrop.io MCP server."""

import logging
import sys
from typing import Optional
from .config import Config


def setup_logging(
    level: Optional[str] = None, format_type: str = "detailed"
) -> logging.Logger:
    """
    Set up logging configuration for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("simple" or "detailed")

    Returns:
        Configured logger instance
    """
    log_level = level or Config.LOG_LEVEL

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("raindrop_mcp")
    logger.setLevel(numeric_level)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Create formatter
    if format_type == "simple":
        formatter = logging.Formatter("%(levelname)s: %(message)s")
    else:  # detailed
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "raindrop_mcp") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# Create default logger
default_logger = setup_logging()
