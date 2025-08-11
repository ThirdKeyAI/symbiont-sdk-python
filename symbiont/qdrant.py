"""Qdrant vector database integration for Symbiont SDK."""

import logging
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from .exceptions import (
    CollectionNotFoundError,
    QdrantConnectionError,
    VectorDatabaseError,
)

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manages interactions with Qdrant vector database."""

    def __init__(self,
                 host: str = "localhost",
                 port: int = 6333,
                 grpc_port: int = 6334,
                 prefer_grpc: bool = False,
                 timeout: float = 60.0,
                 api_key: Optional[str] = None,
                 **kwargs):
        """Initialize Qdrant manager.

        Args:
            host: Qdrant server host
            port: Qdrant HTTP API port
            grpc_port: Qdrant gRPC port
            prefer_grpc: Whether to use gRPC instead of HTTP
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
            **kwargs: Additional client configuration
        """
        self.host = host
        self.port = port
        self.grpc_port = grpc_port
        self.prefer_grpc = prefer_grpc
        self.timeout = timeout
        self.api_key = api_key
        self._client = None
        self._config = kwargs

    def _get_client(self):
        """Get or create Qdrant client instance."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    grpc_port=self.grpc_port,
                    prefer_grpc=self.prefer_grpc,
                    timeout=self.timeout,
                    api_key=self.api_key,
                    **self._config
                )
            except ImportError as e:
                raise VectorDatabaseError(
                    "qdrant-client is required but not installed. "
                    "Install it with: pip install qdrant-client"
                ) from e
            except Exception as e:
                raise QdrantConnectionError(
                    f"Failed to connect to Qdrant at {self.host}:{self.port}: {e}"
                ) from e
        return self._client

    def health_check(self) -> bool:
        """Check if Qdrant server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            client = self._get_client()
            return client.get_collections() is not None
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def create_collection(self,
                         collection_name: str,
                         vector_size: int,
                         distance: str = "Cosine",
                         on_disk_payload: bool = False,
                         hnsw_config: Optional[Dict[str, Any]] = None,
                         optimizers_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new collection.

        Args:
            collection_name: Name of the collection
            vector_size: Size of the vectors
            distance: Distance metric (Cosine, Euclidean, Dot)
            on_disk_payload: Whether to store payload on disk
            hnsw_config: HNSW configuration parameters
            optimizers_config: Optimizer configuration parameters

        Returns:
            Collection creation result
        """
        try:
            from qdrant_client.models import (
                Distance,
                HnswConfigDiff,
                OptimizersConfigDiff,
                VectorParams,
            )

            client = self._get_client()

            # Map distance string to enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclidean": Distance.EUCLID,
                "Dot": Distance.DOT
            }
            distance_metric = distance_map.get(distance, Distance.COSINE)

            # Configure HNSW parameters
            hnsw_config_obj = None
            if hnsw_config:
                hnsw_config_obj = HnswConfigDiff(**hnsw_config)

            # Configure optimizer parameters
            optimizers_config_obj = None
            if optimizers_config:
                optimizers_config_obj = OptimizersConfigDiff(**optimizers_config)

            result = client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_metric,
                    on_disk=on_disk_payload
                ),
                hnsw_config=hnsw_config_obj,
                optimizers_config=optimizers_config_obj
            )

            return {
                "collection_name": collection_name,
                "status": "created",
                "result": result
            }

        except Exception as e:
            raise VectorDatabaseError(f"Failed to create collection {collection_name}: {e}") from e

    def delete_collection(self, collection_name: str) -> Dict[str, Any]:
        """Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            Deletion result
        """
        try:
            client = self._get_client()
            result = client.delete_collection(collection_name)

            return {
                "collection_name": collection_name,
                "status": "deleted",
                "result": result
            }

        except Exception as e:
            raise VectorDatabaseError(f"Failed to delete collection {collection_name}: {e}") from e

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection information
        """
        try:
            client = self._get_client()
            info = client.get_collection(collection_name)

            return {
                "collection_name": collection_name,
                "config": info.config.dict() if hasattr(info.config, 'dict') else str(info.config),
                "status": info.status,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count
            }

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(f"Collection {collection_name} not found") from e
            raise VectorDatabaseError(f"Failed to get collection info for {collection_name}: {e}") from e

    def list_collections(self) -> List[str]:
        """List all collections.

        Returns:
            List of collection names
        """
        try:
            client = self._get_client()
            collections = client.get_collections()
            return [collection.name for collection in collections.collections]

        except Exception as e:
            raise VectorDatabaseError(f"Failed to list collections: {e}") from e

    def upsert_points(self,
                     collection_name: str,
                     points: List[Dict[str, Any]],
                     wait: bool = True) -> Dict[str, Any]:
        """Upsert points into a collection.

        Args:
            collection_name: Name of the collection
            points: List of points to upsert
            wait: Whether to wait for the operation to complete

        Returns:
            Upsert operation result
        """
        try:
            from qdrant_client.models import PointStruct

            client = self._get_client()

            # Convert points to PointStruct objects
            point_structs = []
            for point in points:
                point_id = point.get("id", str(uuid4()))
                vector = point.get("vector", point.get("embedding"))
                payload = point.get("payload", {})

                if vector is None:
                    raise VectorDatabaseError(f"Point {point_id} missing vector/embedding")

                point_structs.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                ))

            result = client.upsert(
                collection_name=collection_name,
                points=point_structs,
                wait=wait
            )

            return {
                "collection_name": collection_name,
                "operation_id": result.operation_id,
                "status": result.status.value,
                "points_count": len(point_structs)
            }

        except Exception as e:
            raise VectorDatabaseError(f"Failed to upsert points to {collection_name}: {e}") from e

    def search_points(self,
                     collection_name: str,
                     query_vector: List[float],
                     limit: int = 10,
                     score_threshold: Optional[float] = None,
                     payload_filter: Optional[Dict[str, Any]] = None,
                     with_payload: bool = True,
                     with_vectors: bool = False) -> List[Dict[str, Any]]:
        """Search for similar points.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            payload_filter: Optional payload filter
            with_payload: Whether to include payload in results
            with_vectors: Whether to include vectors in results

        Returns:
            List of search results
        """
        try:
            from qdrant_client.models import Filter

            client = self._get_client()

            # Convert payload filter if provided
            filter_obj = None
            if payload_filter:
                filter_obj = Filter(**payload_filter)

            results = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_obj,
                with_payload=with_payload,
                with_vectors=with_vectors
            )

            # Convert results to dict format
            search_results = []
            for result in results:
                result_dict = {
                    "id": result.id,
                    "score": result.score
                }

                if with_payload and result.payload:
                    result_dict["payload"] = result.payload

                if with_vectors and result.vector:
                    result_dict["vector"] = result.vector

                search_results.append(result_dict)

            return search_results

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(f"Collection {collection_name} not found") from e
            raise VectorDatabaseError(f"Failed to search in collection {collection_name}: {e}") from e

    def get_points(self,
                  collection_name: str,
                  point_ids: List[Union[str, int]],
                  with_payload: bool = True,
                  with_vectors: bool = False) -> List[Dict[str, Any]]:
        """Retrieve points by IDs.

        Args:
            collection_name: Name of the collection
            point_ids: List of point IDs
            with_payload: Whether to include payload
            with_vectors: Whether to include vectors

        Returns:
            List of retrieved points
        """
        try:
            client = self._get_client()

            results = client.retrieve(
                collection_name=collection_name,
                ids=point_ids,
                with_payload=with_payload,
                with_vectors=with_vectors
            )

            # Convert results to dict format
            points = []
            for result in results:
                point_dict = {
                    "id": result.id
                }

                if with_payload and result.payload:
                    point_dict["payload"] = result.payload

                if with_vectors and result.vector:
                    point_dict["vector"] = result.vector

                points.append(point_dict)

            return points

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(f"Collection {collection_name} not found") from e
            raise VectorDatabaseError(f"Failed to retrieve points from {collection_name}: {e}") from e

    def delete_points(self,
                     collection_name: str,
                     point_ids: List[Union[str, int]],
                     wait: bool = True) -> Dict[str, Any]:
        """Delete points by IDs.

        Args:
            collection_name: Name of the collection
            point_ids: List of point IDs to delete
            wait: Whether to wait for the operation to complete

        Returns:
            Deletion result
        """
        try:
            client = self._get_client()

            result = client.delete(
                collection_name=collection_name,
                points_selector=point_ids,
                wait=wait
            )

            return {
                "collection_name": collection_name,
                "operation_id": result.operation_id,
                "status": result.status.value,
                "deleted_count": len(point_ids)
            }

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(f"Collection {collection_name} not found") from e
            raise VectorDatabaseError(f"Failed to delete points from {collection_name}: {e}") from e

    def count_points(self,
                    collection_name: str,
                    exact: bool = True) -> int:
        """Count points in a collection.

        Args:
            collection_name: Name of the collection
            exact: Whether to return exact count

        Returns:
            Number of points in the collection
        """
        try:
            client = self._get_client()
            result = client.count(collection_name=collection_name, exact=exact)
            return result.count

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(f"Collection {collection_name} not found") from e
            raise VectorDatabaseError(f"Failed to count points in {collection_name}: {e}") from e

    def close(self):
        """Close the Qdrant client connection."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Qdrant client: {e}")
            finally:
                self._client = None


