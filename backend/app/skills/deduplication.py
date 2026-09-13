import logging
from typing import Optional, Tuple
from app.models.schemas import GeminiExtractionResult, NoteRecord
from app.services.chromadb_service import chromadb_service
from app.services.gemini_service import gemini_service
from app.services.database import get_note_by_id, update_note

logger = logging.getLogger(__name__)

def deduplicate_and_merge(
    user_id: str,
    extraction: GeminiExtractionResult,
    embedding: list
) -> Optional[Tuple[str, float, GeminiExtractionResult, NoteRecord]]:
    """
    Checks if an existing note for the given user exceeds the 0.85 cosine similarity threshold.
    If matched, merges existing and new information using Gemini and updates the database.
    Returns (note_id, similarity, merged_result, updated_note_record) if merged; None otherwise.
    """
    match = chromadb_service.find_similar(embedding, user_id=user_id, threshold=0.85)
    if not match:
        return None

    existing_id, similarity = match
    existing_note = get_note_by_id(existing_id, user_id=user_id)
    if not existing_note:
        return None

    logger.info(f"Merging into existing note {existing_id} for user {user_id} (Similarity: {similarity:.4f})")
    merged_result = gemini_service.merge_notes(
        existing_json=existing_note.model_dump(),
        new_json=extraction.model_dump()
    )

    updated_record = update_note(
        note_id=existing_id,
        domain=merged_result.domain.value,
        title=merged_result.title,
        summary=merged_result.core_summary,
        detailed_notes=merged_result.detailed_notes,
        flashcards=merged_result.flashcards,
        github_repos=merged_result.github_repos,
        web_resources=merged_result.web_resources,
        entertainment_recs=merged_result.entertainment_recommendations,
        event_ics=merged_result.event_ics,
        user_id=user_id
    )

    # Update vector embedding in ChromaDB
    chromadb_service.add_or_update(
        note_id=existing_id,
        embedding=embedding,
        document=f"{merged_result.title}. {merged_result.core_summary}",
        user_id=user_id,
        metadata={"domain": merged_result.domain.value, "title": merged_result.title}
    )

    return existing_id, similarity, merged_result, updated_record
