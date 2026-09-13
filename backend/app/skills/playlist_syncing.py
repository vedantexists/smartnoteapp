import logging
import spotipy
from typing import List
from app.config import settings
from app.models.schemas import EntertainmentRec
from app.services.token_manager import token_manager

logger = logging.getLogger(__name__)

def sync_spotify_tracks(user_id: str, recs: List[EntertainmentRec]) -> List[str]:
    """
    Finds songs on Spotify and appends them to user's playlist using OAuth access token.
    """
    songs = [item for item in recs if item.type == "Song"]
    added = []
    if not songs:
        return added

    token = token_manager.get_valid_token(user_id, "spotify")
    playlist_id = settings.spotify_playlist_id

    if not token:
        logger.info(f"No active Spotify OAuth token for user {user_id}. Simulating track additions.")
        for s in songs:
            added.append(f"{s.title} by {s.creator}")
        return added

    try:
        sp = spotipy.Spotify(auth=token)
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
                display_name = f"{track['name']} - {track['artists'][0]['name']}"
                added.append(display_name)
                logger.info(f"Identified Spotify track: {display_name}")

        if track_uris and playlist_id:
            sp.playlist_add_items(playlist_id, track_uris)
            logger.info(f"Appended {len(track_uris)} tracks to Spotify playlist {playlist_id} for user {user_id}")

    except Exception as e:
        logger.error(f"Error syncing tracks to Spotify for user {user_id}: {e}")

    return added
