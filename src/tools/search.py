"""Search functionality for Raindrop.io bookmarks."""

from typing import Dict, List, Any, Optional
from ..raindrop.client import RaindropClient
from ..utils.transformers import (
    mcp_to_raindrop_search_params,
    raindrop_to_mcp_search_results,
    validate_mcp_tool_args,
)
from ..utils.logging import get_logger


logger = get_logger(__name__)


async def search_bookmarks(
    client: RaindropClient, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Search bookmarks with filters.

    Args:
        client: Raindrop API client
        arguments: MCP tool arguments

    Returns:
        Search results in MCP format
    """
    logger.info(f"Searching bookmarks with args: {arguments}")

    # Validate arguments
    validate_mcp_tool_args("search_bookmarks", arguments)

    # Convert MCP args to Raindrop API params
    params = mcp_to_raindrop_search_params(arguments)

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
        "tool": "search_bookmarks",
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
