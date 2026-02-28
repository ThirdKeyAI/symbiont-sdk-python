"""Unit tests for the Symbiont SDK ReasoningClient."""

from unittest.mock import Mock, patch

from symbiont import Client
from symbiont.config import ClientConfig
from symbiont.reasoning import (
    CedarPolicy,
    CircuitBreakerStatus,
    JournalEntry,
    LoopDecision,
    LoopState,
    ProposedAction,
    ProposedActionType,
    RunReasoningLoopRequest,
    RunReasoningLoopResponse,
    LoopConfig,
)
from symbiont.reasoning_client import ReasoningClient


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


class TestReasoningClientAccess:
    """Test that ReasoningClient is accessible from Client."""

    def test_reasoning_property_returns_reasoning_client(self):
        client = _make_client()
        assert client.reasoning is not None
        assert isinstance(client.reasoning, ReasoningClient)

    def test_reasoning_property_is_cached(self):
        client = _make_client()
        first = client.reasoning
        second = client.reasoning
        assert first is second


class TestRunLoop:
    """Test ReasoningClient.run_loop()."""

    @patch("requests.request")
    def test_run_loop_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "loop_id": "loop-1",
            "result": {
                "output": "The answer is 42",
                "iterations": 3,
                "total_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "termination_reason": {"type": "completed"},
                "duration_ms": 5000,
            },
            "journal_entries": [],
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = RunReasoningLoopRequest(config=LoopConfig(), initial_message="What is 6*7?")
        result = client.reasoning.run_loop("agent-1", request)

        assert isinstance(result, RunReasoningLoopResponse)
        assert result.loop_id == "loop-1"
        assert result.result.output == "The answer is 42"


class TestGetLoopStatus:
    """Test ReasoningClient.get_loop_status()."""

    @patch("requests.request")
    def test_get_loop_status_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "agent_id": "agent-1",
            "iteration": 2,
            "total_usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            "pending_observations": [],
            "started_at": "2026-01-01T00:00:00Z",
            "current_phase": "tools",
            "metadata": {},
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.reasoning.get_loop_status("agent-1", "loop-1")

        assert isinstance(result, LoopState)
        assert result.iteration == 2
        assert result.current_phase == "tools"


class TestGetJournalEntries:
    """Test ReasoningClient.get_journal_entries()."""

    @patch("requests.request")
    def test_get_journal_entries_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sequence": 0,
                "timestamp": "2026-01-01T00:00:00Z",
                "agent_id": "agent-1",
                "iteration": 0,
                "event": {"type": "started", "agent_id": "agent-1"},
            },
        ]
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.reasoning.get_journal_entries("agent-1")

        assert len(result) == 1
        assert isinstance(result[0], JournalEntry)
        assert result[0].sequence == 0


class TestListCedarPolicies:
    """Test ReasoningClient.list_cedar_policies()."""

    @patch("requests.request")
    def test_list_cedar_policies_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "deny-all", "source": "forbid(principal,action,resource);", "active": True},
        ]
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.reasoning.list_cedar_policies("agent-1")

        assert len(result) == 1
        assert isinstance(result[0], CedarPolicy)
        assert result[0].name == "deny-all"


class TestEvaluateCedarPolicy:
    """Test ReasoningClient.evaluate_cedar_policy()."""

    @patch("requests.request")
    def test_evaluate_cedar_policy_allow(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"decision": "allow"}
        mock_request.return_value = mock_response

        client = _make_client()
        action = ProposedAction(type=ProposedActionType.RESPOND, content="hello")
        result = client.reasoning.evaluate_cedar_policy("agent-1", action)

        assert isinstance(result, LoopDecision)
        assert result.decision == "allow"


class TestGetCircuitBreakerStatus:
    """Test ReasoningClient.get_circuit_breaker_status()."""

    @patch("requests.request")
    def test_get_circuit_breaker_status_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search": {
                "state": "closed",
                "failure_count": 0,
                "success_count": 10,
                "config": {"failure_threshold": 5, "recovery_timeout_ms": 30000, "half_open_max_calls": 3},
            },
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.reasoning.get_circuit_breaker_status("agent-1")

        assert "search" in result
        assert isinstance(result["search"], CircuitBreakerStatus)
        assert result["search"].state == "closed"


class TestRecallKnowledge:
    """Test ReasoningClient.recall_knowledge()."""

    @patch("requests.request")
    def test_recall_knowledge_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["The sky is blue", "Water boils at 100C"]
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.reasoning.recall_knowledge("agent-1", "what color is the sky?")

        assert len(result) == 2
        assert result[0] == "The sky is blue"


class TestStoreKnowledge:
    """Test ReasoningClient.store_knowledge()."""

    @patch("requests.request")
    def test_store_knowledge_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "k-1"}
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.reasoning.store_knowledge("agent-1", "sky", "color_is", "blue")

        assert result["id"] == "k-1"
