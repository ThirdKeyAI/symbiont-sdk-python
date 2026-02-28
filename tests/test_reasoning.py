"""Unit tests for reasoning models."""

import pytest
from symbiont.reasoning import (
    CedarPolicy,
    CircuitBreakerConfig,
    CircuitBreakerStatus,
    CircuitState,
    FinishReason,
    InferenceOptions,
    InferenceResponse,
    JournalEntry,
    KnowledgeConfig,
    LoopConfig,
    LoopDecision,
    LoopDecisionType,
    LoopEvent,
    LoopEventType,
    LoopResult,
    LoopState,
    Observation,
    ProposedAction,
    ProposedActionType,
    RecoveryStrategy,
    RecoveryStrategyType,
    RunReasoningLoopRequest,
    RunReasoningLoopResponse,
    TerminationReason,
    TerminationReasonType,
    ToolCallRequest,
    ToolDefinition,
    Usage,
)


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    def test_finish_reason_values(self):
        assert FinishReason.STOP == "stop"
        assert FinishReason.TOOL_CALLS == "tool_calls"
        assert FinishReason.MAX_TOKENS == "max_tokens"
        assert FinishReason.CONTENT_FILTER == "content_filter"

    def test_proposed_action_type_values(self):
        assert ProposedActionType.TOOL_CALL == "tool_call"
        assert ProposedActionType.DELEGATE == "delegate"
        assert ProposedActionType.RESPOND == "respond"
        assert ProposedActionType.TERMINATE == "terminate"

    def test_loop_decision_type_values(self):
        assert LoopDecisionType.ALLOW == "allow"
        assert LoopDecisionType.DENY == "deny"
        assert LoopDecisionType.MODIFY == "modify"

    def test_circuit_state_values(self):
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"

    def test_termination_reason_type_values(self):
        assert TerminationReasonType.COMPLETED == "completed"
        assert TerminationReasonType.POLICY_DENIAL == "policy_denial"
        assert TerminationReasonType.ERROR == "error"

    def test_recovery_strategy_type_values(self):
        assert RecoveryStrategyType.RETRY == "retry"
        assert RecoveryStrategyType.DEAD_LETTER == "dead_letter"
        assert RecoveryStrategyType.ESCALATE == "escalate"

    def test_loop_event_type_values(self):
        assert LoopEventType.STARTED == "started"
        assert LoopEventType.TERMINATED == "terminated"
        assert LoopEventType.RECOVERY_TRIGGERED == "recovery_triggered"


# =============================================================================
# Inference Model Tests
# =============================================================================

class TestUsage:
    def test_construction(self):
        u = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert u.prompt_tokens == 10
        assert u.total_tokens == 30

    def test_roundtrip(self):
        u = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        data = u.model_dump()
        u2 = Usage.model_validate(data)
        assert u2 == u


class TestToolDefinition:
    def test_construction(self):
        td = ToolDefinition(name="search", description="Search the web", parameters={"type": "object"})
        assert td.name == "search"


class TestToolCallRequest:
    def test_construction(self):
        tc = ToolCallRequest(id="c-1", name="search", arguments='{"q":"test"}')
        assert tc.name == "search"


class TestInferenceOptions:
    def test_defaults(self):
        opts = InferenceOptions(max_tokens=1000)
        assert opts.temperature == 0.7
        assert opts.tool_definitions == []
        assert opts.model is None

    def test_with_model_override(self):
        opts = InferenceOptions(max_tokens=500, model="gpt-4o")
        assert opts.model == "gpt-4o"


class TestInferenceResponse:
    def test_construction(self):
        resp = InferenceResponse(
            content="Hello",
            finish_reason=FinishReason.STOP,
            usage=Usage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
            model="gpt-4",
        )
        assert resp.content == "Hello"
        assert resp.tool_calls == []


# =============================================================================
# Loop Model Tests
# =============================================================================

class TestObservation:
    def test_defaults(self):
        obs = Observation(source="tool:search", content="result data")
        assert obs.is_error is False
        assert obs.metadata == {}


class TestProposedAction:
    def test_tool_call(self):
        a = ProposedAction(
            type=ProposedActionType.TOOL_CALL,
            call_id="c-1",
            name="search",
            arguments='{"q":"hi"}',
        )
        assert a.type == "tool_call"
        assert a.name == "search"

    def test_respond(self):
        a = ProposedAction(type=ProposedActionType.RESPOND, content="The answer is 42")
        assert a.content == "The answer is 42"

    def test_terminate(self):
        a = ProposedAction(type=ProposedActionType.TERMINATE, reason="done", output="result")
        assert a.reason == "done"

    def test_roundtrip(self):
        a = ProposedAction(type=ProposedActionType.DELEGATE, target="agent-2", message="help")
        data = a.model_dump()
        a2 = ProposedAction.model_validate(data)
        assert a2.type == ProposedActionType.DELEGATE
        assert a2.target == "agent-2"


class TestLoopDecision:
    def test_allow(self):
        d = LoopDecision(decision=LoopDecisionType.ALLOW)
        assert d.reason is None

    def test_deny(self):
        d = LoopDecision(decision=LoopDecisionType.DENY, reason="not allowed")
        assert d.reason == "not allowed"

    def test_modify(self):
        action = ProposedAction(type=ProposedActionType.RESPOND, content="sanitized")
        d = LoopDecision(decision=LoopDecisionType.MODIFY, modified_action=action, reason="redacted")
        assert d.modified_action is not None


