"""Unit tests for data transformers."""

import pytest
from src.utils.transformers import (
    sanitize_tag,
    validate_url,
    validate_collection_id,
    sanitize_text_field,
    mcp_to_raindrop_search_params,
    mcp_to_raindrop_create_bookmark,
    mcp_to_raindrop_update_bookmark,
    mcp_to_raindrop_create_collection,
    validate_mcp_tool_args,
    format_error_response
)


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_sanitize_tag_normal(self):
        """Test tag sanitization with normal input."""
        result = sanitize_tag("Programming")
        assert result == "programming"
    
    def test_sanitize_tag_special_chars(self):
        """Test tag sanitization removes special characters."""
        result = sanitize_tag("Web@Dev#2023!")
        assert result == "webdev2023"
    
    def test_sanitize_tag_whitespace(self):
        """Test tag sanitization normalizes whitespace."""
        result = sanitize_tag("  web   development  ")
        assert result == "web development"
    
    def test_sanitize_tag_too_long(self):
        """Test tag sanitization truncates long tags."""
        long_tag = "a" * 100
        result = sanitize_tag(long_tag)
        assert len(result) == 50
    
    def test_sanitize_tag_non_string(self):
        """Test tag sanitization with non-string input."""
        result = sanitize_tag(123)
        assert result == ""
    
    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://test.org/path") is True
        assert validate_url("https://sub.domain.com/path?query=1") is True
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://example.com") is True  # ftp is valid
        assert validate_url("") is False
        assert validate_url("example.com") is False  # missing scheme
    
    def test_validate_collection_id_valid(self):
        """Test collection ID validation with valid IDs."""
        assert validate_collection_id(1) is True
        assert validate_collection_id(999) is True
        assert validate_collection_id(None) is True  # None is allowed
        assert validate_collection_id(-1) is True  # Unsorted collection
        assert validate_collection_id(-99) is True  # Trash collection
    
    def test_validate_collection_id_invalid(self):
        """Test collection ID validation with invalid IDs."""
        assert validate_collection_id(0) is False
        assert validate_collection_id(-2) is False  # Not a system collection
        assert validate_collection_id(-100) is False  # Not a system collection
        assert validate_collection_id("123") is False
        assert validate_collection_id(1.5) is False
    
    def test_sanitize_text_field_normal(self):
        """Test text field sanitization with normal input."""
        result = sanitize_text_field("Normal text")
        assert result == "Normal text"
    
    def test_sanitize_text_field_whitespace(self):
        """Test text field sanitization normalizes whitespace."""
        result = sanitize_text_field("  Text   with    spaces  ")
        assert result == "Text with spaces"
    
    def test_sanitize_text_field_too_long(self):
        """Test text field sanitization truncates long text."""
        long_text = "a" * 2000
        result = sanitize_text_field(long_text, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_text_field_empty_none(self):
        """Test text field sanitization with empty/None input."""
        assert sanitize_text_field("") == ""
        assert sanitize_text_field(None) == ""
        assert sanitize_text_field(123) == ""


class TestMCPToRaindropTransformers:
    """Test MCP to Raindrop data transformers."""
    
    def test_mcp_to_raindrop_search_params_minimal(self):
        """Test search params transformation with minimal input."""
        args = {}
        result = mcp_to_raindrop_search_params(args)
        
        assert result["sort"] == "-created"  # Default sort (descending)
        assert result["page"] == 0  # Default page
        assert result["perpage"] == 50  # Default per page
    
    def test_mcp_to_raindrop_search_params_complete(self):
        """Test search params transformation with complete input."""
        args = {
            "query": "test query",
            "collection_id": 123,
            "type": "article",
            "tag": "programming",
            "sort": "title",
            "order": "asc",
            "page": 2,
            "per_page": 25
        }
        
        result = mcp_to_raindrop_search_params(args)
        
        assert result["search"] == "test query"
        assert result["collection"] == 123
        assert result["type"] == "article"
        assert result["tag"] == "programming"
        assert result["sort"] == "title"
        assert result["page"] == 2
        assert result["perpage"] == 25
    
    def test_mcp_to_raindrop_search_params_invalid_sort(self):
        """Test search params transformation with invalid sort."""
        args = {"sort": "invalid_sort"}
        
        with pytest.raises(ValueError, match="Invalid sort field"):
            mcp_to_raindrop_search_params(args)
    
    def test_mcp_to_raindrop_create_bookmark_minimal(self):
        """Test bookmark creation transformation with minimal input."""
        args = {"url": "https://example.com"}
        result = mcp_to_raindrop_create_bookmark(args)
        
        assert result["link"] == "https://example.com"
        assert len(result) == 1  # Only link field
    
    def test_mcp_to_raindrop_create_bookmark_complete(self):
        """Test bookmark creation transformation with complete input."""
        args = {
            "url": "https://example.com",
            "title": "Test Title",
            "excerpt": "Test excerpt",
            "note": "Test note",
            "tags": ["tag1", "tag2", "tag1"],  # duplicate tag
            "collection_id": 123
        }
        
        result = mcp_to_raindrop_create_bookmark(args)
        
        assert result["link"] == "https://example.com"
        assert result["title"] == "Test Title"
        assert result["excerpt"] == "Test excerpt"
        assert result["note"] == "Test note"
        assert set(result["tags"]) == {"tag1", "tag2"}  # Duplicates removed
        assert result["collection"] == {"$id": 123}
    
    def test_mcp_to_raindrop_create_bookmark_invalid_url(self):
        """Test bookmark creation transformation with invalid URL."""
        args = {"url": "not-a-url"}
        
        with pytest.raises(ValueError, match="Invalid URL format"):
            mcp_to_raindrop_create_bookmark(args)
    
    def test_mcp_to_raindrop_create_bookmark_missing_url(self):
        """Test bookmark creation transformation with missing URL."""
        args = {"title": "Test"}
        
        with pytest.raises(ValueError, match="URL is required"):
            mcp_to_raindrop_create_bookmark(args)
    
    def test_mcp_to_raindrop_update_bookmark(self):
        """Test bookmark update transformation."""
        args = {
            "bookmark_id": 123,
            "title": "Updated Title",
            "tags": ["new", "tags"],
            "collection_id": None  # Move to root
        }
        
        result = mcp_to_raindrop_update_bookmark(args)
        
        assert result["title"] == "Updated Title"
        assert result["tags"] == ["new", "tags"]
        assert result["collection"] == {"$id": 0}  # Root collection
    
    def test_mcp_to_raindrop_create_collection_minimal(self):
        """Test collection creation transformation with minimal input."""
        args = {"title": "Test Collection"}
        result = mcp_to_raindrop_create_collection(args)
        
        assert result["title"] == "Test Collection"
        assert len(result) == 1
    
    def test_mcp_to_raindrop_create_collection_complete(self):
        """Test collection creation transformation with complete input."""
        args = {
            "title": "Test Collection",
            "description": "Test description",
            "public": True,
            "view": "grid"
        }
        
        result = mcp_to_raindrop_create_collection(args)
        
        assert result["title"] == "Test Collection"
        assert result["description"] == "Test description"
        assert result["public"] is True
        assert result["view"] == "grid"
    
    def test_mcp_to_raindrop_create_collection_invalid_title(self):
        """Test collection creation transformation with invalid title."""
        args = {"title": "   "}  # Only whitespace
        
        with pytest.raises(ValueError, match="Title is required"):
            mcp_to_raindrop_create_collection(args)


class TestMCPToolValidation:
    """Test MCP tool argument validation."""
    
    def test_validate_search_bookmarks(self):
        """Test search_bookmarks validation."""
        # Should not raise for optional args
        validate_mcp_tool_args("search_bookmarks", {})
        validate_mcp_tool_args("search_bookmarks", {"query": "test"})
    
    def test_validate_create_bookmark_valid(self):
        """Test create_bookmark validation with valid args."""
        args = {"url": "https://example.com"}
        validate_mcp_tool_args("create_bookmark", args)
    
    def test_validate_create_bookmark_missing_url(self):
        """Test create_bookmark validation with missing URL."""
        args = {}
        
        with pytest.raises(ValueError, match="URL is required"):
            validate_mcp_tool_args("create_bookmark", args)
    
    def test_validate_create_bookmark_invalid_url(self):
        """Test create_bookmark validation with invalid URL."""
        args = {"url": "not-a-url"}
        
        with pytest.raises(ValueError, match="Invalid URL format"):
            validate_mcp_tool_args("create_bookmark", args)
    
    def test_validate_get_bookmark_valid(self):
        """Test get_bookmark validation with valid args."""
        args = {"bookmark_id": 123}
        validate_mcp_tool_args("get_bookmark", args)
    
    def test_validate_get_bookmark_missing_id(self):
        """Test get_bookmark validation with missing bookmark_id."""
        args = {}
        
        with pytest.raises(ValueError, match="bookmark_id is required"):
            validate_mcp_tool_args("get_bookmark", args)
    
    def test_validate_get_bookmark_invalid_id(self):
        """Test get_bookmark validation with invalid bookmark_id."""
        args = {"bookmark_id": "not-a-number"}
        
        with pytest.raises(ValueError, match="bookmark_id must be an integer"):
            validate_mcp_tool_args("get_bookmark", args)
    
    def test_validate_get_recent_unsorted_valid(self):
        """Test get_recent_unsorted validation with valid args."""
        # Should not raise for no args (uses defaults)
        validate_mcp_tool_args("get_recent_unsorted", {})
        
        # Should not raise for valid limit
        validate_mcp_tool_args("get_recent_unsorted", {"limit": 25})
        validate_mcp_tool_args("get_recent_unsorted", {"limit": 1})
        validate_mcp_tool_args("get_recent_unsorted", {"limit": 50})
    
    def test_validate_get_recent_unsorted_invalid_limit(self):
        """Test get_recent_unsorted validation with invalid limit."""
        # Test limit too low
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 0})
        
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": -1})
        
        # Test limit too high
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 51})
        
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 100})
    
    def test_validate_get_recent_unsorted_invalid_type(self):
        """Test get_recent_unsorted validation with invalid limit type."""
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": "invalid"})
        
        with pytest.raises(ValueError):
            validate_mcp_tool_args("get_recent_unsorted", {"limit": 25.5})


