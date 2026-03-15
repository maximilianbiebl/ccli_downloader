"""Settings persistence for CCLI SongSelect Downloader.

Stores user preferences in a JSON file so they are preserved between sessions.
"""

import json
import os

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "output_folder": "./songs",
    "line_separator": "//",
    "lines_per_slide": 2,
}


def load_settings():
    """Load settings from settings.json, merging with defaults for any missing keys."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            return {**DEFAULT_SETTINGS, **saved}
        except (json.JSONDecodeError, IOError):
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    """Save settings to settings.json."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
