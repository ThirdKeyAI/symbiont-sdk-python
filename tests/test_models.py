"""Unit tests for the Symbiont SDK data models."""

import pytest
from pydantic import ValidationError

from symbiont import Agent


class TestAgentModel:
    """Test Agent model validation and creation."""

    def test_agent_creation_with_valid_data(self):
        """Test that Agent can be created successfully with valid data."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent for validation",
            "system_prompt": "You are a helpful assistant.",
            "tools": ["tool1", "tool2", "tool3"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        agent = Agent(**agent_data)

        assert agent.id == "agent-123"
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent for validation"
        assert agent.system_prompt == "You are a helpful assistant."
        assert agent.tools == ["tool1", "tool2", "tool3"]
        assert agent.model == "gpt-4"
        assert agent.temperature == 0.7
        assert agent.top_p == 0.9
        assert agent.max_tokens == 2000

    def test_agent_creation_with_minimal_valid_data(self):
        """Test Agent creation with minimal but valid data."""
        agent_data = {
            "id": "minimal-agent",
            "name": "Minimal Agent",
            "description": "Minimal test agent",
            "system_prompt": "Be helpful.",
            "tools": [],
            "model": "gpt-3.5-turbo",
            "temperature": 0.0,
            "top_p": 0.1,
            "max_tokens": 100,
        }

        agent = Agent(**agent_data)

        assert agent.id == "minimal-agent"
        assert agent.name == "Minimal Agent"
        assert agent.tools == []
        assert agent.temperature == 0.0
        assert agent.top_p == 0.1
        assert agent.max_tokens == 100

    def test_agent_missing_required_id_raises_validation_error(self):
        """Test that missing 'id' field raises ValidationError."""
        agent_data = {
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("id",)

    def test_agent_missing_required_name_raises_validation_error(self):
        """Test that missing 'name' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("name",)

    def test_agent_missing_required_description_raises_validation_error(self):
        """Test that missing 'description' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("description",)

    def test_agent_missing_required_system_prompt_raises_validation_error(self):
        """Test that missing 'system_prompt' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("system_prompt",)

    def test_agent_missing_required_tools_raises_validation_error(self):
        """Test that missing 'tools' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("tools",)

    def test_agent_missing_required_model_raises_validation_error(self):
        """Test that missing 'model' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("model",)

    def test_agent_missing_required_temperature_raises_validation_error(self):
        """Test that missing 'temperature' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("temperature",)

    def test_agent_missing_required_top_p_raises_validation_error(self):
        """Test that missing 'top_p' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("top_p",)

    def test_agent_missing_required_max_tokens_raises_validation_error(self):
        """Test that missing 'max_tokens' field raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("max_tokens",)

    def test_agent_multiple_missing_fields_raises_validation_error(self):
        """Test that multiple missing required fields raise ValidationError with multiple errors."""
        agent_data = {
            "id": "agent-123",
            # Missing: name, description, system_prompt, tools, model, temperature, top_p, max_tokens
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 8  # All fields except 'id' are missing

        missing_fields = {error["loc"][0] for error in errors}
        expected_missing = {
            "name",
            "description",
            "system_prompt",
            "tools",
            "model",
            "temperature",
            "top_p",
            "max_tokens",
        }
        assert missing_fields == expected_missing

    def test_agent_invalid_temperature_type_raises_validation_error(self):
        """Test that incorrect data type for 'temperature' raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": "invalid",  # Should be float
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("temperature",)
        assert "float_parsing" in errors[0]["type"]

    def test_agent_invalid_top_p_type_raises_validation_error(self):
        """Test that incorrect data type for 'top_p' raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": "invalid",  # Should be float
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("top_p",)
        assert "float_parsing" in errors[0]["type"]

    def test_agent_invalid_max_tokens_type_raises_validation_error(self):
        """Test that incorrect data type for 'max_tokens' raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": ["tool1"],
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": "invalid",  # Should be int
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("max_tokens",)
        assert "int_parsing" in errors[0]["type"]

    def test_agent_invalid_tools_type_raises_validation_error(self):
        """Test that incorrect data type for 'tools' raises ValidationError."""
        agent_data = {
            "id": "agent-123",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful.",
            "tools": "not_a_list",  # Should be list
            "model": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
        }

        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("tools",)
        assert "list_type" in errors[0]["type"]


