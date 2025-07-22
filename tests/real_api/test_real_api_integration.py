"""
Real API Integration Tests for Raindrop.io MCP Server.

These tests make actual API calls to Raindrop.io using your real API token.
They validate end-to-end functionality with live data.

IMPORTANT: These tests will interact with your real Raindrop.io account.
Run with caution and ensure you have a test collection for cleanup.
"""

import pytest
import pytest_asyncio
import asyncio
import os
from typing import List, Optional
from src.raindrop.client import RaindropClient
from src.raindrop.auth import AuthenticationManager
from src.raindrop.models import BookmarkModel, CollectionModel, UserModel
from src.raindrop_mcp.server import RaindropMCPServer
from src.utils.config import Config


@pytest.mark.real_api
class TestRealAPIIntegration:
    """Real API integration tests using actual Raindrop.io API calls."""
    
    @pytest_asyncio.fixture
    async def real_client(self):
        """Create real Raindrop client with actual API connection."""
        if not Config.RAINDROP_API_TOKEN:
            pytest.skip("RAINDROP_API_TOKEN not configured for real API tests")
        
        client = RaindropClient()
        await client.initialize()
        yield client
        await client.cleanup()
    
    @pytest_asyncio.fixture
    async def real_auth_manager(self):
        """Create real authentication manager."""
        if not Config.RAINDROP_API_TOKEN:
            pytest.skip("RAINDROP_API_TOKEN not configured for real API tests")
        
        auth_manager = AuthenticationManager()
        await auth_manager.initialize()
        yield auth_manager
    
    @pytest_asyncio.fixture
    async def test_collection_id(self, real_client):
        """Create a test collection for safe testing and cleanup."""
        # Create test collection
        collection_data = {
            "title": "MCP_TEST_COLLECTION",
            "description": "Temporary collection for MCP server testing - safe to delete"
        }
        
        collection = await real_client.create_collection(collection_data)
        collection_id = collection.id
        
        yield collection_id
        
        # Cleanup: Delete test collection
        try:
            await real_client.delete_collection(collection_id)
        except Exception as e:
            print(f"Warning: Failed to cleanup test collection {collection_id}: {e}")
    
    @pytest.mark.asyncio
    async def test_real_authentication(self, real_auth_manager):
        """Test real API token authentication."""
        # Verify authentication is successful
        assert real_auth_manager.is_authenticated
        
        # Test health check
        health = await real_auth_manager.health_check()
        assert health["authenticated"] is True
        assert health["token_configured"] is True
        assert health["token_valid"] is True
        
        # Test auth headers
        headers = real_auth_manager.get_auth_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert "Content-Type" in headers
    
    @pytest.mark.asyncio
    async def test_real_user_data_retrieval(self, real_client):
        """Test retrieving real user data from API."""
        user = await real_client.get_user()
        
        # Validate user data structure
        assert isinstance(user, UserModel)
        assert user.id is not None
        assert user.email is not None
        assert user.name is not None
        
        # Validate against expected real data (from our earlier API test)
        assert user.email == "vanzan.1250@gmail.com"
        assert user.name == "vanzan-1250"
        assert user.id == 3936337
        
        print(f"[SUCCESS] Real user data validated: {user.name} ({user.email})")
    
    @pytest.mark.asyncio
    async def test_real_collections_listing(self, real_client):
        """Test listing real collections from API."""
        collections = await real_client.list_collections()
        
        # Should have collections (based on earlier API response)
        assert isinstance(collections, list)
        assert len(collections) > 0
        
        # Validate collection structure
        for collection in collections[:3]:  # Check first 3 collections
            assert isinstance(collection, CollectionModel)
            assert collection.id is not None
            assert collection.title is not None
            assert hasattr(collection, 'count')
        
        # Look for known collections from earlier API response
        collection_ids = [c.id for c in collections]
        expected_ids = [52950929, 53876058, 53697120, 54399446, 52902089, 52915706]
        
        # At least some expected collections should exist
        found_collections = [cid for cid in expected_ids if cid in collection_ids]
        assert len(found_collections) > 0, f"Expected collections not found. Got: {collection_ids[:5]}"
        
        print(f"[SUCCESS] Found {len(collections)} real collections")
    
    @pytest.mark.asyncio
    async def test_real_bookmark_search(self, real_client):
        """Test searching real bookmarks from API."""
        # Search without filters (get recent bookmarks)
        search_params = {
            "page": 0,
            "perpage": 10,
            "sort": "-created"  # Most recent first
        }
        
        results = await real_client.search_bookmarks(**search_params)
        
        # Validate search results structure
        assert "items" in results
        assert "count" in results  # API returns "count" as total bookmarks
        
        items = results["items"]
        total_bookmarks = results["count"]  # This is the total count from API
        items_returned = len(items)  # This is items actually returned in this page
        
        # Should have some bookmarks in a real account
        assert isinstance(items, list)
        assert isinstance(total_bookmarks, int)
        assert total_bookmarks >= 0
        assert items_returned >= 0
        assert items_returned <= 10  # We requested perpage=10
        
        # Validate bookmark structure if any exist
        if len(items) > 0:
            bookmark = items[0]
            assert isinstance(bookmark, BookmarkModel)
            assert bookmark.id is not None
            assert bookmark.link is not None
            assert bookmark.title is not None
        
        print(f"[SUCCESS] Found {total_bookmarks} total bookmarks, retrieved {items_returned} in this page")
    
    @pytest.mark.asyncio
    async def test_real_bookmark_crud_operations(self, real_client, test_collection_id):
        """Test real bookmark CRUD operations with cleanup."""
        created_bookmark_id = None
        
        try:
            # 1. CREATE: Create a test bookmark in test collection
            bookmark_data = {
                "link": "https://example.com/mcp-test",
                "title": "MCP Test Bookmark",
                "excerpt": "Test bookmark created by MCP server integration tests",
                "tags": ["mcp-test", "integration-test"],
                "collection": {"$id": test_collection_id}
            }
            
            created_bookmark = await real_client.create_bookmark(bookmark_data)
            created_bookmark_id = created_bookmark.id
            
            # Validate creation
            assert isinstance(created_bookmark, BookmarkModel)
            assert created_bookmark.id is not None
            assert created_bookmark.title == "MCP Test Bookmark"
            assert created_bookmark.link == "https://example.com/mcp-test"
            
            print(f"✅ Created bookmark with ID: {created_bookmark_id}")
            
            # 2. READ: Retrieve the created bookmark
            retrieved_bookmark = await real_client.get_bookmark(created_bookmark_id)
            
            # Validate retrieval
            assert retrieved_bookmark.id == created_bookmark_id
            assert retrieved_bookmark.title == "MCP Test Bookmark"
            assert retrieved_bookmark.link == "https://example.com/mcp-test"
            
            print(f"✅ Retrieved bookmark: {retrieved_bookmark.title}")
            
            # 3. UPDATE: Update the bookmark
            update_data = {
                "title": "Updated MCP Test Bookmark",
                "excerpt": "Updated excerpt for integration testing",
                "tags": ["mcp-test", "integration-test", "updated"]
            }
            
            updated_bookmark = await real_client.update_bookmark(created_bookmark_id, update_data)
            
            # Validate update
            assert updated_bookmark.id == created_bookmark_id
            assert updated_bookmark.title == "Updated MCP Test Bookmark"
            assert "updated" in updated_bookmark.tags
            
            print(f"✅ Updated bookmark: {updated_bookmark.title}")
            
            # 4. DELETE: Delete the test bookmark
            delete_result = await real_client.delete_bookmark(created_bookmark_id)
            
            # Validate deletion
            assert delete_result is True
            
            print(f"✅ Deleted bookmark with ID: {created_bookmark_id}")
            created_bookmark_id = None  # Mark as cleaned up
            
            # 5. VERIFY DELETION: Try to retrieve deleted bookmark (should fail)
            with pytest.raises(Exception):  # Should raise NotFoundError or similar
                await real_client.get_bookmark(created_bookmark_id)
            
            print("✅ Confirmed bookmark deletion")
            
        except Exception as e:
            # Ensure cleanup even if test fails
            if created_bookmark_id:
                try:
                    await real_client.delete_bookmark(created_bookmark_id)
                    print(f"🧹 Cleanup: Deleted bookmark {created_bookmark_id}")
                except Exception:
                    print(f"⚠️  Failed to cleanup bookmark {created_bookmark_id}")
            raise e
    
    @pytest.mark.asyncio
    async def test_real_collection_creation_and_cleanup(self, real_client):
        """Test real collection creation and deletion."""
        collection_id = None
        
        try:
            # Create test collection
            collection_data = {
                "title": "MCP Test Collection 2",
                "description": "Another test collection for validation",
                "public": False
            }
            
            created_collection = await real_client.create_collection(collection_data)
            collection_id = created_collection.id
            
            # Validate creation
            assert isinstance(created_collection, CollectionModel)
            assert created_collection.id is not None
            assert created_collection.title == "MCP Test Collection 2"
            
            print(f"✅ Created collection: {created_collection.title} (ID: {collection_id})")
            
            # Delete the collection
            delete_result = await real_client.delete_collection(collection_id)
            assert delete_result is True
            
            print(f"✅ Deleted collection with ID: {collection_id}")
            collection_id = None  # Mark as cleaned up
            
        except Exception as e:
            # Ensure cleanup even if test fails
            if collection_id:
                try:
                    await real_client.delete_collection(collection_id)
                    print(f"🧹 Cleanup: Deleted collection {collection_id}")
                except Exception:
                    print(f"⚠️  Failed to cleanup collection {collection_id}")
            raise e
    
    @pytest.mark.asyncio
    async def test_real_mcp_server_integration(self, test_collection_id):
        """Test real MCP server with actual API calls (no mocking)."""
        if not Config.RAINDROP_API_TOKEN:
            pytest.skip("RAINDROP_API_TOKEN not configured for real API tests")
        
        server = None
        created_bookmark_id = None
        
        try:
            # Initialize real server (no mocking)
            server = RaindropMCPServer()
            await server.initialize()
            
            # Test list_tools
            tools = await server._list_tools()
            tool_names = [tool.name for tool in tools]
            
            expected_tools = [
                "search_bookmarks", "create_bookmark", "get_bookmark", 
                "update_bookmark", "delete_bookmark", "list_collections", 
                "create_collection"
            ]
            
            for expected_tool in expected_tools:
                assert expected_tool in tool_names
            
            # Test real bookmark creation through MCP
            create_args = {
                "url": "https://example.com/mcp-server-test",
                "title": "MCP Server Integration Test",
                "tags": ["mcp-server", "real-test"],
                "collection_id": test_collection_id
            }
            
            create_result = await server._call_tool("create_bookmark", create_args)
            assert len(create_result) == 1
            
            import json
            response_data = json.loads(create_result[0].text)
            assert response_data["success"] is True
            created_bookmark_id = response_data["data"]["id"]
            
            print(f"✅ MCP server created bookmark: {created_bookmark_id}")
            
            # Test real bookmark retrieval through MCP
            get_args = {"bookmark_id": created_bookmark_id}
            get_result = await server._call_tool("get_bookmark", get_args)
            
            response_data = json.loads(get_result[0].text)
            assert response_data["success"] is True
            assert response_data["data"]["id"] == created_bookmark_id
            assert response_data["data"]["title"] == "MCP Server Integration Test"
            
            print(f"✅ MCP server retrieved bookmark: {response_data['data']['title']}")
            
            # Test real bookmark deletion through MCP
            delete_args = {"bookmark_id": created_bookmark_id}
            delete_result = await server._call_tool("delete_bookmark", delete_args)
            
            response_data = json.loads(delete_result[0].text)
            assert response_data["success"] is True
            
            print(f"✅ MCP server deleted bookmark: {created_bookmark_id}")
            created_bookmark_id = None  # Mark as cleaned up
            
        except Exception as e:
            # Cleanup
            if created_bookmark_id and server:
                try:
                    delete_args = {"bookmark_id": created_bookmark_id}
                    await server._call_tool("delete_bookmark", delete_args)
                    print(f"🧹 Cleanup: Deleted bookmark {created_bookmark_id}")
                except Exception:
                    print(f"⚠️  Failed to cleanup bookmark {created_bookmark_id}")
            raise e
        finally:
            if server:
                await server.cleanup()


@pytest.mark.real_api
@pytest.mark.asyncio
async def test_real_api_rate_limiting():
    """Test that rate limiting works with real API calls."""
    if not Config.RAINDROP_API_TOKEN:
        pytest.skip("RAINDROP_API_TOKEN not configured for real API tests")
    
    client = RaindropClient()
    await client.initialize()
    
    try:
        # Make multiple rapid API calls to test rate limiting
        tasks = []
        for i in range(5):
            task = asyncio.create_task(client.get_user())
            tasks.append(task)
        
        # All should succeed due to rate limiting
        results = await asyncio.gather(*tasks)
        
        # Validate all results
        for result in results:
            assert isinstance(result, UserModel)
            assert result.email == "vanzan.1250@gmail.com"
        
        print("✅ Rate limiting handled multiple concurrent API calls")
        
    finally:
        await client.cleanup()


if __name__ == "__main__":
    # Run real API tests
    pytest.main([
        __file__,
        "-v",
        "-m", "real_api",
        "--tb=short"
    ])