class TestRecoveryStrategy:
    def test_retry(self):
        s = RecoveryStrategy(type=RecoveryStrategyType.RETRY, max_attempts=3, base_delay_ms=1000)
        assert s.max_attempts == 3

    def test_dead_letter(self):
        s = RecoveryStrategy(type=RecoveryStrategyType.DEAD_LETTER)
        assert s.type == "dead_letter"

    def test_escalate(self):
        s = RecoveryStrategy(type=RecoveryStrategyType.ESCALATE, queue="ops", context_snapshot=True)
        assert s.queue == "ops"


class TestTerminationReason:
    def test_completed(self):
        t = TerminationReason(type=TerminationReasonType.COMPLETED)
        assert t.reason is None

    def test_policy_denial(self):
        t = TerminationReason(type=TerminationReasonType.POLICY_DENIAL, reason="blocked")
        assert t.reason == "blocked"

    def test_error(self):
        t = TerminationReason(type=TerminationReasonType.ERROR, message="crash")
        assert t.message == "crash"


class TestLoopConfig:
    def test_defaults(self):
        c = LoopConfig()
        assert c.max_iterations == 10
        assert c.max_total_tokens == 100000
        assert c.timeout_ms == 300000
        assert c.default_recovery.type == RecoveryStrategyType.DEAD_LETTER

    def test_override(self):
        c = LoopConfig(max_iterations=5)
        assert c.max_iterations == 5


class TestLoopState:
    def test_construction(self):
        s = LoopState(
            agent_id="agent-1",
            iteration=2,
            total_usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            started_at="2026-01-01T00:00:00Z",
            current_phase="reasoning",
        )
        assert s.iteration == 2
        assert s.pending_observations == []


class TestLoopResult:
    def test_construction(self):
        r = LoopResult(
            output="Done",
            iterations=3,
            total_usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            termination_reason=TerminationReason(type=TerminationReasonType.COMPLETED),
            duration_ms=5000,
        )
        assert r.output == "Done"
        assert r.termination_reason.type == "completed"


# =============================================================================
# Journal Model Tests
# =============================================================================

class TestLoopEvent:
    def test_started(self):
        e = LoopEvent(type=LoopEventType.STARTED, agent_id="a-1", config=LoopConfig())
        assert e.type == "started"

    def test_terminated(self):
        e = LoopEvent(
            type=LoopEventType.TERMINATED,
            reason=TerminationReason(type=TerminationReasonType.COMPLETED),
            iterations=5,
            total_usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            duration_ms=10000,
        )
        assert e.iterations == 5


class TestJournalEntry:
    def test_construction(self):
        entry = JournalEntry(
            sequence=0,
            timestamp="2026-01-01T00:00:00Z",
            agent_id="agent-1",
            iteration=0,
            event=LoopEvent(type=LoopEventType.STARTED, agent_id="agent-1", config=LoopConfig()),
        )
        assert entry.sequence == 0

    def test_roundtrip(self):
        entry = JournalEntry(
            sequence=1,
            timestamp="2026-01-01T00:00:01Z",
            agent_id="agent-1",
            iteration=1,
            event=LoopEvent(
                type=LoopEventType.REASONING_COMPLETE,
                iteration=1,
                actions=[ProposedAction(type=ProposedActionType.RESPOND, content="hi")],
                usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            ),
        )
        data = entry.model_dump()
        entry2 = JournalEntry.model_validate(data)
        assert entry2.sequence == 1
        assert entry2.event.type == LoopEventType.REASONING_COMPLETE


# =============================================================================
# Cedar / Knowledge / Circuit Breaker Tests
# =============================================================================

class TestCedarPolicy:
    def test_default_active(self):
        p = CedarPolicy(name="deny-all", source="forbid(principal,action,resource);")
        assert p.active is True

    def test_inactive(self):
        p = CedarPolicy(name="p1", source="src", active=False)
        assert p.active is False


class TestKnowledgeConfig:
    def test_defaults(self):
        c = KnowledgeConfig()
        assert c.max_context_items == 5
        assert c.relevance_threshold == 0.7
        assert c.auto_persist is False


class TestCircuitBreakerConfig:
    def test_defaults(self):
        c = CircuitBreakerConfig()
        assert c.failure_threshold == 5
        assert c.recovery_timeout_ms == 30000
        assert c.half_open_max_calls == 3


class TestCircuitBreakerStatus:
    def test_construction(self):
        s = CircuitBreakerStatus(
            state=CircuitState.CLOSED,
            failure_count=0,
            success_count=10,
            config=CircuitBreakerConfig(),
        )
        assert s.state == "closed"
        assert s.success_count == 10


# =============================================================================
# API Request / Response Tests
# =============================================================================

class TestRunReasoningLoopRequest:
    def test_minimal(self):
        r = RunReasoningLoopRequest(config=LoopConfig(), initial_message="Hello")
        assert r.initial_message == "Hello"
        assert r.cedar_policies is None


class TestRunReasoningLoopResponse:
    def test_construction(self):
        r = RunReasoningLoopResponse(
            loop_id="loop-1",
            result=LoopResult(
                output="Done",
                iterations=2,
                total_usage=Usage(prompt_tokens=50, completion_tokens=25, total_tokens=75),
                termination_reason=TerminationReason(type=TerminationReasonType.COMPLETED),
                duration_ms=3000,
            ),
        )
        assert r.loop_id == "loop-1"
        assert r.journal_entries == []
