"""
Memory system implementation for hierarchical agent memory management.

This module implements a hierarchical memory system that supports multiple
storage backends, conversation context management, and memory consolidation.
"""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .exceptions import MemoryError, MemoryRetrievalError, MemoryStorageError


class MemoryLevel(Enum):
    """Memory hierarchy levels for different types of memory storage."""
    SHORT_TERM = "short_term"  # Recent interactions, limited capacity
    LONG_TERM = "long_term"    # Persistent important information
    EPISODIC = "episodic"      # Event-based contextual memory
    SEMANTIC = "semantic"      # Fact-based knowledge memory


class MemoryType(Enum):
    """Types of memory content."""
    CONVERSATION = "conversation"
    FACT = "fact"
    EXPERIENCE = "experience"
    CONTEXT = "context"
    METADATA = "metadata"


@dataclass
class MemoryNode:
    """Individual memory item with metadata and content."""
    id: str
    content: Dict[str, Any]
    memory_type: MemoryType
    memory_level: MemoryLevel
    timestamp: datetime
    agent_id: str
    conversation_id: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = None
    importance_score: float = 0.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.children_ids is None:
            self.children_ids = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory node to dictionary for storage."""
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type.value,
            'memory_level': self.memory_level.value,
            'timestamp': self.timestamp.isoformat(),
            'agent_id': self.agent_id,
            'conversation_id': self.conversation_id,
            'parent_id': self.parent_id,
            'children_ids': self.children_ids,
            'importance_score': self.importance_score,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryNode':
        """Create memory node from dictionary."""
        return cls(
            id=data['id'],
            content=data['content'],
            memory_type=MemoryType(data['memory_type']),
            memory_level=MemoryLevel(data['memory_level']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            agent_id=data['agent_id'],
            conversation_id=data.get('conversation_id'),
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', []),
            importance_score=data.get('importance_score', 0.0),
            access_count=data.get('access_count', 0),
            last_accessed=datetime.fromisoformat(data['last_accessed']) if data.get('last_accessed') else None,
            metadata=data.get('metadata', {})
        )


class MemoryStore(ABC):
    """Abstract base class for memory storage backends."""

    @abstractmethod
    def store(self, memory_node: MemoryNode) -> bool:
        """Store a memory node."""
        pass

    @abstractmethod
    def retrieve(self, memory_id: str) -> Optional[MemoryNode]:
        """Retrieve a memory node by ID."""
        pass

    @abstractmethod
    def search(self, query: Dict[str, Any]) -> List[MemoryNode]:
        """Search for memory nodes matching criteria."""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a memory node."""
        pass

    @abstractmethod
    def list_by_agent(self, agent_id: str, limit: int = 100) -> List[MemoryNode]:
        """List memories for a specific agent."""
        pass


