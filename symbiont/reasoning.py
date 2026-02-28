"""Reasoning loop models for the Symbiont SDK.

Maps Rust runtime types from crates/runtime/src/reasoning/.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================

class FinishReason(str, Enum):
    """Reason the model stopped generating."""
    STOP = "stop"
    TOOL_CALLS = "tool_calls"
    MAX_TOKENS = "max_tokens"
    CONTENT_FILTER = "content_filter"


class ProposedActionType(str, Enum):
    """Type of proposed action from the reasoning loop."""
    TOOL_CALL = "tool_call"
    DELEGATE = "delegate"
    RESPOND = "respond"
    TERMINATE = "terminate"


class LoopDecisionType(str, Enum):
    """Policy gate decision for a proposed action."""
    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"


class TerminationReasonType(str, Enum):
    """Reason the reasoning loop terminated."""
    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    MAX_TOKENS = "max_tokens"
    TIMEOUT = "timeout"
    POLICY_DENIAL = "policy_denial"
    ERROR = "error"


class RecoveryStrategyType(str, Enum):
    """Recovery strategy when a tool call fails."""
    RETRY = "retry"
    FALLBACK = "fallback"
    CACHED_RESULT = "cached_result"
    LLM_RECOVERY = "llm_recovery"
    ESCALATE = "escalate"
    DEAD_LETTER = "dead_letter"


class LoopEventType(str, Enum):
    """Type of event in the reasoning loop journal."""
    STARTED = "started"
    REASONING_COMPLETE = "reasoning_complete"
    POLICY_EVALUATED = "policy_evaluated"
    TOOLS_DISPATCHED = "tools_dispatched"
    OBSERVATIONS_COLLECTED = "observations_collected"
    TERMINATED = "terminated"
    RECOVERY_TRIGGERED = "recovery_triggered"


class CircuitState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# =============================================================================
# Inference Models
# =============================================================================

class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = Field(..., description="Tokens in prompt/input")
    completion_tokens: int = Field(..., description="Tokens in completion/output")
    total_tokens: int = Field(..., description="Total tokens used")


class ToolDefinition(BaseModel):
    """Tool available to the reasoning loop."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Human-readable description")
    parameters: Any = Field(..., description="JSON Schema for parameters")


class ToolCallRequest(BaseModel):
    """Request to invoke a tool."""
    id: str = Field(..., description="Unique call identifier")
    name: str = Field(..., description="Name of tool to invoke")
    arguments: str = Field(..., description="JSON-encoded arguments")


class InferenceOptions(BaseModel):
    """Options for an LLM inference call."""
    max_tokens: int = Field(..., description="Max tokens to generate")
    temperature: float = Field(0.7, description="Sampling temperature")
    tool_definitions: List[ToolDefinition] = Field(default_factory=list, description="Available tools")
    response_format: Dict[str, Any] = Field(default_factory=lambda: {"type": "text"}, description="Response format")
    model: Optional[str] = Field(None, description="Optional model override")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific params")


class InferenceResponse(BaseModel):
    """Response from an LLM inference call."""
    content: str = Field(..., description="Text content of response")
    tool_calls: List[ToolCallRequest] = Field(default_factory=list, description="Tool calls if any")
    finish_reason: FinishReason = Field(..., description="Why generation stopped")
    usage: Usage = Field(..., description="Token usage stats")
    model: str = Field(..., description="Model that served the request")


# =============================================================================
# Loop Models
# =============================================================================

class Observation(BaseModel):
    """Observation from a tool execution or external source."""
    source: str = Field(..., description="Source of the observation")
    content: str = Field(..., description="The observation content")
    is_error: bool = Field(False, description="Whether this is an error")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Metadata for logging/auditing")


