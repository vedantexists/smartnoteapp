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
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Indexes or updates note embedding in ChromaDB."""
        coll = self._get_collection()
        meta = metadata or {}
        # Clean metadata (ChromaDB allows str, int, float, bool)
        safe_meta = {
            k: v if isinstance(v, (str, int, float, bool)) else str(v)
            for k, v in meta.items()
        }
        coll.upsert(
            ids=[note_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[safe_meta]
        )
        logger.info(f"Indexed note {note_id} into ChromaDB.")

    def find_similar(
        self, 
        embedding: List[float], 
        threshold: float = 0.85
    ) -> Optional[Tuple[str, float]]:
        """
        Finds existing note if cosine similarity > threshold (default 0.85).
        For cosine space: distance = 1 - similarity.
        Therefore, similarity = 1 - distance.
        """
        coll = self._get_collection()
        if coll.count() == 0:
            return None

        results = coll.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["distances", "metadatas", "documents"]
        )

        if not results or not results["ids"] or not results["ids"][0]:
            return None

        distance = results["distances"][0][0]
        similarity = 1.0 - distance

        logger.info(f"Top Chroma match: id={results['ids'][0][0]}, distance={distance:.4f}, similarity={similarity:.4f}")

        if similarity >= threshold:
            return results["ids"][0][0], similarity

        return None

    def search(
        self, 
        embedding: List[float], 
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Performs vector semantic search returning [(note_id, similarity), ...]."""
        coll = self._get_collection()
        if coll.count() == 0:
            return []

        n_results = min(limit, coll.count())
        results = coll.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["distances"]
        )

        output = []
        if results and results["ids"] and results["ids"][0]:
            for note_id, dist in zip(results["ids"][0], results["distances"][0]):
                similarity = max(0.0, 1.0 - dist)
                output.append((note_id, similarity))

        return output

chromadb_service = ChromaDBService()
