"""Data models for the Symbiont SDK."""

from pydantic import BaseModel


class Agent(BaseModel):
    """Agent model for the Symbiont platform."""
    
    id: str
    name: str
    description: str
    system_prompt: str
    tools: list[str]
    model: str
    temperature: float
    top_p: float
    max_tokens: int