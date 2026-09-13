---
title: Reel Notes (SmartNote)
emoji: ⚡
colorFrom: indigo
colorTo: purple
sdk: static
short_description: Multi-tenant social video intelligence with OAuth2 PKCE
---

# SmartNote: Autonomous Social Video Knowledge Pipeline & Android Client

[![Build Android APK](https://github.com/vedantexists/smartnoteapp/actions/workflows/build-apk.yml/badge.svg)](https://github.com/vedantexists/smartnoteapp/actions/workflows/build-apk.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Multimodal%20Video-4285F4.svg?logo=google)](https://ai.google.dev)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Deduplication-orange.svg)](https://www.trychroma.com)
[![Android Compose](https://img.shields.io/badge/Android-Jetpack%20Compose-3DDC84.svg?logo=android)](https://developer.android.com/jetpack/compose)

An end-to-end, 100% free-tier optimized pipeline consisting of a **Jetpack Compose Android client** (compatible with all modern Android devices, Android 7.0+ / API 24+) and a **Python FastAPI backend** containerized for Hugging Face Spaces. It ingests social video URLs (Instagram Reels, YouTube Shorts), extracts structured knowledge via the **Google Gemini Multimodal File API**, semantically deduplicates notes with **local ChromaDB**, and automates multi-service actions across **GitHub, Spotify, TMDB, and Notion**.

---

## 🏛️ System Architecture

```mermaid
graph TD
    A[Instagram Reel / YouTube Short] -->|Android Share Sheet| B[SmartNote Android Client]
    B -->|WorkManager CoroutineWorker| C[FastAPI Backend /process-reel]
    C -->|yt-dlp| D[Low-Res MP4 Download]
    D -->|Gemini File API| E[Multimodal Audio + Visual OCR]
    E --> F{Clickbait / Scam Gate}
    F -->|Flagged| G[Status: rejected_clickbait]
    F -->|Substantive| H[Extract Summary, Notes, Repos, Flashcards, ICS]
    H -->|Gemini Embeddings| I[Local ChromaDB Cosine Search]
    I -->|Similarity > 0.85| J[Gemini Intelligent Auto-Merge]
    I -->|Novel Topic| K[Index as New Note]
    J --> L[External Automations]
    K --> L
    L --> M[⭐ GitHub Star (OAuth2 PKCE)]
    L --> N[🎵 Spotify Playlist Add (OAuth2 PKCE)]
    L --> O[🎬 TMDB Watchlist Add]
    L --> P[📝 Notion Page Sync]
    L --> Q[Update Local Room DB]
    Q --> R[Jetpack Compose Feed + 3D Flip Flashcards]
```

---

## 📱 1. Android Client (`app/`)
- **Universal Android Compatibility & Battery Resilience:** Supports Android 7.0+ (API 24 to 34+), covering over 97% of all active Android devices (Samsung, Google Pixel, Xiaomi, OnePlus, Motorola, Nothing, etc.). SmartNote utilizes **AndroidX WorkManager** with `NetworkType.CONNECTED` and exponential backoff, ensuring deferred background sync survives aggressive OEM battery management and process suspension.
- **System Share Receiver:** Configured with `ACTION_SEND` intent filter for `text/plain` to seamlessly intercept links shared directly from Instagram or YouTube.
- **Encrypted Session Management:** Android Jetpack `EncryptedSharedPreferences` with `MasterKey` AES256-GCM.
- **Deep Link Callback Receiver:** Intercepts `reelnotes://auth/callback` to handle 1-tap OAuth2 authorization code flows via Chrome Custom Tabs.
- **Local Persistence (Room DB):** `NoteEntity`, `LinkItemEntity`, `MediaRecEntity`, and `FlashcardEntity` with transactional updates.
- **Interactive Jetpack Compose UI:**
  - **Notes Feed:** Rich card view with integration badges (⭐ GitHub Starred, 🎵 Spotify Added, 🎬 TMDB Added, 📝 Notion Synced).
  - **Semantic Search:** Conceptual querying against the backend vector space.
  - **Active Recall Flashcards:** Interactive 3D flip card with rotation animation (`rotationY`) for spaced repetition review.
  - **Native Calendar Sync:** One-tap calendar event importing (`.ics` via `ACTION_VIEW` and `FileProvider`).
  - **Sunday Digest:** Automated weekly knowledge synthesis overview.

---

## 🐍 2. Backend (`backend/`)
- **Modular Multi-Tenant Architecture:**
  - `auth/`: RFC 7636 PKCE S256 verifier/challenge generation, single-use CSRF tokens with TTL, session JWTs, and deep link redirection (`reelnotes://auth/callback`).
  - `services/`: AES-256 Fernet cryptographic service (`ENCRYPTION_KEY`), automated token refresh, and tenant-isolated ChromaDB client.
  - `skills/`: Modular pipelines for fact checking, deduplication, repo starring, and playlist syncing.
- **Token Encryption at Rest:** User OAuth access and refresh tokens are encrypted using AES-256-GCM (Fernet) in SQLite.
- **Cross-Tenant IDOR Protection:** All database rows and ChromaDB vector queries enforce strict `user_id` matching (`where={"user_id": current_user}`).
- **Multimodal Video Processing:** Downloads lightweight `.mp4` using `yt-dlp` (with SSRF defense blocking private subnets), processes via Gemini 2.5 Flash, and cleans up local media.
- **Clickbait & Fact-Check Gate:** Halts and rejects scams or deceptive promotions (`status: rejected_clickbait`).
- **Semantic Deduplication:** ChromaDB cosine distance evaluation (> 0.85 threshold) with Gemini auto-merging.
- **Automations:**
  - GitHub: Automated repository starring via OAuth2 token exchange.
  - Spotify: Automated playlist appending via OAuth2 PKCE.
  - TMDB & Notion: Movie watchlist and structured notes sync.
- **Scheduled Weekly Digests:** `APScheduler` cron job running every Sunday at 00:00 UTC.

---

## ⚙️ 3. CI/CD Pipeline (`.github/workflows/build-apk.yml`)
- Triggers on `push` to `main` and `workflow_dispatch`.
- Sets up JDK 17 (Temurin) and Android SDK.
- Runs `./gradlew assembleDebug --stacktrace`.
- Publishes the compiled APK as a downloadable workflow artifact (`app-debug`).

---

## 🚀 Quick Start

### Backend Deployment (Hugging Face Spaces)
1. Create a new Docker Space on Hugging Face Spaces.
2. Push the contents of `backend/` or connect this repository.
3. Configure repository secrets from `backend/.env.example` (`GEMINI_API_KEY`, `GITHUB_PAT`, `NOTION_API_KEY`, etc.).

### Local Backend Run
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```

### Android Build
```bash
./gradlew assembleDebug
```
The resulting APK will be generated at `app/build/outputs/apk/debug/app-debug.apk`.
