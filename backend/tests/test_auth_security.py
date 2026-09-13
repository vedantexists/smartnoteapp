import pytest
import os
import uuid
import time
from pathlib import Path

import tempfile
import shutil

# Configure isolated test environment
test_tmp_dir = tempfile.mkdtemp(prefix="smartnote_sec_test_")
os.environ["DATA_DIR"] = str(Path(test_tmp_dir) / "data")
os.environ["TEMP_DIR"] = str(Path(test_tmp_dir) / "temp")

from app.services.crypto import crypto_service
from app.auth.pkce import pkce_manager
from app.auth.jwt import create_session_token, verify_session_token
from app.services.database import (
    init_db, save_note, get_note_by_id, list_notes,
    save_user_token, get_user_token, delete_user_token, get_connected_providers
)
from app.services.downloader import downloader
from app.models.schemas import DomainCategory, Flashcard

@pytest.fixture(autouse=True, scope="session")
def global_cleanup():
    yield
    try:
        shutil.rmtree(test_tmp_dir, ignore_errors=True)
    except Exception:
        pass

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_aes256_token_encryption_and_decryption():
    """Validates AES-256 Fernet token encryption at rest."""
    secret_token = "gho_16C7e42F292c6912E7710c838347Ae178B4a"
    encrypted = crypto_service.encrypt(secret_token)

    # Must be encrypted and never equal plaintext
    assert encrypted is not None
    assert encrypted != secret_token
    assert "gho_" not in encrypted

    # Decryption must recover original token
    decrypted = crypto_service.decrypt(encrypted)
    assert decrypted == secret_token

    # Tampered ciphertext must fail gracefully and return None
    corrupted = encrypted[:-4] + "AAAA"
    assert crypto_service.decrypt(corrupted) is None
    assert crypto_service.decrypt(None) is None

def test_pkce_generation_and_challenge_verification():
    """Validates RFC 7636 PKCE S256 challenge generation and math verification."""
    pkce = pkce_manager.generate_pkce_pair()
    assert len(pkce.code_verifier) >= 43
    assert pkce.code_challenge_method == "S256"
    assert len(pkce.code_challenge) > 20

    # Verification of challenge with verifier
    assert pkce_manager.verify_code_challenge(pkce.code_verifier, pkce.code_challenge) is True
    assert pkce_manager.verify_code_challenge("wrong_verifier", pkce.code_challenge) is False

def test_csrf_state_token_ttl_and_single_use():
    """Validates CSRF state token caching, single-use consumption, and provider binding."""
    user_id = "user_test_123"
    code_verifier = "dummy_verifier_string_1234567890"
    state = pkce_manager.create_state(user_id, "github", code_verifier)

    assert len(state) >= 32

    # Provider mismatch rejection
    wrong_provider = pkce_manager.consume_state(state, "spotify")
    assert wrong_provider is None

    # Valid consumption
    consumed = pkce_manager.consume_state(state, "github")
    assert consumed is not None
    assert consumed.user_id == user_id
    assert consumed.code_verifier == code_verifier

    # Single-use enforcement (replaying must fail)
    replay = pkce_manager.consume_state(state, "github")
    assert replay is None

def test_jwt_session_issuance_and_verification():
    """Validates mobile session JWT creation and verification."""
    uid = "android_device_client_999"
    token = create_session_token(uid, expiration_days=7)
    assert token is not None

    verified_uid = verify_session_token(token)
    assert verified_uid == uid

    # Tampered token rejection
    tampered = token[:-5] + "XXXXX"
    assert verify_session_token(tampered) is None

def test_multi_tenant_isolation_and_idor_prevention():
    """Verifies strict tenant data isolation (User A cannot view User B's data)."""
    user_a = f"user_a_{uuid.uuid4().hex[:6]}"
    user_b = f"user_b_{uuid.uuid4().hex[:6]}"
    note_id = str(uuid.uuid4())

    save_note(
        note_id=note_id,
        source_url="https://instagram.com/reel/12345",
        domain=DomainCategory.TECH_EDUCATION.value,
        title="User A Secret Blueprint",
        summary="Confidential architectural spec.",
        detailed_notes="Proprietary code.",
        flashcards=[],
        github_repos=[],
        web_resources=[],
        entertainment_recs=[],
        user_id=user_a
    )

    # User A can retrieve note
    note_a = get_note_by_id(note_id, user_id=user_a)
    assert note_a is not None
    assert note_a.title == "User A Secret Blueprint"

    # User B attempting IDOR on note_id must be denied (returns None)
    note_b = get_note_by_id(note_id, user_id=user_b)
    assert note_b is None

    # User B note listing must not contain User A's note
    user_b_notes = list_notes(user_id=user_b)
    assert all(n.id != note_id for n in user_b_notes)

def test_ssrf_url_validation_and_rejection():
    """Validates SSRF prevention against private networks, loopbacks, and unauthorized domains."""
    # Valid social media URLs
    assert downloader.validate_and_sanitize_url("https://www.instagram.com/reel/C12345/")
    assert downloader.validate_and_sanitize_url("https://youtu.be/dQw4w9WgXcQ")
    assert downloader.validate_and_sanitize_url("https://youtube.com/shorts/xyz123")

    # Rejected schemes
    with pytest.raises(ValueError, match="scheme"):
        downloader.validate_and_sanitize_url("file:///etc/passwd")

    # Rejected private IP / Localhost (SSRF vectors)
    with pytest.raises(ValueError):
        downloader.validate_and_sanitize_url("http://127.0.0.1:8000/internal")
    with pytest.raises(ValueError):
        downloader.validate_and_sanitize_url("http://localhost:8080")
    with pytest.raises(ValueError):
        downloader.validate_and_sanitize_url("http://169.254.169.254/latest/meta-data/")

    # Rejected unauthorized domain
    with pytest.raises(ValueError, match="Unsupported or unauthorized domain"):
        downloader.validate_and_sanitize_url("https://malicious-site.com/exploit.mp4")

def test_encrypted_user_token_persistence():
    """Validates encrypted token storage in SQLite user_tokens table."""
    test_user = "oauth_test_user_777"
    enc_access = crypto_service.encrypt("gho_oauth_access_sample")
    enc_refresh = crypto_service.encrypt("ghr_oauth_refresh_sample")

    save_user_token(
        user_id=test_user,
        provider="github",
        encrypted_access_token=enc_access,
        encrypted_refresh_token=enc_refresh,
        token_type="Bearer",
        scope="public_repo",
        expires_at=time.time() + 3600
    )

    token_rec = get_user_token(test_user, "github")
    assert token_rec is not None
    assert crypto_service.decrypt(token_rec["encrypted_access_token"]) == "gho_oauth_access_sample"
    assert crypto_service.decrypt(token_rec["encrypted_refresh_token"]) == "ghr_oauth_refresh_sample"

    providers = get_connected_providers(test_user)
    assert "github" in providers

    delete_user_token(test_user, "github")
    assert get_user_token(test_user, "github") is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
