"""Data transformation utilities between MCP and Raindrop.io formats."""

import re
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
from ..raindrop.models import BookmarkModel, CollectionModel, BookmarkType
from ..raindrop.schemas import BookmarkResponse, CollectionResponse, SearchResponse


def remove_duplicates_preserve_order(items: List[str]) -> List[str]:
    """Remove duplicates from list while preserving order."""
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def sanitize_tag(tag: str) -> str:
    """Sanitize a tag string."""
    if not isinstance(tag, str):
        return ""

    # Remove special characters and normalize
    tag = re.sub(r"[^\w\s-]", "", tag)
    tag = re.sub(r"\s+", " ", tag).strip()

    # Limit length
    if len(tag) > 50:
        tag = tag[:50]

    return tag.lower()


def validate_url(url: str) -> bool:
    """Validate a URL string."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_collection_id(collection_id: Optional[int]) -> bool:
    """Validate collection ID."""
    if collection_id is None:
        return True
    return isinstance(collection_id, int) and collection_id > 0


def sanitize_text_field(text: Optional[str], max_length: int = 1000) -> str:
    """Sanitize text field with length limit."""
    if not text or not isinstance(text, str):
        return ""

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    return text


def raindrop_to_mcp_bookmark(bookmark: BookmarkModel) -> BookmarkResponse:
    """Convert Raindrop BookmarkModel to MCP BookmarkResponse."""
    return BookmarkResponse.from_bookmark_model(bookmark)


def raindrop_to_mcp_collection(collection: CollectionModel) -> CollectionResponse:
    """Convert Raindrop CollectionModel to MCP CollectionResponse."""
    return CollectionResponse.from_collection_model(collection)


def raindrop_to_mcp_search_results(
    bookmarks: List[BookmarkModel], total: int, page: int, per_page: int
) -> SearchResponse:
    """Convert Raindrop search results to MCP SearchResponse."""
    items = [raindrop_to_mcp_bookmark(bookmark) for bookmark in bookmarks]
    count = len(items)
    has_more = (page + 1) * per_page < total

    return SearchResponse(
        items=items,
        count=count,
        total=total,
        page=page,
        per_page=per_page,
        has_more=has_more,
    )


def mcp_to_raindrop_create_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MCP create_bookmark args to Raindrop API format."""
    data: Dict[str, Any] = {}

    # Required fields
    url = args.get("url")
    if not url:
        raise ValueError("URL is required")

    if not validate_url(str(url)):
        raise ValueError("Invalid URL format")

    data["link"] = str(url)

    # Optional fields
    if "title" in args:
        data["title"] = sanitize_text_field(args["title"], 300)

    if "excerpt" in args:
        data["excerpt"] = sanitize_text_field(args["excerpt"], 1000)

    if "note" in args:
        data["note"] = sanitize_text_field(args["note"], 10000)

    # Tags processing
    if "tags" in args and args["tags"]:
        if isinstance(args["tags"], list):
            sanitized_tags = [sanitize_tag(tag) for tag in args["tags"]]
            # Remove empty tags and duplicates while preserving order
            sanitized_tags = remove_duplicates_preserve_order(sanitized_tags)
            if sanitized_tags:
                data["tags"] = sanitized_tags

    # Collection
    if "collection_id" in args:
        collection_id = args["collection_id"]
        if validate_collection_id(collection_id):
            data["collection"] = {"$id": collection_id}
        else:
            raise ValueError("Invalid collection ID")

    return data