class TestWebhookInvocationModels:
    """Tests for HTTP Input invocation models (Symbiont v1.10.0)."""

    def test_invocation_status_enum_values(self):
        from symbiont import WebhookInvocationStatus

        assert WebhookInvocationStatus.COMPLETED.value == "completed"
        # Retained for runtimes older than 1.21.0, which still emit it.
        assert WebhookInvocationStatus.EXECUTION_STARTED.value == "execution_started"

    def test_invocation_request_accepts_prompt(self):
        from symbiont import WebhookInvocationRequest

        req = WebhookInvocationRequest(prompt="scan target 10.0.0.1")
        assert req.prompt == "scan target 10.0.0.1"
        assert req.message is None
        assert req.system_prompt is None

    def test_invocation_request_allows_extra_fields(self):
        from symbiont import WebhookInvocationRequest

        req = WebhookInvocationRequest(prompt="x", target="10.0.0.1", tags=["a", "b"])
        dumped = req.model_dump()
        assert dumped["target"] == "10.0.0.1"
        assert dumped["tags"] == ["a", "b"]

    def test_invocation_request_rejects_oversized_system_prompt(self):
        from symbiont import WebhookInvocationRequest

        with pytest.raises(ValidationError):
            WebhookInvocationRequest(system_prompt="x" * 4097)

    def test_tool_run_roundtrip(self):
        from symbiont import WebhookToolRun

        run = WebhookToolRun(
            tool="nmap",
            input={"target": "1.1.1.1"},
            output_preview="open ports: 22,443",
        )
        assert run.tool == "nmap"
        assert run.input["target"] == "1.1.1.1"
        assert run.output_preview.startswith("open ports")

    def test_execution_started_response_still_parses_for_older_runtimes(self):
        from symbiont import WebhookExecutionStartedResponse

        # 1.21.0 no longer emits this, but supported earlier runtimes do.
        resp = WebhookExecutionStartedResponse(
            agent_id="agent-1",
            message_id="msg-1",
            latency_ms=12,
            timestamp="2026-04-22T00:00:00Z",
        )
        assert resp.status == "execution_started"
        assert resp.latency_ms == 12

    def test_completed_response_carries_audit_and_retry_identity(self):
        from symbiont import WebhookCompletedResponse

        resp = WebhookCompletedResponse(
            agent_id="agent-1",
            response="Task complete.",
            termination_reason="Completed",
            iterations=1,
            audit={
                "run_id": "22222222-2222-4222-8222-222222222222",
                "path": "/srv/.symbiont/governed/run.jsonl",
                "public_key": "deadbeef",
            },
            invocation_id="11111111-1111-4111-8111-111111111111",
            replayed=True,
            total_usage={"input_tokens": 10, "output_tokens": 4},
            budget={"remaining_tokens": 900},
            model="m",
            provider="p",
            latency_ms=12,
            timestamp="2026-04-22T00:00:00Z",
        )
        assert resp.audit.run_id == "22222222-2222-4222-8222-222222222222"
        assert resp.audit.public_key == "deadbeef"
        assert resp.termination_reason == "Completed"
        assert resp.replayed is True
        assert resp.total_usage["input_tokens"] == 10

    def test_completed_response_with_tool_runs(self):
        from symbiont import WebhookCompletedResponse, WebhookToolRun

        resp = WebhookCompletedResponse(
            agent_id="agent-1",
            response="Scan complete.",
            tool_runs=[
                WebhookToolRun(
                    tool="nmap",
                    input={"target": "1.1.1.1"},
                    output_preview="open ports: 22",
                ),
            ],
            model="claude-opus-4-7",
            provider="anthropic",
            latency_ms=1234,
            timestamp="2026-04-22T00:00:00Z",
        )
        assert resp.status == "completed"
        assert len(resp.tool_runs) == 1
        assert resp.tool_runs[0].tool == "nmap"


class TestRuntime121Contract:
    """Runtime 1.21.0 response-shape changes."""

    def test_resource_samples_are_nullable(self):
        from symbiont import AgentStatusResponse, ResourceUsage

        # 1.21.0 has no per-agent sampler: CPU and memory come back null and
        # must not be coerced to zero.
        status = AgentStatusResponse(
            agent_id="agent-1",
            state="idle",
            last_activity="2026-10-06T00:00:00Z",
            resource_usage=ResourceUsage(
                memory_bytes=None, cpu_percent=None, active_tasks=2
            ),
            execution_mode="Ephemeral",
        )
        assert status.resource_usage.memory_bytes is None
        assert status.resource_usage.cpu_percent is None
        assert status.resource_usage.active_tasks == 2
        assert status.execution_mode == "Ephemeral"

    def test_reconciled_invocation_raises_with_resolution(self):
        from unittest.mock import MagicMock, patch

        from symbiont import Client
        from symbiont.config import ClientConfig
        from symbiont.exceptions import ReconciledInvocationError

        config = ClientConfig()
        config.auth.jwt_secret_key = "test-secret-key-for-validation"
        config.auth.enable_refresh_tokens = False
        config.api_key = "test-api-key"
        client = Client(config=config)

        response = MagicMock(status_code=409, text="{}")
        response.json.return_value = {
            "status": "reconciled",
            "resolution": {"outcome": "Failed", "rationale": "operator reviewed"},
        }
        with patch("requests.request", return_value=response):
            with pytest.raises(ReconciledInvocationError) as excinfo:
                client.execute_agent("agent-1", idempotency_key="k")
        assert excinfo.value.resolution["outcome"] == "Failed"

    def test_execute_agent_sends_idempotency_key(self):
        from unittest.mock import MagicMock, patch

        from symbiont import Client
        from symbiont.config import ClientConfig

        config = ClientConfig()
        config.auth.jwt_secret_key = "test-secret-key-for-validation"
        config.auth.enable_refresh_tokens = False
        config.api_key = "test-api-key"
        client = Client(config=config)

        response = MagicMock(status_code=200)
        response.json.return_value = {"status": "queued", "execution_id": "e1"}
        with patch("requests.request", return_value=response) as request:
            client.execute_agent("agent-1", idempotency_key="reused-uuid")
        headers = request.call_args.kwargs["headers"]
        assert headers["Idempotency-Key"] == "reused-uuid"
        # The retry identity must not displace authentication.
        assert "Authorization" in headers
