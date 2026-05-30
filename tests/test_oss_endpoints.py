"""Tests for OSS runtime endpoint coverage and /api/v1 prefix de-duplication.

These tests pin two things against Symbiont OSS runtime v1.14.x:

1. The ``/api/v1`` version prefix is de-duplicated in exactly one place
   (``Client._request``). The configured ``base_url`` already carries the
   version segment (default ``http://localhost:8080/api/v1``); endpoints that
   historically also hard-coded an ``api/v1/`` prefix previously produced a
   doubled ``/api/v1/api/v1/`` path that 404s. The de-dup makes the segment
   appear exactly once, while a ``base_url`` with a different prefix is left
   untouched.

2. The agent-execute, inter-agent messaging, and external-agent
   heartbeat/event endpoints the runtime serves are reachable from the client
   at their correct paths.
"""

from unittest.mock import Mock, patch

from symbiont import Client
from symbiont.config import ClientConfig


def _client(base_url=None, api_key="test-key"):
    """Build a Client with refresh tokens disabled (mirrors test_client.py)."""
    config = ClientConfig()
    config.auth.jwt_secret_key = "test-secret-key-for-validation"
    config.auth.enable_refresh_tokens = False
    config.api_key = api_key
    if base_url:
        config.base_url = base_url
    return Client(config=config)


def _mock_ok(payload=None):
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload if payload is not None else {}
    return response


# ---------------------------------------------------------------------------
# /api/v1 prefix de-duplication
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_bare_endpoint_resolves_under_api_v1(mock_request):
    """A bare endpoint resolves under the base_url's /api/v1 segment."""
    mock_request.return_value = _mock_ok({"status": "healthy"})
    client = _client()  # default base_url = http://localhost:8080/api/v1
    client._request("GET", "agents/agent-1")
    assert mock_request.call_args[0] == (
        "GET",
        "http://localhost:8080/api/v1/agents/agent-1",
    )


@patch("requests.request")
def test_prefixed_endpoint_is_not_doubled(mock_request):
    """An endpoint that already carries api/v1/ must not be doubled."""
    mock_request.return_value = _mock_ok({})
    client = _client()  # default base_url ends with /api/v1
    client._request("GET", "api/v1/agents/agent-1")
    assert mock_request.call_args[0] == (
        "GET",
        "http://localhost:8080/api/v1/agents/agent-1",
    )


@patch("requests.request")
def test_custom_prefix_base_url_is_preserved(mock_request):
    """A base_url with a non-/api/v1 prefix is left untouched."""
    mock_request.return_value = _mock_ok({})
    client = _client(base_url="https://api.example.com/v1")
    client._request("GET", "test-endpoint")
    assert mock_request.call_args[0] == (
        "GET",
        "https://api.example.com/v1/test-endpoint",
    )


# ---------------------------------------------------------------------------
# Agent execute
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_execute_agent(mock_request):
    mock_request.return_value = _mock_ok(
        {"execution_id": "exec-1", "status": "started"}
    )
    client = _client()
    result = client.execute_agent("agent-123")
    assert result == {"execution_id": "exec-1", "status": "started"}
    assert mock_request.call_args[0] == (
        "POST",
        "http://localhost:8080/api/v1/agents/agent-123/execute",
    )


# ---------------------------------------------------------------------------
# Inter-agent messaging
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_send_message(mock_request):
    mock_request.return_value = _mock_ok({"message_id": "msg-1", "status": "pending"})
    client = _client()
    result = client.send_message(
        "agent-123", sender="agent-system", payload="hello", ttl_seconds=120
    )
    assert result["message_id"] == "msg-1"
    assert mock_request.call_args[0] == (
        "POST",
        "http://localhost:8080/api/v1/agents/agent-123/messages",
    )
    body = mock_request.call_args[1]["json"]
    assert body == {
        "sender": "agent-system",
        "payload": "hello",
        "ttl_seconds": 120,
    }


@patch("requests.request")
def test_receive_messages(mock_request):
    mock_request.return_value = _mock_ok(
        {"messages": [{"message_id": "msg-1", "payload": "hi"}]}
    )
    client = _client()
    result = client.receive_messages("agent-123")
    assert result["messages"][0]["message_id"] == "msg-1"
    assert mock_request.call_args[0] == (
        "GET",
        "http://localhost:8080/api/v1/agents/agent-123/messages",
    )


@patch("requests.request")
def test_get_message_status(mock_request):
    mock_request.return_value = _mock_ok({"message_id": "msg-1", "status": "delivered"})
    client = _client()
    result = client.get_message_status("msg-1")
    assert result["status"] == "delivered"
    assert mock_request.call_args[0] == (
        "GET",
        "http://localhost:8080/api/v1/messages/msg-1/status",
    )


# ---------------------------------------------------------------------------
# External agent lifecycle: heartbeat + events
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_send_heartbeat(mock_request):
    mock_request.return_value = _mock_ok({})
    client = _client()
    assert client.send_heartbeat("agent-123", state="Running") is None
    assert mock_request.call_args[0] == (
        "POST",
        "http://localhost:8080/api/v1/agents/agent-123/heartbeat",
    )
    assert mock_request.call_args[1]["json"] == {"state": "Running"}


@patch("requests.request")
def test_push_agent_event(mock_request):
    mock_request.return_value = _mock_ok({})
    client = _client()
    assert (
        client.push_agent_event(
            "agent-123", event_type="RunCompleted", payload={"ok": True}
        )
        is None
    )
    assert mock_request.call_args[0] == (
        "POST",
        "http://localhost:8080/api/v1/agents/agent-123/events",
    )
    body = mock_request.call_args[1]["json"]
    assert body == {"event_type": "RunCompleted", "payload": {"ok": True}}
