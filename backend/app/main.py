import logging
import uuid
import datetime
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, status
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

# Auth & Modular Skills
from app.auth.routes import router as auth_router
from app.auth.jwt import get_current_user
from app.skills.fact_checking import check_clickbait_and_scam
from app.skills.deduplication import deduplicate_and_merge
from app.skills.repo_starring import star_github_repositories
from app.skills.playlist_syncing import sync_spotify_tracks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartnote")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing SmartNote Multi-Tenant Backend with OAuth2 & Encryption...")
    init_db()
    init_scheduler()
    logger.info("Database, Encryption, and Schedulers initialized.")
    yield
    logger.info("Shutting down SmartNote Backend...")

app = FastAPI(
    title="SmartNote AI Reel Ingestion Pipeline",
    description="Multi-tenant multimodal video note extractor with OAuth2 PKCE, token encryption, and deduplication",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount OAuth2 Authentication Router
app.include_router(auth_router)

@app.get("/health")
def health_check():
    """Health check for Hugging Face Spaces and Android connectivity verification."""
    return {
        "status": "healthy",
        "service": "smartnote-pipeline",
        "version": "2.0.0",
        "gemini_model": settings.gemini_model,
        "security": {
            "oauth_pkce": True,
            "encryption_at_rest": True,
            "multi_tenant_isolation": True
        }
    }

@app.post("/process-reel", response_model=ProcessReelResponse)
async def process_reel(
    request: ProcessReelRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Ingests an Instagram Reel or YouTube Short URL:
    1. Input sanitization & SSRF defense on URL.
    2. Downloads low-res .mp4 via yt-dlp.
    3. Multimodal extraction & Fact-Check/Clickbait gate via Gemini File API.
    4. Multi-tenant semantic deduplication via ChromaDB (scoped strictly to current_user).
    5. Auto-merges on match or creates new note.
    6. Automates GitHub star and Spotify sync using current user's encrypted OAuth tokens.
    7. Cleans up local media files.
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    logger.info(f"User '{current_user}' processing reel: {url}")
    video_path: Optional[Path] = None

    try:
        # Step 1 & 2: Validate URL (SSRF defense) and download media
        try:
            video_path = downloader.download_video(url)
        except ValueError as val_err:
            raise HTTPException(status_code=400, detail=str(val_err))
        except Exception as dl_err:
            logger.error(f"Download failed for {url}: {dl_err}")
            raise HTTPException(status_code=422, detail=f"Failed to download video: {str(dl_err)}")

        # Step 3: Multimodal Gemini Extraction
        extraction = gemini_service.extract_from_video(video_path)

        # Step 3a: Clickbait / Fact-Check Gate (via modular skill)
        is_rejected, reject_reason = check_clickbait_and_scam(extraction)
        if is_rejected:
            logger.warning(f"Rejected content for user '{current_user}': {reject_reason}")
            rejected_id = str(uuid.uuid4())
            save_note(
                note_id=rejected_id,
                source_url=url,
                domain=DomainCategory.OTHER.value,
                title=f"Rejected: {extraction.title}",
                summary=reject_reason or "Empty clickbait or deceptive scam detected.",
                detailed_notes=extraction.detailed_notes or "",
                flashcards=[],
                github_repos=[],
                web_resources=[],
                entertainment_recs=[],
                event_ics=None,
                status="rejected_clickbait",
                clickbait_reason=reject_reason,
                user_id=current_user
            )
            return ProcessReelResponse(
                status=ProcessStatus.REJECTED_CLICKBAIT,
                note_id=rejected_id,
                message=f"Video rejected: {reject_reason}",
                domain=DomainCategory.OTHER,
                title=extraction.title,
                summary=reject_reason
            )

        # Step 4: Embed summary for vector deduplication
        topic_text = f"{extraction.title}. {extraction.core_summary}"
        embedding = gemini_service.get_embedding(topic_text)

        # Step 5: Multi-Tenant Deduplication (via modular skill)
        merge_result = deduplicate_and_merge(
            user_id=current_user,
            extraction=extraction,
            embedding=embedding
        )

        if merge_result:
            existing_id, similarity, merged_data, updated_note = merge_result
            # Execute integrations for any newly discovered items using user's encrypted tokens
            starred = star_github_repositories(user_id=current_user, repos=merged_data.github_repos)
            spotify_synced = sync_spotify_tracks(user_id=current_user, recs=merged_data.entertainment_recommendations)

            integ_status = IntegrationStatus(
                github_starred=starred,
                spotify_added=spotify_synced,
                tmdb_added=[],
                notion_synced=False
            )

            return ProcessReelResponse(
                status=ProcessStatus.MERGED,
                note_id=existing_id,
                message=f"Merged into existing note (Similarity: {similarity*100:.1f}%)",
                domain=merged_data.domain,
                title=merged_data.title,
                summary=merged_data.core_summary,
                detailed_notes=merged_data.detailed_notes,
                flashcards=merged_data.flashcards,
                github_repos=merged_data.github_repos,
                web_resources=merged_data.web_resources,
                entertainment_recommendations=merged_data.entertainment_recommendations,
                event_ics=merged_data.event_ics,
                integrations=integ_status,
                created_at=updated_note.created_at if updated_note else None,
                updated_at=updated_note.updated_at if updated_note else None
            )

        # Step 6: Novel note -> Save to tenant's storage
        new_note_id = str(uuid.uuid4())
        starred = star_github_repositories(user_id=current_user, repos=extraction.github_repos)
        spotify_synced = sync_spotify_tracks(user_id=current_user, recs=extraction.entertainment_recommendations)

        integ_status = IntegrationStatus(
            github_starred=starred,
            spotify_added=spotify_synced,
            tmdb_added=[],
            notion_synced=False
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
            integrations=integ_status,
            status="success",
            user_id=current_user
        )

        # Index in ChromaDB with user_id metadata
        chromadb_service.add_or_update(
            note_id=new_note_id,
            embedding=embedding,
            document=f"{extraction.title}. {extraction.core_summary}",
            user_id=current_user,
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
            integrations=integ_status,
            created_at=saved.created_at,
            updated_at=saved.updated_at
        )

    finally:
        downloader.cleanup_file(video_path)

@app.get("/search", response_model=SearchResponse)
def search_notes(
    q: str = Query(..., min_length=1, description="Conceptual query"),
    current_user: str = Depends(get_current_user)
):
    """Vector semantic search strictly scoped to the authenticated tenant's notes."""
    query = q.strip()
    query_embedding = gemini_service.get_embedding(query)
    matches = chromadb_service.search(query_embedding, user_id=current_user, limit=15)

    results: List[SearchItem] = []
    for note_id, score in matches:
        note = get_note_by_id(note_id, user_id=current_user)
        if note:
            results.append(SearchItem(note=note, similarity_score=round(score, 4)))

    return SearchResponse(
        query=query,
        count=len(results),
        results=results
    )

@app.get("/digest/weekly", response_model=WeeklyDigestResponse)
async def get_weekly_digest(
    force_refresh: bool = False,
    current_user: str = Depends(get_current_user)
):
    """Returns the aggregated weekly summary for the current user."""
    if not force_refresh:
        existing = get_latest_weekly_digest(user_id=current_user)
        if existing:
            return existing

    digest = await run_weekly_digest_job()
    return digest

@app.get("/notes", response_model=List[NoteRecord])
def get_notes(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    domain: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Retrieves tenant-isolated list of stored notes."""
    return list_notes(user_id=current_user, limit=limit, offset=offset, domain=domain)

@app.get("/notes/{note_id}", response_model=NoteRecord)
def get_single_note(
    note_id: str,
    current_user: str = Depends(get_current_user)
):
    """Fetches full details of a specific note, strictly enforcing tenant ownership (IDOR defense)."""
    note = get_note_by_id(note_id, user_id=current_user)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    return note
