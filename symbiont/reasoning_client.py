"""Reasoning loop client for the Symbiont SDK.

Provides methods for reasoning loop, journal, Cedar policy, circuit breaker,
and knowledge bridge operations via the Symbiont Runtime API.
"""

from typing import Any, Dict, List, Optional

from .reasoning import (
    CedarPolicy,
    CircuitBreakerStatus,
    JournalEntry,
    LoopDecision,
    LoopState,
    ProposedAction,
    RunReasoningLoopRequest,
    RunReasoningLoopResponse,
)


class ReasoningClient:
    """Client for reasoning loop operations via the Symbiont Runtime API.

    This class is typically accessed through the main ``Client`` instance::

        from symbiont import Client
        client = Client()
        response = client.reasoning.run_loop("agent-1", request)
    """

    def __init__(self, parent_client: Any) -> None:
        self._client = parent_client

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated request through the parent client."""
        response = self._client._request(method, path, json=json, params=params)
        return response.json()

    # -------------------------------------------------------------------------
    # Reasoning Loop
    # -------------------------------------------------------------------------

    def run_loop(
        self, agent_id: str, request: RunReasoningLoopRequest
    ) -> RunReasoningLoopResponse:
        """Start a reasoning loop. ``POST /api/v1/agents/{id}/reasoning/loop``"""
        data = self._request(
            "POST",
            f"/api/v1/agents/{agent_id}/reasoning/loop",
            json=request.model_dump(),
        )
        return RunReasoningLoopResponse(**data)

    def get_loop_status(self, agent_id: str, loop_id: str) -> LoopState:
        """Get loop status. ``GET /api/v1/agents/{id}/reasoning/loop/{loop_id}``"""
        data = self._request(
            "GET", f"/api/v1/agents/{agent_id}/reasoning/loop/{loop_id}"
        )
        return LoopState(**data)

    def cancel_loop(self, agent_id: str, loop_id: str) -> None:
        """Cancel a running loop. ``DELETE /api/v1/agents/{id}/reasoning/loop/{loop_id}``"""
        self._request(
            "DELETE", f"/api/v1/agents/{agent_id}/reasoning/loop/{loop_id}"
        )

    # -------------------------------------------------------------------------
    # Journal
    # -------------------------------------------------------------------------

    def get_journal_entries(
        self,
        agent_id: str,
        from_sequence: int = 0,
        limit: int = 100,
    ) -> List[JournalEntry]:
        """Get journal entries. ``GET /api/v1/agents/{id}/reasoning/journal``"""
        data = self._request(
            "GET",
            f"/api/v1/agents/{agent_id}/reasoning/journal",
            params={"from_sequence": from_sequence, "limit": limit},
        )
        return [JournalEntry(**entry) for entry in data]

    def compact_journal(self, agent_id: str) -> Dict[str, int]:
        """Compact journal entries. ``POST /api/v1/agents/{id}/reasoning/journal/compact``"""
        return self._request(
            "POST", f"/api/v1/agents/{agent_id}/reasoning/journal/compact"
        )

    # -------------------------------------------------------------------------
    # Cedar Policies
    # -------------------------------------------------------------------------

    def list_cedar_policies(self, agent_id: str) -> List[CedarPolicy]:
        """List Cedar policies. ``GET /api/v1/agents/{id}/reasoning/cedar``"""
        data = self._request(
            "GET", f"/api/v1/agents/{agent_id}/reasoning/cedar"
        )
        return [CedarPolicy(**item) for item in data]

    def add_cedar_policy(self, agent_id: str, policy: CedarPolicy) -> None:
        """Add a Cedar policy. ``POST /api/v1/agents/{id}/reasoning/cedar``"""
        self._request(
            "POST",
            f"/api/v1/agents/{agent_id}/reasoning/cedar",
            json=policy.model_dump(),
        )

    def remove_cedar_policy(self, agent_id: str, policy_name: str) -> bool:
        """Remove a Cedar policy. ``DELETE /api/v1/agents/{id}/reasoning/cedar/{name}``"""
        data = self._request(
            "DELETE", f"/api/v1/agents/{agent_id}/reasoning/cedar/{policy_name}"
        )
        return data.get("removed", False)

    def evaluate_cedar_policy(
        self, agent_id: str, action: ProposedAction
    ) -> LoopDecision:
        """Evaluate a Cedar policy. ``POST /api/v1/agents/{id}/reasoning/cedar/evaluate``"""
        data = self._request(
            "POST",
            f"/api/v1/agents/{agent_id}/reasoning/cedar/evaluate",
            json=action.model_dump(),
        )
        return LoopDecision(**data)

    # -------------------------------------------------------------------------
    # Circuit Breakers
    # -------------------------------------------------------------------------

    def get_circuit_breaker_status(
        self, agent_id: str
    ) -> Dict[str, CircuitBreakerStatus]:
        """Get circuit breaker status. ``GET /api/v1/agents/{id}/reasoning/circuit-breakers``"""
        data = self._request(
            "GET", f"/api/v1/agents/{agent_id}/reasoning/circuit-breakers"
        )
        return {k: CircuitBreakerStatus(**v) for k, v in data.items()}

    def reset_circuit_breaker(self, agent_id: str, tool_name: str) -> None:
        """Reset a circuit breaker. ``POST /api/v1/agents/{id}/reasoning/circuit-breakers/{tool}/reset``"""
        self._request(
            "POST",
            f"/api/v1/agents/{agent_id}/reasoning/circuit-breakers/{tool_name}/reset",
        )

    # -------------------------------------------------------------------------
    # Knowledge Bridge
    # -------------------------------------------------------------------------

    def recall_knowledge(
        self, agent_id: str, query: str, limit: int = 5
    ) -> List[str]:
        """Recall knowledge. ``POST /api/v1/agents/{id}/reasoning/knowledge/recall``"""
        return self._request(
            "POST",
            f"/api/v1/agents/{agent_id}/reasoning/knowledge/recall",
            json={"query": query, "limit": limit},
        )

    def store_knowledge(
        self,
        agent_id: str,
        subject: str,
        predicate: str,
        object: str,
        confidence: float = 0.8,
    ) -> Dict[str, str]:
        """Store knowledge. ``POST /api/v1/agents/{id}/reasoning/knowledge/store``"""
        return self._request(
            "POST",
            f"/api/v1/agents/{agent_id}/reasoning/knowledge/store",
            json={
                "subject": subject,
                "predicate": predicate,
                "object": object,
                "confidence": confidence,
            },
        )
