"""ToolClad manifest management client for Symbiont SDK."""

from typing import Any, Dict, List


class ToolCladClient:
    """Client for ToolClad manifest operations.

    This class is typically accessed through the main ``Client`` instance::

        from symbiont import Client
        client = Client()
        tools = client.toolclad.list_tools()
    """

    def __init__(self, client):
        self._client = client

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all discovered ToolClad manifests."""
        response = self._client._request("GET", "api/v1/tools")
        return response.json()

    def validate_manifest(self, path: str) -> Dict[str, Any]:
        """Validate a .clad.toml manifest file.

        Args:
            path: Path to the manifest file (relative to tools_dir)
        """
        response = self._client._request(
            "POST", "api/v1/tools/validate", json={"path": path}
        )
        return response.json()

    def test_tool(self, tool_name: str, args: Dict[str, str]) -> Dict[str, Any]:
        """Dry-run a tool with given arguments (no execution).

        Returns the command that would be executed and validation results.
        """
        response = self._client._request(
            "POST", f"api/v1/tools/{tool_name}/test", json={"args": args}
        )
        return response.json()

    def get_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get the MCP-compatible JSON schema for a tool."""
        response = self._client._request("GET", f"api/v1/tools/{tool_name}/schema")
        return response.json()

    def execute_tool(self, tool_name: str, args: Dict[str, str]) -> Dict[str, Any]:
        """Execute a tool with validated arguments.

        Returns an evidence envelope with results.
        """
        response = self._client._request(
            "POST", f"api/v1/tools/{tool_name}/execute", json={"args": args}
        )
        return response.json()

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a tool manifest."""
        response = self._client._request("GET", f"api/v1/tools/{tool_name}")
        return response.json()

    def reload_tools(self) -> Dict[str, Any]:
        """Trigger a hot-reload of tool manifests from the tools directory."""
        response = self._client._request("POST", "api/v1/tools/reload")
        return response.json()
