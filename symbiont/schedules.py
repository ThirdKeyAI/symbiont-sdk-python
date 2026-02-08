"""Schedule management for the Symbiont SDK.

Provides CRUD operations and lifecycle management for cron-scheduled agent jobs
via the Symbiont Runtime API.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import APIError, NotFoundError


@dataclass
class CreateScheduleRequest:
    """Request to create a new scheduled job."""

    name: str
    cron_expression: str
    agent_name: str
    timezone: str = "UTC"
    policy_ids: List[str] = field(default_factory=list)
    one_shot: bool = False


@dataclass
class CreateScheduleResponse:
    """Response after creating a schedule."""

    job_id: str
    next_run: Optional[str]
    status: str


@dataclass
class UpdateScheduleRequest:
    """Request to update an existing schedule."""

    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    policy_ids: Optional[List[str]] = None
    one_shot: Optional[bool] = None


@dataclass
class ScheduleSummary:
    """Summary of a scheduled job (list view)."""

    job_id: str
    name: str
    cron_expression: str
    timezone: str
    status: str
    enabled: bool
    next_run: Optional[str]
    run_count: int


@dataclass
class ScheduleDetail:
    """Full detail of a scheduled job."""

    job_id: str
    name: str
    cron_expression: str
    timezone: str
    status: str
    enabled: bool
    one_shot: bool
    next_run: Optional[str]
    last_run: Optional[str]
    run_count: int
    failure_count: int
    created_at: str
    updated_at: str


@dataclass
class ScheduleRunEntry:
    """A single run history entry."""

    run_id: str
    started_at: str
    completed_at: Optional[str]
    status: str
    error: Optional[str]
    execution_time_ms: Optional[int]


@dataclass
class ScheduleHistoryResponse:
    """Run history for a scheduled job."""

    job_id: str
    history: List[ScheduleRunEntry]


@dataclass
class NextRunsResponse:
    """Next N computed run times."""

    job_id: str
    next_runs: List[str]


@dataclass
class ScheduleActionResponse:
    """Response for pause/resume/trigger actions."""

    job_id: str
    action: str
    status: str


@dataclass
class DeleteScheduleResponse:
    """Response for deleting a schedule."""

    job_id: str
    deleted: bool


class ScheduleClient:
    """Client for managing cron schedules via the Symbiont Runtime API.

    This class is typically accessed through the main ``Client`` instance::

        from symbiont import Client
        client = Client()
        schedules = client.schedules.list_schedules()
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
        return self._client._request(method, path, json=json, params=params)

    def list_schedules(self) -> List[ScheduleSummary]:
        """List all scheduled jobs. ``GET /schedules``"""
        data = self._request("GET", "/schedules")
        return [ScheduleSummary(**item) for item in data]

    def create_schedule(self, request: CreateScheduleRequest) -> CreateScheduleResponse:
        """Create a new scheduled job. ``POST /schedules``"""
        payload = {
            "name": request.name,
            "cron_expression": request.cron_expression,
            "agent_name": request.agent_name,
            "timezone": request.timezone,
            "policy_ids": request.policy_ids,
            "one_shot": request.one_shot,
        }
        data = self._request("POST", "/schedules", json=payload)
        return CreateScheduleResponse(**data)

    def get_schedule(self, job_id: str) -> ScheduleDetail:
        """Get details of a scheduled job. ``GET /schedules/{id}``"""
        data = self._request("GET", f"/schedules/{job_id}")
        return ScheduleDetail(**data)

    def update_schedule(
        self, job_id: str, request: UpdateScheduleRequest
    ) -> ScheduleDetail:
        """Update a scheduled job. ``PUT /schedules/{id}``"""
        payload: Dict[str, Any] = {}
        if request.cron_expression is not None:
            payload["cron_expression"] = request.cron_expression
        if request.timezone is not None:
            payload["timezone"] = request.timezone
        if request.policy_ids is not None:
            payload["policy_ids"] = request.policy_ids
        if request.one_shot is not None:
            payload["one_shot"] = request.one_shot
        data = self._request("PUT", f"/schedules/{job_id}", json=payload)
        return ScheduleDetail(**data)

    def delete_schedule(self, job_id: str) -> DeleteScheduleResponse:
        """Delete a scheduled job. ``DELETE /schedules/{id}``"""
        data = self._request("DELETE", f"/schedules/{job_id}")
        return DeleteScheduleResponse(**data)

    def pause_schedule(self, job_id: str) -> ScheduleActionResponse:
        """Pause a scheduled job. ``POST /schedules/{id}/pause``"""
        data = self._request("POST", f"/schedules/{job_id}/pause")
        return ScheduleActionResponse(**data)

    def resume_schedule(self, job_id: str) -> ScheduleActionResponse:
        """Resume a paused job. ``POST /schedules/{id}/resume``"""
        data = self._request("POST", f"/schedules/{job_id}/resume")
        return ScheduleActionResponse(**data)

    def trigger_schedule(self, job_id: str) -> ScheduleActionResponse:
        """Force-trigger a job immediately. ``POST /schedules/{id}/trigger``"""
        data = self._request("POST", f"/schedules/{job_id}/trigger")
        return ScheduleActionResponse(**data)

    def get_schedule_history(
        self, job_id: str, limit: int = 50
    ) -> ScheduleHistoryResponse:
        """Get run history. ``GET /schedules/{id}/history``"""
        data = self._request(
            "GET", f"/schedules/{job_id}/history", params={"limit": limit}
        )
        history = [ScheduleRunEntry(**entry) for entry in data.get("history", [])]
        return ScheduleHistoryResponse(job_id=data["job_id"], history=history)

    def get_schedule_next_runs(
        self, job_id: str, count: int = 10
    ) -> NextRunsResponse:
        """Get next N run times. ``GET /schedules/{id}/next-runs``"""
        data = self._request(
            "GET", f"/schedules/{job_id}/next-runs", params={"count": count}
        )
        return NextRunsResponse(**data)
