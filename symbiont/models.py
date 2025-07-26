"""Data models for the Symbiont SDK."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent state enumeration."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class ReviewStatus(str, Enum):
    """Review session status enumeration."""
    SUBMITTED = "submitted"
    PENDING_ANALYSIS = "pending_analysis" 
    ANALYZING = "analyzing"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SIGNED = "signed"


class FindingSeverity(str, Enum):
    """Security finding severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(str, Enum):
    """Security finding categories."""
    SCHEMA_INJECTION = "schema_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXPOSURE = "data_exposure"
    MALICIOUS_CODE = "malicious_code"
    RESOURCE_ABUSE = "resource_abuse"


# =============================================================================
# Core Agent Models
# =============================================================================

class Agent(BaseModel):
    """Agent model for the Symbiont platform."""
    
    id: str
    name: str
    description: str
    system_prompt: str
    tools: List[str]
    model: str
    temperature: float
    top_p: float
    max_tokens: int


class ResourceUsage(BaseModel):
    """Resource usage information for agents."""
    memory_bytes: int = Field(..., description="Memory usage in bytes")
    cpu_percent: float = Field(..., description="CPU usage percentage")
    active_tasks: int = Field(..., description="Number of active tasks")


class AgentStatusResponse(BaseModel):
    """Response structure for agent status queries."""
    agent_id: str
    state: AgentState
    last_activity: datetime
    resource_usage: ResourceUsage


# =============================================================================
# Workflow Models
# =============================================================================

class WorkflowExecutionRequest(BaseModel):
    """Request structure for workflow execution."""
    workflow_id: str = Field(..., description="The workflow definition or identifier")
    parameters: Dict[str, Any] = Field(..., description="Parameters to pass to the workflow")
    agent_id: Optional[str] = Field(None, description="Optional agent ID to execute the workflow")


class WorkflowExecutionResponse(BaseModel):
    """Response structure for workflow execution."""
    execution_id: str
    status: str
    started_at: datetime
    result: Optional[Dict[str, Any]] = None


# =============================================================================
# Tool Review API Models
# =============================================================================

class ToolProvider(BaseModel):
    """Tool provider information."""
    name: str
    public_key_url: Optional[str] = None


class ToolSchema(BaseModel):
    """Tool schema definition."""
    type: str = "object"
    properties: Dict[str, Any]
    required: List[str] = []


class Tool(BaseModel):
    """Tool definition for review."""
    name: str
    description: str
    tool_schema: ToolSchema = Field(..., alias="schema")
    provider: ToolProvider


class SecurityFinding(BaseModel):
    """Security analysis finding."""
    finding_id: str
    severity: FindingSeverity
    category: FindingCategory
    title: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommendation: Optional[str] = None


class AnalysisResults(BaseModel):
    """Security analysis results."""
    analysis_id: str
    risk_score: int = Field(..., ge=0, le=100)
    findings: List[SecurityFinding]
    recommendations: List[str] = []
    completed_at: datetime


class ReviewSessionState(BaseModel):
    """Review session state information."""
    type: str
    analysis_id: Optional[str] = None
    analysis_completed_at: Optional[datetime] = None
    critical_findings: List[SecurityFinding] = []
    human_reviewer_id: Optional[str] = None
    review_started_at: Optional[datetime] = None


class ReviewSession(BaseModel):
    """Tool review session."""
    review_id: str
    tool: Tool
    status: ReviewStatus
    state: ReviewSessionState
    submitted_by: str
    submitted_at: datetime
    estimated_completion: Optional[datetime] = None
    priority: str = "normal"


class ReviewSessionCreate(BaseModel):
    """Request to create a new review session."""
    tool: Tool
    submitted_by: str
    priority: str = "normal"


class ReviewSessionResponse(BaseModel):
    """Response when creating a review session."""
    review_id: str
    status: ReviewStatus
    submitted_at: datetime
    estimated_completion: Optional[datetime] = None


class ReviewSessionList(BaseModel):
    """List of review sessions with pagination."""
    sessions: List[ReviewSession]
    pagination: Dict[str, Any]


class HumanReviewDecision(BaseModel):
    """Human reviewer decision."""
    decision: str  # "approve" or "reject"
    comments: Optional[str] = None
    reviewer_id: str


# =============================================================================
# System Models
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    uptime_seconds: int
    timestamp: datetime
    version: str


class ErrorResponse(BaseModel):
    """Error response structure."""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None


class PaginationInfo(BaseModel):
    """Pagination information."""
    page: int
    limit: int
    total: int
    has_next: bool


# =============================================================================
# Signing Models
# =============================================================================

class SigningRequest(BaseModel):
    """Request to sign an approved tool."""
    review_id: str
    signing_key_id: str


class SigningResponse(BaseModel):
    """Response from signing operation."""
    signature: str
    signed_at: datetime
    signer_id: str
    signature_algorithm: str


class SignedTool(BaseModel):
    """Signed tool information."""
    tool: Tool
    signature: str
    signed_at: datetime
    signer_id: str
    signature_algorithm: str
    review_id: str