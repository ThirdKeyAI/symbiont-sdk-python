"""Symbiont SDK API Client."""

import os
import requests
from typing import Optional

from .exceptions import APIError, AuthenticationError, NotFoundError, RateLimitError


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