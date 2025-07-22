"""Unit tests for Raindrop.io data models."""

import pytest
from datetime import datetime
from src.raindrop.models import BookmarkModel, CollectionModel, UserModel, BookmarkType, CollectionView


class TestBookmarkModel:
    """Test cases for BookmarkModel."""
    
    def test_bookmark_from_dict_minimal(self):
        """Test creating bookmark from minimal API response."""
        data = {
            "_id": 123,
            "title": "Test Bookmark",
            "link": "https://example.com"
        }
        
        bookmark = BookmarkModel.from_dict(data)
        
        assert bookmark.id == 123
        assert bookmark.title == "Test Bookmark"
        assert bookmark.link == "https://example.com"
        assert bookmark.type == BookmarkType.LINK
        assert bookmark.tags == []
        assert bookmark.excerpt == ""
        assert bookmark.note == ""
    
    def test_bookmark_from_dict_complete(self):
        """Test creating bookmark from complete API response."""
        data = {
            "_id": 456,
            "title": "Complete Bookmark",
            "excerpt": "Test excerpt",
            "note": "Test note",
            "type": "article",
            "cover": "https://example.com/cover.jpg",
            "tags": ["test", "bookmark"],
            "created": "2023-12-01T10:00:00Z",
            "lastUpdate": "2023-12-01T11:00:00Z",
            "domain": "example.com",
            "link": "https://example.com/article",
            "media": [
                {"link": "https://example.com/image.jpg", "type": "image"}
            ],
            "user": {"id": 1, "name": "Test User"},
            "collection": {"_id": 789, "title": "Test Collection"}
        }
        
        bookmark = BookmarkModel.from_dict(data)
        
        assert bookmark.id == 456
        assert bookmark.title == "Complete Bookmark"
        assert bookmark.excerpt == "Test excerpt"
        assert bookmark.note == "Test note"
        assert bookmark.type == BookmarkType.ARTICLE
        assert bookmark.cover == "https://example.com/cover.jpg"
        assert bookmark.tags == ["test", "bookmark"]
        assert bookmark.domain == "example.com"
        assert bookmark.link == "https://example.com/article"
        assert len(bookmark.media) == 1
        assert bookmark.media[0].link == "https://example.com/image.jpg"
        assert bookmark.user.id == 1
        assert bookmark.user.name == "Test User"
    
    def test_bookmark_to_dict(self):
        """Test converting bookmark to dictionary."""
        bookmark = BookmarkModel(
            id=123,
            title="Test Bookmark",
            link="https://example.com",
            tags=["test"]
        )
        
        result = bookmark.to_dict()
        
        assert result["_id"] == 123
        assert result["title"] == "Test Bookmark"
        assert result["link"] == "https://example.com"
        assert result["type"] == "link"
        assert result["tags"] == ["test"]
    
    def test_bookmark_validation_valid(self):
        """Test bookmark validation with valid data."""
        bookmark = BookmarkModel(
            id=123,
            title="Test Bookmark",
            link="https://example.com"
        )
        
        assert bookmark.validate() is True
    
    def test_bookmark_validation_invalid_no_link(self):
        """Test bookmark validation with missing link."""
        bookmark = BookmarkModel(
            id=123,
            title="Test Bookmark",
            link=""
        )
        
        assert bookmark.validate() is False
    
    def test_bookmark_validation_invalid_no_title(self):
        """Test bookmark validation with missing title."""
        bookmark = BookmarkModel(
            id=123,
            title="",
            link="https://example.com"
        )
        
        assert bookmark.validate() is False


class TestCollectionModel:
    """Test cases for CollectionModel."""
    
    def test_collection_from_dict_minimal(self):
        """Test creating collection from minimal API response."""
        data = {
            "_id": 789,
            "title": "Test Collection"
        }
        
        collection = CollectionModel.from_dict(data)
        
        assert collection.id == 789
        assert collection.title == "Test Collection"
        assert collection.description == ""
        assert collection.public is False
        assert collection.view == CollectionView.LIST
        assert collection.count == 0
    
    def test_collection_from_dict_complete(self):
        """Test creating collection from complete API response."""
        data = {
            "_id": 789,
            "title": "Complete Collection",
            "description": "Test description",
            "public": True,
            "view": "grid",
            "count": 25,
            "cover": ["https://example.com/cover1.jpg"],
            "created": "2023-12-01T10:00:00Z",
            "lastUpdate": "2023-12-01T11:00:00Z",
            "expanded": False,
            "sort": 1,
            "user": {"id": 1, "name": "Test User"}
        }
        
        collection = CollectionModel.from_dict(data)
        
        assert collection.id == 789
        assert collection.title == "Complete Collection"
        assert collection.description == "Test description"
        assert collection.public is True
        assert collection.view == CollectionView.GRID
        assert collection.count == 25
        assert collection.cover == ["https://example.com/cover1.jpg"]
        assert collection.expanded is False
        assert collection.sort == 1
        assert collection.user.id == 1
    
    def test_collection_to_dict(self):
        """Test converting collection to dictionary."""
        collection = CollectionModel(
            id=789,
            title="Test Collection",
            description="Test description",
            public=True,
            count=10
        )
        
        result = collection.to_dict()
        
        assert result["_id"] == 789
        assert result["title"] == "Test Collection"
        assert result["description"] == "Test description"
        assert result["public"] is True
        assert result["count"] == 10
        assert result["view"] == "list"


class TestUserModel:
    """Test cases for UserModel."""
    
    def test_user_from_dict_minimal(self):
        """Test creating user from minimal API response."""
        data = {"id": 1}
        
        user = UserModel.from_dict(data)
        
        assert user.id == 1
        assert user.name == ""
        assert user.email == ""
        assert user.registered is None
        assert user.lastAction is None
    
    def test_user_from_dict_complete(self):
        """Test creating user from complete API response."""
        data = {
            "id": 1,
            "name": "Test User",
            "email": "test@example.com",
            "registered": "2023-01-01T00:00:00Z",
            "lastAction": "2023-12-01T10:00:00Z"
        }
        
        user = UserModel.from_dict(data)
        
        assert user.id == 1
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.registered is not None
        assert user.lastAction is not None
    
    def test_datetime_parsing_invalid(self):
        """Test datetime parsing with invalid format."""
        data = {
            "id": 1,
            "registered": "invalid-date"
        }
        
        user = UserModel.from_dict(data)
        
        assert user.id == 1
        assert user.registered is None