class InMemoryStore(MemoryStore):
    """In-memory storage backend for testing and development."""

    def __init__(self):
        self._memories: Dict[str, MemoryNode] = {}

    def store(self, memory_node: MemoryNode) -> bool:
        """Store a memory node in memory."""
        try:
            self._memories[memory_node.id] = memory_node
            return True
        except Exception as e:
            raise MemoryStorageError(f"Failed to store memory: {e}") from e

    def retrieve(self, memory_id: str) -> Optional[MemoryNode]:
        """Retrieve a memory node by ID."""
        try:
            memory = self._memories.get(memory_id)
            if memory:
                memory.access_count += 1
                memory.last_accessed = datetime.now()
            return memory
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to retrieve memory: {e}") from e

    def search(self, query: Dict[str, Any]) -> List[MemoryNode]:
        """Search for memory nodes matching criteria."""
        try:
            results = []
            for memory in self._memories.values():
                if self._matches_query(memory, query):
                    results.append(memory)

            # Sort by importance score and timestamp
            results.sort(key=lambda m: (m.importance_score, m.timestamp), reverse=True)
            return results
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to search memories: {e}") from e

    def delete(self, memory_id: str) -> bool:
        """Delete a memory node."""
        try:
            if memory_id in self._memories:
                del self._memories[memory_id]
                return True
            return False
        except Exception as e:
            raise MemoryStorageError(f"Failed to delete memory: {e}") from e

    def list_by_agent(self, agent_id: str, limit: int = 100) -> List[MemoryNode]:
        """List memories for a specific agent."""
        try:
            agent_memories = [
                memory for memory in self._memories.values()
                if memory.agent_id == agent_id
            ]
            agent_memories.sort(key=lambda m: m.timestamp, reverse=True)
            return agent_memories[:limit]
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to list agent memories: {e}") from e

    def _matches_query(self, memory: MemoryNode, query: Dict[str, Any]) -> bool:
        """Check if memory matches query criteria."""
        for key, value in query.items():
            if key == 'agent_id' and memory.agent_id != value:
                return False
            elif key == 'conversation_id' and memory.conversation_id != value:
                return False
            elif key == 'memory_type' and memory.memory_type != MemoryType(value):
                return False
            elif key == 'memory_level' and memory.memory_level != MemoryLevel(value):
                return False
            elif key == 'content_contains':
                content_str = json.dumps(memory.content).lower()
                if value.lower() not in content_str:
                    return False
        return True