class ProposedAction(BaseModel):
    """Action proposed by the reasoning loop."""
    type: ProposedActionType = Field(..., description="Action type")
    # ToolCall fields
    call_id: Optional[str] = Field(None, description="Unique call identifier (tool_call)")
    name: Optional[str] = Field(None, description="Tool name (tool_call)")
    arguments: Optional[str] = Field(None, description="JSON-encoded arguments (tool_call)")
    # Delegate fields
    target: Optional[str] = Field(None, description="Target agent identifier (delegate)")
    message: Optional[str] = Field(None, description="Message to send (delegate)")
    # Respond fields
    content: Optional[str] = Field(None, description="Response content (respond)")
    # Terminate fields
    reason: Optional[str] = Field(None, description="Reason for termination (terminate)")
    output: Optional[str] = Field(None, description="Final output (terminate)")


class LoopDecision(BaseModel):
    """Decision from the policy gate."""
    decision: LoopDecisionType = Field(..., description="Decision type")
    reason: Optional[str] = Field(None, description="Reason for deny/modify")
    modified_action: Optional[ProposedAction] = Field(None, description="Modified action (modify only)")


class RecoveryStrategy(BaseModel):
    """Strategy for recovering from tool failures."""
    type: RecoveryStrategyType = Field(..., description="Strategy type")
    # Retry fields
    max_attempts: Optional[int] = Field(None, description="Max retry attempts (retry)")
    base_delay_ms: Optional[int] = Field(None, description="Base delay in ms (retry)")
    # Fallback fields
    alternatives: Optional[List[str]] = Field(None, description="Alternative tools (fallback)")
    # CachedResult fields
    max_staleness_ms: Optional[int] = Field(None, description="Max cache staleness in ms (cached_result)")
    # LlmRecovery fields
    max_recovery_attempts: Optional[int] = Field(None, description="Max LLM recovery attempts (llm_recovery)")
    # Escalate fields
    queue: Optional[str] = Field(None, description="Escalation queue (escalate)")
    context_snapshot: Optional[bool] = Field(None, description="Include context snapshot (escalate)")


class TerminationReason(BaseModel):
    """Reason the reasoning loop terminated."""
    type: TerminationReasonType = Field(..., description="Termination type")
    reason: Optional[str] = Field(None, description="Reason for policy_denial")
    message: Optional[str] = Field(None, description="Error message (error)")


class LoopConfig(BaseModel):
    """Configuration for a reasoning loop run."""
    max_iterations: int = Field(10, description="Maximum iterations before forced termination")
    max_total_tokens: int = Field(100000, description="Maximum tokens before forced termination")
    timeout_ms: int = Field(300000, description="Maximum wall-clock time in ms")
    default_recovery: RecoveryStrategy = Field(
        default_factory=lambda: RecoveryStrategy(type=RecoveryStrategyType.DEAD_LETTER),
        description="Default recovery strategy",
    )
    tool_timeout_ms: int = Field(30000, description="Per-tool timeout in ms")
    max_concurrent_tools: int = Field(4, description="Max concurrent tool calls")
    context_token_budget: int = Field(4096, description="Token budget for context window")
    tool_definitions: List[ToolDefinition] = Field(default_factory=list, description="Available tools")


class LoopState(BaseModel):
    """Current state of a reasoning loop."""
    agent_id: str = Field(..., description="Agent identity")
    iteration: int = Field(..., description="Current iteration (0-indexed)")
    total_usage: Usage = Field(..., description="Cumulative token usage")
    pending_observations: List[Observation] = Field(default_factory=list, description="Pending observations")
    started_at: str = Field(..., description="Timestamp when loop started")
    current_phase: str = Field(..., description="Current loop phase")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class LoopResult(BaseModel):
    """Result of a completed reasoning loop."""
    output: str = Field(..., description="Final response content")
    iterations: int = Field(..., description="Total iterations")
    total_usage: Usage = Field(..., description="Total token usage")
    termination_reason: TerminationReason = Field(..., description="Why loop terminated")
    duration_ms: int = Field(..., description="Wall-clock duration in ms")


# =============================================================================
# Journal Models
# =============================================================================

