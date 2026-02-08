"""Channel adapter management for the Symbiont SDK.

Provides CRUD operations, lifecycle management, and enterprise features
(identity mappings, audit logs) for channel adapters via the Symbiont Runtime API.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RegisterChannelRequest:
    """Request to register a new channel adapter."""

    name: str
    platform: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegisterChannelResponse:
    """Response after registering a channel."""

    id: str
    name: str
    platform: str
    status: str


@dataclass
class UpdateChannelRequest:
    """Request to update an existing channel."""

    config: Optional[Dict[str, Any]] = None


@dataclass
class ChannelSummary:
    """Summary of a channel adapter (list view)."""

    id: str
    name: str
    platform: str
    status: str


@dataclass
class ChannelDetail:
    """Detailed channel adapter information."""

    id: str
    name: str
    platform: str
    status: str
    config: Dict[str, Any]
    created_at: str
    updated_at: str


@dataclass
class ChannelActionResponse:
    """Generic action response for start/stop."""

    id: str
    action: str
    status: str


@dataclass
class DeleteChannelResponse:
    """Response for deleting a channel."""

    id: str
    deleted: bool


@dataclass
class ChannelHealthResponse:
    """Channel health and connectivity info."""

    id: str
    connected: bool
    platform: str
    workspace_name: Optional[str]
    channels_active: int
    last_message_at: Optional[str]
    uptime_secs: int


# ── Enterprise types ────────────────────────────────────────────


@dataclass
class IdentityMappingEntry:
    """Identity mapping between a platform user and a Symbiont user."""

    platform_user_id: str
    platform: str
    symbiont_user_id: str
    email: Optional[str]
    display_name: str
    roles: List[str]
    verified: bool
    created_at: str


@dataclass
class AddIdentityMappingRequest:
    """Request to add an identity mapping."""

    platform_user_id: str
    symbiont_user_id: str
    display_name: str
    roles: List[str] = field(default_factory=list)
    email: Optional[str] = None


@dataclass
class ChannelAuditEntry:
    """A single channel audit log entry."""

    timestamp: str
    event_type: str
    user_id: Optional[str]
    channel_id: Optional[str]
    agent: Optional[str]
    details: Dict[str, Any]


@dataclass
class ChannelAuditResponse:
    """Response for channel audit log queries."""

    channel_id: str
    entries: List[ChannelAuditEntry]


class ChannelClient:
    """Client for managing channel adapters via the Symbiont Runtime API.

    This class is typically accessed through the main ``Client`` instance::

        from symbiont import Client
        client = Client()
        channels = client.channels.list_channels()
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

    # ── Community endpoints ─────────────────────────────────────

    def list_channels(self) -> List[ChannelSummary]:
        """List all registered channel adapters. ``GET /channels``"""
        data = self._request("GET", "/channels")
        return [ChannelSummary(**item) for item in data]

    def register_channel(
        self, request: RegisterChannelRequest
    ) -> RegisterChannelResponse:
        """Register a new channel adapter. ``POST /channels``"""
        payload = {
            "name": request.name,
            "platform": request.platform,
            "config": request.config,
        }
        data = self._request("POST", "/channels", json=payload)
        return RegisterChannelResponse(**data)

    def get_channel(self, channel_id: str) -> ChannelDetail:
        """Get details of a channel adapter. ``GET /channels/{id}``"""
        data = self._request("GET", f"/channels/{channel_id}")
        return ChannelDetail(**data)

    def update_channel(
        self, channel_id: str, request: UpdateChannelRequest
    ) -> ChannelDetail:
        """Update a channel adapter. ``PUT /channels/{id}``"""
        payload: Dict[str, Any] = {}
        if request.config is not None:
            payload["config"] = request.config
        data = self._request("PUT", f"/channels/{channel_id}", json=payload)
        return ChannelDetail(**data)

    def delete_channel(self, channel_id: str) -> DeleteChannelResponse:
        """Delete a channel adapter. ``DELETE /channels/{id}``"""
        data = self._request("DELETE", f"/channels/{channel_id}")
        return DeleteChannelResponse(**data)

    def start_channel(self, channel_id: str) -> ChannelActionResponse:
        """Start a channel adapter. ``POST /channels/{id}/start``"""
        data = self._request("POST", f"/channels/{channel_id}/start")
        return ChannelActionResponse(**data)

    def stop_channel(self, channel_id: str) -> ChannelActionResponse:
        """Stop a channel adapter. ``POST /channels/{id}/stop``"""
        data = self._request("POST", f"/channels/{channel_id}/stop")
        return ChannelActionResponse(**data)

    def get_channel_health(self, channel_id: str) -> ChannelHealthResponse:
        """Get channel health info. ``GET /channels/{id}/health``"""
        data = self._request("GET", f"/channels/{channel_id}/health")
        return ChannelHealthResponse(**data)

    # ── Enterprise endpoints ────────────────────────────────────

    def list_mappings(self, channel_id: str) -> List[IdentityMappingEntry]:
        """List identity mappings. ``GET /channels/{id}/mappings``"""
        data = self._request("GET", f"/channels/{channel_id}/mappings")
        return [IdentityMappingEntry(**item) for item in data]

    def add_mapping(
        self, channel_id: str, request: AddIdentityMappingRequest
    ) -> IdentityMappingEntry:
        """Add an identity mapping. ``POST /channels/{id}/mappings``"""
        payload = {
            "platform_user_id": request.platform_user_id,
            "symbiont_user_id": request.symbiont_user_id,
            "display_name": request.display_name,
            "roles": request.roles,
        }
        if request.email is not None:
            payload["email"] = request.email
        data = self._request(
            "POST", f"/channels/{channel_id}/mappings", json=payload
        )
        return IdentityMappingEntry(**data)

    def remove_mapping(self, channel_id: str, user_id: str) -> None:
        """Remove an identity mapping. ``DELETE /channels/{id}/mappings/{user_id}``"""
        self._client._request(
            "DELETE", f"/channels/{channel_id}/mappings/{user_id}"
        )

    def query_audit(
        self, channel_id: str, limit: int = 50
    ) -> ChannelAuditResponse:
        """Get audit log entries. ``GET /channels/{id}/audit``"""
        data = self._request(
            "GET", f"/channels/{channel_id}/audit", params={"limit": limit}
        )
        entries = [ChannelAuditEntry(**entry) for entry in data.get("entries", [])]
        return ChannelAuditResponse(
            channel_id=data["channel_id"], entries=entries
        )
