# SmartNote AI Reel Ingestion Pipeline (Backend)

An autonomous, production-ready Python FastAPI pipeline designed to ingest Instagram Reels and YouTube Shorts, extract structured knowledge via Google Gemini Multimodal File API, semantically deduplicate notes using ChromaDB, orchestrate multi-service free tier automations (GitHub, Spotify, TMDB, Notion), and schedule weekly digests.

---

## ⚡ Key Architectural Features

1. **Multimodal Gemini File API**:
   - Downloads 480p/720p low-res `.mp4` using `yt-dlp` to minimize network overhead.
   - Uploads to Gemini File API (`ACTIVE` polling) to analyze visual frames, OCR text, and audio track simultaneously.
   - **Clickbait & Fact-Check Gate**: Automatically flags and halts on scams, dropshipping spam, or empty promotional content (`status: rejected_clickbait`).
   - Deep extraction: Core summary, Markdown notes, active recall flashcards, GitHub repos (`owner/repo`), curated web tools, entertainment recs, and `.ics` event strings.
   - Deletes uploaded media from Google servers after generation.

2. **ChromaDB Semantic Deduplication**:
   - Computes text embeddings for extracted notes.
   - Evaluates cosine similarity against stored vectors.
   - If similarity > 0.85, prompts Gemini to cleanly merge existing and new notes without redundancy (`status: merged`).
   - If novel, indexes as a new record (`status: success`).

3. **Multi-Service Free-Tier Integrations**:
   - **GitHub**: Stars identified repositories (`PUT https://api.github.com/user/starred/{owner}/{repo}`) using Personal Access Token.
   - **Spotify**: Discovers tracks mentioned in entertainment recommendations and appends them to user's playlist via `spotipy`.
   - **TMDB**: Searches movies and TV series and adds them to user watchlist.
   - **Notion**: Appends structured notes, callout blocks for flashcards, and web links to a Notion parent page or database.

4. **Scheduled Weekly Digests**:
   - Runs `APScheduler` cron job every Sunday at 00:00 UTC.
   - Aggregates the previous 7 days of captured insights into an executive digest with top flashcards for spaced repetition.

5. **Containerized for Hugging Face Spaces**:
   - Non-root user (UID 1000) for security.
   - Exposes port `7860`.
   - Local SQLite and ChromaDB data persisted under `/data`.

---

## 🚀 API Endpoints

- `POST /process-reel`: Ingests video URL, runs extraction, deduplication, and automations.
- `GET /search?q={query}`: Vector semantic search over stored notes.
- `GET /digest/weekly`: Aggregated weekly knowledge summary.
- `GET /notes`: List notes with category and pagination filters.
- `GET /notes/{id}`: Detailed single note view.
- `GET /health`: Service health check.

---

## 🛠️ Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment template
cp .env.example .env

# 3. Start development server
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```