class RedisMemoryStore(MemoryStore):
    """Redis-based memory storage backend."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0", key_prefix: str = "symbiont:memory"):
        if not REDIS_AVAILABLE:
            raise MemoryError("Redis not available. Install redis package.")

        try:
            self.redis_client = redis.from_url(redis_url)
            self.key_prefix = key_prefix
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            raise MemoryStorageError(f"Failed to connect to Redis: {e}") from e

    def _get_key(self, memory_id: str) -> str:
        """Get Redis key for memory ID."""
        return f"{self.key_prefix}:{memory_id}"

    def _get_agent_key(self, agent_id: str) -> str:
        """Get Redis key for agent memory list."""
        return f"{self.key_prefix}:agent:{agent_id}"

    def store(self, memory_node: MemoryNode) -> bool:
        """Store a memory node in Redis."""
        try:
            key = self._get_key(memory_node.id)
            agent_key = self._get_agent_key(memory_node.agent_id)

            # Store memory data
            memory_data = json.dumps(memory_node.to_dict())
            self.redis_client.set(key, memory_data)

            # Add to agent's memory list
            self.redis_client.lpush(agent_key, memory_node.id)

            # Set TTL for short-term memories
            if memory_node.memory_level == MemoryLevel.SHORT_TERM:
                self.redis_client.expire(key, 3600)  # 1 hour TTL

            return True
        except Exception as e:
            raise MemoryStorageError(f"Failed to store memory in Redis: {e}") from e

    def retrieve(self, memory_id: str) -> Optional[MemoryNode]:
        """Retrieve a memory node by ID from Redis."""
        try:
            key = self._get_key(memory_id)
            memory_data = self.redis_client.get(key)

            if memory_data:
                data = json.loads(memory_data)
                memory = MemoryNode.from_dict(data)

                # Update access statistics
                memory.access_count += 1
                memory.last_accessed = datetime.now()

                # Update in Redis
                updated_data = json.dumps(memory.to_dict())
                self.redis_client.set(key, updated_data)

                return memory
            return None
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to retrieve memory from Redis: {e}") from e

    def search(self, query: Dict[str, Any]) -> List[MemoryNode]:
        """Search for memory nodes matching criteria in Redis."""
        try:
            results = []

            # If agent_id specified, search within agent's memories
            if 'agent_id' in query:
                agent_key = self._get_agent_key(query['agent_id'])
                memory_ids = self.redis_client.lrange(agent_key, 0, -1)

                for memory_id in memory_ids:
                    memory = self.retrieve(memory_id.decode('utf-8'))
                    if memory and self._matches_query(memory, query):
                        results.append(memory)
            else:
                # Search all memories (less efficient)
                pattern = f"{self.key_prefix}:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    if not key.decode('utf-8').startswith(f"{self.key_prefix}:agent:"):
                        memory_id = key.decode('utf-8').split(':')[-1]
                        memory = self.retrieve(memory_id)
                        if memory and self._matches_query(memory, query):
                            results.append(memory)

            # Sort by importance score and timestamp
            results.sort(key=lambda m: (m.importance_score, m.timestamp), reverse=True)
            return results
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to search memories in Redis: {e}") from e

    def delete(self, memory_id: str) -> bool:
        """Delete a memory node from Redis."""
        try:
            key = self._get_key(memory_id)
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            raise MemoryStorageError(f"Failed to delete memory from Redis: {e}") from e

    def list_by_agent(self, agent_id: str, limit: int = 100) -> List[MemoryNode]:
        """List memories for a specific agent from Redis."""
        try:
            agent_key = self._get_agent_key(agent_id)
            memory_ids = self.redis_client.lrange(agent_key, 0, limit - 1)

            memories = []
            for memory_id in memory_ids:
                memory = self.retrieve(memory_id.decode('utf-8'))
                if memory:
                    memories.append(memory)

            return memories
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to list agent memories from Redis: {e}") from e

    def _matches_query(self, memory: MemoryNode, query: Dict[str, Any]) -> bool:
        """Check if memory matches query criteria."""
        for key, value in query.items():
            if key == 'agent_id' and memory.agent_id != value:
                return False
            elif key == 'conversation_id' and memory.conversation_id != value:
                return False
            elif key == 'memory_type' and memory.memory_type != MemoryType(value):
                return False
            elif key == 'memory_level' and memory.memory_level != MemoryLevel(value):
                return False
            elif key == 'content_contains':
                content_str = json.dumps(memory.content).lower()
                if value.lower() not in content_str:
                    return False
        return True


class HierarchicalMemory:
    """Manages hierarchical memory structure with different levels."""

    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.consolidation_thresholds = {
            MemoryLevel.SHORT_TERM: 50,  # Max short-term memories
            MemoryLevel.LONG_TERM: 1000,  # Max long-term memories
            MemoryLevel.EPISODIC: 500,   # Max episodic memories
            MemoryLevel.SEMANTIC: 2000   # Max semantic memories
        }

    def add_memory(
        self,
        content: Dict[str, Any],
        memory_type: MemoryType,
        memory_level: MemoryLevel,
        agent_id: str,
        conversation_id: Optional[str] = None,
        importance_score: float = 0.0,
        parent_id: Optional[str] = None
    ) -> MemoryNode:
        """Add a new memory to the hierarchy."""
        memory_node = MemoryNode(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            memory_level=memory_level,
            timestamp=datetime.now(),
            agent_id=agent_id,
            conversation_id=conversation_id,
            parent_id=parent_id,
            importance_score=importance_score
        )

        if not self.memory_store.store(memory_node):
            raise MemoryStorageError("Failed to store memory node")

        # Check if consolidation is needed
        self._check_consolidation(agent_id, memory_level)

        return memory_node

    def get_memory(self, memory_id: str) -> Optional[MemoryNode]:
        """Retrieve a memory by ID."""
        return self.memory_store.retrieve(memory_id)

    def search_memories(
        self,
        agent_id: str,
        query: Optional[Dict[str, Any]] = None,
        memory_levels: Optional[List[MemoryLevel]] = None,
        limit: int = 50
    ) -> List[MemoryNode]:
        """Search memories with optional filtering."""
        search_query = {'agent_id': agent_id}

        if query:
            search_query.update(query)

        results = self.memory_store.search(search_query)

        # Filter by memory levels if specified
        if memory_levels:
            results = [m for m in results if m.memory_level in memory_levels]

        return results[:limit]

    def get_conversation_context(self, conversation_id: str, agent_id: str) -> List[MemoryNode]:
        """Get all memories related to a conversation."""
        query = {
            'agent_id': agent_id,
            'conversation_id': conversation_id
        }
        return self.memory_store.search(query)

    def consolidate_memories(self, agent_id: str) -> Dict[str, int]:
        """Consolidate memories by promoting important ones and pruning old ones."""
        consolidated = {
            'promoted': 0,
            'pruned': 0,
            'consolidated': 0
        }

        for level in MemoryLevel:
            level_memories = self.search_memories(
                agent_id=agent_id,
                query={'memory_level': level.value}
            )

            threshold = self.consolidation_thresholds[level]

            if len(level_memories) > threshold:
                # Sort by importance and recency
                level_memories.sort(
                    key=lambda m: (m.importance_score, m.timestamp),
                    reverse=True
                )

                # Keep important memories, prune others
                to_keep = level_memories[:threshold]
                to_prune = level_memories[threshold:]

                # Promote highly important short-term memories to long-term
                if level == MemoryLevel.SHORT_TERM:
                    for memory in to_keep:
                        if memory.importance_score > 0.7:
                            memory.memory_level = MemoryLevel.LONG_TERM
                            self.memory_store.store(memory)
                            consolidated['promoted'] += 1

                # Prune less important memories
                for memory in to_prune:
                    self.memory_store.delete(memory.id)
                    consolidated['pruned'] += 1

        return consolidated

    def _check_consolidation(self, agent_id: str, memory_level: MemoryLevel):
        """Check if consolidation is needed for a memory level."""
        level_memories = self.search_memories(
            agent_id=agent_id,
            query={'memory_level': memory_level.value}
        )

        threshold = self.consolidation_thresholds[memory_level]

        if len(level_memories) > threshold * 1.2:  # 20% buffer
            self.consolidate_memories(agent_id)


class MemoryManager:
    """Main memory management system."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Initialize memory store based on configuration
        storage_type = self.config.get('storage_type', 'memory')

        if storage_type == 'redis':
            redis_url = self.config.get('redis_url', 'redis://localhost:6379/0')
            self.memory_store = RedisMemoryStore(redis_url)
        else:
            self.memory_store = InMemoryStore()

        self.hierarchical_memory = HierarchicalMemory(self.memory_store)

    def add_memory(
        self,
        content: Dict[str, Any],
        memory_type: MemoryType,
        memory_level: MemoryLevel,
        agent_id: str,
        conversation_id: Optional[str] = None,
        importance_score: float = 0.0,
        parent_id: Optional[str] = None
    ) -> MemoryNode:
        """Add a new memory to the system."""
        return self.hierarchical_memory.add_memory(
            content=content,
            memory_type=memory_type,
            memory_level=memory_level,
            agent_id=agent_id,
            conversation_id=conversation_id,
            importance_score=importance_score,
            parent_id=parent_id
        )

    def get_memory(self, memory_id: str) -> Optional[MemoryNode]:
        """Retrieve a memory by ID."""
        return self.hierarchical_memory.get_memory(memory_id)

    def search_memory(
        self,
        agent_id: str,
        query: Optional[Dict[str, Any]] = None,
        memory_levels: Optional[List[MemoryLevel]] = None,
        limit: int = 50
    ) -> List[MemoryNode]:
        """Search memories with filtering options."""
        return self.hierarchical_memory.search_memories(
            agent_id=agent_id,
            query=query,
            memory_levels=memory_levels,
            limit=limit
        )

    def get_conversation_context(self, conversation_id: str, agent_id: str) -> List[MemoryNode]:
        """Get conversation context."""
        return self.hierarchical_memory.get_conversation_context(conversation_id, agent_id)

    def consolidate_memory(self, agent_id: str) -> Dict[str, int]:
        """Consolidate memories for an agent."""
        return self.hierarchical_memory.consolidate_memories(agent_id)

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        return self.memory_store.delete(memory_id)

    def list_agent_memories(self, agent_id: str, limit: int = 100) -> List[MemoryNode]:
        """List all memories for an agent."""
        return self.memory_store.list_by_agent(agent_id, limit)
