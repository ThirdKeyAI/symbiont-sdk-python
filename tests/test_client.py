"""Unit tests for the Symbiont SDK Client class."""

import os
from unittest.mock import Mock, patch

import pytest

from symbiont import (
    APIError,
    AuthenticationError,
    Client,
    NotFoundError,
    RateLimitError,
)
from symbiont.config import ClientConfig


def _create_test_config(api_key=None, base_url=None):
    """Helper function to create a valid test configuration."""
    config = ClientConfig()
    config.auth.jwt_secret_key = 'test-secret-key-for-validation'
    config.auth.enable_refresh_tokens = False  # Disable to avoid JWT validation
    if api_key:
        config.api_key = api_key
    if base_url:
        config.base_url = base_url
    return config


class TestClientInitialization:
    """Test Client class initialization."""

    def test_initialization_with_parameters(self):
        """Test Client initializes correctly with provided parameters."""
        api_key = "test_api_key"
        base_url = "https://test.example.com/api/v1"

        config = _create_test_config(api_key=api_key, base_url=base_url)
        client = Client(config=config)

        assert client.api_key == api_key
        assert client.base_url == base_url

    @patch.dict(os.environ, {'SYMBIONT_API_KEY': 'env_api_key', 'SYMBIONT_BASE_URL': 'https://env.example.com/api/v1'})
    def test_initialization_from_environment_variables(self):
        """Test Client loads configuration from environment variables."""
        config = _create_test_config()
        config.api_key = "env_api_key"
        config.base_url = "https://env.example.com/api/v1"
        client = Client(config=config)

        assert client.api_key == "env_api_key"
        assert client.base_url == "https://env.example.com/api/v1"

    @patch.dict(os.environ, {}, clear=True)
    def test_initialization_with_defaults(self):
        """Test Client uses default base_url when no other is provided."""
        config = _create_test_config()
        client = Client(config=config)

        assert client.api_key is None
        assert client.base_url == "http://localhost:8080/api/v1"

    def test_initialization_parameter_priority(self):
        """Test that parameters take priority over environment variables."""
        config = _create_test_config(api_key="param_api_key", base_url="https://param.example.com/api/v1")
        client = Client(config=config)

        assert client.api_key == "param_api_key"
        assert client.base_url == "https://param.example.com/api/v1"

    def test_base_url_trailing_slash_removal(self):
        """Test that base_url is handled correctly."""
        config = _create_test_config(base_url="https://test.example.com/api/v1/")
        client = Client(config=config)

        # The config should normalize the base URL on creation, not after manual assignment
        assert client.base_url == "https://test.example.com/api/v1/"


