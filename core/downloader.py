"""
TikTok Clipper — YouTube Video Downloader
Uses yt-dlp to download videos and livestreams from YouTube.
"""
import os
import sys
import json
import subprocess
import logging
import shutil
from typing import Optional

import config

YTDLP_CMD = [sys.executable, "-m", "yt_dlp"]

logger = logging.getLogger(__name__)


class Downloader:
    """Download YouTube videos using yt-dlp."""

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

    def download(self, url: str, progress_callback=None) -> dict:
        """
        Download a YouTube video.

        Returns dict with:
            - file_path: path to downloaded video
            - title: video title
            - duration: video duration in seconds
            - thumbnail: thumbnail URL
        """
        logger.info(f"Downloading: {url}")

        # First, get video info
        info = self._get_info(url)
        title = info.get("title", "unknown")
        duration = info.get("duration", 0)
        thumbnail = info.get("thumbnail", "")
        video_id = info.get("id", "video")

        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:80]
        output_template = os.path.join(self.temp_dir, f"{video_id}_{safe_title}.%(ext)s")

        # Fetch cookies setting
        settings = config.load_settings()
        browser = settings.get("youtube_cookies_browser", "chrome")
        cookie_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")

        # Download with yt-dlp
        cmd = [
            *YTDLP_CMD,
            "--format", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "--merge-output-format", "mp4",
            "--output", output_template,
            "--no-playlist",
            "--extractor-args", "youtube:player_client=ios,default",
            "--progress",
            "--newline"
        ]
        
        if os.path.exists(cookie_file):
            cmd.extend(["--cookies", cookie_file])
        elif browser and browser.lower() != "none":
            cmd.extend(["--cookies-from-browser", browser.lower()])
            
        cmd.append(url)

        logger.info(f"Running: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        output_file = None
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.debug(line)
                # Parse progress
                if progress_callback and "[download]" in line and "%" in line:
                    try:
                        pct_str = line.split("%")[0].split()[-1]
                        pct = float(pct_str)
                        progress_callback("download", pct)
                    except (ValueError, IndexError):
                        pass
                # Detect output file
                if "[Merger]" in line and "Merging formats into" in line:
                    output_file = line.split('"')[1] if '"' in line else None
                elif "[download] Destination:" in line:
                    output_file = line.replace("[download] Destination:", "").strip()

        process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"yt-dlp failed with return code {process.returncode}")

        # Find the downloaded file if not yet detected
        if not output_file or not os.path.exists(output_file):
            output_file = self._find_downloaded_file(video_id)

        if not output_file:
            raise FileNotFoundError("Downloaded file not found")

        logger.info(f"Downloaded: {output_file}")

        return {
            "file_path": output_file,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "video_id": video_id,
        }

    def _get_info(self, url: str) -> dict:
        """Get video info without downloading."""
        settings = config.load_settings()
        browser = settings.get("youtube_cookies_browser", "chrome")
        cookie_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
        
        cmd = [
            *YTDLP_CMD,
            "--dump-json",
            "--no-download",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=ios,default"
        ]
        
        if os.path.exists(cookie_file):
            cmd.extend(["--cookies", cookie_file])
        elif browser and browser.lower() != "none":
            cmd.extend(["--cookies-from-browser", browser.lower()])
            
        # Try to find Node.js for JS Challenge
        node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        if os.path.exists(node_path):
            cmd.extend(["--js-runtimes", f"node:{node_path}"])
            
        cmd.append(url)
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video info: {result.stderr}")
        return json.loads(result.stdout)

    def _find_downloaded_file(self, video_id: str) -> Optional[str]:
        """Find the downloaded file by video ID."""
        for f in os.listdir(self.temp_dir):
            if video_id in f and f.endswith(".mp4"):
                return os.path.join(self.temp_dir, f)
        # Fallback: return most recent mp4
        mp4_files = [
            os.path.join(self.temp_dir, f)
            for f in os.listdir(self.temp_dir)
            if f.endswith(".mp4")
        ]
        if mp4_files:
            return max(mp4_files, key=os.path.getmtime)
        return None

    def download_livestream(self, url: str, duration_seconds: int = 300, progress_callback=None) -> dict:
        """
        Download a portion of a YouTube livestream.
        
        Args:
            url: YouTube livestream URL
            duration_seconds: how many seconds to capture (default 5 min)
        """
        logger.info(f"Downloading livestream: {url} ({duration_seconds}s)")

        info = self._get_info(url)
        title = info.get("title", "livestream")
        video_id = info.get("id", "live")

        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:80]
        output_file = os.path.join(self.temp_dir, f"{video_id}_{safe_title}.mp4")

        settings = config.load_settings()
        browser = settings.get("youtube_cookies_browser", "chrome")
        cookie_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")

        cmd = [
            *YTDLP_CMD,
            "--format", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "--merge-output-format", "mp4",
            "--output", output_file,
            "--no-playlist",
            "--live-from-start",
            "--extractor-args", "youtube:player_client=ios,default",
            "--download-sections", f"*0-{duration_seconds}"
        ]
        
        if os.path.exists(cookie_file):
            cmd.extend(["--cookies", cookie_file])
        elif browser and browser.lower() != "none":
            cmd.extend(["--cookies-from-browser", browser.lower()])
            
        # Try to find Node.js for JS Challenge
        node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        if os.path.exists(node_path):
            cmd.extend(["--js-runtimes", f"node:{node_path}"])
            
        cmd.append(url)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        for line in process.stdout:
            line = line.strip()
            if line:
                logger.debug(line)
                if progress_callback and "[download]" in line and "%" in line:
                    try:
                        pct_str = line.split("%")[0].split()[-1]
                        pct = float(pct_str)
                        progress_callback("download", pct)
                    except (ValueError, IndexError):
                        pass

        process.wait()

        if not os.path.exists(output_file):
            output_file = self._find_downloaded_file(video_id)

        if not output_file:
            raise FileNotFoundError("Livestream download file not found")

        return {
            "file_path": output_file,
            "title": title,
            "duration": duration_seconds,
            "thumbnail": info.get("thumbnail", ""),
            "video_id": video_id,
        }
