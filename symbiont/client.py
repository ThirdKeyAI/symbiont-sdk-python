"""Symbiont SDK API Client."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .auth import AuthManager, AuthUser
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
    AgentDeployRequest,
    AgentDeployResponse,
    AgentMetrics,
    AgentStatusResponse,
    AnalysisResults,
    # Phase 3 Qdrant Integration models
    CollectionCreateRequest,
    CollectionInfo,
    CollectionResponse,
    ConsolidationResponse,
    # Configuration models (Phase 1)
    ContextQuery,
    ContextResponse,
    ConversationContext,
    # Agent DSL models
    DslCompileRequest,
    DslCompileResponse,
    EndpointMetrics,
    # System models
    HealthResponse,
    # Phase 4 HTTP Endpoint Management models
    HttpEndpointCreateRequest,
    HttpEndpointInfo,
    HttpEndpointResponse,
    HttpEndpointUpdateRequest,
    HttpInputCreateRequest,
    HttpInputServerInfo,
    HttpInputUpdateRequest,
    HumanReviewDecision,
    # Vector Database & RAG models
    KnowledgeItem,
    McpConnectionInfo,
    McpResourceInfo,
    # MCP Management models
    McpServerConfig,
    McpToolInfo,
    MemoryQuery,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    # Phase 2 Memory System models
    MemoryStoreRequest,
    ReviewSession,
    ReviewSessionCreate,
    ReviewSessionList,
    ReviewSessionResponse,
    # Secrets Management models
    SecretBackendConfig,
    SecretListResponse,
    SecretRequest,
    SecretResponse,
    SignedTool,
    SigningRequest,
    SigningResponse,
    SystemMetrics,
    UpsertResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorUpsertRequest,
    WebhookTriggerRequest,
    WebhookTriggerResponse,
    WorkflowExecutionRequest,
)
from .channels import ChannelClient
from .schedules import ScheduleClient


class Client:
    """Main API client for the Symbiont Agent Runtime System."""

    def __init__(self,
                 config: Optional[Union[ClientConfig, Dict[str, Any], str, Path]] = None,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None):
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
            self.config.base_url = base_url.rstrip('/')

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
        url = f"{self.config.base_url}/{endpoint.lstrip('/')}"

        # Set default headers
        headers = kwargs.pop('headers', {})

        # Add authentication headers
        self._add_auth_headers(headers)

        # Add timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.config.timeout

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
                        if 'expired' in response.text.lower():
                            raise AuthenticationExpiredError(
                                "Authentication token has expired",
                                response_text=response.text
                            )
                        else:
                            raise AuthenticationError(
                                "Authentication failed - check your credentials",
                                response_text=response.text
                            )

                # Handle other error responses
                response_text = response.text

                if response.status_code == 403:
                    raise PermissionDeniedError(
                        "Insufficient permissions for this operation",
                        response_text=response_text
                    )
                elif response.status_code == 404:
                    raise NotFoundError(
                        "Resource not found",
                        response_text=response_text
                    )
                elif response.status_code == 429:
                    raise RateLimitError(
                        "Rate limit exceeded - too many requests",
                        response_text=response_text
                    )
                else:
                    # Handle other 4xx and 5xx errors
                    raise APIError(
                        f"API request failed with status {response.status_code}",
                        status_code=response.status_code,
                        response_text=response_text
                    )

            except requests.RequestException as e:
                if attempt == max_retries:
                    raise APIError(f"Request failed after {max_retries + 1} attempts: {e}") from e
                time.sleep(2 ** attempt)  # Exponential backoff

        # This should never be reached
        raise APIError("Unexpected error in request handling")

    def _add_auth_headers(self, headers: Dict[str, str]) -> None:
        """Add authentication headers to the request.

        Args:
            headers: Headers dictionary to modify
        """
        if self._current_tokens.get('access'):
            headers['Authorization'] = f'Bearer {self._current_tokens["access"]}'
        elif self.config.api_key:
            headers['Authorization'] = f'Bearer {self.config.api_key}'

    def _try_refresh_token(self) -> bool:
        """Try to refresh the access token using refresh token.

        Returns:
            True if token was refreshed successfully, False otherwise
        """
        if not self.config.auth.enable_refresh_tokens:
            return False

        refresh_token = self._current_tokens.get('refresh')
        if not refresh_token:
            return False

        try:
            new_token = self.auth_manager.refresh_access_token(refresh_token)
            if new_token:
                self._current_tokens['access'] = new_token.token
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
            self._current_tokens['access'] = token

            return {
                "user_id": user.user_id,
                "roles": user.roles,
                "permissions": [p.value for p in user.permissions],
                "authenticated": True
            }
        else:
            raise AuthenticationError("Invalid JWT token")

    def refresh_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token.

        Returns:
            Token refresh response
        """
        refresh_token = self._current_tokens.get('refresh')
        if not refresh_token:
            raise TokenRefreshError("No refresh token available")

        new_token = self.auth_manager.refresh_access_token(refresh_token)
        if new_token:
            self._current_tokens['access'] = new_token.token
            self._last_token_refresh = time.time()

            return {
                "access_token": new_token.token,
                "token_type": "Bearer",
                "expires_in": self.config.auth.jwt_expiration_seconds
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

    def get_agent_metrics(self, agent_id: str) -> AgentMetrics:
        """Get metrics for a specific agent.

        Args:
            agent_id: The agent identifier

        Returns:
            AgentMetrics: Agent-specific metrics
        """
        response = self._request("GET", f"agents/{agent_id}/metrics")
        return AgentMetrics(**response.json())

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
        response = self._request("GET", f"agents/{agent_id}")
        return AgentStatusResponse(**response.json())

    # =============================================================================
    # Workflow Execution Methods
    # =============================================================================

    def execute_workflow(self, workflow_request: Union[WorkflowExecutionRequest, Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a workflow.

        Args:
            workflow_request: Workflow execution request

        Returns:
            Dict[str, Any]: Workflow execution result
        """
        if isinstance(workflow_request, dict):
            workflow_request = WorkflowExecutionRequest(**workflow_request)

        response = self._request("POST", "workflows", json=workflow_request.model_dump())
        return response.json()

    # =============================================================================
    # Tool Review API Methods
    # =============================================================================

    def submit_tool_for_review(self, review_request: Union[ReviewSessionCreate, Dict[str, Any]]) -> ReviewSessionResponse:
        """Submit a tool for security review.

        Args:
            review_request: Tool review request

        Returns:
            ReviewSessionResponse: Review session information
        """
        if isinstance(review_request, dict):
            review_request = ReviewSessionCreate(**review_request)

        response = self._request("POST", "tool-review/sessions", json=review_request.model_dump())
        return ReviewSessionResponse(**response.json())

    def get_review_session(self, review_id: str) -> ReviewSession:
        """Get details of a specific review session.

        Args:
            review_id: The review session identifier

        Returns:
            ReviewSession: Review session details
        """
        response = self._request("GET", f"tool-review/sessions/{review_id}")
        return ReviewSession(**response.json())

    def list_review_sessions(self,
                           page: int = 1,
                           limit: int = 20,
                           status: Optional[str] = None,
                           author: Optional[str] = None) -> ReviewSessionList:
        """List review sessions with optional filtering.

        Args:
            page: Page number for pagination
            limit: Number of items per page
            status: Filter by review status
            author: Filter by tool author

        Returns:
            ReviewSessionList: List of review sessions with pagination
        """
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status
        if author:
            params["author"] = author

        response = self._request("GET", "tool-review/sessions", params=params)
        return ReviewSessionList(**response.json())

    def get_analysis_results(self, analysis_id: str) -> AnalysisResults:
        """Get detailed security analysis results.

        Args:
            analysis_id: The analysis identifier

        Returns:
            AnalysisResults: Security analysis results
        """
        response = self._request("GET", f"tool-review/analysis/{analysis_id}")
        return AnalysisResults(**response.json())

    def submit_human_review_decision(self, review_id: str, decision: Union[HumanReviewDecision, Dict[str, Any]]) -> Dict[str, Any]:
        """Submit a human review decision.

        Args:
            review_id: The review session identifier
            decision: Human review decision

        Returns:
            Dict[str, Any]: Decision submission result
        """
        if isinstance(decision, dict):
            decision = HumanReviewDecision(**decision)

        response = self._request("POST", f"tool-review/sessions/{review_id}/decisions", json=decision.model_dump())
        return response.json()

    def sign_approved_tool(self, signing_request: Union[SigningRequest, Dict[str, Any]]) -> SigningResponse:
        """Sign an approved tool.

        Args:
            signing_request: Tool signing request

        Returns:
            SigningResponse: Signing operation result
        """
        if isinstance(signing_request, dict):
            signing_request = SigningRequest(**signing_request)

        response = self._request("POST", "tool-review/sign", json=signing_request.model_dump())
        return SigningResponse(**response.json())

    def get_signed_tool(self, review_id: str) -> SignedTool:
        """Get signed tool information.

        Args:
            review_id: The review session identifier

        Returns:
            SignedTool: Signed tool information
        """
        response = self._request("GET", f"tool-review/signed/{review_id}")
        return SignedTool(**response.json())

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

    def wait_for_review_completion(self, review_id: str, timeout: int = 300) -> ReviewSession:
        """Wait for a review session to complete.

        Args:
            review_id: The review session identifier
            timeout: Maximum wait time in seconds

        Returns:
            ReviewSession: Final review session state

        Raises:
            TimeoutError: If review doesn't complete within timeout
        """
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            session = self.get_review_session(review_id)
            if session.status in ["approved", "rejected", "signed"]:
                return session
            time.sleep(5)  # Check every 5 seconds

        raise TimeoutError(f"Review {review_id} did not complete within {timeout} seconds")

    # =============================================================================
    # Secrets Management Methods
    # =============================================================================

    def configure_secret_backend(self, config: Union[SecretBackendConfig, Dict[str, Any]]) -> Dict[str, Any]:
        """Configure the secrets backend.

        Args:
            config: Secret backend configuration

        Returns:
            Dict[str, Any]: Configuration confirmation
        """
        if isinstance(config, dict):
            config = SecretBackendConfig(**config)

        response = self._request("POST", "secrets/config", json=config.model_dump())
        return response.json()

    def store_secret(self, secret_request: Union[SecretRequest, Dict[str, Any]]) -> SecretResponse:
        """Store a secret for an agent.

        Args:
            secret_request: Secret storage request

        Returns:
            SecretResponse: Secret storage confirmation
        """
        if isinstance(secret_request, dict):
            secret_request = SecretRequest(**secret_request)

        response = self._request("POST", "secrets", json=secret_request.model_dump())
        return SecretResponse(**response.json())

    def get_secret(self, agent_id: str, secret_name: str) -> str:
        """Retrieve a secret value.

        Args:
            agent_id: The agent identifier
            secret_name: Name of the secret

        Returns:
            str: The secret value
        """
        response = self._request("GET", f"secrets/{agent_id}/{secret_name}")
        return response.json()["value"]

    def list_secrets(self, agent_id: str) -> SecretListResponse:
        """List all secrets for an agent.

        Args:
            agent_id: The agent identifier

        Returns:
            SecretListResponse: List of secret names
        """
        response = self._request("GET", f"secrets/{agent_id}")
        return SecretListResponse(**response.json())

    def delete_secret(self, agent_id: str, secret_name: str) -> Dict[str, Any]:
        """Delete a secret.

        Args:
            agent_id: The agent identifier
            secret_name: Name of the secret to delete

        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        response = self._request("DELETE", f"secrets/{agent_id}/{secret_name}")
        return response.json()

    # =============================================================================
    # MCP Management Methods
    # =============================================================================

    def add_mcp_server(self, config: Union[McpServerConfig, Dict[str, Any]]) -> Dict[str, Any]:
        """Add a new MCP server configuration.

        Args:
            config: MCP server configuration

        Returns:
            Dict[str, Any]: Addition confirmation
        """
        if isinstance(config, dict):
            config = McpServerConfig(**config)

        response = self._request("POST", "mcp/servers", json=config.model_dump())
        return response.json()

    def list_mcp_servers(self) -> List[McpConnectionInfo]:
        """List all configured MCP servers.

        Returns:
            List[McpConnectionInfo]: MCP server information
        """
        response = self._request("GET", "mcp/servers")
        return [McpConnectionInfo(**server) for server in response.json()]

    def get_mcp_server(self, server_name: str) -> McpConnectionInfo:
        """Get information about a specific MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            McpConnectionInfo: MCP server information
        """
        response = self._request("GET", f"mcp/servers/{server_name}")
        return McpConnectionInfo(**response.json())

    def connect_mcp_server(self, server_name: str) -> Dict[str, Any]:
        """Connect to an MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Dict[str, Any]: Connection result
        """
        response = self._request("POST", f"mcp/servers/{server_name}/connect")
        return response.json()

    def disconnect_mcp_server(self, server_name: str) -> Dict[str, Any]:
        """Disconnect from an MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Dict[str, Any]: Disconnection result
        """
        response = self._request("POST", f"mcp/servers/{server_name}/disconnect")
        return response.json()

    def list_mcp_tools(self, server_name: Optional[str] = None) -> List[McpToolInfo]:
        """List available MCP tools.

        Args:
            server_name: Optional server name to filter by

        Returns:
            List[McpToolInfo]: Available MCP tools
        """
        endpoint = "mcp/tools"
        params = {}
        if server_name:
            params["server"] = server_name

        response = self._request("GET", endpoint, params=params)
        return [McpToolInfo(**tool) for tool in response.json()]

    def list_mcp_resources(self, server_name: Optional[str] = None) -> List[McpResourceInfo]:
        """List available MCP resources.

        Args:
            server_name: Optional server name to filter by

        Returns:
            List[McpResourceInfo]: Available MCP resources
        """
        endpoint = "mcp/resources"
        params = {}
        if server_name:
            params["server"] = server_name

        response = self._request("GET", endpoint, params=params)
        return [McpResourceInfo(**resource) for resource in response.json()]

    # =============================================================================
    # Vector Database & RAG Methods
    # =============================================================================

    def add_knowledge_item(self, item: Union[KnowledgeItem, Dict[str, Any]]) -> Dict[str, Any]:
        """Add a knowledge item to the vector database.

        Args:
            item: Knowledge item to add

        Returns:
            Dict[str, Any]: Addition confirmation
        """
        if isinstance(item, dict):
            item = KnowledgeItem(**item)

        response = self._request("POST", "knowledge", json=item.model_dump())
        return response.json()

    def search_knowledge(self, search_request: Union[VectorSearchRequest, Dict[str, Any]]) -> VectorSearchResponse:
        """Search the knowledge base using vector similarity.

        Args:
            search_request: Vector search request

        Returns:
            VectorSearchResponse: Search results
        """
        if isinstance(search_request, dict):
            search_request = VectorSearchRequest(**search_request)

        response = self._request("POST", "knowledge/search", json=search_request.model_dump())
        return VectorSearchResponse(**response.json())

    def get_context(self, context_query: Union[ContextQuery, Dict[str, Any]]) -> ContextResponse:
        """Get relevant context for RAG operations.

        Args:
            context_query: Context query request

        Returns:
            ContextResponse: Relevant context information
        """
        if isinstance(context_query, dict):
            context_query = ContextQuery(**context_query)

        response = self._request("POST", "rag/context", json=context_query.model_dump())
        return ContextResponse(**response.json())

    def delete_knowledge_item(self, item_id: str) -> Dict[str, Any]:
        """Delete a knowledge item from the vector database.

        Args:
            item_id: ID of the knowledge item to delete

        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        response = self._request("DELETE", f"knowledge/{item_id}")
        return response.json()

    # =============================================================================
    # Agent DSL Methods
    # =============================================================================

    def compile_dsl(self, compile_request: Union[DslCompileRequest, Dict[str, Any]]) -> DslCompileResponse:
        """Compile DSL code into an agent.

        Args:
            compile_request: DSL compilation request

        Returns:
            DslCompileResponse: Compilation result
        """
        if isinstance(compile_request, dict):
            compile_request = DslCompileRequest(**compile_request)

        response = self._request("POST", "dsl/compile", json=compile_request.model_dump())
        return DslCompileResponse(**response.json())

    def deploy_agent(self, deploy_request: Union[AgentDeployRequest, Dict[str, Any]]) -> AgentDeployResponse:
        """Deploy a compiled agent.

        Args:
            deploy_request: Agent deployment request

        Returns:
            AgentDeployResponse: Deployment result
        """
        if isinstance(deploy_request, dict):
            deploy_request = AgentDeployRequest(**deploy_request)

        response = self._request("POST", "agents/deploy", json=deploy_request.model_dump())
        return AgentDeployResponse(**response.json())

    def get_agent_deployment(self, deployment_id: str) -> AgentDeployResponse:
        """Get information about an agent deployment.

        Args:
            deployment_id: The deployment identifier

        Returns:
            AgentDeployResponse: Deployment information
        """
        response = self._request("GET", f"agents/deployments/{deployment_id}")
        return AgentDeployResponse(**response.json())

    def list_agent_deployments(self, agent_id: Optional[str] = None) -> List[AgentDeployResponse]:
        """List agent deployments.

        Args:
            agent_id: Optional agent ID to filter by

        Returns:
            List[AgentDeployResponse]: Agent deployments
        """
        endpoint = "agents/deployments"
        params = {}
        if agent_id:
            params["agent_id"] = agent_id

        response = self._request("GET", endpoint, params=params)
        return [AgentDeployResponse(**deployment) for deployment in response.json()]

    def stop_agent_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Stop an agent deployment.

        Args:
            deployment_id: The deployment identifier

        Returns:
            Dict[str, Any]: Stop confirmation
        """
        response = self._request("POST", f"agents/deployments/{deployment_id}/stop")
        return response.json()

    # =============================================================================
    # HTTP Input Methods
    # =============================================================================

    def create_http_input_server(self, request: Union[HttpInputCreateRequest, Dict[str, Any]]) -> HttpInputServerInfo:
        """Create and start an HTTP input server.

        Args:
            request: HTTP input server creation request

        Returns:
            HttpInputServerInfo: Server information
        """
        if isinstance(request, dict):
            request = HttpInputCreateRequest(**request)

        response = self._request("POST", "http-input/servers", json=request.model_dump())
        return HttpInputServerInfo(**response.json())

    def list_http_input_servers(self) -> List[HttpInputServerInfo]:
        """List all HTTP input servers.

        Returns:
            List[HttpInputServerInfo]: List of server information
        """
        response = self._request("GET", "http-input/servers")
        return [HttpInputServerInfo(**server) for server in response.json()]

    def get_http_input_server(self, server_id: str) -> HttpInputServerInfo:
        """Get information about a specific HTTP input server.

        Args:
            server_id: The server identifier

        Returns:
            HttpInputServerInfo: Server information
        """
        response = self._request("GET", f"http-input/servers/{server_id}")
        return HttpInputServerInfo(**response.json())

    def update_http_input_server(self, request: Union[HttpInputUpdateRequest, Dict[str, Any]]) -> HttpInputServerInfo:
        """Update an HTTP input server configuration.

        Args:
            request: HTTP input server update request

        Returns:
            HttpInputServerInfo: Updated server information
        """
        if isinstance(request, dict):
            request = HttpInputUpdateRequest(**request)

        response = self._request("PUT", f"http-input/servers/{request.server_id}", json=request.model_dump())
        return HttpInputServerInfo(**response.json())

    def start_http_input_server(self, server_id: str) -> Dict[str, Any]:
        """Start an HTTP input server.

        Args:
            server_id: The server identifier

        Returns:
            Dict[str, Any]: Start confirmation
        """
        response = self._request("POST", f"http-input/servers/{server_id}/start")
        return response.json()

    def stop_http_input_server(self, server_id: str) -> Dict[str, Any]:
        """Stop an HTTP input server.

        Args:
            server_id: The server identifier

        Returns:
            Dict[str, Any]: Stop confirmation
        """
        response = self._request("POST", f"http-input/servers/{server_id}/stop")
        return response.json()

    def delete_http_input_server(self, server_id: str) -> Dict[str, Any]:
        """Delete an HTTP input server.

        Args:
            server_id: The server identifier

        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        response = self._request("DELETE", f"http-input/servers/{server_id}")
        return response.json()

    def trigger_webhook(self, request: Union[WebhookTriggerRequest, Dict[str, Any]]) -> WebhookTriggerResponse:
        """Manually trigger a webhook for testing purposes.

        Args:
            request: Webhook trigger request

        Returns:
            WebhookTriggerResponse: Trigger response
        """
        if isinstance(request, dict):
            request = WebhookTriggerRequest(**request)

        response = self._request("POST", f"http-input/servers/{request.server_id}/trigger", json=request.model_dump())
        return WebhookTriggerResponse(**response.json())

    def get_http_input_metrics(self, server_id: str) -> Dict[str, Any]:
        """Get metrics for an HTTP input server.

        Args:
            server_id: The server identifier

        Returns:
            Dict[str, Any]: Server metrics
        """
        response = self._request("GET", f"http-input/servers/{server_id}/metrics")
        return response.json()

    # =============================================================================
    # Phase 2 Memory System Methods
    # =============================================================================

    def add_memory(self, memory_request: Union[MemoryStoreRequest, Dict[str, Any]]) -> MemoryResponse:
        """Store a new memory in the system.

        Args:
            memory_request: Memory storage request

        Returns:
            MemoryResponse: Memory storage response
        """
        if isinstance(memory_request, dict):
            memory_request = MemoryStoreRequest(**memory_request)

        response = self._request("POST", "memory", json=memory_request.model_dump())
        return MemoryResponse(**response.json())

    def get_memory(self, memory_query: Union[MemoryQuery, Dict[str, Any]]) -> MemoryResponse:
        """Retrieve a specific memory.

        Args:
            memory_query: Memory query parameters

        Returns:
            MemoryResponse: Memory retrieval response
        """
        if isinstance(memory_query, dict):
            memory_query = MemoryQuery(**memory_query)

        response = self._request("GET", "memory", params=memory_query.model_dump(exclude_none=True))
        return MemoryResponse(**response.json())

    def search_memory(self, search_request: Union[MemorySearchRequest, Dict[str, Any]]) -> MemorySearchResponse:
        """Search for memories matching criteria.

        Args:
            search_request: Memory search request

        Returns:
            MemorySearchResponse: Search results
        """
        if isinstance(search_request, dict):
            search_request = MemorySearchRequest(**search_request)

        response = self._request("POST", "memory/search", json=search_request.model_dump())
        return MemorySearchResponse(**response.json())

    def consolidate_memory(self, agent_id: str) -> ConsolidationResponse:
        """Consolidate memories for an agent.

        Args:
            agent_id: The agent identifier

        Returns:
            ConsolidationResponse: Consolidation process results
        """
        response = self._request("POST", f"memory/consolidate/{agent_id}")
        return ConsolidationResponse(**response.json())

    def get_conversation_context(self, conversation_id: str, agent_id: str) -> ConversationContext:
        """Get conversation context with associated memories.

        Args:
            conversation_id: The conversation identifier
            agent_id: The agent identifier

        Returns:
            ConversationContext: Conversation context with memories
        """
        params = {
            "conversation_id": conversation_id,
            "agent_id": agent_id
        }
        response = self._request("GET", "memory/conversation", params=params)
        return ConversationContext(**response.json())

    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory by ID.

        Args:
            memory_id: The memory identifier

        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        response = self._request("DELETE", f"memory/{memory_id}")
        return response.json()

    def list_agent_memories(self, agent_id: str, limit: int = 100) -> MemorySearchResponse:
        """List all memories for an agent.

        Args:
            agent_id: The agent identifier
            limit: Maximum number of memories to return

        Returns:
            MemorySearchResponse: List of agent memories
        """
        params = {
            "agent_id": agent_id,
            "limit": limit
        }
        response = self._request("GET", "memory/agent", params=params)
        return MemorySearchResponse(**response.json())

    # =============================================================================
    # Phase 3 Qdrant Vector Database Methods
    # =============================================================================

    def create_vector_collection(self, collection_request: Union[CollectionCreateRequest, Dict[str, Any]]) -> CollectionResponse:
        """Create a new vector collection.

        Args:
            collection_request: Collection creation request

        Returns:
            CollectionResponse: Collection creation result
        """
        if isinstance(collection_request, dict):
            collection_request = CollectionCreateRequest(**collection_request)

        response = self._request("POST", "vectors/collections", json=collection_request.model_dump())
        return CollectionResponse(**response.json())

    def delete_vector_collection(self, collection_name: str) -> Dict[str, Any]:
        """Delete a vector collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        response = self._request("DELETE", f"vectors/collections/{collection_name}")
        return response.json()

    def get_collection_info(self, collection_name: str) -> CollectionInfo:
        """Get information about a vector collection.

        Args:
            collection_name: Name of the collection

        Returns:
            CollectionInfo: Collection information
        """
        response = self._request("GET", f"vectors/collections/{collection_name}")
        return CollectionInfo(**response.json())

    def list_vector_collections(self) -> List[str]:
        """List all vector collections.

        Returns:
            List[str]: List of collection names
        """
        response = self._request("GET", "vectors/collections")
        return response.json()

    def add_vectors(self, upsert_request: Union[VectorUpsertRequest, Dict[str, Any]]) -> UpsertResponse:
        """Add vectors to a collection.

        Args:
            upsert_request: Vector upsert request

        Returns:
            UpsertResponse: Upsert operation result
        """
        if isinstance(upsert_request, dict):
            upsert_request = VectorUpsertRequest(**upsert_request)

        response = self._request("POST", "vectors/upsert", json=upsert_request.model_dump())
        return UpsertResponse(**response.json())

    def get_vectors(self, collection_name: str, vector_ids: List[Union[str, int]]) -> List[Dict[str, Any]]:
        """Get vectors by IDs from a collection.

        Args:
            collection_name: Name of the collection
            vector_ids: List of vector IDs to retrieve

        Returns:
            List[Dict[str, Any]]: Retrieved vectors
        """
        params = {
            "collection_name": collection_name,
            "ids": vector_ids
        }
        response = self._request("GET", "vectors/retrieve", params=params)
        return response.json()

    def search_vectors(self, search_request: Union[VectorSearchRequest, Dict[str, Any]]) -> VectorSearchResponse:
        """Search vectors using similarity search.

        Args:
            search_request: Vector search request

        Returns:
            VectorSearchResponse: Search results
        """
        if isinstance(search_request, dict):
            search_request = VectorSearchRequest(**search_request)

        response = self._request("POST", "vectors/search", json=search_request.model_dump())
        return VectorSearchResponse(**response.json())

    def delete_vectors(self, collection_name: str, vector_ids: List[Union[str, int]]) -> Dict[str, Any]:
        """Delete vectors from a collection.

        Args:
            collection_name: Name of the collection
            vector_ids: List of vector IDs to delete

        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        data = {
            "collection_name": collection_name,
            "ids": vector_ids
        }
        response = self._request("DELETE", "vectors/delete", json=data)
        return response.json()

    def count_vectors(self, collection_name: str) -> int:
        """Count vectors in a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            int: Number of vectors in the collection
        """
        response = self._request("GET", f"vectors/collections/{collection_name}/count")
        return response.json()["count"]

    # =============================================================================
    # Phase 4 HTTP Endpoint Management Methods
    # =============================================================================

    def create_http_endpoint(self, endpoint_request: Union[HttpEndpointCreateRequest, Dict[str, Any]]) -> HttpEndpointResponse:
        """Create a new HTTP endpoint.

        Args:
            endpoint_request: HTTP endpoint creation request

        Returns:
            HttpEndpointResponse: Endpoint creation result
        """
        if isinstance(endpoint_request, dict):
            endpoint_request = HttpEndpointCreateRequest(**endpoint_request)

        response = self._request("POST", "endpoints", json=endpoint_request.model_dump())
        return HttpEndpointResponse(**response.json())

    def list_http_endpoints(self) -> List[HttpEndpointInfo]:
        """List all HTTP endpoints.

        Returns:
            List[HttpEndpointInfo]: List of endpoint information
        """
        response = self._request("GET", "endpoints")
        return [HttpEndpointInfo(**endpoint) for endpoint in response.json()]

    def update_http_endpoint(self, endpoint_request: Union[HttpEndpointUpdateRequest, Dict[str, Any]]) -> HttpEndpointResponse:
        """Update an existing HTTP endpoint.

        Args:
            endpoint_request: HTTP endpoint update request

        Returns:
            HttpEndpointResponse: Endpoint update result
        """
        if isinstance(endpoint_request, dict):
            endpoint_request = HttpEndpointUpdateRequest(**endpoint_request)

        response = self._request("PUT", f"endpoints/{endpoint_request.endpoint_id}", json=endpoint_request.model_dump())
        return HttpEndpointResponse(**response.json())

    def delete_http_endpoint(self, endpoint_id: str) -> Dict[str, Any]:
        """Delete an HTTP endpoint.

        Args:
            endpoint_id: The endpoint identifier

        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        response = self._request("DELETE", f"endpoints/{endpoint_id}")
        return response.json()

    def get_http_endpoint(self, endpoint_id: str) -> HttpEndpointInfo:
        """Get information about a specific HTTP endpoint.

        Args:
            endpoint_id: The endpoint identifier

        Returns:
            HttpEndpointInfo: Endpoint information
        """
        response = self._request("GET", f"endpoints/{endpoint_id}")
        return HttpEndpointInfo(**response.json())

    def get_endpoint_metrics(self, endpoint_id: str) -> EndpointMetrics:
        """Get metrics for a specific HTTP endpoint.

        Args:
            endpoint_id: The endpoint identifier

        Returns:
            EndpointMetrics: Endpoint metrics information
        """
        response = self._request("GET", f"endpoints/{endpoint_id}/metrics")
        return EndpointMetrics(**response.json())

    def enable_http_endpoint(self, endpoint_id: str) -> Dict[str, Any]:
        """Enable/activate an HTTP endpoint.

        Args:
            endpoint_id: The endpoint identifier

        Returns:
            Dict[str, Any]: Operation confirmation
        """
        response = self._request("POST", f"endpoints/{endpoint_id}/enable")
        return response.json()

    def disable_http_endpoint(self, endpoint_id: str) -> Dict[str, Any]:
        """Disable/deactivate an HTTP endpoint.

        Args:
            endpoint_id: The endpoint identifier

        Returns:
            Dict[str, Any]: Operation confirmation
        """
        response = self._request("POST", f"endpoints/{endpoint_id}/disable")
        return response.json()
