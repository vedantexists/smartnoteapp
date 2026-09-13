import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings

logger = logging.getLogger(__name__)

class TokenEncryptionService:
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._init_cipher()

    def _init_cipher(self):
        key = settings.encryption_key.strip()
        if key:
            try:
                # Validate key length/format
                self._fernet = Fernet(key.encode("utf-8"))
                logger.info("Token encryption service initialized with configured ENCRYPTION_KEY.")
                return
            except Exception as e:
                logger.error(f"Invalid ENCRYPTION_KEY provided: {e}. Falling back to dynamic key.")

        # Fallback dynamic key for local dev / tests
        fallback_key = Fernet.generate_key()
        self._fernet = Fernet(fallback_key)
        logger.warning(
            "Running with dynamic in-memory ENCRYPTION_KEY. "
            "Set ENCRYPTION_KEY in .env for persistent encrypted storage across restarts."
        )

    def encrypt(self, plain_text: Optional[str]) -> Optional[str]:
        """Encrypts token string using AES-256 Fernet."""
        if not plain_text:
            return None
        if not self._fernet:
            self._init_cipher()
        encrypted_bytes = self._fernet.encrypt(plain_text.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt(self, cipher_text: Optional[str]) -> Optional[str]:
        """Decrypts token string back to plaintext."""
        if not cipher_text:
            return None
        if not self._fernet:
            self._init_cipher()
        try:
            decrypted_bytes = self._fernet.decrypt(cipher_text.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            logger.error("Failed to decrypt token: InvalidToken or mismatched encryption key.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error decrypting token: {e}")
            return None

crypto_service = TokenEncryptionService()