def mcp_to_raindrop_update_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MCP update_bookmark args to Raindrop API format."""
    bookmark_id = args.get("bookmark_id")
    if not bookmark_id or not isinstance(bookmark_id, int):
        raise ValueError("Valid bookmark_id is required")

    data: Dict[str, Any] = {}

    # Optional update fields
    if "title" in args:
        data["title"] = sanitize_text_field(args["title"], 300)

    if "excerpt" in args:
        data["excerpt"] = sanitize_text_field(args["excerpt"], 1000)

    if "note" in args:
        data["note"] = sanitize_text_field(args["note"], 10000)

    # Tags processing
    if "tags" in args:
        if args["tags"] is None:
            data["tags"] = []
        elif isinstance(args["tags"], list):
            sanitized_tags = [sanitize_tag(tag) for tag in args["tags"]]
            # Remove empty tags and duplicates while preserving order
            sanitized_tags = remove_duplicates_preserve_order(sanitized_tags)
            data["tags"] = sanitized_tags

    # Collection
    if "collection_id" in args:
        collection_id = args["collection_id"]
        if collection_id is None:
            data["collection"] = {"$id": 0}  # Move to root
        elif validate_collection_id(collection_id):
            data["collection"] = {"$id": collection_id}
        else:
            raise ValueError("Invalid collection ID")

    return data


def mcp_to_raindrop_search_params(args: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MCP search_bookmarks args to Raindrop API parameters."""
    params: Dict[str, Any] = {}

    # Search query
    if args.get("query"):
        params["search"] = str(args["query"])

    # Collection filter
    if args.get("collection_id"):
        collection_id = args["collection_id"]
        if validate_collection_id(collection_id):
            params["collection"] = collection_id
        else:
            raise ValueError("Invalid collection ID")

    # Type filter
    if args.get("type"):
        bookmark_type = args["type"]
        try:
            # Validate bookmark type
            BookmarkType(bookmark_type)
            params["type"] = bookmark_type
        except ValueError:
            raise ValueError(f"Invalid bookmark type: {bookmark_type}")

    # Tag filter
    if args.get("tag"):
        tag = sanitize_tag(args["tag"])
        if tag:
            params["tag"] = tag

    # Sorting
    sort_field = args.get("sort", "created")
    sort_order = args.get("order", "desc")

    valid_sorts = ["score", "created", "lastUpdate", "title", "domain"]
    if sort_field not in valid_sorts:
        raise ValueError(f"Invalid sort field: {sort_field}")

    if sort_order not in ["asc", "desc"]:
        raise ValueError(f"Invalid sort order: {sort_order}")

    params["sort"] = f"{sort_field}"
    if sort_order == "desc":
        params["sort"] = f"-{sort_field}"

    # Pagination
    page = args.get("page", 0)
    per_page = args.get("per_page", 50)

    if not isinstance(page, int) or page < 0:
        raise ValueError("Page must be a non-negative integer")

    if not isinstance(per_page, int) or per_page < 1 or per_page > 50:
        raise ValueError("Per page must be an integer between 1 and 50")

    params["page"] = page
    params["perpage"] = per_page

    return params


def mcp_to_raindrop_create_collection(args: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MCP create_collection args to Raindrop API format."""
    title = args.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError("Title is required and cannot be empty")

    data: Dict[str, Any] = {"title": sanitize_text_field(title, 100)}

    # Optional fields
    if "description" in args:
        data["description"] = sanitize_text_field(args["description"], 500)

    if "public" in args:
        data["public"] = bool(args["public"])

    if "view" in args:
        view = args["view"]
        valid_views = ["list", "simple", "grid", "masonry"]
        if view not in valid_views:
            raise ValueError(f"Invalid view type: {view}")
        data["view"] = view

    # Parent collection for subcollections
    if "parent_id" in args:
        parent_id = args["parent_id"]
        if validate_collection_id(parent_id):
            data["parent"] = {"$id": parent_id}
        else:
            raise ValueError("Invalid parent collection ID")

    return data


def format_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
    """Format an error for MCP response."""
    error_type = type(error).__name__

    # Determine error code based on exception type
    if isinstance(error, ValueError):
        code = "INVALID_INPUT"
    elif isinstance(error, KeyError):
        code = "MISSING_FIELD"
    elif isinstance(error, PermissionError):
        code = "PERMISSION_DENIED"
    elif "rate limit" in str(error).lower():
        code = "RATE_LIMIT_EXCEEDED"
    elif "not found" in str(error).lower():
        code = "NOT_FOUND"
    elif "unauthorized" in str(error).lower():
        code = "UNAUTHORIZED"
    else:
        code = "INTERNAL_ERROR"

    response = {"error": {"code": code, "message": str(error)}}

    if context:
        response["error"]["context"] = context

    return response


def validate_mcp_tool_args(tool_name: str, args: Dict[str, Any]) -> None:
    """Validate MCP tool arguments."""
    if tool_name == "search_bookmarks":
        # Optional validation - most fields have defaults
        pass

    elif tool_name == "create_bookmark":
        if "url" not in args:
            raise ValueError("URL is required")
        if not validate_url(str(args["url"])):
            raise ValueError("Invalid URL format")

    elif tool_name == "get_bookmark":
        if "bookmark_id" not in args:
            raise ValueError("bookmark_id is required")
        if not isinstance(args["bookmark_id"], int):
            raise ValueError("bookmark_id must be an integer")

    elif tool_name == "update_bookmark":
        if "bookmark_id" not in args:
            raise ValueError("bookmark_id is required")
        if not isinstance(args["bookmark_id"], int):
            raise ValueError("bookmark_id must be an integer")

    elif tool_name == "delete_bookmark":
        if "bookmark_id" not in args:
            raise ValueError("bookmark_id is required")
        if not isinstance(args["bookmark_id"], int):
            raise ValueError("bookmark_id must be an integer")

    elif tool_name == "create_collection":
        if "title" not in args:
            raise ValueError("title is required")
        if not isinstance(args["title"], str) or not args["title"].strip():
            raise ValueError("title must be a non-empty string")
        # Validate parent_id if provided
        if "parent_id" in args and not validate_collection_id(args["parent_id"]):
            raise ValueError("parent_id must be a valid collection ID")
