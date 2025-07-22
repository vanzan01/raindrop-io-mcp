"""MCP protocol schemas for Raindrop.io operations."""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pydantic import BaseModel, Field, HttpUrl, field_validator
from enum import Enum


class SortOrder(Enum):
    """Sort order options."""

    ASC = "asc"
    DESC = "desc"


class SearchSort(Enum):
    """Search sort options."""

    SCORE = "score"
    CREATED = "created"
    LAST_UPDATE = "lastUpdate"
    TITLE = "title"
    DOMAIN = "domain"


class BookmarkType(Enum):
    """Bookmark type enumeration."""

    LINK = "link"
    ARTICLE = "article"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


# Tool argument schemas
class SearchBookmarksArgs(BaseModel):
    """Arguments for search_bookmarks tool."""

    query: Optional[str] = Field(None, description="Search query string")
    collection_id: Optional[int] = Field(
        None, description="Collection ID to search within"
    )
    type: Optional[str] = Field(None, description="Bookmark type filter")
    tag: Optional[str] = Field(None, description="Tag filter")
    sort: Optional[str] = Field("created", description="Sort field")
    order: Optional[str] = Field("desc", description="Sort order (asc/desc)")
    page: Optional[int] = Field(0, ge=0, description="Page number (0-based)")
    per_page: Optional[int] = Field(50, ge=1, le=50, description="Items per page")

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort field."""
        valid_sorts = ["score", "created", "lastUpdate", "title", "domain"]
        if v and v not in valid_sorts:
            raise ValueError(f"Sort must be one of: {', '.join(valid_sorts)}")
        return v

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort order."""
        if v and v.lower() not in ["asc", "desc"]:
            raise ValueError("Order must be 'asc' or 'desc'")
        return v.lower() if v else v


class CreateBookmarkArgs(BaseModel):
    """Arguments for create_bookmark tool."""

    url: HttpUrl = Field(..., description="Bookmark URL")
    title: Optional[str] = Field(None, max_length=300, description="Bookmark title")
    excerpt: Optional[str] = Field(
        None, max_length=1000, description="Bookmark excerpt"
    )
    note: Optional[str] = Field(None, max_length=10000, description="Personal note")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    collection_id: Optional[int] = Field(None, description="Collection ID")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags list."""
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("Maximum 50 tags allowed")
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            if len(tag) > 50:
                raise ValueError("Tag length cannot exceed 50 characters")
        return v


class UpdateBookmarkArgs(BaseModel):
    """Arguments for update_bookmark tool."""

    bookmark_id: int = Field(..., description="Bookmark ID to update")
    title: Optional[str] = Field(None, max_length=300, description="New title")
    excerpt: Optional[str] = Field(None, max_length=1000, description="New excerpt")
    note: Optional[str] = Field(None, max_length=10000, description="New note")
    tags: Optional[List[str]] = Field(None, description="New tags list")
    collection_id: Optional[int] = Field(None, description="New collection ID")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags list."""
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("Maximum 50 tags allowed")
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            if len(tag) > 50:
                raise ValueError("Tag length cannot exceed 50 characters")
        return v


class GetBookmarkArgs(BaseModel):
    """Arguments for get_bookmark tool."""

    bookmark_id: int = Field(..., description="Bookmark ID to retrieve")


class DeleteBookmarkArgs(BaseModel):
    """Arguments for delete_bookmark tool."""

    bookmark_id: int = Field(..., description="Bookmark ID to delete")


class ListCollectionsArgs(BaseModel):
    """Arguments for list_collections tool."""

    sort: Optional[str] = Field("title", description="Sort field")
    order: Optional[str] = Field("asc", description="Sort order")

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort field."""
        valid_sorts = ["title", "count", "created", "lastUpdate"]
        if v and v not in valid_sorts:
            raise ValueError(f"Sort must be one of: {', '.join(valid_sorts)}")
        return v

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort order."""
        if v and v.lower() not in ["asc", "desc"]:
            raise ValueError("Order must be 'asc' or 'desc'")
        return v.lower() if v else v


class CreateCollectionArgs(BaseModel):
    """Arguments for create_collection tool."""

    title: str = Field(
        ..., min_length=1, max_length=100, description="Collection title"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Collection description"
    )
    public: Optional[bool] = Field(False, description="Make collection public")
    view: Optional[str] = Field("list", description="Collection view type")

    @field_validator("view")
    @classmethod
    def validate_view(cls, v: Optional[str]) -> Optional[str]:
        """Validate view type."""
        valid_views = ["list", "simple", "grid", "masonry"]
        if v and v not in valid_views:
            raise ValueError(f"View must be one of: {', '.join(valid_views)}")
        return v


