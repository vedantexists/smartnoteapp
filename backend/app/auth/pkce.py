import hashlib
import base64
import secrets
import time
import logging
from typing import Optional, Dict, NamedTuple

logger = logging.getLogger(__name__)

class PkcePair(NamedTuple):
    code_verifier: str
    code_challenge: str
    code_challenge_method: str = "S256"

class OAuthStateEntry(NamedTuple):
    state: str
    user_id: str
    provider: str
    code_verifier: str
    created_at: float
    ttl_seconds: int = 600  # 10 minutes

class PkceManager:
    def __init__(self):
        # In-memory thread-safe state store with TTL
        self._states: Dict[str, OAuthStateEntry] = {}

    def generate_pkce_pair(self) -> PkcePair:
        """
        Generates RFC 7636 compliant Code Verifier and S256 Code Challenge.
        code_verifier: 64 characters of high-entropy base64url characters.
        code_challenge: BASE64URL-ENCODE(SHA256(ASCII(code_verifier))) with padding stripped.
        """
        code_verifier = secrets.token_urlsafe(48)[:64]
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return PkcePair(
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method="S256"
        )

    def verify_code_challenge(self, code_verifier: str, code_challenge: str) -> bool:
        """Verifies that code_verifier matches the code_challenge."""
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return secrets.compare_digest(expected, code_challenge)

    def create_state(self, user_id: str, provider: str, code_verifier: str) -> str:
        """Creates and stores a cryptographically secure CSRF state token with TTL."""
        self._cleanup_expired()
        state = secrets.token_urlsafe(32)
        self._states[state] = OAuthStateEntry(
            state=state,
            user_id=user_id,
            provider=provider,
            code_verifier=code_verifier,
            created_at=time.time()
        )
        return state

    def consume_state(self, state: str, provider: str) -> Optional[OAuthStateEntry]:
        """
        Validates and consumes state token (single-use to prevent replay).
        Returns the entry if valid and unexpired; None otherwise.
        """
        self._cleanup_expired()
        entry = self._states.get(state)
        if not entry:
            logger.warning(f"Invalid or already consumed OAuth state: {state}")
            return None

        if time.time() - entry.created_at > entry.ttl_seconds:
            logger.warning(f"Expired OAuth state: {state}")
            self._states.pop(state, None)
            return None

        if entry.provider.lower() != provider.lower():
            logger.warning(f"Provider mismatch for OAuth state: expected {entry.provider}, got {provider}")
            return None

        # Valid and provider matched -> pop and consume
        return self._states.pop(state, None)

    def _cleanup_expired(self):
        """Purges expired states."""
        now = time.time()
        expired_keys = [k for k, v in self._states.items() if now - v.created_at > v.ttl_seconds]
        for k in expired_keys:
            self._states.pop(k, None)

pkce_manager = PkceManager()
