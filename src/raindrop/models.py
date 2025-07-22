"""Data models for Raindrop.io API responses."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class BookmarkType(Enum):
    """Bookmark type enumeration."""

    LINK = "link"
    ARTICLE = "article"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


class CollectionView(Enum):
    """Collection view enumeration."""

    LIST = "list"
    SIMPLE = "simple"
    GRID = "grid"
    MASONRY = "masonry"


@dataclass
class MediaModel:
    """Media information for a bookmark."""

    link: Optional[str] = None
    type: Optional[str] = None


@dataclass
class UserModel:
    """User information model."""

    id: int
    name: str = ""
    email: str = ""
    registered: Optional[datetime] = None
    lastAction: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserModel":
        """Create UserModel from dictionary data."""
        return cls(
            id=data.get("_id") or data.get("id") or data.get("$id"),  # Handle _id, id, and $id formats
            name=data.get("name", ""),
            email=data.get("email", ""),
            registered=cls._parse_datetime(data.get("registered")),
            lastAction=cls._parse_datetime(data.get("lastAction")),
        )

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None


@dataclass
class CollectionModel:
    """Collection model for Raindrop.io collections."""

    id: int
    title: str
    description: str = ""
    public: bool = False
    view: CollectionView = CollectionView.LIST
    count: int = 0
    cover: Optional[List[str]] = None
    created: Optional[datetime] = None
    lastUpdate: Optional[datetime] = None
    expanded: bool = True
    sort: int = 0
    user: Optional[UserModel] = None
    parent_id: Optional[int] = None

    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.cover is None:
            self.cover = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollectionModel":
        """Create CollectionModel from dictionary data."""
        user_data = data.get("user")
        user = UserModel.from_dict(user_data) if user_data else None

        # Parse parent collection ID
        parent_id = None
        parent_data = data.get("parent")
        if parent_data and isinstance(parent_data, dict):
            parent_id = parent_data.get("$id")

        return cls(
            id=data.get("_id") or data.get("id") or data.get("$id"),  # Handle _id, id, and $id formats
            title=data.get("title", ""),
            description=data.get("description", ""),
            public=data.get("public", False),
            view=CollectionView(data.get("view", "list")),
            count=data.get("count", 0),
            cover=data.get("cover", []),
            created=cls._parse_datetime(data.get("created")),
            lastUpdate=cls._parse_datetime(data.get("lastUpdate")),
            expanded=data.get("expanded", True),
            sort=data.get("sort", 0),
            user=user,
            parent_id=parent_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {
            "_id": self.id,
            "title": self.title,
            "description": self.description,
            "public": self.public,
            "view": self.view.value,
            "count": self.count,
            "cover": self.cover,
            "expanded": self.expanded,
            "sort": self.sort,
        }

        if self.created:
            result["created"] = self.created.isoformat()
        if self.lastUpdate:
            result["lastUpdate"] = self.lastUpdate.isoformat()
        if self.user:
            result["user"] = {
                "id": self.user.id,
                "name": self.user.name,
                "email": self.user.email,
            }
        if self.parent_id:
            result["parent"] = {"$id": self.parent_id}

        return result

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None


@dataclass
class BookmarkModel:
    """Bookmark model for Raindrop.io bookmarks."""

    id: int
    title: str
    excerpt: str = ""
    note: str = ""
    type: BookmarkType = BookmarkType.LINK
    cover: str = ""
    tags: List[str] = field(default_factory=list)
    created: Optional[datetime] = None
    lastUpdate: Optional[datetime] = None
    domain: str = ""
    link: str = ""
    media: Optional[List[MediaModel]] = None
    user: Optional[UserModel] = None
    collection: Optional[CollectionModel] = None

    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.media is None:
            self.media = []
        if not self.tags:
            self.tags = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookmarkModel":
        """Create BookmarkModel from dictionary data."""
        # Parse user data
        user_data = data.get("user")
        user = UserModel.from_dict(user_data) if user_data else None

        # Parse collection data
        collection_data = data.get("collection")
        collection = None
        if collection_data and isinstance(collection_data, dict):
            collection = CollectionModel.from_dict(collection_data)

        # Parse media data
        media_list = []
        media_data = data.get("media", [])
        if isinstance(media_data, list):
            for item in media_data:
                if isinstance(item, dict):
                    media_list.append(
                        MediaModel(link=item.get("link"), type=item.get("type"))
                    )

        # Parse bookmark type
        bookmark_type = BookmarkType.LINK
        type_str = data.get("type", "link")
        try:
            bookmark_type = BookmarkType(type_str)
        except ValueError:
            bookmark_type = BookmarkType.LINK

        return cls(
            id=data["_id"],
            title=data.get("title", ""),
            excerpt=data.get("excerpt", ""),
            note=data.get("note", ""),
            type=bookmark_type,
            cover=data.get("cover", ""),
            tags=data.get("tags", []),
            created=cls._parse_datetime(data.get("created")),
            lastUpdate=cls._parse_datetime(data.get("lastUpdate")),
            domain=data.get("domain", ""),
            link=data.get("link", ""),
            media=media_list,
            user=user,
            collection=collection,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {
            "_id": self.id,
            "title": self.title,
            "excerpt": self.excerpt,
            "note": self.note,
            "type": self.type.value,
            "cover": self.cover,
            "tags": self.tags,
            "domain": self.domain,
            "link": self.link,
        }

        if self.created:
            result["created"] = self.created.isoformat()
        if self.lastUpdate:
            result["lastUpdate"] = self.lastUpdate.isoformat()

        if self.media:
            result["media"] = [{"link": m.link, "type": m.type} for m in self.media]

        if self.user:
            result["user"] = {
                "id": self.user.id,
                "name": self.user.name,
                "email": self.user.email,
            }

        if self.collection:
            result["collection"] = self.collection.to_dict()

        return result

    def validate(self) -> bool:
        """Validate bookmark data."""
        if not self.link:
            return False
        if not self.title:
            return False
        return True

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