# Response schemas
@dataclass
class BookmarkResponse:
    """MCP response for bookmark data."""

    id: int
    title: str
    url: str
    excerpt: str
    note: str
    type: str
    tags: List[str]
    created: Optional[str]
    lastUpdate: Optional[str]
    domain: str
    collection_id: Optional[int]
    collection_title: Optional[str]

    @classmethod
    def from_bookmark_model(cls, bookmark: Any) -> "BookmarkResponse":
        """Create response from BookmarkModel."""
        return cls(
            id=bookmark.id,
            title=bookmark.title,
            url=bookmark.link,
            excerpt=bookmark.excerpt,
            note=bookmark.note,
            type=bookmark.type.value,
            tags=bookmark.tags,
            created=bookmark.created.isoformat() if bookmark.created else None,
            lastUpdate=bookmark.lastUpdate.isoformat() if bookmark.lastUpdate else None,
            domain=bookmark.domain,
            collection_id=bookmark.collection.id if bookmark.collection else None,
            collection_title=bookmark.collection.title if bookmark.collection else None,
        )


@dataclass
class CollectionResponse:
    """MCP response for collection data."""

    id: int
    title: str
    description: str
    public: bool
    count: int
    created: Optional[str]
    lastUpdate: Optional[str]

    @classmethod
    def from_collection_model(cls, collection: Any) -> "CollectionResponse":
        """Create response from CollectionModel."""
        return cls(
            id=collection.id,
            title=collection.title,
            description=collection.description,
            public=collection.public,
            count=collection.count,
            created=collection.created.isoformat() if collection.created else None,
            lastUpdate=(
                collection.lastUpdate.isoformat() if collection.lastUpdate else None
            ),
        )


@dataclass
class SearchResponse:
    """MCP response for search results."""

    items: List[BookmarkResponse]
    count: int
    total: int
    page: int
    per_page: int
    has_more: bool


@dataclass
class ErrorResponse:
    """MCP error response."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# MCP tool definitions
MCP_TOOLS = {
    "search_bookmarks": {
        "description": "Search bookmarks with optional filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"},
                "collection_id": {
                    "type": "integer",
                    "description": "Collection ID to search within",
                },
                "type": {
                    "type": "string",
                    "description": "Bookmark type filter (link, article, image, video, document, audio)",
                },
                "tag": {"type": "string", "description": "Tag filter"},
                "sort": {
                    "type": "string",
                    "enum": ["score", "created", "lastUpdate", "title", "domain"],
                    "default": "created",
                    "description": "Sort field",
                },
                "order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "default": "desc",
                    "description": "Sort order",
                },
                "page": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Page number (0-based)",
                },
                "per_page": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 50,
                    "description": "Items per page",
                },
            },
        },
    },
    "create_bookmark": {
        "description": "Create a new bookmark",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Bookmark URL",
                },
                "title": {
                    "type": "string",
                    "maxLength": 300,
                    "description": "Bookmark title",
                },
                "excerpt": {
                    "type": "string",
                    "maxLength": 1000,
                    "description": "Bookmark excerpt",
                },
                "note": {
                    "type": "string",
                    "maxLength": 10000,
                    "description": "Personal note",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 50,
                    "description": "List of tags",
                },
                "collection_id": {"type": "integer", "description": "Collection ID"},
            },
            "required": ["url"],
        },
    },
    "get_bookmark": {
        "description": "Get bookmark details by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bookmark_id": {"type": "integer", "description": "Bookmark ID"}
            },
            "required": ["bookmark_id"],
        },
    },
    "update_bookmark": {
        "description": "Update an existing bookmark",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bookmark_id": {
                    "type": "integer",
                    "description": "Bookmark ID to update",
                },
                "title": {
                    "type": "string",
                    "maxLength": 300,
                    "description": "New title",
                },
                "excerpt": {
                    "type": "string",
                    "maxLength": 1000,
                    "description": "New excerpt",
                },
                "note": {
                    "type": "string",
                    "maxLength": 10000,
                    "description": "New note",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 50,
                    "description": "New tags list",
                },
                "collection_id": {
                    "type": "integer",
                    "description": "New collection ID",
                },
            },
            "required": ["bookmark_id"],
        },
    },
    "delete_bookmark": {
        "description": "Delete a bookmark",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bookmark_id": {
                    "type": "integer",
                    "description": "Bookmark ID to delete",
                }
            },
            "required": ["bookmark_id"],
        },
    },
    "list_collections": {
        "description": "List all collections",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sort": {
                    "type": "string",
                    "enum": ["title", "count", "created", "lastUpdate"],
                    "default": "title",
                    "description": "Sort field",
                },
                "order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "default": "asc",
                    "description": "Sort order",
                },
            },
        },
    },
    "create_collection": {
        "description": "Create a new collection",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Collection title",
                },
                "description": {
                    "type": "string",
                    "maxLength": 500,
                    "description": "Collection description",
                },
                "public": {
                    "type": "boolean",
                    "default": False,
                    "description": "Make collection public",
                },
                "view": {
                    "type": "string",
                    "enum": ["list", "simple", "grid", "masonry"],
                    "default": "list",
                    "description": "Collection view type",
                },
            },
            "required": ["title"],
        },
    },
}
