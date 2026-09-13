import logging
import uuid
import datetime
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import (
    ProcessReelRequest, ProcessReelResponse, ProcessStatus,
    SearchResponse, SearchItem, NoteRecord, WeeklyDigestResponse,
    DomainCategory, IntegrationStatus
)
from app.services.database import (
    init_db, save_note, update_note, get_note_by_id, list_notes,
    get_latest_weekly_digest
)
from app.services.downloader import downloader
from app.services.gemini_service import gemini_service
from app.services.chromadb_service import chromadb_service
from app.services.integrations import integrations_service
from app.scheduler.weekly_digest import init_scheduler, run_weekly_digest_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartnote")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing SmartNote Backend...")
    init_db()
    init_scheduler()
    logger.info("Database and Scheduler successfully initialized.")
    yield
    # Shutdown
    logger.info("Shutting down SmartNote Backend...")

app = FastAPI(
    title="SmartNote AI Reel Ingestion Pipeline",
    description="Multimodal short-form video note extractor, semantic deduplicator, and automation orchestrator",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Android client & web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Health check for Hugging Face Spaces and Android connectivity verification."""
    return {
        "status": "healthy",
        "service": "smartnote-pipeline",
        "version": "1.0.0",
        "gemini_model": settings.gemini_model,
        "storage": str(settings.get_resolved_data_dir())
    }

@app.post("/process-reel", response_model=ProcessReelResponse)
async def process_reel(request: ProcessReelRequest):
    """
    Ingests an Instagram Reel or YouTube Short URL:
    1. Downloads low-res .mp4 via yt-dlp.
    2. Multimodal extraction & Fact-Check/Clickbait gate via Gemini File API.
    3. Semantic deduplication via ChromaDB (cosine similarity > 0.85).
    4. Auto-merges on match or creates new note.
    5. Automates GitHub star, Spotify playlist, TMDB watchlist, and Notion sync.
    6. Cleans up local media files.
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    logger.info(f"Received process request for: {url}")
    video_path: Optional[Path] = None

    try:
        # Step 1: Download low-res media
        try:
            video_path = downloader.download_video(url)
        except Exception as dl_err:
            logger.error(f"Download failed for {url}: {dl_err}")
            # If download fails (e.g. invalid URL, network issue), return clean failure
            raise HTTPException(status_code=422, detail=f"Failed to download video: {str(dl_err)}")

        # Step 2: Multimodal Gemini Extraction
        extraction = gemini_service.extract_from_video(video_path)

        # Step 2a: Clickbait / Fact-Check Gate
        if extraction.is_clickbait_or_scam:
            logger.warning(f"Rejected clickbait/scam video: {url}. Reason: {extraction.clickbait_reason}")
            # Record rejection in database for audit
            rejected_id = str(uuid.uuid4())
            save_note(
                note_id=rejected_id,
                source_url=url,
                domain=DomainCategory.OTHER.value,
                title=f"Rejected: {extraction.title}",
                summary=extraction.clickbait_reason or "Empty clickbait or deceptive scam detected.",
                detailed_notes=extraction.detailed_notes or "",
                flashcards=[],
                github_repos=[],
                web_resources=[],
                entertainment_recs=[],
                event_ics=None,
                status="rejected_clickbait",
                clickbait_reason=extraction.clickbait_reason
            )
            return ProcessReelResponse(
                status=ProcessStatus.REJECTED_CLICKBAIT,
                note_id=rejected_id,
                message=f"Video rejected: {extraction.clickbait_reason or 'Clickbait or scam detected'}",
                domain=DomainCategory.OTHER,
                title=extraction.title,
                summary=extraction.clickbait_reason
            )

        # Step 3: Embed summary for ChromaDB deduplication
        topic_text = f"{extraction.title}. {extraction.core_summary}"
        embedding = gemini_service.get_embedding(topic_text)

        # Step 4: Check for semantic match (Cosine similarity > 0.85)
        similar_match = chromadb_service.find_similar(embedding, threshold=0.85)

        if similar_match:
            existing_note_id, similarity = similar_match
            logger.info(f"Duplicate/overlapping topic found! Existing ID: {existing_note_id} (Similarity: {similarity:.4f})")
            existing_note = get_note_by_id(existing_note_id)

            if existing_note:
                # Merge using Gemini
                merged_result = gemini_service.merge_notes(
                    existing_json=existing_note.model_dump(),
                    new_json=extraction.model_dump()
                )

                # Execute integrations for any newly discovered items
                new_repos = [r for r in merged_result.github_repos if r not in existing_note.github_repos]
                new_recs = [r for r in merged_result.entertainment_recommendations if r.title.lower() not in {e.title.lower() for e in existing_note.entertainment_recommendations}]
                
                integration_status = integrations_service.execute_all_integrations(
                    github_repos=new_repos,
                    entertainment_recs=new_recs,
                    title=merged_result.title,
                    domain=merged_result.domain.value,
                    summary=merged_result.core_summary,
                    detailed_notes=merged_result.detailed_notes,
                    source_url=url,
                    web_resources=merged_result.web_resources,
                    flashcards=merged_result.flashcards
                )

                # Update existing note in SQLite
                updated = update_note(
                    note_id=existing_note_id,
                    domain=merged_result.domain.value,
                    title=merged_result.title,
                    summary=merged_result.core_summary,
                    detailed_notes=merged_result.detailed_notes,
                    flashcards=merged_result.flashcards,
                    github_repos=merged_result.github_repos,
                    web_resources=merged_result.web_resources,
                    entertainment_recs=merged_result.entertainment_recommendations,
                    event_ics=merged_result.event_ics,
                    integrations=integration_status
                )

                # Update ChromaDB vector
                chromadb_service.add_or_update(
                    note_id=existing_note_id,
                    embedding=embedding,
                    document=f"{merged_result.title}. {merged_result.core_summary}",
                    metadata={"domain": merged_result.domain.value, "title": merged_result.title}
                )

                return ProcessReelResponse(
                    status=ProcessStatus.MERGED,
                    note_id=existing_note_id,
                    message=f"Merged into existing note (Similarity: {similarity*100:.1f}%)",
                    domain=merged_result.domain,
                    title=merged_result.title,
                    summary=merged_result.core_summary,
                    detailed_notes=merged_result.detailed_notes,
                    flashcards=merged_result.flashcards,
                    github_repos=merged_result.github_repos,
                    web_resources=merged_result.web_resources,
                    entertainment_recommendations=merged_result.entertainment_recommendations,
                    event_ics=merged_result.event_ics,
                    integrations=updated.integrations if updated else integration_status,
                    created_at=updated.created_at if updated else None,
                    updated_at=updated.updated_at if updated else None
                )

        # Step 5: No duplicate match -> Save as new note
        new_note_id = str(uuid.uuid4())
        logger.info(f"Saving new note with ID: {new_note_id}")

        integration_status = integrations_service.execute_all_integrations(
            github_repos=extraction.github_repos,
            entertainment_recs=extraction.entertainment_recommendations,
            title=extraction.title,
            domain=extraction.domain.value,
            summary=extraction.core_summary,
            detailed_notes=extraction.detailed_notes,
            source_url=url,
            web_resources=extraction.web_resources,
            flashcards=extraction.flashcards
        )

        saved = save_note(
            note_id=new_note_id,
            source_url=url,
            domain=extraction.domain.value,
            title=extraction.title,
            summary=extraction.core_summary,
            detailed_notes=extraction.detailed_notes,
            flashcards=extraction.flashcards,
            github_repos=extraction.github_repos,
            web_resources=extraction.web_resources,
            entertainment_recs=extraction.entertainment_recommendations,
            event_ics=extraction.event_ics,
            integrations=integration_status,
            status="success"
        )

        # Index in ChromaDB
        chromadb_service.add_or_update(
            note_id=new_note_id,
            embedding=embedding,
            document=f"{extraction.title}. {extraction.core_summary}",
            metadata={"domain": extraction.domain.value, "title": extraction.title}
        )

        return ProcessReelResponse(
            status=ProcessStatus.SUCCESS,
            note_id=new_note_id,
            message="Note extracted and indexed successfully",
            domain=extraction.domain,
            title=extraction.title,
            summary=extraction.core_summary,
            detailed_notes=extraction.detailed_notes,
            flashcards=extraction.flashcards,
            github_repos=extraction.github_repos,
            web_resources=extraction.web_resources,
            entertainment_recommendations=extraction.entertainment_recommendations,
            event_ics=extraction.event_ics,
            integrations=integration_status,
            created_at=saved.created_at,
            updated_at=saved.updated_at
        )

    finally:
        # Step 6: Guaranteed Cleanup of local temporary media file
        downloader.cleanup_file(video_path)

@app.get("/search", response_model=SearchResponse)
def search_notes(q: str = Query(..., min_length=1, description="Conceptual query")):
    """Vector semantic search over stored notes using ChromaDB."""
    query = q.strip()
    query_embedding = gemini_service.get_embedding(query)
    matches = chromadb_service.search(query_embedding, limit=15)

    results: List[SearchItem] = []
    for note_id, score in matches:
        note = get_note_by_id(note_id)
        if note:
            results.append(SearchItem(note=note, similarity_score=round(score, 4)))

    return SearchResponse(
        query=query,
        count=len(results),
        results=results
    )

@app.get("/digest/weekly", response_model=WeeklyDigestResponse)
async def get_weekly_digest(force_refresh: bool = False):
    """
    Returns the aggregated weekly summary.
    If force_refresh is True or no prior digest exists, triggers generation.
    """
    if not force_refresh:
        existing = get_latest_weekly_digest()
        if existing:
            return existing

    digest = await run_weekly_digest_job()
    return digest

@app.get("/notes", response_model=List[NoteRecord])
def get_notes(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    domain: Optional[str] = None
):
    """Retrieves list of stored notes with optional pagination and category filtering."""
    return list_notes(limit=limit, offset=offset, domain=domain)

@app.get("/notes/{note_id}", response_model=NoteRecord)
def get_single_note(note_id: str):
    """Fetches full details of a specific note."""
    note = get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
