"""
Database manager for multiple database support
Supports RDBMS, NoSQL, Vector databases
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum


class DatabaseType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    REDIS = "redis"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    CHROMADB = "chromadb"
    QDRANT = "qdrant"


class DatabaseManager:
    """
    Unified database manager for multiple database types.

    Supports:
    - RDBMS: PostgreSQL, MySQL, SQLite
    - NoSQL: MongoDB, Redis
    - Vector DB: Pinecone, Weaviate, ChromaDB, Qdrant

    Example:
        ```python
        db_manager = DatabaseManager()

        # Configure databases
        await db_manager.add_connection(
            "main_db",
            DatabaseType.POSTGRESQL,
            url="postgresql://localhost/mydb"
        )

        await db_manager.add_connection(
            "cache",
            DatabaseType.REDIS,
            url="redis://localhost"
        )

        await db_manager.add_connection(
            "vectors",
            DatabaseType.CHROMADB,
            config={"path": "./chroma_db"}
        )
        ```
    """

    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self.configs: Dict[str, Dict] = {}

    async def add_connection(
        self,
        name: str,
        db_type: DatabaseType,
        url: str = None,
        config: Dict = None,
        **kwargs
    ):
        """
        Add database connection.

        Args:
            name: Connection name
            db_type: Type of database
            url: Connection URL
            config: Additional configuration
        """
        self.configs[name] = {
            "type": db_type,
            "url": url,
            "config": config or {},
            **kwargs
        }

        # Initialize connection based on type
        if db_type in [DatabaseType.POSTGRESQL, DatabaseType.MYSQL, DatabaseType.SQLITE]:
            connection = await self._init_sql_connection(url, **kwargs)
        elif db_type == DatabaseType.MONGODB:
            connection = await self._init_mongodb_connection(url, **kwargs)
        elif db_type == DatabaseType.REDIS:
            connection = await self._init_redis_connection(url, **kwargs)
        elif db_type in [DatabaseType.PINECONE, DatabaseType.WEAVIATE,
                         DatabaseType.CHROMADB, DatabaseType.QDRANT]:
            connection = await self._init_vector_db_connection(db_type, config or {}, **kwargs)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

        self.connections[name] = connection

    async def _init_sql_connection(self, url: str, **kwargs):
        """Initialize SQL database connection."""
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(url, **kwargs)
        return engine

    async def _init_mongodb_connection(self, url: str, **kwargs):
        """Initialize MongoDB connection."""
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(url, **kwargs)
        return client

    async def _init_redis_connection(self, url: str, **kwargs):
        """Initialize Redis connection."""
        import aioredis
        redis = await aioredis.from_url(url, **kwargs)
        return redis

    async def _init_vector_db_connection(
        self,
        db_type: DatabaseType,
        config: Dict,
        **kwargs
    ):
        """Initialize vector database connection."""
        if db_type == DatabaseType.CHROMADB:
            import chromadb
            client = chromadb.Client(chromadb.Config(**config))
            return client
        elif db_type == DatabaseType.PINECONE:
            import pinecone
            pinecone.init(**config)
            return pinecone
        elif db_type == DatabaseType.WEAVIATE:
            import weaviate
            client = weaviate.Client(**config)
            return client
        elif db_type == DatabaseType.QDRANT:
            from qdrant_client import QdrantClient
            client = QdrantClient(**config)
            return client

    def get_connection(self, name: str):
        """Get database connection by name."""
        return self.connections.get(name)

    async def close_all(self):
        """Close all database connections."""
        for name, connection in self.connections.items():
            await self._close_connection(name, connection)
        self.connections.clear()

    async def _close_connection(self, name: str, connection: Any):
        """Close specific connection."""
        config = self.configs.get(name, {})
        db_type = config.get("type")

        if db_type in [DatabaseType.POSTGRESQL, DatabaseType.MYSQL, DatabaseType.SQLITE]:
            await connection.dispose()
        elif db_type == DatabaseType.MONGODB:
            connection.close()
        elif db_type == DatabaseType.REDIS:
            await connection.close()


class VectorDBManager:
    """
    Specialized manager for vector databases.

    Simplifies working with vector embeddings and similarity search.

    Example:
        ```python
        vector_db = VectorDBManager(
            db_type="chromadb",
            collection_name="documents"
        )

        # Add vectors
        await vector_db.add(
            ids=["doc1", "doc2"],
            embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
            metadata=[{"source": "file1"}, {"source": "file2"}]
        )

        # Search
        results = await vector_db.search(
            query_embedding=[0.15, 0.25, ...],
            top_k=5
        )
        ```
    """

    def __init__(
        self,
        db_type: str = "chromadb",
        collection_name: str = "default",
        config: Dict = None
    ):
        self.db_type = db_type
        self.collection_name = collection_name
        self.config = config or {}
        self.client = None
        self.collection = None

    async def initialize(self):
        """Initialize vector database."""
        if self.db_type == "chromadb":
            import chromadb
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
        elif self.db_type == "pinecone":
            import pinecone
            pinecone.init(**self.config)
            self.collection = pinecone.Index(self.collection_name)

    async def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict] = None,
        documents: List[str] = None
    ):
        """Add vectors to database."""
        if self.db_type == "chromadb":
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadata,
                documents=documents
            )

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Dict = None
    ):
        """Search for similar vectors."""
        if self.db_type == "chromadb":
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter
            )
            return results

    async def delete(self, ids: List[str]):
        """Delete vectors by IDs."""
        if self.db_type == "chromadb":
            self.collection.delete(ids=ids)
