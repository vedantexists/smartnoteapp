import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from app.config import settings
import yt_dlp

logger = logging.getLogger(__name__)

class MediaDownloader:
    def __init__(self):
        self.temp_dir = settings.get_resolved_temp_dir()

    def download_video(self, url: str) -> Path:
        """
        Downloads social video from Instagram Reels or YouTube Shorts in low resolution (480p-720p)
        to minimize bandwidth, storage, and Gemini upload latency.
        """
        unique_id = uuid.uuid4().hex[:12]
        output_template = str(self.temp_dir / f"reel_{unique_id}.%(ext)s")

        ydl_opts = {
            # Target lightweight 480p-720p mp4
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'socket_timeout': 30,
            'retries': 3,
        }

        # Check for cookies file if provided
        cookies_path = settings.ytdlp_cookies_path
        if cookies_path and os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
            logger.info(f"Using cookies file from {cookies_path}")

        logger.info(f"Starting download for URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Find the actual downloaded file
            expected_file = self.temp_dir / f"reel_{unique_id}.mp4"
            if expected_file.exists():
                logger.info(f"Downloaded video successfully: {expected_file} ({expected_file.stat().st_size} bytes)")
                return expected_file

            # Check if ext differed
            for file in self.temp_dir.glob(f"reel_{unique_id}.*"):
                if file.is_file():
                    logger.info(f"Found downloaded video with ext: {file}")
                    return file

        raise FileNotFoundError(f"Failed to locate downloaded video for {url}")

    def cleanup_file(self, file_path: Optional[Path]):
        """Safely deletes local media file after processing."""
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Error deleting temporary file {file_path}: {e}")

downloader = MediaDownloader()