class CollectionManager:
    """Manages Qdrant collection lifecycle operations."""

    def __init__(self, qdrant_manager: QdrantManager):
        """Initialize collection manager.

        Args:
            qdrant_manager: QdrantManager instance
        """
        self.qdrant = qdrant_manager

    def ensure_collection_exists(self,
                                collection_name: str,
                                vector_size: int,
                                distance: str = "Cosine",
                                **kwargs) -> bool:
        """Ensure a collection exists, creating it if necessary.

        Args:
            collection_name: Name of the collection
            vector_size: Size of the vectors
            distance: Distance metric
            **kwargs: Additional collection parameters

        Returns:
            True if collection was created, False if it already existed
        """
        try:
            self.qdrant.get_collection_info(collection_name)
            return False  # Collection already exists
        except CollectionNotFoundError:
            self.qdrant.create_collection(
                collection_name=collection_name,
                vector_size=vector_size,
                distance=distance,
                **kwargs
            )
            return True  # Collection was created


class VectorOperations:
    """Handles vector CRUD operations."""

    def __init__(self, qdrant_manager: QdrantManager):
        """Initialize vector operations.

        Args:
            qdrant_manager: QdrantManager instance
        """
        self.qdrant = qdrant_manager

    def add_vectors(self,
                   collection_name: str,
                   vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add vectors to a collection.

        Args:
            collection_name: Name of the collection
            vectors: List of vector objects

        Returns:
            Operation result
        """
        return self.qdrant.upsert_points(collection_name, vectors)

    def get_vectors(self,
                   collection_name: str,
                   vector_ids: List[Union[str, int]]) -> List[Dict[str, Any]]:
        """Get vectors by IDs.

        Args:
            collection_name: Name of the collection
            vector_ids: List of vector IDs

        Returns:
            List of vectors
        """
        return self.qdrant.get_points(
            collection_name=collection_name,
            point_ids=vector_ids,
            with_vectors=True,
            with_payload=True
        )

    def search_vectors(self,
                      collection_name: str,
                      query_vector: List[float],
                      limit: int = 10,
                      **kwargs) -> List[Dict[str, Any]]:
        """Search for similar vectors.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        return self.qdrant.search_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            **kwargs
        )


