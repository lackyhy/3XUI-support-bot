import json
from pathlib import Path
import config

SETTINGS_FILE = config.DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "language": "en"
}

def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "language" not in data:
                data["language"] = "en"
            return data
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(data: dict):
    config.DATA_DIR.mkdir(exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_language() -> str:
    return load_settings().get("language", "en")

def set_language(lang: str):
    settings = load_settings()
    settings["language"] = lang
    save_settings(settings)
