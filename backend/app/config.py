from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os
import sys

class Settings(BaseSettings):
    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Persistent & Temp Directories
    data_dir: str = "/data"
    temp_dir: str = "/tmp/smartnote_media"

    # External Integrations
    github_pat: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:7860/callback"
    spotify_playlist_id: str = ""
    spotify_refresh_token: str = ""
    tmdb_api_key: str = ""
    tmdb_account_id: str = ""
    tmdb_session_id: str = ""
    notion_api_key: str = ""
    notion_database_id: str = ""

    # Optional yt-dlp cookies
    ytdlp_cookies_path: str = ""

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 7860
    environment: str = "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_resolved_data_dir(self) -> Path:
        """
        Returns a validated writable Path for SQLite & ChromaDB.
        Falls back to local ./data if /data is not writable (e.g., local Windows/macOS dev).
        """
        target = Path(self.data_dir)
        try:
            target.mkdir(parents=True, exist_ok=True)
            # Test write
            test_file = target / ".write_test"
            test_file.touch()
            test_file.unlink()
            return target
        except Exception:
            fallback = Path.cwd() / "data"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def get_resolved_temp_dir(self) -> Path:
        """
        Returns a validated writable Path for temporary video downloads.
        Falls back to local ./temp_media if /tmp is not writable.
        """
        target = Path(self.temp_dir)
        try:
            target.mkdir(parents=True, exist_ok=True)
            test_file = target / ".write_test"
            test_file.touch()
            test_file.unlink()
            return target
        except Exception:
            fallback = Path.cwd() / "temp_media"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

settings = Settings()
