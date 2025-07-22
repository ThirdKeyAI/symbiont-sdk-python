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
            "max_tokens": 2000
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
            "max_tokens": 100
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "top_p": 0.9
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
        expected_missing = {"name", "description", "system_prompt", "tools", "model", "temperature", "top_p", "max_tokens"}
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
            "max_tokens": 2000
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
            "max_tokens": 2000
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
            "max_tokens": "invalid"  # Should be int
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
            "max_tokens": 2000
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Agent(**agent_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("tools",)
        assert "list_type" in errors[0]["type"]