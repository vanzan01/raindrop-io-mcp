"""Bookmark CRUD operations for Raindrop.io."""

from typing import Dict, Any
from ..raindrop.client import RaindropClient
from ..utils.transformers import (
    mcp_to_raindrop_create_bookmark,
    mcp_to_raindrop_update_bookmark,
    raindrop_to_mcp_bookmark,
    validate_mcp_tool_args,
)
from ..utils.logging import get_logger


logger = get_logger(__name__)


async def create_bookmark(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new bookmark.

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments

    Returns:
        Created bookmark in MCP format
    """
    logger.info(f"Creating bookmark with args: {arguments}")

    # Validate arguments
    validate_mcp_tool_args("create_bookmark", arguments)

    # Convert MCP args to Raindrop API format
    bookmark_data = mcp_to_raindrop_create_bookmark(arguments)

    # Call Raindrop API
    bookmark = await client.create_bookmark(bookmark_data)

    # Convert response to MCP format
    mcp_bookmark = raindrop_to_mcp_bookmark(bookmark)

    return {
        "success": True,
        "tool": "create_bookmark",
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


async def get_bookmark(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get bookmark by ID.

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments

    Returns:
        Bookmark data in MCP format
    """
    bookmark_id = arguments["bookmark_id"]
    logger.info(f"Getting bookmark with ID: {bookmark_id}")

    # Validate arguments
    validate_mcp_tool_args("get_bookmark", arguments)

    # Call Raindrop API
    bookmark = await client.get_bookmark(bookmark_id)

    # Convert response to MCP format
    mcp_bookmark = raindrop_to_mcp_bookmark(bookmark)

    return {
        "success": True,
        "tool": "get_bookmark",
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


async def update_bookmark(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing bookmark.

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments

    Returns:
        Updated bookmark in MCP format
    """
    bookmark_id = arguments["bookmark_id"]
    logger.info(f"Updating bookmark {bookmark_id} with args: {arguments}")

    # Validate arguments
    validate_mcp_tool_args("update_bookmark", arguments)

    # Convert MCP args to Raindrop API format
    update_data = mcp_to_raindrop_update_bookmark(arguments)

    # Call Raindrop API
    bookmark = await client.update_bookmark(bookmark_id, update_data)

    # Convert response to MCP format
    mcp_bookmark = raindrop_to_mcp_bookmark(bookmark)

    return {
        "success": True,
        "tool": "update_bookmark",
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


async def delete_bookmark(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Delete a bookmark.

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments

    Returns:
        Deletion confirmation
    """
    bookmark_id = arguments["bookmark_id"]
    logger.info(f"Deleting bookmark with ID: {bookmark_id}")

    # Validate arguments
    validate_mcp_tool_args("delete_bookmark", arguments)

    # Call Raindrop API
    success = await client.delete_bookmark(bookmark_id)

    return {
        "success": success,
        "tool": "delete_bookmark",
        "data": {"bookmark_id": bookmark_id, "deleted": success},
    }
