import re
import logging
import requests
from typing import List, Optional
from app.config import settings
from app.services.token_manager import token_manager

logger = logging.getLogger(__name__)

REPO_REGEX = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")

def clean_repo_name(repo: str) -> Optional[str]:
    """Strictly validates and formats repo to owner/repo."""
    repo = repo.strip()
    repo = re.sub(r"^https?://github\.com/", "", repo)
    repo = re.sub(r"\.git$", "", repo)
    repo = repo.strip("/")
    if REPO_REGEX.match(repo):
        return repo
    return None

def star_github_repositories(user_id: str, repos: List[str]) -> List[str]:
    """
    Stars GitHub repositories using user's encrypted OAuth2 token (or fallback PAT).
    """
    starred = []
    if not repos:
        return starred

    # Fetch user's decrypted OAuth token or fallback PAT
    token = token_manager.get_valid_token(user_id, "github") or settings.github_pat

    if not token:
        logger.info(f"No GitHub token found for user {user_id}. Simulating starring.")
        for r in repos:
            clean = clean_repo_name(r)
            if clean:
                starred.append(clean)
        return starred

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    for repo in repos:
        clean = clean_repo_name(repo)
        if not clean:
            logger.warning(f"Invalid GitHub repo identifier rejected: '{repo}'")
            continue

        url = f"https://api.github.com/user/starred/{clean}"
        try:
            resp = requests.put(url, headers=headers, timeout=10)
            if resp.status_code in (204, 200):
                logger.info(f"Starred {clean} on GitHub for user {user_id}")
                starred.append(clean)
            else:
                logger.warning(f"Failed to star {clean}: HTTP {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error executing GitHub star on {clean}: {e}")

    return starred
