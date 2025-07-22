#!/usr/bin/env python3
"""
Raindrop.io MCP Server Entry Point.

This module provides the main entry point for the Raindrop.io Model Context Protocol server.
The server enables AI assistants to interact with Raindrop.io bookmark management through
standardized MCP tools.
"""

import asyncio
import sys
import signal
from typing import Optional, Any

from .raindrop.server import RaindropMCPServer
from .utils.logging import setup_logging, get_logger
from .utils.config import Config


# Configure logging
logger = setup_logging()


class ServerManager:
    """Manages server lifecycle with graceful shutdown."""

    def __init__(self) -> None:
        self.server: Optional[RaindropMCPServer] = None
        self._shutdown_event = asyncio.Event()

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            # Unix signals
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
        else:
            # Windows signal
            signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self._shutdown_event.set()

    async def run(self) -> int:
        """
        Run the MCP server with proper lifecycle management.

        Returns:
            Exit code (0 for success, 1 for error)
        """
        exit_code = 0

        try:
            # Setup signal handlers
            self.setup_signal_handlers()

            # Validate configuration
            Config.validate()
            logger.info("Configuration validated successfully")

            # Create server instance
            self.server = RaindropMCPServer()

            # Create tasks for server and shutdown monitoring
            server_task = asyncio.create_task(self.server.run_stdio())
            shutdown_task = asyncio.create_task(self._shutdown_event.wait())

            logger.info("Raindrop MCP Server starting...")

            # Wait for either server completion or shutdown signal
            done, pending = await asyncio.wait(
                [server_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Check if server task completed with an exception
            for task in done:
                if task == server_task:
                    try:
                        await task  # Re-raise any exception
                    except asyncio.CancelledError:
                        pass  # Expected during shutdown
                    except Exception as e:
                        logger.error(f"Server error: {e}")
                        exit_code = 1

            logger.info("Raindrop MCP Server stopped")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            exit_code = 1
        finally:
            # Ensure cleanup
            if self.server:
                try:
                    await self.server.cleanup()
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")

        return exit_code


async def async_main() -> int:
    """Async main function."""
    manager = ServerManager()
    return await manager.run()


def main() -> None:
    """Main entry point."""
    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
