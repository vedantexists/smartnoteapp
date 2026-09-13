import sqlite3
import json
import uuid
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.config import settings
from app.models.schemas import (
    NoteRecord, WebResource, EntertainmentRec, Flashcard, 
    IntegrationStatus, DomainCategory, WeeklyDigestResponse
)

def get_db_path() -> Path:
    data_dir = settings.get_resolved_data_dir()
    return data_dir / "smartnotes.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        source_url TEXT NOT NULL,
        domain TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        detailed_notes TEXT NOT NULL,
        event_ics TEXT,
        status TEXT NOT NULL,
        clickbait_reason TEXT,
        github_repos TEXT,
        github_starred TEXT,
        spotify_added TEXT,
        tmdb_added TEXT,
        notion_synced INTEGER DEFAULT 0,
        notion_url TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS link_items (
        id TEXT PRIMARY KEY,
        note_id TEXT NOT NULL,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        purpose TEXT NOT NULL,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_recs (
        id TEXT PRIMARY KEY,
        note_id TEXT NOT NULL,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        creator TEXT NOT NULL,
        reason TEXT NOT NULL,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards (
        id TEXT PRIMARY KEY,
        note_id TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        key_takeaway TEXT,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weekly_digests (
        id TEXT PRIMARY KEY,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        digest_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_domain ON notes(domain);")

    conn.commit()
    conn.close()

def save_note(
    note_id: str,
    source_url: str,
    domain: str,
    title: str,
    summary: str,
    detailed_notes: str,
    flashcards: List[Flashcard],
    github_repos: List[str],
    web_resources: List[WebResource],
    entertainment_recs: List[EntertainmentRec],
    event_ics: Optional[str] = None,
    integrations: Optional[IntegrationStatus] = None,
    status: str = "success",
    clickbait_reason: Optional[str] = None
) -> NoteRecord:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    integ = integrations or IntegrationStatus()

    cursor.execute("""
    INSERT INTO notes (
        id, source_url, domain, title, summary, detailed_notes, event_ics,
        status, clickbait_reason, github_repos, github_starred, spotify_added,
        tmdb_added, notion_synced, notion_url, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        note_id,
        source_url,
        domain,
        title,
        summary,
        detailed_notes,
        event_ics,
        status,
        clickbait_reason,
        json.dumps(github_repos),
        json.dumps(integ.github_starred),
        json.dumps(integ.spotify_added),
        json.dumps(integ.tmdb_added),
        1 if integ.notion_synced else 0,
        integ.notion_url,
        now,
        now
    ))

    # Insert link items
    for item in web_resources:
        cursor.execute("""
        INSERT INTO link_items (id, note_id, name, url, purpose)
        VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), note_id, item.name, item.url, item.purpose))

    # Insert media recs
    for item in entertainment_recs:
        cursor.execute("""
        INSERT INTO media_recs (id, note_id, title, type, creator, reason)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), note_id, item.title, item.type, item.creator, item.reason))

    # Insert flashcards
    for item in flashcards:
        cursor.execute("""
        INSERT INTO flashcards (id, note_id, question, answer, key_takeaway)
        VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), note_id, item.question, item.answer, item.key_takeaway))

    conn.commit()
    conn.close()

    return get_note_by_id(note_id)

