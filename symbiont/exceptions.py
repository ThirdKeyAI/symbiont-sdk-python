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
