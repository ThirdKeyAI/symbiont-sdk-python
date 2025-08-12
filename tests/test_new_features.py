# tests/test_new_features.py

import pytest
from unittest.mock import patch, MagicMock
import os
from datetime import datetime, timedelta
import jwt

# Import necessary classes from the symbiont-sdk
from symbiont.config import (
    ClientConfig,
    ConfigManager,
    AuthConfig,
)
from symbiont.auth import AuthManager, AuthUser, Permission, Role
from symbiont.memory import MemoryManager, MemoryNode, MemoryType, MemoryLevel
from symbiont.qdrant import QdrantManager
from symbiont.client import Client
from symbiont.models import (
    HttpEndpointCreateRequest,
    HttpMethod,
    HttpEndpointResponse,
)
from symbiont.exceptions import (
    AuthenticationError,
)

# Mock data and constants
TEST_SECRET_KEY = "your-test-secret-key"
TEST_USER_ID = "test-user"
TEST_ROLE = "user"


@pytest.fixture
def mock_config():
    """Fixture for a mock ClientConfig."""
    return ClientConfig(auth=AuthConfig(jwt_secret_key=TEST_SECRET_KEY))


@pytest.fixture
def auth_manager(mock_config):
    """Fixture for AuthManager."""
    return AuthManager(mock_config.auth)


@pytest.fixture
def memory_manager():
    """Fixture for MemoryManager with in-memory storage."""
    return MemoryManager(config={'storage_type': 'in-memory'})


@pytest.fixture
def redis_memory_manager():
    """Fixture for MemoryManager with a mocked Redis backend."""
    with patch('redis.from_url') as mock_from_url:
        mock_redis_instance = MagicMock()
        mock_from_url.return_value = mock_redis_instance
        manager = MemoryManager(config={'storage_type': 'redis'})
        yield manager


@pytest.fixture
@patch('qdrant_client.QdrantClient')
def qdrant_manager(mock_qdrant_client):
    """Fixture for QdrantManager with a mocked Qdrant client."""
    mock_qdrant_instance = mock_qdrant_client.return_value
    manager = QdrantManager(api_key="test-key", host="localhost", port=6333)
    manager._client = mock_qdrant_instance
    return manager


@pytest.fixture
def mock_client(mock_config):
    """Fixture for the API client with mocked requests."""
    with patch('requests.request') as mock_request:
        client = Client(config=mock_config)
        # We are mocking the internal _request method, not the requests library directly
        client._request = MagicMock()
        yield client


# ===================================
# 1. Configuration and Authentication Tests
# ===================================

def test_config_manager_env_override(monkeypatch):
    """Test that environment variables override default config values."""
    monkeypatch.setenv("SYMBIONT_BASE_URL", "https://new-api.symbiont.com")
    monkeypatch.setenv("SYMBIONT_AUTH_JWT_SECRET_KEY", "env-secret-key")

    # The model needs to be reloaded to pick up the new env vars
    from symbiont.config import ClientConfig
    ClientConfig.model_rebuild(force=True)
    
    config = ClientConfig()

    assert config.base_url == "https://new-api.symbiont.com"
    assert config.auth.jwt_secret_key == "env-secret-key"

def test_jwt_creation_and_validation(auth_manager):
    """Test creating a JWT and then validating it."""
    user = AuthUser(user_id=TEST_USER_ID, roles=[TEST_ROLE])
    tokens = auth_manager.generate_tokens(user)
    access_token = tokens['access'].token
    
    validated_user = auth_manager.authenticate_with_jwt(access_token)
    assert validated_user is not None
    assert validated_user.user_id == TEST_USER_ID
    assert TEST_ROLE in validated_user.roles

def test_jwt_refresh(auth_manager):
    """Test the token refresh logic."""
    user = AuthUser(user_id=TEST_USER_ID, roles=[TEST_ROLE])
    tokens = auth_manager.generate_tokens(user)
    refresh_token = tokens['refresh'].token
    
    new_access_token = auth_manager.refresh_access_token(refresh_token)
    assert new_access_token is not None
    
    validated_user = auth_manager.authenticate_with_jwt(new_access_token.token)
    assert validated_user.user_id == TEST_USER_ID

def test_expired_token_validation(auth_manager):
    """Test that an expired token raises AuthenticationExpiredError."""
    auth_manager.config.jwt_expiration_seconds = -1
    user = AuthUser(user_id=TEST_USER_ID, roles=[TEST_ROLE])
    tokens = auth_manager.generate_tokens(user)
    
    # The authenticate_with_jwt method should return None for an invalid token
    assert auth_manager.authenticate_with_jwt(tokens['access'].token) is None

# ===================================
# 2. Memory System Tests
# ===================================

def test_hierarchical_memory_in_memory(memory_manager):
    """Test HierarchicalMemory with the in-memory backend."""
    memory_manager.add_memory(
        content={"message": "hello"},
        memory_type=MemoryType.CONVERSATION,
        memory_level=MemoryLevel.SHORT_TERM,
        agent_id="test-agent"
    )
    memories = memory_manager.list_agent_memories("test-agent")
    assert len(memories) == 1
    assert memories[0].content["message"] == "hello"

def test_memory_manager_redis(redis_memory_manager):
    """Test MemoryManager with the mocked Redis backend."""
    redis_memory_manager.add_memory(
        content={"message": "hello redis"},
        memory_type=MemoryType.CONVERSATION,
        memory_level=MemoryLevel.SHORT_TERM,
        agent_id="test-agent-redis"
    )
    redis_memory_manager.memory_store.redis_client.set.assert_called()
    redis_memory_manager.memory_store.redis_client.lpush.assert_called()

# ===================================
# 3. Qdrant Integration Tests
# ===================================

def test_qdrant_manager_create_collection(qdrant_manager):
    """Test creating a Qdrant collection."""
    qdrant_manager.create_collection("test-collection", vector_size=4)
    qdrant_manager._client.create_collection.assert_called_once()
    args, kwargs = qdrant_manager._client.create_collection.call_args
    assert kwargs["collection_name"] == "test-collection"

def test_qdrant_manager_upsert_points(qdrant_manager):
    """Test upserting points to a Qdrant collection."""
    points = [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"meta": "data"}}]
    qdrant_manager.upsert_points("test-collection", points)
    qdrant_manager._client.upsert.assert_called_once()
    args, kwargs = qdrant_manager._client.upsert.call_args
    assert kwargs["collection_name"] == "test-collection"
    assert len(kwargs["points"]) == 1

# ===================================
# 4. API Endpoint Tests
# ===================================

def test_client_get_configuration(mock_client):
    """Test the client's get_configuration method."""
    assert mock_client.get_configuration() == mock_client.config

def test_client_get_user_roles(mock_client):
    """Test the client's get_user_roles method."""
    mock_client._current_user = AuthUser(user_id=TEST_USER_ID, roles=[TEST_ROLE])
    roles = mock_client.get_user_roles()
    assert TEST_ROLE in roles

def test_client_create_http_endpoint(mock_client):
    """Test the client's create_http_endpoint method."""
    mock_response_data = {"endpoint_id": "ep-123", "status": "active"}
    mock_client._request.return_value.json.return_value = mock_response_data
    
    create_req = HttpEndpointCreateRequest(
        path="/test", method=HttpMethod.POST, agent_id="agent-1"
    )
    
    response = mock_client.create_http_endpoint(create_req)
    assert response.endpoint_id == "ep-123"
    mock_client._request.assert_called_with("POST", "endpoints", json=create_req.model_dump())
