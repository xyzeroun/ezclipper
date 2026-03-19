"""
TikTok Clipper — Configuration
"""
import os
import json

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# Ensure dirs exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# --- Default Settings ---
DEFAULT_SETTINGS = {
    "openrouter_api_key": "",
    "openrouter_model": "openai/gpt-4o-mini",
    "kie_api_key": "",
    "whisper_model": "base",           # tiny, base, small, medium, large-v3
    "whisper_language": "id",           # Indonesian
    "max_clips": 5,
    "min_clip_duration": 60,            # seconds
    "max_clip_duration": 180,            # seconds
    "output_resolution": "720p",
    "output_fps": 30,
    "caption_font_size": 20,
    "caption_color": "#FFFFFF",
    "caption_highlight_color": "#FFD700",
    "caption_position": "bottom",       # bottom, center
    "youtube_cookies_browser": "chrome",  # chrome, edge, firefox, brave, opera, vivaldi
    "auto_open_browser": True,
    "server_port": 8000,
}


def load_settings() -> dict:
    """Load settings from file, merging with defaults."""
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings.update(saved)
        except Exception:
            pass
    return settings


def save_settings(settings: dict):
    """Save settings to file."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def get_setting(key: str):
    """Get a single setting value."""
    settings = load_settings()
    return settings.get(key, DEFAULT_SETTINGS.get(key))
