"""Unit tests for the Symbiont SDK ChannelClient."""

from unittest.mock import Mock, patch

from symbiont import Client
from symbiont.config import ClientConfig
from symbiont.channels import (
    AddIdentityMappingRequest,
    ChannelActionResponse,
    ChannelAuditEntry,
    ChannelAuditResponse,
    ChannelDetail,
    ChannelHealthResponse,
    ChannelSummary,
    DeleteChannelResponse,
    IdentityMappingEntry,
    RegisterChannelRequest,
    RegisterChannelResponse,
    UpdateChannelRequest,
)


def _create_test_config():
    """Helper to create a valid test configuration."""
    config = ClientConfig()
    config.auth.jwt_secret_key = "test-secret-key-for-validation"
    config.auth.enable_refresh_tokens = False
    config.api_key = "test-api-key"
    return config


def _make_client():
    """Create a Client with mocked config."""
    return Client(config=_create_test_config())


class TestChannelClientAccess:
    """Test that ChannelClient is accessible from Client."""

    def test_channels_property_returns_channel_client(self):
        client = _make_client()
        assert client.channels is not None

    def test_channels_property_is_cached(self):
        client = _make_client()
        first = client.channels
        second = client.channels
        assert first is second


class TestListChannels:
    """Test ChannelClient.list_channels()."""

    @patch("requests.request")
    def test_list_channels_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "ch-1",
                "name": "ops-slack",
                "platform": "slack",
                "status": "running",
            }
        ]
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.list_channels()

        assert len(result) == 1
        assert isinstance(result[0], ChannelSummary)
        assert result[0].id == "ch-1"
        assert result[0].platform == "slack"

    @patch("requests.request")
    def test_list_channels_empty(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.list_channels()

        assert result == []


class TestRegisterChannel:
    """Test ChannelClient.register_channel()."""

    @patch("requests.request")
    def test_register_channel_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "ch-new",
            "name": "eng-teams",
            "platform": "teams",
            "status": "stopped",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = RegisterChannelRequest(
            name="eng-teams",
            platform="teams",
            config={"tenant_id": "abc-123"},
        )
        result = client.channels.register_channel(request)

        assert isinstance(result, RegisterChannelResponse)
        assert result.id == "ch-new"
        assert result.platform == "teams"


class TestGetChannel:
    """Test ChannelClient.get_channel()."""

    @patch("requests.request")
    def test_get_channel_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ch-1",
            "name": "ops-slack",
            "platform": "slack",
            "status": "running",
            "config": {"bot_token": "xoxb-***"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.get_channel("ch-1")

        assert isinstance(result, ChannelDetail)
        assert result.id == "ch-1"
        assert result.status == "running"


class TestUpdateChannel:
    """Test ChannelClient.update_channel()."""

    @patch("requests.request")
    def test_update_channel_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ch-1",
            "name": "ops-slack",
            "platform": "slack",
            "status": "running",
            "config": {"bot_token": "xoxb-new"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = UpdateChannelRequest(config={"bot_token": "xoxb-new"})
        result = client.channels.update_channel("ch-1", request)

        assert isinstance(result, ChannelDetail)
        assert result.config["bot_token"] == "xoxb-new"

    @patch("requests.request")
    def test_update_channel_only_sends_non_none_fields(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ch-1",
            "name": "ops-slack",
            "platform": "slack",
            "status": "running",
            "config": {},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = UpdateChannelRequest()  # config is None
        client.channels.update_channel("ch-1", request)

        call_kwargs = mock_request.call_args[1]
        payload = call_kwargs["json"]
        assert "config" not in payload


class TestDeleteChannel:
    """Test ChannelClient.delete_channel()."""

    @patch("requests.request")
    def test_delete_channel_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "ch-1", "deleted": True}
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.delete_channel("ch-1")

        assert isinstance(result, DeleteChannelResponse)
        assert result.deleted is True


class TestStartStopChannel:
    """Test start and stop actions."""

    @patch("requests.request")
    def test_start_channel(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ch-1",
            "action": "start",
            "status": "running",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.start_channel("ch-1")

        assert isinstance(result, ChannelActionResponse)
        assert result.action == "start"

    @patch("requests.request")
    def test_stop_channel(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ch-1",
            "action": "stop",
            "status": "stopped",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.stop_channel("ch-1")

        assert isinstance(result, ChannelActionResponse)
        assert result.action == "stop"


class TestGetChannelHealth:
    """Test ChannelClient.get_channel_health()."""

    @patch("requests.request")
    def test_get_channel_health_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ch-1",
            "connected": True,
            "platform": "slack",
            "workspace_name": "Acme Corp",
            "channels_active": 5,
            "last_message_at": "2024-01-01T12:00:00Z",
            "uptime_secs": 86400,
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.get_channel_health("ch-1")

        assert isinstance(result, ChannelHealthResponse)
        assert result.connected is True
        assert result.workspace_name == "Acme Corp"
        assert result.channels_active == 5


class TestChannelMappings:
    """Test enterprise identity mapping endpoints."""

    @patch("requests.request")
    def test_list_mappings_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "platform_user_id": "U123",
                "platform": "slack",
                "symbiont_user_id": "user@acme.com",
                "email": "user@acme.com",
                "display_name": "Alice",
                "roles": ["admin"],
                "verified": True,
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.list_mappings("ch-1")

        assert len(result) == 1
        assert isinstance(result[0], IdentityMappingEntry)
        assert result[0].platform_user_id == "U123"

    @patch("requests.request")
    def test_add_mapping_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "platform_user_id": "U456",
            "platform": "slack",
            "symbiont_user_id": "bob@acme.com",
            "email": "bob@acme.com",
            "display_name": "Bob",
            "roles": ["user"],
            "verified": False,
            "created_at": "2024-01-02T00:00:00Z",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = AddIdentityMappingRequest(
            platform_user_id="U456",
            symbiont_user_id="bob@acme.com",
            display_name="Bob",
            roles=["user"],
            email="bob@acme.com",
        )
        result = client.channels.add_mapping("ch-1", request)

        assert isinstance(result, IdentityMappingEntry)
        assert result.symbiont_user_id == "bob@acme.com"


class TestChannelAudit:
    """Test enterprise audit log endpoint."""

    @patch("requests.request")
    def test_query_audit_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "channel_id": "ch-1",
            "entries": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "event_type": "message_received",
                    "user_id": "U123",
                    "channel_id": "C456",
                    "agent": "helper",
                    "details": {"action": "invoke"},
                }
            ],
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.channels.query_audit("ch-1")

        assert isinstance(result, ChannelAuditResponse)
        assert result.channel_id == "ch-1"
        assert len(result.entries) == 1
        assert isinstance(result.entries[0], ChannelAuditEntry)
        assert result.entries[0].event_type == "message_received"

    @patch("requests.request")
    def test_query_audit_custom_limit(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"channel_id": "ch-1", "entries": []}
        mock_request.return_value = mock_response

        client = _make_client()
        client.channels.query_audit("ch-1", limit=10)

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"] == {"limit": 10}
