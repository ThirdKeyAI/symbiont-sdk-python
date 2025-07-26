"""Symbiont SDK API Client."""

import os
import requests
from typing import Optional, List, Dict, Any, Union

from .exceptions import APIError, AuthenticationError, NotFoundError, RateLimitError
from .models import (
    # Agent models
    Agent, AgentStatusResponse, WorkflowExecutionRequest, ReviewSession, ReviewSessionCreate, ReviewSessionResponse, 
    ReviewSessionList, AnalysisResults, HumanReviewDecision,
    SigningRequest, SigningResponse, SignedTool,
    
    # System models
    HealthResponse
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

    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics.
        
        Returns:
            Dict[str, Any]: System metrics data
        """
        response = self._request("GET", "metrics")
        return response.json()

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