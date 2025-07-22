"""Collection management operations for Raindrop.io."""

from typing import Dict, List, Any
from ..raindrop.client import RaindropClient
from ..utils.transformers import (
    mcp_to_raindrop_create_collection,
    raindrop_to_mcp_collection,
    validate_mcp_tool_args,
)
from ..utils.logging import get_logger


logger = get_logger(__name__)


async def list_collections(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    List all collections.

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments

    Returns:
        Collections list in MCP format
    """
    logger.info(f"Listing collections with args: {arguments}")

    # Validate arguments (optional for this tool)
    validate_mcp_tool_args("list_collections", arguments)

    # Call Raindrop API
    collections = await client.list_collections()

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
        "tool": "list_collections",
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
                    "parent_id": collection.parent_id,
                }
                for collection in mcp_collections
            ],
            "count": len(mcp_collections),
            "sort": {"field": sort_field, "order": sort_order},
        },
    }


async def create_collection(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new collection.

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments

    Returns:
        Created collection in MCP format
    """
    logger.info(f"Creating collection with args: {arguments}")

    # Validate arguments
    validate_mcp_tool_args("create_collection", arguments)

    # Convert MCP args to Raindrop API format
    collection_data = mcp_to_raindrop_create_collection(arguments)

    # Call Raindrop API
    collection = await client.create_collection(collection_data)

    # Convert response to MCP format
    mcp_collection = raindrop_to_mcp_collection(collection)

    return {
        "success": True,
        "tool": "create_collection",
        "data": {
            "id": mcp_collection.id,
            "title": mcp_collection.title,
            "description": mcp_collection.description,
            "public": mcp_collection.public,
            "count": mcp_collection.count,
            "created": mcp_collection.created,
            "lastUpdate": mcp_collection.lastUpdate,
            "parent_id": mcp_collection.parent_id,
        },
    }
