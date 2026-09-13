import os
import uuid
import logging
import urllib.parse
import ipaddress
import socket
from pathlib import Path
from typing import Optional
from app.config import settings
import yt_dlp

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = {
    "instagram.com", "www.instagram.com", "instagr.am",
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com"
}

class MediaDownloader:
    def __init__(self):
        self.temp_dir = settings.get_resolved_temp_dir()

    def validate_and_sanitize_url(self, raw_url: str) -> str:
        """
        SSRF & Injection Defense:
        Ensures URL has safe HTTP/HTTPS scheme and matches allowed social platforms.
        Rejects internal addresses, loopbacks, and cloud metadata IPs.
        """
        raw_url = raw_url.strip()
        parsed = urllib.parse.urlparse(raw_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Invalid URL scheme: Only http and https are allowed")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: Missing hostname")

        # SSRF Defense: Check if hostname resolves to private/loopback IP
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("Access to private/internal network addresses is prohibited")
        except ValueError:
            # It's a domain name, verify against allowed social media domains
            domain_matched = False
            for allowed in ALLOWED_DOMAINS:
                if hostname == allowed or hostname.endswith("." + allowed):
                    domain_matched = True
                    break
            if not domain_matched:
                raise ValueError(
                    f"Unsupported or unauthorized domain: '{hostname}'. "
                    f"Supported domains: {', '.join(sorted(ALLOWED_DOMAINS))}"
                )

        return raw_url

    def download_video(self, url: str) -> Path:
        """
        Downloads social video in low resolution (480p-720p) with SSRF validation.
        """
        safe_url = self.validate_and_sanitize_url(url)
        unique_id = uuid.uuid4().hex[:12]
        output_template = str(self.temp_dir / f"reel_{unique_id}.%(ext)s")

        ydl_opts = {
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'socket_timeout': 30,
            'retries': 3,
        }

        cookies_path = settings.ytdlp_cookies_path
        if cookies_path and os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
            logger.info(f"Using cookies file from {cookies_path}")

        logger.info(f"Starting download for sanitized URL: {safe_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(safe_url, download=True)
            expected_file = self.temp_dir / f"reel_{unique_id}.mp4"
            if expected_file.exists():
                logger.info(f"Downloaded video successfully: {expected_file}")
                return expected_file

            for file in self.temp_dir.glob(f"reel_{unique_id}.*"):
                if file.is_file():
                    return file

        raise FileNotFoundError(f"Failed to locate downloaded video for {safe_url}")

    def cleanup_file(self, file_path: Optional[Path]):
        """Safely deletes local media file after processing."""
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Error deleting temporary file {file_path}: {e}")

downloader = MediaDownloader()
