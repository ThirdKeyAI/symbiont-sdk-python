# tests/test_new_features.py

from unittest.mock import MagicMock, patch

import pytest

from symbiont.auth import AuthManager, AuthUser
from symbiont.client import Client

# Import necessary classes from the symbiont-sdk
from symbiont.config import (
    AuthConfig,
    ClientConfig,
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
def mock_client(mock_config):
    """Fixture for the API client with mocked requests."""
    with patch("requests.request"):
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
    access_token = tokens["access"].token

    validated_user = auth_manager.authenticate_with_jwt(access_token)
    assert validated_user is not None
    assert validated_user.user_id == TEST_USER_ID
    assert TEST_ROLE in validated_user.roles


def test_jwt_refresh(auth_manager):
    """Test the token refresh logic."""
    user = AuthUser(user_id=TEST_USER_ID, roles=[TEST_ROLE])
    tokens = auth_manager.generate_tokens(user)
    refresh_token = tokens["refresh"].token

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
    assert auth_manager.authenticate_with_jwt(tokens["access"].token) is None


# ===================================
# 2. Client Convenience Method Tests
# ===================================


def test_client_get_configuration(mock_client):
    """Test the client's get_configuration method."""
    assert mock_client.get_configuration() == mock_client.config


def test_client_get_user_roles(mock_client):
    """Test the client's get_user_roles method."""
    mock_client._current_user = AuthUser(user_id=TEST_USER_ID, roles=[TEST_ROLE])
    roles = mock_client.get_user_roles()
    assert TEST_ROLE in roles
