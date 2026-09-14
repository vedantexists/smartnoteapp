import urllib.parse
import logging
import requests
import time
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel

from app.config import settings
from app.auth.pkce import pkce_manager
from app.auth.jwt import create_session_token, get_current_user
from app.services.crypto import crypto_service
from app.services.database import (
    save_user_token, get_user_token, delete_user_token,
    get_connected_providers, ensure_user_exists
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & OAuth2"])

class SessionResponse(BaseModel):
    user_id: str
    access_token: str
    token_type: str = "Bearer"
    expires_in_days: int

class AuthStatusResponse(BaseModel):
    user_id: str
    connected_providers: List[str]

@router.post("/session", response_model=SessionResponse)
def create_or_renew_session(user_id: Optional[str] = Query(None, description="Client device UUID")):
    """Issues a session JWT for the mobile client. Creates a new user_id if none provided."""
    import uuid
    uid = user_id.strip() if user_id and user_id.strip() else str(uuid.uuid4())
    ensure_user_exists(uid)
    token = create_session_token(uid)
    return SessionResponse(
        user_id=uid,
        access_token=token,
        token_type="Bearer",
        expires_in_days=settings.jwt_expiration_days
    )

@router.get("/status", response_model=AuthStatusResponse)
def get_auth_status(current_user: str = Depends(get_current_user)):
    """Returns connected OAuth providers for the authenticated user."""
    connected = get_connected_providers(current_user)
    return AuthStatusResponse(user_id=current_user, connected_providers=connected)

def _get_normalized_redirect_uri(provider: str) -> str:
    base = settings.oauth_redirect_base.strip()
    if not base.startswith("http://") and not base.startswith("https://"):
        if "onrender.com" not in base and not base.startswith("localhost"):
            base = f"https://{base}.onrender.com"
        else:
            base = f"https://{base}"
    base = base.rstrip("/")
    return f"{base}/auth/{provider.lower()}/callback"

@router.get("/{provider}/login")
def oauth_login(
    provider: str,
    user_id: Optional[str] = Query("default_user", description="Tenant User ID"),
    redirect_mode: bool = Query(True, description="Redirect directly vs return JSON")
):
    """
    Initiates standard Authorization Code Flow with PKCE and CSRF state defense.
    """
    prov = provider.lower()
    if prov not in ("github", "spotify"):
        raise HTTPException(status_code=400, detail="Supported providers: github, spotify")

    uid = user_id.strip() if user_id else "default_user"
    pkce = pkce_manager.generate_pkce_pair()
    state = pkce_manager.create_state(user_id=uid, provider=prov, code_verifier=pkce.code_verifier)

    redirect_uri = _get_normalized_redirect_uri(prov)

    if prov == "github":
        client_id = settings.github_client_id.strip()
        if not client_id:
            raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "public_repo,user:email",
            "state": state
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

    else: # spotify
        client_id = settings.spotify_client_id.strip()
        if not client_id:
            raise HTTPException(status_code=500, detail="SPOTIFY_CLIENT_ID not configured")
        
        params = {
            "response_type": "code",
            "client_id": client_id,
            "scope": "playlist-modify-public playlist-modify-private user-read-email",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": pkce.code_challenge,
            "code_challenge_method": pkce.code_challenge_method
        }
        auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"

    if redirect_mode:
        return RedirectResponse(auth_url)
    return {"auth_url": auth_url, "state": state, "provider": prov}

@router.get("/{provider}/callback")
def oauth_callback(
    provider: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Exchanges code for access & refresh tokens, validates CSRF state + PKCE,
    encrypts tokens with AES-256 Fernet, and redirects to Android app deep link.
    """
    prov = provider.lower()
    if error:
        logger.warning(f"OAuth callback returned error for {prov}: {error}")
        return _render_deep_link_redirect(status="error", provider=prov, message=error)

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing authorization code or state token")

    # Validate & consume single-use state token
    state_entry = pkce_manager.consume_state(state, provider=prov)
    if not state_entry:
        raise HTTPException(status_code=403, detail="Invalid, expired, or already consumed OAuth state")

    user_id = state_entry.user_id
    code_verifier = state_entry.code_verifier
    redirect_uri = _get_normalized_redirect_uri(prov)

    try:
        if prov == "github":
            token_url = "https://github.com/login/oauth/access_token"
            data = {
                "client_id": settings.github_client_id.strip(),
                "client_secret": settings.github_client_secret.strip(),
                "code": code,
                "redirect_uri": redirect_uri
            }
            headers = {"Accept": "application/json"}
            resp = requests.post(token_url, data=data, headers=headers, timeout=15)

            if resp.status_code != 200:
                logger.error(f"GitHub token exchange failed: {resp.text}")
                return _render_deep_link_redirect(status="failed", provider=prov, message="GitHub token exchange error")

            payload = resp.json()
            access_token = payload.get("access_token")
            refresh_token = payload.get("refresh_token")
            token_type = payload.get("token_type", "Bearer")
            scope = payload.get("scope")
            expires_in = payload.get("expires_in")
            expires_at = (time.time() + expires_in) if expires_in else None

        else: # spotify
            token_url = "https://accounts.spotify.com/api/token"
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.spotify_client_id,
                "client_secret": settings.spotify_client_secret,
                "code_verifier": code_verifier # PKCE verification
            }
            resp = requests.post(token_url, data=data, timeout=15)

            if resp.status_code != 200:
                logger.error(f"Spotify token exchange failed: {resp.text}")
                return _render_deep_link_redirect(status="failed", provider=prov, message="Spotify token exchange error")

            payload = resp.json()
            access_token = payload.get("access_token")
            refresh_token = payload.get("refresh_token")
            token_type = payload.get("token_type", "Bearer")
            scope = payload.get("scope")
            expires_in = payload.get("expires_in", 3600)
            expires_at = time.time() + expires_in

        if not access_token:
            return _render_deep_link_redirect(status="failed", provider=prov, message="No access token returned")

        # Encrypt tokens before saving
        encrypted_access = crypto_service.encrypt(access_token)
        encrypted_refresh = crypto_service.encrypt(refresh_token) if refresh_token else None

        save_user_token(
            user_id=user_id,
            provider=prov,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_type=token_type,
            scope=scope,
            expires_at=expires_at
        )

        logger.info(f"Successfully linked {prov} for user {user_id} with encrypted tokens.")
        return _render_deep_link_redirect(status="success", provider=prov, user_id=user_id)

    except Exception as e:
        logger.error(f"Error handling {prov} callback: {e}")
        return _render_deep_link_redirect(status="error", provider=prov, message=str(e))

@router.delete("/{provider}")
def disconnect_provider(provider: str, current_user: str = Depends(get_current_user)):
    """Disconnects and removes encrypted tokens for provider."""
    delete_user_token(current_user, provider.lower())
    return {"status": "disconnected", "provider": provider.lower()}

def _render_deep_link_redirect(status: str, provider: str, user_id: Optional[str] = None, message: Optional[str] = None):
    deep_link = f"{settings.app_deep_link}?status={status}&provider={provider}"
    if user_id:
        deep_link += f"&user_id={user_id}"
    if message:
        deep_link += f"&message={urllib.parse.quote(message)}"

    # HTML page that attempts deep link redirect to Android app with desktop instructions
    is_success = status.lower() == "success"
    heading_color = "#10B981" if is_success else "#EF4444"
    heading_text = f"Authentication {status.capitalize()}!"
    body_msg = f"Connected to <strong>{provider.capitalize()}</strong>." if is_success else f"Reason: {message or 'Authentication failed'}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>SmartNote Authentication</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, -apple-system, sans-serif; background: #0B0F19; color: #F8FAFC; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 1rem; box-sizing: border-box; text-align: center; }}
            .card {{ background: #151D2F; border: 1px solid rgba(255, 255, 255, 0.1); padding: 2.5rem 2rem; border-radius: 1.25rem; max-width: 440px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }}
            h2 {{ color: {heading_color}; margin-top: 0; font-size: 1.5rem; }}
            p {{ color: #94A3B8; font-size: 0.95rem; line-height: 1.5; }}
            .badge {{ display: inline-block; background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 0.35rem 0.85rem; border-radius: 999px; font-weight: 600; font-size: 0.85rem; margin-bottom: 1rem; }}
            a.btn {{ display: inline-block; margin-top: 1.25rem; padding: 0.85rem 1.75rem; background: #6366F1; color: white; text-decoration: none; border-radius: 0.75rem; font-weight: 600; font-size: 0.95rem; }}
            .note {{ margin-top: 1.5rem; font-size: 0.8rem; color: #64748B; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 1rem; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">{"✅ Successfully Authenticated" if is_success else "⚠️ Notice"}</div>
            <h2>{heading_text}</h2>
            <p>{body_msg}</p>
            <p>Your OAuth tokens have been encrypted with AES-256 and stored securely.</p>
            <a class="btn" href="{deep_link}">Return to SmartNote App</a>
            <div class="note">
                📱 <strong>On your phone:</strong> Tapping above opens SmartNote.<br>
                💻 <strong>On a computer:</strong> You can safely close this browser window.
            </div>
        </div>
        <script>
            // Attempt automatic deep link navigation on mobile
            if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {{
                setTimeout(function() {{
                    window.location.href = "{deep_link}";
                }}, 300);
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
