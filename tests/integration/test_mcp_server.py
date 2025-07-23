"""Integration tests for MCP server."""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from src.raindrop.server import RaindropMCPServer
from src.raindrop.models import BookmarkModel, CollectionModel, UserModel


class TestRaindropMCPServer:
    """Integration tests for RaindropMCPServer."""
    
    @pytest.fixture
    def mock_raindrop_client(self):
        """Create mock Raindrop client."""
        client = AsyncMock()
        
        # Mock user data
        client.get_user.return_value = UserModel(
            id=1,
            name="Test User",
            email="test@example.com"
        )
        
        # Mock search results
        client.search_bookmarks.return_value = {
            "items": [
                BookmarkModel(
                    id=123,
                    title="Test Bookmark",
                    link="https://example.com",
                    excerpt="Test excerpt",
                    tags=["test"]
                )
            ],
            "total": 1,
            "count": 1
        }
        
        # Mock bookmark operations
        client.get_bookmark.return_value = BookmarkModel(
            id=123,
            title="Test Bookmark",
            link="https://example.com"
        )
        
        client.create_bookmark.return_value = BookmarkModel(
            id=124,
            title="New Bookmark",
            link="https://new.example.com"
        )
        
        client.update_bookmark.return_value = BookmarkModel(
            id=123,
            title="Updated Bookmark",
            link="https://example.com"
        )
        
        client.delete_bookmark.return_value = True
        
        # Mock collections
        client.list_collections.return_value = [
            CollectionModel(
                id=1,
                title="Test Collection",
                description="Test description",
                count=5
            )
        ]
        
        client.create_collection.return_value = CollectionModel(
            id=2,
            title="New Collection",
            description="New description"
        )
        
        return client
    
    @pytest_asyncio.fixture
    async def server(self, mock_raindrop_client):
        """Create MCP server with mocked dependencies."""
        server_instance = None
        patches = []
        
        try:
            # Create and start patches
            mock_auth_patch = patch('src.raindrop.server.AuthenticationManager')
            mock_rate_limiter_patch = patch('src.raindrop.server.RateLimiter')
            mock_client_patch = patch('src.raindrop.server.RaindropClient')
            
            patches = [mock_auth_patch, mock_rate_limiter_patch, mock_client_patch]
            mock_auth = mock_auth_patch.start()
            mock_rate_limiter = mock_rate_limiter_patch.start()  
            mock_client_class = mock_client_patch.start()
            
            # Setup mocks
            mock_auth_instance = AsyncMock()
            mock_auth.return_value = mock_auth_instance
            
            mock_rate_limiter_instance = AsyncMock()
            mock_rate_limiter.return_value = mock_rate_limiter_instance
            
            mock_client_class.return_value = mock_raindrop_client
            
            server_instance = RaindropMCPServer()
            await server_instance.initialize()
            
            yield server_instance
            
        finally:
            # Cleanup
            if server_instance:
                try:
                    await server_instance.cleanup()
                except Exception:
                    pass  # Ignore cleanup errors in tests
            
            # Stop all patches
            for p in patches:
                try:
                    p.stop()
                except Exception:
                    pass  # Ignore patch stop errors
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initialization process."""
        with patch('src.raindrop.server.AuthenticationManager') as mock_auth, \
             patch('src.raindrop.server.RateLimiter') as mock_rate_limiter, \
             patch('src.raindrop.server.RaindropClient') as mock_client:
            
            mock_auth_instance = AsyncMock()
            mock_auth.return_value = mock_auth_instance
            
            mock_rate_limiter_instance = AsyncMock()
            mock_rate_limiter.return_value = mock_rate_limiter_instance
            
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            server = RaindropMCPServer()
            await server.initialize()
            
            # Verify initialization calls
            mock_auth_instance.initialize.assert_called_once()
            mock_rate_limiter_instance.start.assert_called_once()
            mock_client_instance.initialize.assert_called_once()
            
            await server.cleanup()
    
    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test listing available tools."""
        tools = await server._list_tools()
        
        assert len(tools) > 0
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "search_bookmarks",
            "create_bookmark", 
            "get_bookmark",
            "update_bookmark",
            "delete_bookmark",
            "list_collections",
            "create_collection",
            "get_recent_unsorted"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
        
        # Verify tool schema structure
        search_tool = next(tool for tool in tools if tool.name == "search_bookmarks")
        assert search_tool.description is not None
        assert search_tool.inputSchema is not None
    
    @pytest.mark.asyncio
    async def test_search_bookmarks_tool(self, server):
        """Test search_bookmarks tool execution."""
        arguments = {
            "query": "test",
            "page": 0,
            "per_page": 10
        }
        
        result = await server._call_tool("search_bookmarks", arguments)
        
        assert len(result) == 1
        assert result[0].type == "text"
        
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert "data" in response_data
        assert "items" in response_data["data"]
        assert len(response_data["data"]["items"]) == 1
    
    @pytest.mark.asyncio
    async def test_create_bookmark_tool(self, server):
        """Test create_bookmark tool execution."""
        arguments = {
            "url": "https://test.example.com",
            "title": "Test Bookmark",
            "tags": ["test", "bookmark"]
        }
        
        result = await server._call_tool("create_bookmark", arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["id"] == 124
        assert response_data["data"]["title"] == "New Bookmark"
    
    @pytest.mark.asyncio
    async def test_get_bookmark_tool(self, server):
        """Test get_bookmark tool execution."""
        arguments = {"bookmark_id": 123}
        
        result = await server._call_tool("get_bookmark", arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["id"] == 123
    
    @pytest.mark.asyncio
    async def test_update_bookmark_tool(self, server):
        """Test update_bookmark tool execution."""
        arguments = {
            "bookmark_id": 123,
            "title": "Updated Title",
            "tags": ["updated"]
        }
        
        result = await server._call_tool("update_bookmark", arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["title"] == "Updated Bookmark"
    
    @pytest.mark.asyncio
    async def test_delete_bookmark_tool(self, server):
        """Test delete_bookmark tool execution."""
        arguments = {"bookmark_id": 123}
        
        result = await server._call_tool("delete_bookmark", arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["deleted"] is True
    
    @pytest.mark.asyncio
    async def test_list_collections_tool(self, server):
        """Test list_collections tool execution."""
        arguments = {"sort": "title", "order": "asc"}
        
        result = await server._call_tool("list_collections", arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert len(response_data["data"]["collections"]) == 1
        assert response_data["data"]["collections"][0]["title"] == "Test Collection"
    
    @pytest.mark.asyncio
    async def test_create_collection_tool(self, server):
        """Test create_collection tool execution."""
        arguments = {
            "title": "New Collection",
            "description": "New collection description"
        }
        
        result = await server._call_tool("create_collection", arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["id"] == 2
        assert response_data["data"]["title"] == "New Collection"
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self, server):
        """Test tool error handling."""
        # Test with invalid tool name
        result = await server._call_tool("invalid_tool", {})
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert "error" in response_data
        assert response_data["error"]["code"] in ["INTERNAL_ERROR", "INVALID_INPUT"]
    
    @pytest.mark.asyncio
    async def test_tool_validation_error(self, server):
        """Test tool argument validation error."""
        # Test create_bookmark without required URL
        result = await server._call_tool("create_bookmark", {})
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert "error" in response_data
    
    @pytest.mark.asyncio
    async def test_server_capabilities(self, server):
        """Test server capabilities."""
        capabilities = server.get_capabilities()
        
        assert "tools" in capabilities
        assert capabilities["tools"]["listChanged"] is True
        assert "logging" in capabilities
    
    @pytest.mark.asyncio
    async def test_server_cleanup(self, server):
        """Test server cleanup process."""
        # Server cleanup is handled by fixture, just verify it doesn't raise
        await server.cleanup()
        
        # Multiple cleanup calls should be safe
        await server.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_recent_unsorted_tool(self, server):
        """Test get_recent_unsorted tool execution."""
        arguments = {"limit": 25}
        
        result = await server._call_tool("get_recent_unsorted", arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert "data" in response_data
        assert "items" in response_data["data"]
        assert "pagination" in response_data["data"]
    
    @pytest.mark.asyncio
    async def test_uninitialized_server_error(self):
        """Test error when calling tools on uninitialized server."""
        server = RaindropMCPServer()
        
        result = await server._call_tool("search_bookmarks", {})
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert "error" in response_data