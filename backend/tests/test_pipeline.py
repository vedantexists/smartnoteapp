import pytest
import uuid
from pathlib import Path
from app.models.schemas import (
    DomainCategory, WebResource, EntertainmentRec, Flashcard,
    IntegrationStatus, ProcessStatus, ProcessReelRequest
)
from app.services.database import (
    init_db, save_note, update_note, get_note_by_id, list_notes,
    save_weekly_digest, get_latest_weekly_digest
)
from app.services.integrations import integrations_service
from app.services.gemini_service import gemini_service
from app.services.chromadb_service import chromadb_service

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Sets up a temporary SQLite and ChromaDB directory for isolated testing."""
    monkeypatch.setattr("app.config.settings.data_dir", str(tmp_path / "data"))
    monkeypatch.setattr("app.config.settings.temp_dir", str(tmp_path / "temp"))
    init_db()

def test_database_crud():
    note_id = str(uuid.uuid4())
    flashcards = [
        Flashcard(question="What is WorkManager?", answer="Android background dispatch library.", key_takeaway="Survives task kill.")
    ]
    links = [
        WebResource(name="Jetpack Compose", url="https://developer.android.com/compose", purpose="Declarative UI")
    ]
    recs = [
        EntertainmentRec(title="Mr. Robot", type="Series", creator="Sam Esmail", reason="Realistic cybersecurity")
    ]
    status = IntegrationStatus(github_starred=["google/workmanager"], notion_synced=True)

    saved = save_note(
        note_id=note_id,
        source_url="https://instagram.com/reel/test1",
        domain=DomainCategory.TECH_EDUCATION.value,
        title="Modern Android Architecture",
        summary="A review of Jetpack Compose and WorkManager.",
        detailed_notes="### Jetpack Compose\nDeclarative UI framework.",
        flashcards=flashcards,
        github_repos=["google/workmanager"],
        web_resources=links,
        entertainment_recs=recs,
        integrations=status,
        status="success"
    )

    assert saved is not None
    assert saved.id == note_id
    assert len(saved.flashcards) == 1
    assert saved.flashcards[0].question == "What is WorkManager?"
    assert len(saved.web_resources) == 1
    assert len(saved.entertainment_recommendations) == 1
    assert saved.integrations.notion_synced is True

    # Test retrieval
    fetched = get_note_by_id(note_id)
    assert fetched is not None
    assert fetched.title == "Modern Android Architecture"

    # Test update / merge
    new_card = Flashcard(question="What is Room DB?", answer="SQLite abstraction.", key_takeaway="Local persistence")
    updated = update_note(
        note_id=note_id,
        title="Modern Android Architecture & Persistence",
        flashcards=[new_card]
    )
    assert updated is not None
    assert updated.title == "Modern Android Architecture & Persistence"
    assert len(updated.flashcards) == 2

def test_github_repo_validation():
    valid = integrations_service._clean_repo_name("owner/repo")
    assert valid == "owner/repo"

    valid_url = integrations_service._clean_repo_name("https://github.com/facebook/react.git")
    assert valid_url == "facebook/react"

    invalid = integrations_service._clean_repo_name("not_a_github_repo")
    assert invalid is None

    non_repo_link = integrations_service._clean_repo_name("https://medium.com/@user/story")
    assert non_repo_link is None

def test_chromadb_similarity_deduplication():
    # Use deterministic vectors to test similarity threshold
    vec1 = [1.0] + [0.0] * 767
    vec2 = [0.99] + [0.01] * 767  # Cosine similarity > 0.95
    vec_diff = [0.0] * 767 + [1.0] # Orthogonal, similarity ~ 0

    note_id_1 = str(uuid.uuid4())
    chromadb_service.add_or_update(
        note_id=note_id_1,
        embedding=vec1,
        document="React 19 Server Components",
        metadata={"domain": "TECH_EDUCATION"}
    )

    # Search with very similar vector
    match = chromadb_service.find_similar(vec2, threshold=0.85)
    assert match is not None
    matched_id, similarity = match
    assert matched_id == note_id_1
    assert similarity >= 0.85

    # Search with dissimilar vector
    diff_match = chromadb_service.find_similar(vec_diff, threshold=0.85)
    assert diff_match is None

def test_json_cleaner():
    raw_markdown_json = """
    ```json
    {
      "is_clickbait_or_scam": false,
      "domain": "TECH_EDUCATION",
      "title": "Clean Architecture Guide",
      "core_summary": "Guide on architecture",
      "detailed_notes": "Detailed notes here",
      "flashcards": [],
      "github_repos": ["torvalds/linux"],
      "web_resources": [],
      "entertainment_recommendations": []
    }
    ```
    """
    clean = gemini_service._clean_json_str(raw_markdown_json)
    assert not clean.startswith("```")
    res = gemini_service._parse_json_result(raw_markdown_json)
    assert res.title == "Clean Architecture Guide"
    assert res.github_repos == ["torvalds/linux"]
