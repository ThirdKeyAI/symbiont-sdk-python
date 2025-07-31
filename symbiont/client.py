"""Symbiont SDK API Client."""

import os
from typing import Any, Dict, List, Optional, Union

import requests

from .exceptions import APIError, AuthenticationError, NotFoundError, RateLimitError
from .models import (
    # Agent models
    Agent,
    AgentDeployRequest,
    AgentDeployResponse,
    AgentMetrics,
    AgentStatusResponse,
    AnalysisResults,
    ContextQuery,
    ContextResponse,
    # Agent DSL models
    DslCompileRequest,
    DslCompileResponse,
    # System models
    HealthResponse,
    # HTTP Input models
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
    VectorSearchRequest,
    VectorSearchResponse,
    WebhookTriggerRequest,
    WebhookTriggerResponse,
    WorkflowExecutionRequest,
)


class Client:
    """Main API client for the Symbiont Agent Runtime System."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the Symbiont API client.

        Args:
            api_key: API key for authentication. Uses SYMBIONT_API_KEY environment variable if not provided.
            base_url: Base URL for the API. Uses SYMBIONT_BASE_URL environment variable or defaults to http://localhost:8080/api/v1.
        """
        # Determine api_key priority: parameter -> environment variable -> None
        self.api_key = api_key or os.getenv('SYMBIONT_API_KEY')

        # Determine base_url priority: parameter -> environment variable -> default
        self.base_url = (
            base_url or
            os.getenv('SYMBIONT_BASE_URL') or
            "http://localhost:8080/api/v1"
        ).rstrip('/')

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
            NotFoundError: For 404 Not Found responses
            RateLimitError: For 429 Too Many Requests responses
            APIError: For other 4xx and 5xx responses
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Set default headers
        headers = kwargs.pop('headers', {})
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        # Make the request
        response = requests.request(method, url, headers=headers, **kwargs)

        # Check for success (2xx status codes)
        if not (200 <= response.status_code < 300):
            response_text = response.text

            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed - check your API key",
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

        return response

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

        response = self._request("POST", "workflows", json=workflow_request.dict())
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

        response = self._request("POST", "tool-review/sessions", json=review_request.dict())
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

        response = self._request("POST", f"tool-review/sessions/{review_id}/decisions", json=decision.dict())
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

        response = self._request("POST", "tool-review/sign", json=signing_request.dict())
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

        response = self._request("POST", "agents", json=agent_data.dict())
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

        response = self._request("POST", "secrets/config", json=config.dict())
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

        response = self._request("POST", "secrets", json=secret_request.dict())
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

        response = self._request("POST", "mcp/servers", json=config.dict())
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

        response = self._request("POST", "knowledge", json=item.dict())
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

        response = self._request("POST", "knowledge/search", json=search_request.dict())
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

        response = self._request("POST", "rag/context", json=context_query.dict())
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

        response = self._request("POST", "dsl/compile", json=compile_request.dict())
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

        response = self._request("POST", "agents/deploy", json=deploy_request.dict())
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

        response = self._request("POST", "http-input/servers", json=request.dict())
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

        response = self._request("PUT", f"http-input/servers/{request.server_id}", json=request.dict())
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

        response = self._request("POST", f"http-input/servers/{request.server_id}/trigger", json=request.dict())
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
