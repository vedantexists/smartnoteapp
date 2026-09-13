import sys
import os
import uuid
import datetime
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Configure temporary directories for test
test_data_dir = backend_dir / "test_data_tmp"
test_data_dir.mkdir(parents=True, exist_ok=True)
os.environ["DATA_DIR"] = str(test_data_dir)
os.environ["TEMP_DIR"] = str(test_data_dir / "temp")

from app.config import settings
from app.models.schemas import (
    DomainCategory, WebResource, EntertainmentRec, Flashcard,
    IntegrationStatus, ProcessStatus, GeminiExtractionResult
)
from app.services.database import (
    init_db, save_note, update_note, get_note_by_id, list_notes,
    save_weekly_digest, get_latest_weekly_digest
)
from app.services.integrations import integrations_service
from app.services.gemini_service import gemini_service

def main():
    print("=== Running Backend Verification Tests ===")
    
    # 1. Database Init & CRUD
    init_db()
    print("[PASS] SQLite Database initialized successfully.")

    note_id = str(uuid.uuid4())
    cards = [
        Flashcard(question="What is WorkManager?", answer="Android background dispatch library.", key_takeaway="Survives ColorOS killer.")
    ]
    links = [
        WebResource(name="Jetpack Compose", url="https://developer.android.com/compose", purpose="Declarative UI toolkit")
    ]
    recs = [
        EntertainmentRec(title="The Social Network", type="Movie", creator="David Fincher", reason="Founding story")
    ]
    status = IntegrationStatus(github_starred=["google/workmanager"], notion_synced=True)

    saved = save_note(
        note_id=note_id,
        source_url="https://instagram.com/reel/abc123xyz",
        domain=DomainCategory.TECH_EDUCATION.value,
        title="Modern Android Development",
        summary="Guide on Jetpack Compose and WorkManager for aggressive battery management.",
        detailed_notes="### Jetpack Compose\nState-driven declarative UI.",
        flashcards=cards,
        github_repos=["google/workmanager"],
        web_resources=links,
        entertainment_recs=recs,
        integrations=status,
        status="success"
    )
    assert saved is not None
    assert saved.id == note_id
    assert len(saved.flashcards) == 1
    assert len(saved.web_resources) == 1
    assert len(saved.entertainment_recommendations) == 1
    assert saved.integrations.notion_synced is True
    print("[PASS] Note CRUD and relational tables verified.")

    # 2. GitHub Repo Sanitization
    valid_repo = integrations_service._clean_repo_name("https://github.com/torvalds/linux.git")
    assert valid_repo == "torvalds/linux", f"Expected torvalds/linux, got {valid_repo}"
    
    invalid_repo = integrations_service._clean_repo_name("https://example.com/not-github")
    assert invalid_repo is None
    print("[PASS] GitHub owner/repo regex and URL extraction verified.")

    # 3. Gemini Extraction JSON cleaner
    sample_markdown = """
    ```json
    {
        "is_clickbait_or_scam": false,
        "domain": "TECH_EDUCATION",
        "title": "Clean Architecture on Android",
        "core_summary": "Separation of concerns using Room and Compose.",
        "detailed_notes": "### Steps\\n1. Room entities\\n2. Dao interfaces",
        "flashcards": [
            {"question": "What is Room?", "answer": "SQLite abstraction", "key_takeaway": "Type safe"}
        ],
        "github_repos": ["android/architecture-samples"],
        "web_resources": [
            {"name": "Android Dev", "url": "https://developer.android.com", "purpose": "Docs"}
        ],
        "entertainment_recommendations": [],
        "event_ics": null
    }
    ```
    """
    clean_json = gemini_service._clean_json_str(sample_markdown)
    assert not clean_json.startswith("```")
    parsed = gemini_service._parse_json_result(sample_markdown)
    assert parsed.title == "Clean Architecture on Android"
    assert parsed.github_repos == ["android/architecture-samples"]
    print("[PASS] Gemini JSON parser and code fence stripper verified.")

    # 4. Note Merging Simulation
    merged = gemini_service.merge_notes(saved.model_dump(), parsed.model_dump())
    assert "android/architecture-samples" in merged.github_repos
    assert "google/workmanager" in merged.github_repos
    print("[PASS] Semantic note merging logic verified.")

    # Clean up test data
    import shutil
    shutil.rmtree(test_data_dir, ignore_errors=True)
    print("[PASS] Temporary test data cleaned up.")
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