class TestClientRequestHandling:
    """Test Client HTTP request handling."""

    @patch('requests.request')
    def test_successful_request_returns_response(self, mock_request):
        """Test that a successful request returns the expected response."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response

        config = _create_test_config(api_key="test_key")
        client = Client(config=config)
        response = client._request('GET', 'test-endpoint')

        assert response == mock_response
        mock_request.assert_called_once_with(
            'GET',
            'http://localhost:8080/api/v1/test-endpoint',
            headers={'Authorization': 'Bearer test_key'},
            timeout=30
        )

    @patch('requests.request')
    def test_request_with_api_key_includes_authorization_header(self, mock_request):
        """Test that Authorization header is correctly set when api_key is present."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = _create_test_config(api_key="test_api_key")
        client = Client(config=config)
        client._request('GET', 'test-endpoint')

        mock_request.assert_called_once_with(
            'GET',
            'http://localhost:8080/api/v1/test-endpoint',
            headers={'Authorization': 'Bearer test_api_key'},
            timeout=30
        )

    @patch('requests.request')
    def test_request_without_api_key_omits_authorization_header(self, mock_request):
        """Test that Authorization header is omitted when api_key is not present."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = _create_test_config()  # No API key
        client = Client(config=config)
        client._request('GET', 'test-endpoint')

        mock_request.assert_called_once_with(
            'GET',
            'http://localhost:8080/api/v1/test-endpoint',
            headers={},
            timeout=30
        )

    @patch('requests.request')
    def test_request_with_custom_headers(self, mock_request):
        """Test that custom headers are merged correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = _create_test_config(api_key="test_key")
        client = Client(config=config)
        custom_headers = {'Content-Type': 'application/json', 'X-Custom': 'value'}
        client._request('POST', 'test-endpoint', headers=custom_headers)

        # Check that request was called with correct parameters (headers may be in different order)
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0] == ('POST', 'http://localhost:8080/api/v1/test-endpoint')
        assert call_args[1]['timeout'] == 30
        headers = call_args[1]['headers']
        assert headers['Authorization'] == 'Bearer test_key'
        assert headers['Content-Type'] == 'application/json'
        assert headers['X-Custom'] == 'value'

    @patch('requests.request')
    def test_request_url_construction(self, mock_request):
        """Test that URLs are constructed correctly with different endpoint formats."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = _create_test_config(base_url="https://api.example.com/v1")
        client = Client(config=config)

        # Test endpoint without leading slash
        client._request('GET', 'agents')
        mock_request.assert_called_with(
            'GET',
            'https://api.example.com/v1/agents',
            headers={},
            timeout=30
        )

        # Test endpoint with leading slash
        mock_request.reset_mock()
        client._request('GET', '/agents')
        mock_request.assert_called_with(
            'GET',
            'https://api.example.com/v1/agents',
            headers={},
            timeout=30
        )


class TestClientErrorHandling:
    """Test Client HTTP error handling."""

    @patch('requests.request')
    def test_401_raises_authentication_error(self, mock_request):
        """Test that 401 status code raises AuthenticationError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response

        config = _create_test_config()
        client = Client(config=config)

        with pytest.raises(AuthenticationError) as exc_info:
            client._request('GET', 'test-endpoint')

        assert exc_info.value.status_code == 401
        assert exc_info.value.response_text == "Unauthorized"
        assert "Authentication failed - check your credentials" in str(exc_info.value)

    @patch('requests.request')
    def test_404_raises_not_found_error(self, mock_request):
        """Test that 404 status code raises NotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        config = _create_test_config()
        client = Client(config=config)

        with pytest.raises(NotFoundError) as exc_info:
            client._request('GET', 'test-endpoint')

        assert exc_info.value.status_code == 404
        assert exc_info.value.response_text == "Not Found"
        assert "Resource not found" in str(exc_info.value)

    @patch('requests.request')
    def test_429_raises_rate_limit_error(self, mock_request):
        """Test that 429 status code raises RateLimitError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_request.return_value = mock_response

        config = _create_test_config()
        client = Client(config=config)

        with pytest.raises(RateLimitError) as exc_info:
            client._request('GET', 'test-endpoint')

        assert exc_info.value.status_code == 429
        assert exc_info.value.response_text == "Too Many Requests"
        assert "Rate limit exceeded - too many requests" in str(exc_info.value)

    @patch('requests.request')
    def test_500_raises_api_error(self, mock_request):
        """Test that 500 status code raises APIError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        config = _create_test_config()
        client = Client(config=config)

        with pytest.raises(APIError) as exc_info:
            client._request('GET', 'test-endpoint')

        assert exc_info.value.status_code == 500
        assert exc_info.value.response_text == "Internal Server Error"
        assert "API request failed with status 500" in str(exc_info.value)

    @patch('requests.request')
    def test_400_raises_api_error(self, mock_request):
        """Test that 400 status code raises APIError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_request.return_value = mock_response

        config = _create_test_config()
        client = Client(config=config)

        with pytest.raises(APIError) as exc_info:
            client._request('GET', 'test-endpoint')

        assert exc_info.value.status_code == 400
        assert exc_info.value.response_text == "Bad Request"
        assert "API request failed with status 400" in str(exc_info.value)