class SearchEngine:
    """Semantic search implementation using Qdrant."""

    def __init__(self, qdrant_manager: QdrantManager):
        """Initialize search engine.

        Args:
            qdrant_manager: QdrantManager instance
        """
        self.qdrant = qdrant_manager

    def semantic_search(self,
                       collection_name: str,
                       query_text: str,
                       limit: int = 10,
                       score_threshold: Optional[float] = None,
                       embedding_function: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Perform semantic search using text query.

        Args:
            collection_name: Name of the collection
            query_text: Text query to search for
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            embedding_function: Function to convert text to embeddings

        Returns:
            List of search results
        """
        if embedding_function is None:
            raise VectorDatabaseError("embedding_function is required for semantic search")

        # Convert text to vector
        query_vector = embedding_function(query_text)

        # Perform vector search
        return self.qdrant.search_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True
        )


class EmbeddingManager:
    """Manages embedding generation and storage."""

    def __init__(self, qdrant_manager: QdrantManager):
        """Initialize embedding manager.

        Args:
            qdrant_manager: QdrantManager instance
        """
        self.qdrant = qdrant_manager
        self._embedding_functions = {}

    def register_embedding_function(self,
                                   name: str,
                                   function: callable):
        """Register an embedding function.

        Args:
            name: Name of the embedding function
            function: Function that converts text to embeddings
        """
        self._embedding_functions[name] = function

    def get_embedding_function(self, name: str) -> callable:
        """Get a registered embedding function.

        Args:
            name: Name of the embedding function

        Returns:
            The embedding function
        """
        if name not in self._embedding_functions:
            raise VectorDatabaseError(f"Embedding function '{name}' not registered")
        return self._embedding_functions[name]

    def embed_and_store(self,
                       collection_name: str,
                       texts: List[str],
                       embedding_function_name: str,
                       metadata: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Embed texts and store in collection.

        Args:
            collection_name: Name of the collection
            texts: List of texts to embed
            embedding_function_name: Name of registered embedding function
            metadata: Optional metadata for each text

        Returns:
            Storage operation result
        """
        embedding_function = self.get_embedding_function(embedding_function_name)

        # Generate embeddings
        embeddings = [embedding_function(text) for text in texts]

        # Prepare points for storage
        points = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            point_metadata = metadata[i] if metadata and i < len(metadata) else {}
            point_metadata["text"] = text
            point_metadata["embedding_function"] = embedding_function_name

            points.append({
                "id": str(uuid4()),
                "vector": embedding,
                "payload": point_metadata
            })

        # Store in Qdrant
        return self.qdrant.upsert_points(collection_name, points)