class LoopEvent(BaseModel):
    """Event recorded in the reasoning loop journal."""
    type: LoopEventType = Field(..., description="Event type")
    # Started fields
    agent_id: Optional[str] = Field(None, description="Agent ID (started)")
    config: Optional[LoopConfig] = Field(None, description="Loop config (started)")
    # ReasoningComplete / PolicyEvaluated / ToolsDispatched / ObservationsCollected fields
    iteration: Optional[int] = Field(None, description="Iteration number")
    actions: Optional[List[ProposedAction]] = Field(None, description="Proposed actions (reasoning_complete)")
    usage: Optional[Usage] = Field(None, description="Token usage (reasoning_complete)")
    action_count: Optional[int] = Field(None, description="Action count (policy_evaluated)")
    denied_count: Optional[int] = Field(None, description="Denied count (policy_evaluated)")
    tool_count: Optional[int] = Field(None, description="Tool count (tools_dispatched)")
    duration_ms: Optional[int] = Field(None, description="Duration in ms (tools_dispatched, terminated)")
    observation_count: Optional[int] = Field(None, description="Observation count (observations_collected)")
    # Terminated fields
    reason: Optional[TerminationReason] = Field(None, description="Termination reason (terminated)")
    iterations: Optional[int] = Field(None, description="Total iterations (terminated)")
    total_usage: Optional[Usage] = Field(None, description="Total usage (terminated)")
    # RecoveryTriggered fields
    tool_name: Optional[str] = Field(None, description="Tool name (recovery_triggered)")
    strategy: Optional[RecoveryStrategy] = Field(None, description="Recovery strategy (recovery_triggered)")
    error: Optional[str] = Field(None, description="Error message (recovery_triggered)")


class JournalEntry(BaseModel):
    """Entry in the reasoning loop journal."""
    sequence: int = Field(..., description="Monotonically increasing sequence")
    timestamp: str = Field(..., description="When entry was created")
    agent_id: str = Field(..., description="Agent this entry belongs to")
    iteration: int = Field(..., description="Iteration it was created in")
    event: LoopEvent = Field(..., description="The event recorded")


# =============================================================================
# Cedar Policy Models
# =============================================================================

class CedarPolicy(BaseModel):
    """Cedar policy source definition."""
    name: str = Field(..., description="Unique policy name")
    source: str = Field(..., description="Cedar policy source text")
    active: bool = Field(True, description="Whether policy is active")


# =============================================================================
# Knowledge Bridge Models
# =============================================================================

class KnowledgeConfig(BaseModel):
    """Configuration for the knowledge bridge."""
    max_context_items: int = Field(5, description="Max items to inject per iteration")
    relevance_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Relevance threshold")
    auto_persist: bool = Field(False, description="Auto-store learnings after loop")


# =============================================================================
# Circuit Breaker Models
# =============================================================================

class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = Field(5, ge=1, description="Failures before opening")
    recovery_timeout_ms: int = Field(30000, ge=0, description="Open to HalfOpen delay in ms")
    half_open_max_calls: int = Field(3, ge=1, description="Max calls in HalfOpen")


class CircuitBreakerStatus(BaseModel):
    """Current status of a circuit breaker."""
    state: CircuitState = Field(..., description="Current circuit state")
    failure_count: int = Field(..., ge=0, description="Consecutive failure count")
    success_count: int = Field(..., ge=0, description="Success count")
    config: CircuitBreakerConfig = Field(..., description="Breaker configuration")


# =============================================================================
# API Request / Response Models
# =============================================================================

class RunReasoningLoopRequest(BaseModel):
    """Request to start a reasoning loop."""
    config: LoopConfig = Field(..., description="Loop configuration")
    initial_message: str = Field(..., description="Initial message to start the loop")
    inference_options: Optional[InferenceOptions] = Field(None, description="Inference options")
    cedar_policies: Optional[List[CedarPolicy]] = Field(None, description="Cedar policies to apply")
    knowledge_config: Optional[KnowledgeConfig] = Field(None, description="Knowledge bridge config")


class RunReasoningLoopResponse(BaseModel):
    """Response from a reasoning loop run."""
    loop_id: str = Field(..., description="Unique loop execution ID")
    result: LoopResult = Field(..., description="Loop result")
    journal_entries: List[JournalEntry] = Field(default_factory=list, description="Journal entries")
