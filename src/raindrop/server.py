"""MCP protocol handler for Raindrop.io server."""

import asyncio
from typing import Dict, List, Optional, Any, Sequence
import json
import sys

from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp import types
import mcp.server.stdio

from .schemas import MCP_TOOLS
from ..raindrop.client import RaindropClient
from ..raindrop.auth import AuthenticationManager
from ..raindrop.rate_limiter import RateLimiter
from ..utils.logging import get_logger
from ..tools.bookmarks import get_recent_unsorted
from ..utils.transformers import (
    validate_mcp_tool_args,
    mcp_to_raindrop_search_params,
    mcp_to_raindrop_create_bookmark,
    mcp_to_raindrop_update_bookmark,
    mcp_to_raindrop_create_collection,
    raindrop_to_mcp_search_results,
    raindrop_to_mcp_bookmark,
    raindrop_to_mcp_collection,
    format_error_response,
)


logger = get_logger(__name__)


class RaindropMCPServer:
    """
    MCP server for Raindrop.io integration.

    Implements the Model Context Protocol to provide AI assistants
    with access to Raindrop.io bookmark management functionality.
    """

    def __init__(
        self,
        auth_manager: Optional[AuthenticationManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize the MCP server.

        Args:
            auth_manager: Authentication manager instance
            rate_limiter: Rate limiter instance
        """
        self.auth_manager = auth_manager or AuthenticationManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.raindrop_client: Optional[RaindropClient] = None

        # Create MCP server instance
        self.server: Server = Server("raindrop-mcp")

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools."""
            return await self._list_tools()

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Execute a tool call."""
            return await self._call_tool(name, arguments)

    async def _list_tools(self) -> List[types.Tool]:
        """Return list of available MCP tools."""
        tools = []

        for tool_name, tool_def in MCP_TOOLS.items():
            tool = types.Tool(
                name=tool_name,
                description=tool_def["description"],
                inputSchema=tool_def["inputSchema"],
            )
            tools.append(tool)

        logger.debug(f"Listed {len(tools)} tools")
        return tools

    async def _call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Execute a tool call.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution results as MCP content
        """
        logger.info(f"Calling tool: {name} with args: {arguments}")

        try:
            # Validate arguments
            validate_mcp_tool_args(name, arguments)

            # Ensure client is initialized
            if not self.raindrop_client:
                raise RuntimeError("Raindrop client not initialized")
            
            assert self.raindrop_client is not None

            # Route to appropriate handler
            if name == "search_bookmarks":
                result = await self._handle_search_bookmarks(arguments)
            elif name == "create_bookmark":
                result = await self._handle_create_bookmark(arguments)
            elif name == "get_bookmark":
                result = await self._handle_get_bookmark(arguments)
            elif name == "update_bookmark":
                result = await self._handle_update_bookmark(arguments)
            elif name == "delete_bookmark":
                result = await self._handle_delete_bookmark(arguments)
            elif name == "list_collections":
                result = await self._handle_list_collections(arguments)
            elif name == "create_collection":
                result = await self._handle_create_collection(arguments)
            elif name == "get_recent_unsorted":
                result = await self._handle_get_recent_unsorted(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

            # Format successful response
            response_text = json.dumps(result, indent=2, ensure_ascii=False)
            return [types.TextContent(type="text", text=response_text)]

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            error_response = format_error_response(e, f"Tool: {name}")
            error_text = json.dumps(error_response, indent=2, ensure_ascii=False)
            return [types.TextContent(type="text", text=error_text)]

    async def _handle_search_bookmarks(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle search_bookmarks tool call."""
        # Convert MCP args to Raindrop API params
        params = mcp_to_raindrop_search_params(arguments)

        # Call Raindrop API
        api_response = await self.raindrop_client.search_bookmarks(**params)

        # Convert response to MCP format
        mcp_response = raindrop_to_mcp_search_results(
            bookmarks=api_response["items"],
            total=api_response.get("total", 0),
            page=params.get("page", 0),
            per_page=params.get("perpage", 50),
        )

        return {
            "success": True,
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "url": item.url,
                        "excerpt": item.excerpt,
                        "note": item.note,
                        "type": item.type,
                        "tags": item.tags,
                        "created": item.created,
                        "lastUpdate": item.lastUpdate,
                        "domain": item.domain,
                        "collection_id": item.collection_id,
                        "collection_title": item.collection_title,
                    }
                    for item in mcp_response.items
                ],
                "count": mcp_response.count,
                "total": mcp_response.total,
                "page": mcp_response.page,
                "per_page": mcp_response.per_page,
                "has_more": mcp_response.has_more,
            },
        }

    async def _handle_create_bookmark(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle create_bookmark tool call."""
        # Convert MCP args to Raindrop API format
        bookmark_data = mcp_to_raindrop_create_bookmark(arguments)

        # Call Raindrop API
        bookmark = await self.raindrop_client.create_bookmark(bookmark_data)

        # Convert response to MCP format
        mcp_bookmark = raindrop_to_mcp_bookmark(bookmark)

        return {
            "success": True,
            "data": {
                "id": mcp_bookmark.id,
                "title": mcp_bookmark.title,
                "url": mcp_bookmark.url,
                "excerpt": mcp_bookmark.excerpt,
                "note": mcp_bookmark.note,
                "type": mcp_bookmark.type,
                "tags": mcp_bookmark.tags,
                "created": mcp_bookmark.created,
                "lastUpdate": mcp_bookmark.lastUpdate,
                "domain": mcp_bookmark.domain,
                "collection_id": mcp_bookmark.collection_id,
                "collection_title": mcp_bookmark.collection_title,
            },
        }

    async def _handle_get_bookmark(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_bookmark tool call."""
        bookmark_id = arguments["bookmark_id"]

        # Call Raindrop API
        bookmark = await self.raindrop_client.get_bookmark(bookmark_id)

        # Convert response to MCP format
        mcp_bookmark = raindrop_to_mcp_bookmark(bookmark)

        return {
            "success": True,
            "data": {
                "id": mcp_bookmark.id,
                "title": mcp_bookmark.title,
                "url": mcp_bookmark.url,
                "excerpt": mcp_bookmark.excerpt,
                "note": mcp_bookmark.note,
                "type": mcp_bookmark.type,
                "tags": mcp_bookmark.tags,
                "created": mcp_bookmark.created,
                "lastUpdate": mcp_bookmark.lastUpdate,
                "domain": mcp_bookmark.domain,
                "collection_id": mcp_bookmark.collection_id,
                "collection_title": mcp_bookmark.collection_title,
            },
        }

    async def _handle_update_bookmark(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle update_bookmark tool call."""
        bookmark_id = arguments["bookmark_id"]

        # Convert MCP args to Raindrop API format
        update_data = mcp_to_raindrop_update_bookmark(arguments)

        # Call Raindrop API
        bookmark = await self.raindrop_client.update_bookmark(bookmark_id, update_data)

        # Convert response to MCP format
        mcp_bookmark = raindrop_to_mcp_bookmark(bookmark)

        return {
            "success": True,
            "data": {
                "id": mcp_bookmark.id,
                "title": mcp_bookmark.title,
                "url": mcp_bookmark.url,
                "excerpt": mcp_bookmark.excerpt,
                "note": mcp_bookmark.note,
                "type": mcp_bookmark.type,
                "tags": mcp_bookmark.tags,
                "created": mcp_bookmark.created,
                "lastUpdate": mcp_bookmark.lastUpdate,
                "domain": mcp_bookmark.domain,
                "collection_id": mcp_bookmark.collection_id,
                "collection_title": mcp_bookmark.collection_title,
            },
        }

    async def _handle_delete_bookmark(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle delete_bookmark tool call."""
        bookmark_id = arguments["bookmark_id"]

        # Call Raindrop API
        success = await self.raindrop_client.delete_bookmark(bookmark_id)

        return {
            "success": success,
            "data": {"bookmark_id": bookmark_id, "deleted": success},
        }

    async def _handle_list_collections(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle list_collections tool call."""
        # Call Raindrop API
        collections = await self.raindrop_client.list_collections()

        # Convert response to MCP format
        mcp_collections = [
            raindrop_to_mcp_collection(collection) for collection in collections
        ]

        # Apply sorting if requested
        sort_field = arguments.get("sort", "title")
        sort_order = arguments.get("order", "asc")

        reverse = sort_order.lower() == "desc"

        if sort_field == "title":
            mcp_collections.sort(key=lambda x: x.title.lower(), reverse=reverse)
        elif sort_field == "count":
            mcp_collections.sort(key=lambda x: x.count, reverse=reverse)
        elif sort_field == "created":
            mcp_collections.sort(key=lambda x: x.created or "", reverse=reverse)
        elif sort_field == "lastUpdate":
            mcp_collections.sort(key=lambda x: x.lastUpdate or "", reverse=reverse)

        return {
            "success": True,
            "data": {
                "collections": [
                    {
                        "id": collection.id,
                        "title": collection.title,
                        "description": collection.description,
                        "public": collection.public,
                        "count": collection.count,
                        "created": collection.created,
                        "lastUpdate": collection.lastUpdate,
                    }
                    for collection in mcp_collections
                ],
                "count": len(mcp_collections),
            },
        }

    async def _handle_create_collection(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle create_collection tool call."""
        # Convert MCP args to Raindrop API format
        collection_data = mcp_to_raindrop_create_collection(arguments)

        # Call Raindrop API
        collection = await self.raindrop_client.create_collection(collection_data)

        # Convert response to MCP format
        mcp_collection = raindrop_to_mcp_collection(collection)

        return {
            "success": True,
            "data": {
                "id": mcp_collection.id,
                "title": mcp_collection.title,
                "description": mcp_collection.description,
                "public": mcp_collection.public,
                "count": mcp_collection.count,
                "created": mcp_collection.created,
                "lastUpdate": mcp_collection.lastUpdate,
            },
        }

    async def _handle_get_recent_unsorted(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get_recent_unsorted tool call."""
        return await get_recent_unsorted(self.raindrop_client, arguments)

    async def initialize(self) -> None:
        """Initialize the server and its dependencies."""
        logger.info("Initializing Raindrop MCP server")

        try:
            # Initialize authentication
            await self.auth_manager.initialize()
            logger.info("Authentication initialized")

            # Start rate limiter
            await self.rate_limiter.start()
            logger.info("Rate limiter started")

            # Initialize Raindrop client
            self.raindrop_client = RaindropClient(
                auth_manager=self.auth_manager, rate_limiter=self.rate_limiter
            )
            await self.raindrop_client.initialize()
            logger.info("Raindrop client initialized")

            logger.info("Raindrop MCP server initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            await self.cleanup()
            raise

    async def cleanup(self) -> None:
        """Cleanup server resources."""
        logger.info("Cleaning up Raindrop MCP server")

        if self.raindrop_client:
            await self.raindrop_client.close()

        await self.rate_limiter.stop()

        logger.info("Raindrop MCP server cleanup complete")

    async def run_stdio(self) -> None:
        """Run the server using stdio transport."""
        logger.info("Starting Raindrop MCP server with stdio transport")

        try:
            # Initialize server
            await self.initialize()

            # Run MCP server with stdio
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="raindrop-mcp",
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            await self.cleanup()

    def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities."""
        return {
            "tools": {"listChanged": True},
            "logging": {},
        }


async def main() -> None:
    """Main entry point for the MCP server."""
    # Create and run server
    server = RaindropMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
