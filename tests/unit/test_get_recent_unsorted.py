"""Unit tests for get_recent_unsorted functionality."""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from src.tools.bookmarks import get_recent_unsorted
from src.raindrop.models import BookmarkModel, BookmarkType, CollectionModel
from src.utils.transformers import validate_mcp_tool_args
from src.raindrop.schemas import GetRecentUnsortedArgs


class TestGetRecentUnsortedFunction:
    """Test cases for get_recent_unsorted function."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock Raindrop client."""
        client = AsyncMock()
        
        # Mock search_bookmarks response
        client.search_bookmarks.return_value = {
            "items": [
                BookmarkModel(
                    id=123,
                    title="Recent Bookmark 1",
                    link="https://example.com/1",
                    excerpt="First recent bookmark",
                    tags=["recent", "test"],
                    created=datetime.fromisoformat("2023-12-01T12:00:00"),
                    lastUpdate=datetime.fromisoformat("2023-12-01T12:00:00")
                ),
                BookmarkModel(
                    id=124,
                    title="Recent Bookmark 2", 
                    link="https://example.com/2",
                    excerpt="Second recent bookmark",
                    tags=["recent"],
                    created=datetime.fromisoformat("2023-12-01T11:00:00"),
                    lastUpdate=datetime.fromisoformat("2023-12-01T11:00:00")
                )
            ],
            "total": 150,
            "count": 2
        }
        
        return client
    
    @pytest.mark.asyncio
    async def test_get_recent_unsorted_default_limit(self, mock_client):
        """Test get_recent_unsorted with default limit."""
        arguments = {}
        
        result = await get_recent_unsorted(mock_client, arguments)
        
        # Verify client was called with correct parameters
        mock_client.search_bookmarks.assert_called_once()
        call_args = mock_client.search_bookmarks.call_args[1]
        
        assert call_args["collection"] == -1  # Unsorted collection
        assert call_args["sort"] == "-created"  # Newest first (transformed format)
        assert call_args["page"] == 0  # First page
        assert call_args["perpage"] == 50  # Default limit
        
        # Verify response structure
        assert result["success"] is True
        assert result["tool"] == "get_recent_unsorted"
        assert "data" in result
        assert "items" in result["data"]
        assert "pagination" in result["data"]
    
    @pytest.mark.asyncio
    async def test_get_recent_unsorted_custom_limit(self, mock_client):
        """Test get_recent_unsorted with custom limit."""
        arguments = {"limit": 25}
        
        result = await get_recent_unsorted(mock_client, arguments)
        
        # Verify client was called with custom limit
        call_args = mock_client.search_bookmarks.call_args[1]
        assert call_args["perpage"] == 25
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_recent_unsorted_max_limit_enforced(self, mock_client):
        """Test that invalid limit raises error."""
        arguments = {"limit": 100}  # Exceeds max
        
        # Should raise validation error
        with pytest.raises(ValueError, match="limit must be between 1 and 50"):
            await get_recent_unsorted(mock_client, arguments)
    
    @pytest.mark.asyncio
    async def test_get_recent_unsorted_empty_results(self, mock_client):
        """Test get_recent_unsorted with no results."""
        # Mock empty response
        mock_client.search_bookmarks.return_value = {
            "items": [],
            "total": 0,
            "count": 0
        }
        
        arguments = {}
        result = await get_recent_unsorted(mock_client, arguments)
        
        assert result["success"] is True
        assert len(result["data"]["items"]) == 0
        assert result["data"]["pagination"]["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_recent_unsorted_client_error(self, mock_client):
        """Test get_recent_unsorted handles client errors."""
        # Mock client to raise exception
        mock_client.search_bookmarks.side_effect = Exception("API Error")
        
        arguments = {}
        
        with pytest.raises(Exception, match="API Error"):
            await get_recent_unsorted(mock_client, arguments)
    
    @pytest.mark.asyncio
    async def test_get_recent_unsorted_validation_called(self, mock_client):
        """Test that argument validation is called."""
        arguments = {"limit": 25}
        
        # Mock validate_mcp_tool_args to track calls
        with patch('src.tools.bookmarks.validate_mcp_tool_args') as mock_validate:
            await get_recent_unsorted(mock_client, arguments)
            mock_validate.assert_called_once_with("get_recent_unsorted", arguments)


class TestGetRecentUnsortedValidation:
    """Test argument validation for get_recent_unsorted."""
    
    def test_validation_no_args(self):
        """Test validation with no arguments (should pass)."""
        # Should not raise
        validate_mcp_tool_args("get_recent_unsorted", {})
    
    def test_validation_valid_limit(self):
        """Test validation with valid limit."""
        # Should not raise
        validate_mcp_tool_args("get_recent_unsorted", {"limit": 25})
        validate_mcp_tool_args("get_recent_unsorted", {"limit": 1})
        validate_mcp_tool_args("get_recent_unsorted", {"limit": 50})
    
    def test_validation_invalid_limit_too_low(self):
        """Test validation with limit too low."""
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 0})
        
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": -1})
    
    def test_validation_invalid_limit_too_high(self):
        """Test validation with limit too high."""
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 51})
        
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 100})
    
    def test_validation_invalid_limit_type(self):
        """Test validation with invalid limit type."""
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": "25"})
        
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 25.5})
    
    def test_validation_extra_args(self):
        """Test validation ignores extra arguments."""
        # Should not raise, extra args are ignored
        validate_mcp_tool_args("get_recent_unsorted", {
            "limit": 25,
            "extra_arg": "ignored"
        })


