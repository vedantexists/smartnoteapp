import time
import logging
import requests
from typing import Optional, Dict, Any
from app.config import settings
from app.services.crypto import crypto_service
from app.services.database import get_user_token, save_user_token

logger = logging.getLogger(__name__)

class TokenManager:

    def get_valid_token(self, user_id: str, provider: str) -> Optional[str]:
        """
        Retrieves, decrypts, and automatically refreshes user's OAuth access token if expired.
        """
        record = get_user_token(user_id, provider)
        if not record:
            return None

        encrypted_access = record.get("encrypted_access_token")
        encrypted_refresh = record.get("encrypted_refresh_token")
        expires_at = record.get("expires_at")

        access_token = crypto_service.decrypt(encrypted_access)
        if not access_token:
            logger.warning(f"Could not decrypt access token for user {user_id} and provider {provider}")
            return None

        # If token has an expiry and is expiring within 60s
        now = time.time()
        if expires_at and (expires_at - now < 60):
            logger.info(f"Access token for {user_id} ({provider}) is expiring or expired. Attempting refresh...")
            refresh_token = crypto_service.decrypt(encrypted_refresh)
            if refresh_token:
                refreshed_access = self._refresh_token(user_id, provider, refresh_token)
                if refreshed_access:
                    return refreshed_access

        return access_token

    def _refresh_token(self, user_id: str, provider: str, refresh_token: str) -> Optional[str]:
        """Executes provider-specific token refresh."""
        if provider.lower() == "spotify":
            return self._refresh_spotify(user_id, refresh_token)
        elif provider.lower() == "github":
            return self._refresh_github(user_id, refresh_token)
        return None

    def _refresh_spotify(self, user_id: str, refresh_token: str) -> Optional[str]:
        client_id = settings.spotify_client_id
        client_secret = settings.spotify_client_secret
        if not (client_id and client_secret):
            logger.warning("Spotify client credentials missing for token refresh.")
            return None

        url = "https://accounts.spotify.com/api/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }
        try:
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                new_access = payload.get("access_token")
                new_refresh = payload.get("refresh_token") or refresh_token
                expires_in = payload.get("expires_in", 3600)
                expires_at = time.time() + expires_in

                save_user_token(
                    user_id=user_id,
                    provider="spotify",
                    encrypted_access_token=crypto_service.encrypt(new_access),
                    encrypted_refresh_token=crypto_service.encrypt(new_refresh),
                    token_type=payload.get("token_type", "Bearer"),
                    scope=payload.get("scope"),
                    expires_at=expires_at
                )
                logger.info(f"Successfully refreshed Spotify token for user {user_id}")
                return new_access
            else:
                logger.error(f"Failed to refresh Spotify token: HTTP {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Exception during Spotify token refresh: {e}")
        return None

    def _refresh_github(self, user_id: str, refresh_token: str) -> Optional[str]:
        client_id = settings.github_client_id
        client_secret = settings.github_client_secret
        if not (client_id and client_secret):
            return None

        url = "https://github.com/login/oauth/access_token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        headers = {"Accept": "application/json"}
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                new_access = payload.get("access_token")
                new_refresh = payload.get("refresh_token") or refresh_token
                expires_in = payload.get("expires_in")
                expires_at = (time.time() + expires_in) if expires_in else None

                save_user_token(
                    user_id=user_id,
                    provider="github",
                    encrypted_access_token=crypto_service.encrypt(new_access),
                    encrypted_refresh_token=crypto_service.encrypt(new_refresh),
                    token_type=payload.get("token_type", "Bearer"),
                    scope=payload.get("scope"),
                    expires_at=expires_at
                )
                return new_access
        except Exception as e:
            logger.error(f"Exception during GitHub token refresh: {e}")
        return None

token_manager = TokenManager()
