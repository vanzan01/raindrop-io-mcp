"""Bookmark CRUD operations for Raindrop.io."""

from typing import Dict, Any
from ..raindrop.client import RaindropClient
from ..utils.transformers import (
    mcp_to_raindrop_create_bookmark,
    mcp_to_raindrop_update_bookmark,
    raindrop_to_mcp_bookmark,
    mcp_to_raindrop_search_params,
    raindrop_to_mcp_search_results,
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


async def get_recent_unsorted(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get recent unsorted bookmarks.
    
    This is a convenience function that retrieves the most recent bookmarks
    from the "Unsorted" collection (collection_id=-1), sorted by creation date 
    in descending order (newest first).

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments containing optional 'limit' parameter

    Returns:
        Recent unsorted bookmarks in MCP format
    """
    limit = arguments.get("limit", 50)
    logger.info(f"Getting {limit} recent unsorted bookmarks")

    # Validate arguments
    validate_mcp_tool_args("get_recent_unsorted", arguments)

    # Build search parameters for unsorted collection
    search_args = {
        "collection_id": -1,  # Unsorted collection
        "sort": "created",    # Sort field
        "order": "desc",      # Newest first (descending order)
        "page": 0,           # First page
        "per_page": min(limit, 50),  # Respect API limits
    }

    # Convert MCP args to Raindrop API params
    params = mcp_to_raindrop_search_params(search_args)

    # Call Raindrop API
    api_response = await client.search_bookmarks(**params)

    # Convert response to MCP format
    mcp_response = raindrop_to_mcp_search_results(
        bookmarks=api_response["items"],
        total=api_response.get("total", 0),
        page=params.get("page", 0),
        per_page=params.get("perpage", 50),
    )

    return {
        "success": True,
        "tool": "get_recent_unsorted",
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
            "pagination": {
                "count": mcp_response.count,
                "total": mcp_response.total,
                "page": mcp_response.page,
                "per_page": mcp_response.per_page,
                "has_more": mcp_response.has_more,
            },
        },
    }