class TestErrorFormatting:
    """Test error response formatting."""
    
    def test_format_error_response_value_error(self):
        """Test error formatting for ValueError."""
        error = ValueError("Invalid input")
        result = format_error_response(error)
        
        assert result["error"]["code"] == "INVALID_INPUT"
        assert result["error"]["message"] == "Invalid input"
    
    def test_format_error_response_key_error(self):
        """Test error formatting for KeyError."""
        error = KeyError("missing_field")
        result = format_error_response(error)
        
        assert result["error"]["code"] == "MISSING_FIELD"
        assert "missing_field" in result["error"]["message"]
    
    def test_format_error_response_with_context(self):
        """Test error formatting with context."""
        error = ValueError("Test error")
        result = format_error_response(error, "Tool: test_tool")
        
        assert result["error"]["code"] == "INVALID_INPUT"
        assert result["error"]["message"] == "Test error"
        assert result["error"]["context"] == "Tool: test_tool"
    
    def test_format_error_response_rate_limit(self):
        """Test error formatting for rate limit errors."""
        error = Exception("Rate limit exceeded")
        result = format_error_response(error)
        
        assert result["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "rate limit" in result["error"]["message"].lower()
    
    def test_format_error_response_not_found(self):
        """Test error formatting for not found errors."""
        error = Exception("Resource not found")
        result = format_error_response(error)
        
        assert result["error"]["code"] == "NOT_FOUND"
        assert "not found" in result["error"]["message"].lower()
    
    def test_format_error_response_unauthorized(self):
        """Test error formatting for unauthorized errors."""
        error = Exception("Unauthorized access")
        result = format_error_response(error)
        
        assert result["error"]["code"] == "UNAUTHORIZED"
        assert "unauthorized" in result["error"]["message"].lower()
    
    def test_format_error_response_generic(self):
        """Test error formatting for generic errors."""
        error = RuntimeError("Something went wrong")
        result = format_error_response(error)
        
        assert result["error"]["code"] == "INTERNAL_ERROR"
        assert result["error"]["message"] == "Something went wrong"