def update_note(
    note_id: str,
    domain: Optional[str] = None,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    detailed_notes: Optional[str] = None,
    flashcards: Optional[List[Flashcard]] = None,
    github_repos: Optional[List[str]] = None,
    web_resources: Optional[List[WebResource]] = None,
    entertainment_recs: Optional[List[EntertainmentRec]] = None,
    event_ics: Optional[str] = None,
    integrations: Optional[IntegrationStatus] = None
) -> Optional[NoteRecord]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    existing = get_note_by_id(note_id)
    if not existing:
        conn.close()
        return None

    update_fields = []
    params = []

    if domain:
        update_fields.append("domain = ?")
        params.append(domain)
    if title:
        update_fields.append("title = ?")
        params.append(title)
    if summary:
        update_fields.append("summary = ?")
        params.append(summary)
    if detailed_notes:
        update_fields.append("detailed_notes = ?")
        params.append(detailed_notes)
    if event_ics is not None:
        update_fields.append("event_ics = ?")
        params.append(event_ics)
    if github_repos is not None:
        # Merge uniquely with existing
        merged_repos = list(dict.fromkeys(existing.github_repos + github_repos))
        update_fields.append("github_repos = ?")
        params.append(json.dumps(merged_repos))

    if integrations:
        merged_starred = list(dict.fromkeys(existing.integrations.github_starred + integrations.github_starred))
        merged_spotify = list(dict.fromkeys(existing.integrations.spotify_added + integrations.spotify_added))
        merged_tmdb = list(dict.fromkeys(existing.integrations.tmdb_added + integrations.tmdb_added))
        notion_synced = 1 if (existing.integrations.notion_synced or integrations.notion_synced) else 0
        notion_url = integrations.notion_url or existing.integrations.notion_url

        update_fields.extend([
            "github_starred = ?",
            "spotify_added = ?",
            "tmdb_added = ?",
            "notion_synced = ?",
            "notion_url = ?"
        ])
        params.extend([
            json.dumps(merged_starred),
            json.dumps(merged_spotify),
            json.dumps(merged_tmdb),
            notion_synced,
            notion_url
        ])

    update_fields.append("updated_at = ?")
    params.append(now)

    params.append(note_id)
    cursor.execute(f"UPDATE notes SET {', '.join(update_fields)} WHERE id = ?", params)

    # If web_resources provided, append non-duplicates
    if web_resources:
        existing_urls = {item.url for item in existing.web_resources}
        for item in web_resources:
            if item.url not in existing_urls:
                cursor.execute("""
                INSERT INTO link_items (id, note_id, name, url, purpose)
                VALUES (?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), note_id, item.name, item.url, item.purpose))
                existing_urls.add(item.url)

    # If entertainment_recs provided, append non-duplicates
    if entertainment_recs:
        existing_titles = {item.title.lower() for item in existing.entertainment_recommendations}
        for item in entertainment_recs:
            if item.title.lower() not in existing_titles:
                cursor.execute("""
                INSERT INTO media_recs (id, note_id, title, type, creator, reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), note_id, item.title, item.type, item.creator, item.reason))
                existing_titles.add(item.title.lower())

    # If flashcards provided, append non-duplicates
    if flashcards:
        existing_qs = {fc.question.lower().strip() for fc in existing.flashcards}
        for fc in flashcards:
            if fc.question.lower().strip() not in existing_qs:
                cursor.execute("""
                INSERT INTO flashcards (id, note_id, question, answer, key_takeaway)
                VALUES (?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), note_id, fc.question, fc.answer, fc.key_takeaway))
                existing_qs.add(fc.question.lower().strip())

    conn.commit()
    conn.close()

    return get_note_by_id(note_id)

def get_note_by_id(note_id: str) -> Optional[NoteRecord]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    # Fetch links
    cursor.execute("SELECT name, url, purpose FROM link_items WHERE note_id = ?", (note_id,))
    links = [WebResource(name=r["name"], url=r["url"], purpose=r["purpose"]) for r in cursor.fetchall()]

    # Fetch media recs
    cursor.execute("SELECT title, type, creator, reason FROM media_recs WHERE note_id = ?", (note_id,))
    recs = [EntertainmentRec(title=r["title"], type=r["type"], creator=r["creator"], reason=r["reason"]) for r in cursor.fetchall()]

    # Fetch flashcards
    cursor.execute("SELECT question, answer, key_takeaway FROM flashcards WHERE note_id = ?", (note_id,))
    cards = [Flashcard(question=r["question"], answer=r["answer"], key_takeaway=r["key_takeaway"]) for r in cursor.fetchall()]

    conn.close()

    github_repos = json.loads(row["github_repos"]) if row["github_repos"] else []
    github_starred = json.loads(row["github_starred"]) if row["github_starred"] else []
    spotify_added = json.loads(row["spotify_added"]) if row["spotify_added"] else []
    tmdb_added = json.loads(row["tmdb_added"]) if row["tmdb_added"] else []

    integrations = IntegrationStatus(
        github_starred=github_starred,
        spotify_added=spotify_added,
        tmdb_added=tmdb_added,
        notion_synced=bool(row["notion_synced"]),
        notion_url=row["notion_url"]
    )

    return NoteRecord(
        id=row["id"],
        source_url=row["source_url"],
        domain=DomainCategory(row["domain"]) if row["domain"] in DomainCategory.__members__ else DomainCategory.OTHER,
        title=row["title"],
        summary=row["summary"],
        detailed_notes=row["detailed_notes"],
        flashcards=cards,
        github_repos=github_repos,
        web_resources=links,
        entertainment_recommendations=recs,
        event_ics=row["event_ics"],
        integrations=integrations,
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

def list_notes(limit: int = 50, offset: int = 0, domain: Optional[str] = None) -> List[NoteRecord]:
    conn = get_connection()
    cursor = conn.cursor()
    if domain:
        cursor.execute("SELECT id FROM notes WHERE status = 'success' AND domain = ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (domain, limit, offset))
    else:
        cursor.execute("SELECT id FROM notes WHERE status = 'success' ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        n = get_note_by_id(r["id"])
        if n:
            results.append(n)
    return results

def get_notes_in_range(start_date: str, end_date: str) -> List[NoteRecord]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id FROM notes 
    WHERE status = 'success' AND created_at >= ? AND created_at <= ?
    ORDER BY created_at ASC
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    notes = []
    for r in rows:
        n = get_note_by_id(r["id"])
        if n:
            notes.append(n)
    return notes

def save_weekly_digest(digest: WeeklyDigestResponse):
    conn = get_connection()
    cursor = conn.cursor()
    digest_id = str(uuid.uuid4())
    cursor.execute("""
    INSERT INTO weekly_digests (id, start_date, end_date, digest_json, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        digest_id,
        digest.start_date,
        digest.end_date,
        digest.model_dump_json(),
        digest.generated_at
    ))
    conn.commit()
    conn.close()

def get_latest_weekly_digest() -> Optional[WeeklyDigestResponse]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT digest_json FROM weekly_digests ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return WeeklyDigestResponse.model_validate_json(row["digest_json"])
