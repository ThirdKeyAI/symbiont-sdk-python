"""Custom exception classes for the Symbiont Python SDK."""


class SymbiontError(Exception):
    """Base exception class for all Symbiont SDK errors."""

    def __init__(self, message: str, status_code: int = None):
        """Initialize the SymbiontError.

        Args:
            message: Error message describing what went wrong.
            status_code: HTTP status code if applicable.
        """
        super().__init__(message)
        self.status_code = status_code


class APIError(SymbiontError):
    """Generic API error for 4xx and 5xx HTTP status codes."""

    def __init__(self, message: str, status_code: int, response_text: str = None):
        """Initialize the APIError.

        Args:
            message: Error message describing what went wrong.
            status_code: HTTP status code.
            response_text: Raw response text from the API.
        """
        super().__init__(message, status_code)
        self.response_text = response_text


class AuthenticationError(SymbiontError):
    """Authentication error for 401 Unauthorized responses."""

    def __init__(self, message: str = "Authentication failed", response_text: str = None):
        """Initialize the AuthenticationError.

        Args:
            message: Error message describing the authentication failure.
            response_text: Raw response text from the API.
        """
        super().__init__(message, 401)
        self.response_text = response_text


class NotFoundError(SymbiontError):
    """Not found error for 404 responses."""

    def __init__(self, message: str = "Resource not found", response_text: str = None):
        """Initialize the NotFoundError.

        Args:
            message: Error message describing what resource was not found.
            response_text: Raw response text from the API.
        """
        super().__init__(message, 404)
        self.response_text = response_text


class RateLimitError(SymbiontError):
    """Rate limit error for 429 Too Many Requests responses."""

    def __init__(self, message: str = "Rate limit exceeded", response_text: str = None):
        """Initialize the RateLimitError.

        Args:
            message: Error message describing the rate limit violation.
            response_text: Raw response text from the API.
        """
        super().__init__(message, 429)
        self.response_text = response_text


# =============================================================================
# Phase 1 New Exception Classes
# =============================================================================

class ConfigurationError(SymbiontError):
    """Configuration-related errors."""

    def __init__(self, message: str, config_key: str = None):
        """Initialize the ConfigurationError.

        Args:
            message: Error message describing the configuration issue.
            config_key: Optional configuration key that caused the error.
        """
        super().__init__(message)
        self.config_key = config_key


class AuthenticationExpiredError(AuthenticationError):
    """Authentication expired error for expired tokens."""

    def __init__(self, message: str = "Authentication token has expired", response_text: str = None):
        """Initialize the AuthenticationExpiredError.

        Args:
            message: Error message describing the expiration.
            response_text: Raw response text from the API.
        """
        super().__init__(message, response_text)


class TokenRefreshError(AuthenticationError):
    """Token refresh error for failed token refresh attempts."""

    def __init__(self, message: str = "Failed to refresh authentication token", response_text: str = None):
        """Initialize the TokenRefreshError.

        Args:
            message: Error message describing the refresh failure.
            response_text: Raw response text from the API.
        """
        super().__init__(message, response_text)


class PermissionDeniedError(SymbiontError):
    """Permission denied error for insufficient privileges."""

    def __init__(self, message: str = "Insufficient permissions for this operation", required_permission: str = None):
        """Initialize the PermissionDeniedError.

        Args:
            message: Error message describing the permission issue.
            required_permission: Optional required permission that was missing.
        """
        super().__init__(message, 403)
        self.required_permission = required_permission


# =============================================================================
# Phase 2 Memory System Exception Classes
# =============================================================================

class MemoryError(SymbiontError):
    """Base exception for memory system errors."""
    pass


class MemoryStorageError(MemoryError):
    """Raised when memory storage operations fail."""

    def __init__(self, message: str = "Memory storage error", storage_type: str = None):
        """Initialize the MemoryStorageError.

        Args:
            message: Error message describing the storage failure.
            storage_type: Optional storage backend type that failed.
        """
        super().__init__(message)
        self.storage_type = storage_type


class MemoryRetrievalError(MemoryError):
    """Raised when memory retrieval operations fail."""

    def __init__(self, message: str = "Memory retrieval error", memory_id: str = None):
        """Initialize the MemoryRetrievalError.

        Args:
            message: Error message describing the retrieval failure.
            memory_id: Optional memory ID that failed to retrieve.
        """
        super().__init__(message)
        self.memory_id = memory_id


# =============================================================================
# Phase 3 Vector Database Exception Classes
# =============================================================================

class VectorDatabaseError(SymbiontError):
    """Base exception for vector database errors."""
    pass


class QdrantConnectionError(VectorDatabaseError):
    """Raised when Qdrant connection operations fail."""

    def __init__(self, message: str = "Qdrant connection error", host: str = None):
        """Initialize the QdrantConnectionError.

        Args:
            message: Error message describing the connection failure.
            host: Optional Qdrant host that failed to connect.
        """
        super().__init__(message)
        self.host = host


class CollectionNotFoundError(VectorDatabaseError):
    """Raised when a vector collection is not found."""

    def __init__(self, message: str = "Vector collection not found", collection_name: str = None):
        """Initialize the CollectionNotFoundError.

        Args:
            message: Error message describing the collection error.
            collection_name: Optional collection name that was not found.
        """
        super().__init__(message, 404)
        self.collection_name = collection_name


class EmbeddingError(SymbiontError):
    """Raised when embedding generation operations fail."""

    def __init__(self, message: str = "Embedding generation error", model: str = None):
        """Initialize the EmbeddingError.

        Args:
            message: Error message describing the embedding failure.
            model: Optional embedding model that failed.
        """
        super().__init__(message)
        self.model = model


# =============================================================================
# Phase 4 HTTP Endpoint Management Exception Classes
# =============================================================================

class EndpointError(SymbiontError):
    """Base exception for HTTP endpoint management errors."""
    pass


class EndpointNotFoundError(EndpointError):
    """Raised when an HTTP endpoint is not found."""

    def __init__(self, message: str = "HTTP endpoint not found", endpoint_id: str = None):
        """Initialize the EndpointNotFoundError.

        Args:
            message: Error message describing the endpoint error.
            endpoint_id: Optional endpoint ID that was not found.
        """
        super().__init__(message, 404)
        self.endpoint_id = endpoint_id


class EndpointConflictError(EndpointError):
    """Raised when an HTTP endpoint creation conflicts with existing endpoints."""

    def __init__(self, message: str = "HTTP endpoint conflict", path: str = None, method: str = None):
        """Initialize the EndpointConflictError.

        Args:
            message: Error message describing the endpoint conflict.
            path: Optional endpoint path that conflicts.
            method: Optional HTTP method that conflicts.
        """
        super().__init__(message, 409)
        self.path = path
        self.method = method


class EndpointConfigurationError(EndpointError):
    """Raised when HTTP endpoint configuration is invalid."""

    def __init__(self, message: str = "Invalid endpoint configuration", config_field: str = None):
        """Initialize the EndpointConfigurationError.

        Args:
            message: Error message describing the configuration issue.
            config_field: Optional configuration field that is invalid.
        """
        super().__init__(message, 400)
        self.config_field = config_field


class EndpointRateLimitError(EndpointError):
    """Raised when an HTTP endpoint rate limit is exceeded."""

    def __init__(self, message: str = "Endpoint rate limit exceeded", endpoint_id: str = None):
        """Initialize the EndpointRateLimitError.

        Args:
            message: Error message describing the rate limit violation.
            endpoint_id: Optional endpoint ID that exceeded the rate limit.
        """
        super().__init__(message, 429)
        self.endpoint_id = endpoint_id
