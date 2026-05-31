"""Symbiont SDK API Client."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .auth import AuthManager, AuthUser
from .channels import ChannelClient
from .config import ClientConfig, ConfigManager
from .exceptions import (
    APIError,
    AuthenticationError,
    AuthenticationExpiredError,
    ConfigurationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    TokenRefreshError,
)
from .models import (
    # Agent models
    Agent,
    AgentStatusResponse,
    # System models
    HealthResponse,
    SystemMetrics,
    # Workflow models
    WorkflowExecutionRequest,
)
from .schedules import ScheduleClient


class Client:
    """Main API client for the Symbiont Agent Runtime System."""

    def __init__(
        self,
        config: Optional[Union[ClientConfig, Dict[str, Any], str, Path]] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize the Symbiont API client.

        Args:
            config: Configuration object, dictionary, or path to config file.
                   If None, loads from environment variables and defaults.
            api_key: API key for authentication. Overrides config if provided.
            base_url: Base URL for the API. Overrides config if provided.
        """
        # Initialize configuration manager
        self._config_manager = ConfigManager()

        # Load configuration
        if isinstance(config, (str, Path)):
            # Config file path provided
            self.config = self._config_manager.load(config)
        elif isinstance(config, dict):
            # Dictionary config provided
            self.config = ClientConfig(**config)
        elif isinstance(config, ClientConfig):
            # Configuration object provided
            self.config = config
            self._config_manager._config = config
        else:
            # Load from environment and defaults
            self.config = self._config_manager.load()

        # Override with explicit parameters
        if api_key:
            self.config.api_key = api_key
        if base_url:
            self.config.base_url = base_url.rstrip("/")

        # Validate configuration
        config_errors = self._config_manager.validate_required_settings()
        if config_errors:
            error_msg = "Configuration validation failed: " + "; ".join(
                f"{key}: {msg}" for key, msg in config_errors.items()
            )
            raise ConfigurationError(error_msg)

        # Initialize authentication manager
        self.auth_manager = AuthManager(self.config.auth)
        self._current_user: Optional[AuthUser] = None
        self._current_tokens: Dict[str, str] = {}
        self._last_token_refresh = 0

        # Request rate limiting
        self._request_count = 0
        self._request_window_start = time.time()

        # Backward compatibility properties
        self.api_key = self.config.api_key
        self.base_url = self.config.base_url

        # Lazy-loaded sub-clients
        self._schedules: Optional[ScheduleClient] = None
        self._channels: Optional[ChannelClient] = None
        self._agentpin: Optional[Any] = None
        self._metrics_client: Optional[Any] = None

    @property
    def schedules(self) -> ScheduleClient:
        """Lazy-loaded schedule management client."""
        if self._schedules is None:
            self._schedules = ScheduleClient(self)
        return self._schedules

    @property
    def channels(self) -> ChannelClient:
        """Lazy-loaded channel adapter management client."""
        if self._channels is None:
            self._channels = ChannelClient(self)
        return self._channels

    @property
    def agentpin(self):
        """Lazy-loaded AgentPin client for credential verification and discovery."""
        if self._agentpin is None:
            from .agentpin import AgentPinClient

            self._agentpin = AgentPinClient(self)
        return self._agentpin

    @property
    def metrics_client(self):
        """Lazy-loaded metrics client for runtime metrics queries."""
        if self._metrics_client is None:
            from .metrics import MetricsClient

            self._metrics_client = MetricsClient(self)
        return self._metrics_client

    def _request(self, method: str, endpoint: str, **kwargs):
        """Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (without leading slash)
            **kwargs: Additional arguments to pass to requests

        Returns:
            requests.Response: The response object

        Raises:
            AuthenticationError: For 401 Unauthorized responses
            AuthenticationExpiredError: For expired tokens
            TokenRefreshError: For token refresh failures
            NotFoundError: For 404 Not Found responses
            RateLimitError: For 429 Too Many Requests responses
            APIError: For other 4xx and 5xx responses
        """
        # De-duplicate the API version prefix in exactly one place. The
        # configured ``base_url`` is expected to include the version segment
        # (the default is ``http://localhost:8080/api/v1``). Some call sites
        # historically passed endpoints that ALSO carried an ``api/v1/``
        # prefix, producing a doubled ``/api/v1/api/v1/`` path that 404s
        # against the runtime. When ``base_url`` already ends with
        # ``/api/v1``, strip a leading ``api/v1/`` from the endpoint so the
        # version segment appears exactly once. Base URLs with a different
        # prefix (or none) are left untouched, preserving the behavior of
        # custom deployments.
        endpoint_clean = endpoint.lstrip("/")
        if self.config.base_url.rstrip("/").endswith(
            "/api/v1"
        ) and endpoint_clean.startswith("api/v1/"):
            endpoint_clean = endpoint_clean[len("api/v1/") :]
        url = f"{self.config.base_url}/{endpoint_clean}"

        # Set default headers
        headers = kwargs.pop("headers", {})

        # Add authentication headers
        self._add_auth_headers(headers)

        # Add timeout if not specified
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.config.timeout

        # Make the request with retry logic
        max_retries = self.config.max_retries
        for attempt in range(max_retries + 1):
            try:
                response = requests.request(method, url, headers=headers, **kwargs)

                # Handle successful response
                if 200 <= response.status_code < 300:
                    return response

                # Handle authentication errors with potential token refresh
                if response.status_code == 401:
                    if attempt < max_retries and self._try_refresh_token():
                        # Token refreshed, update headers and retry
                        self._add_auth_headers(headers)
                        continue
                    else:
                        # No refresh possible or refresh failed
                        if "expired" in response.text.lower():
                            raise AuthenticationExpiredError(
                                "Authentication token has expired",
                                response_text=response.text,
                            )
                        else:
                            raise AuthenticationError(
                                "Authentication failed - check your credentials",
                                response_text=response.text,
                            )

                # Handle other error responses
                response_text = response.text

                if response.status_code == 403:
                    raise PermissionDeniedError(
                        "Insufficient permissions for this operation",
                        response_text=response_text,
                    )
                elif response.status_code == 404:
                    raise NotFoundError(
                        "Resource not found", response_text=response_text
                    )
                elif response.status_code == 429:
                    raise RateLimitError(
                        "Rate limit exceeded - too many requests",
                        response_text=response_text,
                    )
                else:
                    # Handle other 4xx and 5xx errors
                    raise APIError(
                        f"API request failed with status {response.status_code}",
                        status_code=response.status_code,
                        response_text=response_text,
                    )

            except requests.RequestException as e:
                if attempt == max_retries:
                    raise APIError(
                        f"Request failed after {max_retries + 1} attempts: {e}"
                    ) from e
                time.sleep(2**attempt)  # Exponential backoff

        # This should never be reached
        raise APIError("Unexpected error in request handling")

    def _add_auth_headers(self, headers: Dict[str, str]) -> None:
        """Add authentication headers to the request.

        Args:
            headers: Headers dictionary to modify
        """
        if self._current_tokens.get("access"):
            headers["Authorization"] = f'Bearer {self._current_tokens["access"]}'
        elif self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

    def _try_refresh_token(self) -> bool:
        """Try to refresh the access token using refresh token.

        Returns:
            True if token was refreshed successfully, False otherwise
        """
        if not self.config.auth.enable_refresh_tokens:
            return False

        refresh_token = self._current_tokens.get("refresh")
        if not refresh_token:
            return False

        try:
            new_token = self.auth_manager.refresh_access_token(refresh_token)
            if new_token:
                self._current_tokens["access"] = new_token.token
                self._last_token_refresh = time.time()
                return True
        except Exception:
            # Token refresh failed, clear tokens
            self._current_tokens.clear()
            self._current_user = None

        return False

    # =============================================================================
    # Phase 1 Enhanced Authentication Methods
    # =============================================================================

    def configure_client(self, config: ClientConfig) -> Dict[str, Any]:
        """Configure the client with new configuration.

        Args:
            config: New client configuration

        Returns:
            Configuration confirmation
        """
        self.config = config
        self._config_manager._config = config
        self.auth_manager = AuthManager(config.auth)

        # Update backward compatibility properties
        self.api_key = config.api_key
        self.base_url = config.base_url

        return {"status": "configured", "timestamp": time.time()}

    def get_configuration(self) -> ClientConfig:
        """Get current client configuration.

        Returns:
            Current configuration
        """
        return self.config

    def reload_configuration(self) -> Dict[str, Any]:
        """Reload configuration from sources.

        Returns:
            Reload confirmation
        """
        self.config = self._config_manager.reload()
        self.auth_manager = AuthManager(self.config.auth)

        # Update backward compatibility properties
        self.api_key = self.config.api_key
        self.base_url = self.config.base_url

        return {"status": "reloaded", "timestamp": time.time()}

    def authenticate_jwt(self, token: str) -> Dict[str, Any]:
        """Authenticate using JWT token.

        Args:
            token: JWT token for authentication

        Returns:
            Authentication response
        """
        user = self.auth_manager.authenticate_with_jwt(token)
        if user:
            self._current_user = user
            self._current_tokens["access"] = token

            return {
                "user_id": user.user_id,
                "roles": user.roles,
                "permissions": [p.value for p in user.permissions],
                "authenticated": True,
            }
        else:
            raise AuthenticationError("Invalid JWT token")

    def refresh_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token.

        Returns:
            Token refresh response
        """
        refresh_token = self._current_tokens.get("refresh")
        if not refresh_token:
            raise TokenRefreshError("No refresh token available")

        new_token = self.auth_manager.refresh_access_token(refresh_token)
        if new_token:
            self._current_tokens["access"] = new_token.token
            self._last_token_refresh = time.time()

            return {
                "access_token": new_token.token,
                "token_type": "Bearer",  # nosec B105
                "expires_in": self.config.auth.jwt_expiration_seconds,
            }
        else:
            raise TokenRefreshError("Failed to refresh token")

    def validate_permissions(self, action: str, resource: str = None) -> bool:
        """Validate if current user has permission for an action.

        Args:
            action: Action to validate
            resource: Optional resource identifier

        Returns:
            True if user has permission, False otherwise
        """
        if not self._current_user:
            return False

        return self.auth_manager.validate_permissions(
            self._current_user, action, resource
        )

    def get_user_roles(self) -> List[str]:
        """Get current user's roles.

        Returns:
            List of role names
        """
        if not self._current_user:
            return []
        return self.auth_manager.get_user_roles(self._current_user)

    # =============================================================================
    # System & Health Methods
    # =============================================================================

    def health_check(self) -> HealthResponse:
        """Get system health status.

        Returns:
            HealthResponse: System health information
        """
        response = self._request("GET", "health")
        return HealthResponse(**response.json())

    def get_metrics(self) -> SystemMetrics:
        """Get enhanced system metrics.

        Returns:
            SystemMetrics: Comprehensive system metrics
        """
        response = self._request("GET", "metrics")
        return SystemMetrics(**response.json())

    # =============================================================================
    # Agent Management Methods
    # =============================================================================

    def list_agents(self) -> List[str]:
        """List all agents.

        Returns:
            List[str]: List of agent IDs
        """
        response = self._request("GET", "agents")
        return response.json()

    def get_agent_status(self, agent_id: str) -> AgentStatusResponse:
        """Get status of a specific agent.

        Args:
            agent_id: The agent identifier

        Returns:
            AgentStatusResponse: Agent status information
        """
        response = self._request("GET", f"agents/{agent_id}/status")
        return AgentStatusResponse(**response.json())

    # =============================================================================
    # Workflow Execution Methods
    # =============================================================================

    def execute_workflow(
        self, workflow_request: Union[WorkflowExecutionRequest, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a workflow.

        Args:
            workflow_request: Workflow execution request

        Returns:
            Dict[str, Any]: Workflow execution result
        """
        if isinstance(workflow_request, dict):
            workflow_request = WorkflowExecutionRequest(**workflow_request)

        response = self._request(
            "POST", "workflows/execute", json=workflow_request.model_dump()
        )
        return response.json()

    # =============================================================================
    # Convenience Methods
    # =============================================================================

    def create_agent(self, agent_data: Union[Agent, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new agent (if supported by the runtime).

        Args:
            agent_data: Agent configuration

        Returns:
            Dict[str, Any]: Created agent information
        """
        if isinstance(agent_data, dict):
            agent_data = Agent(**agent_data)

        response = self._request("POST", "agents", json=agent_data.model_dump())
        return response.json()

    # =============================================================================
    # Agent Lifecycle Methods
    # =============================================================================

    def delete_agent(self, agent_id: str) -> Dict:
        """Delete an agent and its metadata.

        Args:
            agent_id: The agent identifier

        Returns:
            Dict: Deletion confirmation
        """
        response = self._request("DELETE", f"agents/{agent_id}")
        return response.json()

    def execute_agent(self, agent_id: str) -> Dict:
        """Execute an agent immediately.

        Triggers a fresh execution of an existing agent. Maps to
        ``POST /api/v1/agents/{id}/execute`` on the runtime.

        Args:
            agent_id: The agent identifier

        Returns:
            Dict: ``{"execution_id": str, "status": str}``
        """
        response = self._request("POST", f"api/v1/agents/{agent_id}/execute", json={})
        return response.json()

    # =============================================================================
    # Inter-Agent Messaging Methods
    # =============================================================================

    def send_message(
        self,
        agent_id: str,
        sender: str,
        payload: str,
        ttl_seconds: Optional[int] = None,
        topic: Optional[str] = None,
        agentpin_jwt: Optional[str] = None,
    ) -> Dict:
        """Send a message to an agent via the runtime message bus.

        Maps to ``POST /api/v1/agents/{id}/messages``. The payload is
        plaintext; the receiving runtime handles bus-level encryption
        internally. If ``topic`` is set the message is published to the
        topic instead of delivered directly.

        Args:
            agent_id: The recipient agent identifier (URL path).
            sender: The sender agent identifier.
            payload: Plaintext message body.
            ttl_seconds: Optional TTL in seconds (runtime default 300).
            topic: Optional pub/sub topic.
            agentpin_jwt: Optional AgentPin JWT. Required when the
                receiving runtime enforces AgentPin verification.

        Returns:
            Dict: ``{"message_id": str, "status": str}``
        """
        body: Dict[str, Any] = {"sender": sender, "payload": payload}
        if ttl_seconds is not None:
            body["ttl_seconds"] = ttl_seconds
        if topic is not None:
            body["topic"] = topic
        if agentpin_jwt is not None:
            body["agentpin_jwt"] = agentpin_jwt
        response = self._request(
            "POST", f"api/v1/agents/{agent_id}/messages", json=body
        )
        return response.json()

    def receive_messages(self, agent_id: str) -> Dict:
        """Receive and consume an agent's pending messages.

        Maps to ``GET /api/v1/agents/{id}/messages``. Returns the
        plaintext message envelopes queued for the agent and removes
        them from the queue.

        Args:
            agent_id: The agent identifier.

        Returns:
            Dict: ``{"messages": [MessageEnvelope, ...]}`` where each
            envelope carries ``message_id``, ``sender``, ``recipient``,
            ``topic``, ``payload``, ``message_type``, ``timestamp_secs``,
            and ``ttl_seconds``.
        """
        response = self._request("GET", f"api/v1/agents/{agent_id}/messages")
        return response.json()

    def get_message_status(self, message_id: str) -> Dict:
        """Get the delivery status of a previously sent message.

        Maps to ``GET /api/v1/messages/{id}/status``.

        Args:
            message_id: The message identifier returned by
                :meth:`send_message`.

        Returns:
            Dict: ``{"message_id": str, "status": str}`` where status is
            one of ``"pending"``, ``"delivered"``, ``"failed"``,
            ``"expired"``.
        """
        response = self._request("GET", f"api/v1/messages/{message_id}/status")
        return response.json()

    # =============================================================================
    # External Agent Lifecycle Methods (Heartbeat & Events)
    # =============================================================================

    def send_heartbeat(
        self,
        agent_id: str,
        state: str,
        metadata: Optional[Dict[str, str]] = None,
        last_result: Optional[str] = None,
        agentpin_jwt: Optional[str] = None,
    ) -> None:
        """Report a heartbeat for an externally-running agent.

        Maps to ``POST /api/v1/agents/{id}/heartbeat``. Used by agents
        running outside the runtime (remote, containerized, cloud) to
        report liveness and current state.

        Args:
            agent_id: The agent identifier.
            state: Current agent state, e.g. ``"Running"``,
                ``"Completed"``, ``"Failed"`` (matches the runtime
                ``AgentState`` variants, PascalCase).
            metadata: Optional key/value metadata update.
            last_result: Optional summary of the last execution.
            agentpin_jwt: Optional AgentPin JWT. Required when the
                runtime enforces AgentPin verification.
        """
        body: Dict[str, Any] = {"state": state}
        if metadata is not None:
            body["metadata"] = metadata
        if last_result is not None:
            body["last_result"] = last_result
        if agentpin_jwt is not None:
            body["agentpin_jwt"] = agentpin_jwt
        self._request("POST", f"api/v1/agents/{agent_id}/heartbeat", json=body)

    def push_agent_event(
        self,
        agent_id: str,
        event_type: str,
        payload: Any,
        agentpin_jwt: Optional[str] = None,
    ) -> None:
        """Push a lifecycle event from an externally-running agent.

        Maps to ``POST /api/v1/agents/{id}/events``.

        Args:
            agent_id: The agent identifier.
            event_type: One of ``"RunStarted"``, ``"RunCompleted"``,
                ``"RunFailed"`` (matches the runtime ``AgentEventType``
                variants, PascalCase).
            payload: Event-specific JSON-serializable data.
            agentpin_jwt: Optional AgentPin JWT. Required when the
                runtime enforces AgentPin verification.
        """
        body: Dict[str, Any] = {"event_type": event_type, "payload": payload}
        if agentpin_jwt is not None:
            body["agentpin_jwt"] = agentpin_jwt
        self._request("POST", f"api/v1/agents/{agent_id}/events", json=body)
