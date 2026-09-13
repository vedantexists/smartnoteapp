import logging
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from app.config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

class ChromaDBService:
    def __init__(self):
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            chroma_dir = settings.get_resolved_data_dir() / "chroma"
            chroma_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initializing persistent ChromaDB client at {chroma_dir}")
            
            self._client = chromadb.PersistentClient(
                path=str(chroma_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Using cosine distance: distance = 1 - cosine_similarity
            self._collection = self._client.get_or_create_collection(
                name="social_notes",
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def add_or_update(
        self, 
        note_id: str, 
        embedding: List[float], 
        document: str, 
        user_id: str = "default_user",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Indexes or updates note embedding in ChromaDB with strict user_id scoping."""
        coll = self._get_collection()
        meta = metadata or {}
        safe_meta = {
            k: v if isinstance(v, (str, int, float, bool)) else str(v)
            for k, v in meta.items()
        }
        safe_meta["user_id"] = user_id

        coll.upsert(
            ids=[note_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[safe_meta]
        )
        logger.info(f"Indexed note {note_id} for user {user_id} into ChromaDB.")

    def find_similar(
        self, 
        embedding: List[float], 
        user_id: str = "default_user",
        threshold: float = 0.85
    ) -> Optional[Tuple[str, float]]:
        """
        Finds existing note belonging to the specified user if cosine similarity > threshold.
        Enforces where={"user_id": user_id} for strict multi-tenant isolation.
        """
        coll = self._get_collection()
        if coll.count() == 0:
            return None

        try:
            results = coll.query(
                query_embeddings=[embedding],
                n_results=1,
                where={"user_id": user_id},
                include=["distances", "metadatas", "documents"]
            )
        except Exception as e:
            logger.warning(f"ChromaDB query with filter failed (possibly empty collection for user): {e}")
            return None

        if not results or not results["ids"] or not results["ids"][0]:
            return None

        distance = results["distances"][0][0]
        similarity = 1.0 - distance

        logger.info(f"Top Chroma match for user {user_id}: id={results['ids'][0][0]}, similarity={similarity:.4f}")

        if similarity >= threshold:
            return results["ids"][0][0], similarity

        return None

    def search(
        self, 
        embedding: List[float], 
        user_id: str = "default_user",
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Performs vector semantic search strictly scoped to the tenant's user_id."""
        coll = self._get_collection()
        if coll.count() == 0:
            return []

        try:
            results = coll.query(
                query_embeddings=[embedding],
                n_results=limit,
                where={"user_id": user_id},
                include=["distances"]
            )
        except Exception as e:
            logger.warning(f"Chroma search with filter failed: {e}")
            return []

        output = []
        if results and results["ids"] and results["ids"][0]:
            for note_id, dist in zip(results["ids"][0], results["distances"][0]):
                similarity = max(0.0, 1.0 - dist)
                output.append((note_id, similarity))

        return output

chromadb_service = ChromaDBService()
