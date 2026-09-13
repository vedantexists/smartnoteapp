import re
import logging
import requests
from typing import List, Optional, Dict, Any, Tuple
from app.config import settings
from app.models.schemas import IntegrationStatus, WebResource, EntertainmentRec, Flashcard

logger = logging.getLogger(__name__)

class IntegrationService:
    def __init__(self):
        self.github_pat = settings.github_pat
        self.spotify_client_id = settings.spotify_client_id
        self.spotify_client_secret = settings.spotify_client_secret
        self.spotify_playlist_id = settings.spotify_playlist_id
        self.spotify_refresh_token = settings.spotify_refresh_token
        self.tmdb_api_key = settings.tmdb_api_key
        self.tmdb_account_id = settings.tmdb_account_id
        self.tmdb_session_id = settings.tmdb_session_id
        self.notion_api_key = settings.notion_api_key
        self.notion_database_id = settings.notion_database_id

    # --------------------------------------------------------------------------
    # 1. GitHub Integration (Strict owner/repo starring)
    # --------------------------------------------------------------------------
    def star_github_repos(self, repos: List[str]) -> List[str]:
        """
        Stars detected GitHub repositories strictly formatted as owner/repo.
        Issues PUT https://api.github.com/user/starred/{owner}/{repo} with configured PAT.
        """
        starred = []
        if not repos:
            return starred

        if not self.github_pat:
            logger.info("GITHUB_PAT not set. Simulating GitHub starring.")
            # For testing/demo without PAT, validate format and simulate success
            for r in repos:
                clean_repo = self._clean_repo_name(r)
                if clean_repo:
                    starred.append(clean_repo)
            return starred

        headers = {
            "Authorization": f"Bearer {self.github_pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        for repo in repos:
            clean_repo = self._clean_repo_name(repo)
            if not clean_repo:
                logger.warning(f"Skipping invalid GitHub repo format: {repo}")
                continue

            url = f"https://api.github.com/user/starred/{clean_repo}"
            try:
                # 204 No Content signifies successful star
                resp = requests.put(url, headers=headers, timeout=10)
                if resp.status_code in (204, 200):
                    logger.info(f"Successfully starred GitHub repo: {clean_repo}")
                    starred.append(clean_repo)
                else:
                    logger.warning(f"Failed to star {clean_repo}: HTTP {resp.status_code} - {resp.text}")
            except Exception as e:
                logger.error(f"Error starring GitHub repo {clean_repo}: {e}")

        return starred

    def _clean_repo_name(self, repo: str) -> Optional[str]:
        """Ensures strict owner/repo format and removes URLs or markdown."""
        repo = repo.strip()
        # Remove github.com prefixes if present
        repo = re.sub(r"^https?://github\.com/", "", repo)
        repo = re.sub(r"\.git$", "", repo)
        repo = repo.strip("/")

        # Must match owner/repo pattern
        if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", repo):
            return repo
        return None

    # --------------------------------------------------------------------------
    # 2. Spotify Integration (Search track -> Append to Playlist)
    # --------------------------------------------------------------------------
    def add_spotify_tracks(self, entertainment_recs: List[EntertainmentRec]) -> List[str]:
        """
        Searches Spotify for detected songs and appends them to user-configured playlist.
        """
        songs = [item for item in entertainment_recs if item.type == "Song"]
        added = []
        if not songs:
            return added

        if not (self.spotify_client_id and self.spotify_client_secret and self.spotify_playlist_id):
            logger.info("Spotify credentials or playlist ID not set. Simulating track addition.")
            for s in songs:
                added.append(f"{s.title} by {s.creator}")
            return added

        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

            # If refresh token available, use user auth; else client credentials
            if self.spotify_refresh_token:
                auth_manager = SpotifyOAuth(
                    client_id=self.spotify_client_id,
                    client_secret=self.spotify_client_secret,
                    redirect_uri=settings.spotify_redirect_uri,
                    scope="playlist-modify-public playlist-modify-private"
                )
                auth_manager.refresh_access_token(self.spotify_refresh_token)
                sp = spotipy.Spotify(auth_manager=auth_manager)
            else:
                sp = spotipy.Spotify(
                    client_credentials_manager=SpotifyClientCredentials(
                        client_id=self.spotify_client_id,
                        client_secret=self.spotify_client_secret
                    )
                )

            track_uris = []
            for song in songs:
                query = f"track:{song.title}"
                if song.creator:
                    query += f" artist:{song.creator}"
                results = sp.search(q=query, type="track", limit=1)
                tracks = results.get("tracks", {}).get("items", [])
                if tracks:
                    track = tracks[0]
                    track_uris.append(track["uri"])
                    added.append(f"{track['name']} - {track['artists'][0]['name']}")
                    logger.info(f"Discovered Spotify track: {track['name']} ({track['uri']})")

            if track_uris and self.spotify_refresh_token:
                sp.playlist_add_items(self.spotify_playlist_id, track_uris)
                logger.info(f"Appended {len(track_uris)} tracks to Spotify playlist {self.spotify_playlist_id}")

        except Exception as e:
            logger.error(f"Error in Spotify integration: {e}")

        return added

    # --------------------------------------------------------------------------
    # 3. TMDB Integration (Search Movie/Series -> Add to Watchlist)
    # --------------------------------------------------------------------------
    def add_tmdb_watchlist(self, entertainment_recs: List[EntertainmentRec]) -> List[str]:
        """
        Searches TMDB for movies/TV shows and adds them to the user's watchlist.
        """
        media_items = [item for item in entertainment_recs if item.type in ("Movie", "Series")]
        added = []
        if not media_items:
            return added

        if not self.tmdb_api_key:
            logger.info("TMDB_API_KEY not set. Simulating TMDB watchlist addition.")
            for m in media_items:
                added.append(f"{m.title} ({m.type})")
            return added

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.tmdb_api_key}" if len(self.tmdb_api_key) > 50 else None
        }

        for item in media_items:
            media_type = "movie" if item.type == "Movie" else "tv"
            search_url = f"https://api.themoviedb.org/3/search/{media_type}"
            params = {"query": item.title}
            if not headers.get("Authorization"):
                params["api_key"] = self.tmdb_api_key

            try:
                resp = requests.get(search_url, headers=headers, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if results:
                        first = results[0]
                        media_id = first["id"]
                        title = first.get("title") or first.get("name", item.title)
                        
                        # Add to watchlist if account_id or session_id configured
                        if self.tmdb_account_id:
                            watch_url = f"https://api.themoviedb.org/3/account/{self.tmdb_account_id}/watchlist"
                            watch_params = {}
                            if self.tmdb_session_id:
                                watch_params["session_id"] = self.tmdb_session_id
                            if not headers.get("Authorization"):
                                watch_params["api_key"] = self.tmdb_api_key

                            body = {
                                "media_type": media_type,
                                "media_id": media_id,
                                "watchlist": True
                            }
                            w_resp = requests.post(watch_url, headers=headers, params=watch_params, json=body, timeout=10)
                            if w_resp.status_code in (200, 201):
                                logger.info(f"Added '{title}' (ID {media_id}) to TMDB watchlist.")
                        
                        added.append(f"{title} ({item.type})")
                else:
                    logger.warning(f"TMDB search failed for {item.title}: HTTP {resp.status_code}")
            except Exception as e:
                logger.error(f"Error in TMDB integration for {item.title}: {e}")

        return added

    # --------------------------------------------------------------------------
    # 4. Notion Integration (Create Page with Structured Blocks)
    # --------------------------------------------------------------------------
    def sync_to_notion(
        self,
        title: str,
        domain: str,
        summary: str,
        detailed_notes: str,
        source_url: str,
        web_resources: List[WebResource],
        flashcards: List[Flashcard]
    ) -> Tuple[bool, Optional[str]]:
        """
        Creates or appends a structured page in Notion with title, properties,
        detailed notes breakdown, flashcard callouts, and web tool links.
        """
        if not (self.notion_api_key and self.notion_database_id):
            logger.info("Notion credentials not set. Simulating Notion sync.")
            return True, "https://notion.so/simulated-note"

        try:
            from notion_client import Client
            notion = Client(auth=self.notion_api_key)

            # Build children blocks
            children = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Summary & Core Insights"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": summary[:2000]}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Detailed Notes"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": detailed_notes[:2000]}}]
                    }
                }
            ]

            # Flashcards callout blocks
            if flashcards:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Active Recall Flashcards"}}]
                    }
                })
                for fc in flashcards[:5]:
                    callout_text = f"Q: {fc.question}\nA: {fc.answer}"
                    if fc.key_takeaway:
                        callout_text += f"\nKey: {fc.key_takeaway}"
                    children.append({
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{"type": "text", "text": {"content": callout_text[:2000]}}],
                            "icon": {"emoji": "💡"}
                        }
                    })

            # Web tools bookmark blocks
            if web_resources:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Recommended Tools & Resources"}}]
                    }
                })
                for res in web_resources[:5]:
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {"type": "text", "text": {"content": f"{res.name}: {res.purpose} - "}},
                                {"type": "text", "text": {"content": res.url, "link": {"url": res.url}}}
                            ]
                        }
                    })

            # Create page in database
            new_page = notion.pages.create(
                parent={"database_id": self.notion_database_id},
                properties={
                    "Name": {
                        "title": [{"type": "text", "text": {"content": title[:100]}}]
                    }
                },
                children=children
            )

            page_url = new_page.get("url", f"https://notion.so/{new_page.get('id', '').replace('-', '')}")
            logger.info(f"Successfully synced note to Notion: {page_url}")
            return True, page_url

        except Exception as e:
            logger.error(f"Error syncing to Notion: {e}")
            return False, None

    def execute_all_integrations(
        self,
        github_repos: List[str],
        entertainment_recs: List[EntertainmentRec],
        title: str,
        domain: str,
        summary: str,
        detailed_notes: str,
        source_url: str,
        web_resources: List[WebResource],
        flashcards: List[Flashcard]
    ) -> IntegrationStatus:
        """Executes all free-tier API automations in parallel or sequence."""
        starred_repos = self.star_github_repos(github_repos)
        spotify_added = self.add_spotify_tracks(entertainment_recs)
        tmdb_added = self.add_tmdb_watchlist(entertainment_recs)
        notion_synced, notion_url = self.sync_to_notion(
            title=title,
            domain=domain,
            summary=summary,
            detailed_notes=detailed_notes,
            source_url=source_url,
            web_resources=web_resources,
            flashcards=flashcards
        )

        return IntegrationStatus(
            github_starred=starred_repos,
            spotify_added=spotify_added,
            tmdb_added=tmdb_added,
            notion_synced=notion_synced,
            notion_url=notion_url
        )

integrations_service = IntegrationService()
