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
