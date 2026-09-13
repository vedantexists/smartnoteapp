"""
Modular Extraction and Integration Skills
"""
from .fact_checking import check_clickbait_and_scam
from .repo_starring import star_github_repositories
from .playlist_syncing import sync_spotify_tracks
from .deduplication import deduplicate_and_merge

__all__ = [
    "check_clickbait_and_scam",
    "star_github_repositories",
    "sync_spotify_tracks",
    "deduplicate_and_merge"
]