class TestGetRecentUnsortedSchema:
    """Test Pydantic schema for get_recent_unsorted."""
    
    def test_schema_default_values(self):
        """Test schema with default values."""
        args = GetRecentUnsortedArgs()
        
        assert args.limit == 50
    
    def test_schema_valid_limit(self):
        """Test schema with valid limit values."""
        args = GetRecentUnsortedArgs(limit=25)
        assert args.limit == 25
        
        args = GetRecentUnsortedArgs(limit=1)
        assert args.limit == 1
        
        args = GetRecentUnsortedArgs(limit=50)
        assert args.limit == 50
    
    def test_schema_invalid_limit_too_low(self):
        """Test schema validation with limit too low."""
        with pytest.raises(ValueError):
            GetRecentUnsortedArgs(limit=0)
        
        with pytest.raises(ValueError):
            GetRecentUnsortedArgs(limit=-1)
    
    def test_schema_invalid_limit_too_high(self):
        """Test schema validation with limit too high."""
        with pytest.raises(ValueError):
            GetRecentUnsortedArgs(limit=51)
        
        with pytest.raises(ValueError):
            GetRecentUnsortedArgs(limit=100)
    
    def test_schema_limit_type_coercion(self):
        """Test schema coerces valid string to int."""
        args = GetRecentUnsortedArgs(limit="25")
        assert args.limit == 25
        assert isinstance(args.limit, int)
    
    def test_schema_invalid_limit_type(self):
        """Test schema validation with invalid limit type."""
        with pytest.raises(ValueError):
            GetRecentUnsortedArgs(limit="invalid")
        
        with pytest.raises(ValueError):
            GetRecentUnsortedArgs(limit=[25])


class TestGetRecentUnsortedIntegration:
    """Integration tests for get_recent_unsorted with real-like data."""
    
    @pytest.fixture
    def realistic_mock_client(self):
        """Create mock client with realistic data."""
        client = AsyncMock()
        
        # Create unsorted collection
        unsorted_collection = CollectionModel(
            id=-1,
            title="Unsorted"  
        )
        
        # Create realistic bookmark data
        bookmarks = []
        for i in range(10):
            bookmarks.append(BookmarkModel(
                id=100 + i,
                title=f"Unsorted Article {i+1}",
                link=f"https://example{i+1}.com/article",
                excerpt=f"This is the excerpt for article {i+1}",
                note=f"Personal note for article {i+1}",
                type=BookmarkType.ARTICLE if i % 2 == 0 else BookmarkType.LINK,
                tags=[f"tag{i}", "unsorted"] if i % 3 == 0 else [],
                domain=f"example{i+1}.com",
                collection=unsorted_collection
            ))
        
        client.search_bookmarks.return_value = {
            "items": bookmarks,
            "total": 150,
            "count": len(bookmarks)
        }
        
        return client
    
    @pytest.mark.asyncio
    async def test_realistic_get_recent_unsorted(self, realistic_mock_client):
        """Test get_recent_unsorted with realistic data."""
        arguments = {"limit": 10}
        
        result = await get_recent_unsorted(realistic_mock_client, arguments)
        
        # Verify basic structure
        assert result["success"] is True
        assert result["tool"] == "get_recent_unsorted"
        
        # Verify items
        items = result["data"]["items"]
        assert len(items) == 10
        
        # Verify first item (most recent)
        first_item = items[0]
        assert first_item["id"] == 100
        assert first_item["title"] == "Unsorted Article 1"
        assert first_item["collection_id"] == -1
        assert first_item["collection_title"] == "Unsorted"
        
        # Verify data completeness
        for item in items:
            assert "id" in item
            assert "title" in item
            assert "url" in item
            assert "excerpt" in item
            assert "note" in item
            assert "type" in item
            assert "tags" in item
            assert "created" in item
            assert "lastUpdate" in item
            assert "domain" in item
            assert "collection_id" in item
            assert "collection_title" in item
        
        # Verify pagination
        pagination = result["data"]["pagination"]
        assert pagination["count"] == 10
        assert pagination["total"] == 150
        assert pagination["page"] == 0
        assert pagination["per_page"] == 10
        assert pagination["has_more"] is True  # Since count < total
    
    @pytest.mark.asyncio
    async def test_verify_unsorted_collection_targeting(self, realistic_mock_client):
        """Test that the function specifically targets the unsorted collection."""
        arguments = {"limit": 5}
        
        await get_recent_unsorted(realistic_mock_client, arguments)
        
        # Verify the search was called with unsorted collection ID
        call_args = realistic_mock_client.search_bookmarks.call_args[1]
        assert call_args["collection"] == -1  # -1 is unsorted collection ID
        assert call_args["sort"] == "-created"  # Newest first
        assert call_args["page"] == 0  # First page only
        assert call_args["perpage"] == 5  # Requested limit
    
    @pytest.mark.asyncio
    async def test_response_format_consistency(self, realistic_mock_client):
        """Test that response format is consistent with search_bookmarks."""
        arguments = {"limit": 3}
        
        result = await get_recent_unsorted(realistic_mock_client, arguments)
        
        # Verify response follows same format as search_bookmarks
        assert "success" in result
        assert "tool" in result
        assert "data" in result
        assert "items" in result["data"]
        assert "pagination" in result["data"]
        
        # Verify pagination structure
        pagination = result["data"]["pagination"]
        required_pagination_fields = ["count", "total", "page", "per_page", "has_more"]
        for field in required_pagination_fields:
            assert field in pagination
        
        # Verify item structure matches bookmark format
        if result["data"]["items"]:
            item = result["data"]["items"][0]
            required_item_fields = [
                "id", "title", "url", "excerpt", "note", "type", 
                "tags", "created", "lastUpdate", "domain", 
                "collection_id", "collection_title"
            ]
            for field in required_item_fields:
                assert field in item