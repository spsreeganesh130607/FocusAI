"""Validated, local preferences and user activity classifications."""

import json
import os
import threading
from pathlib import Path
from urllib.parse import urlsplit

THEMES = ("Arctic Light", "Midnight", "Forest", "Lavender", "Warm Sand")
ALLOWED_DELAYS = (1, 2, 5)
ALLOWED_CATEGORIES = ("PRODUCTIVE", "NEUTRAL", "DISTRACTING")
DEFAULTS = {
    "theme": "Arctic Light",
    "motivational_reminders_enabled": False,
    "first_reminder_minutes": 2,
    "repeat_reminder_minutes": 5,
    "unknown_prompt_enabled": True,
    "unknown_prompt_minutes": 2,
    "classifications": {},
}


def default_settings_path():
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "FocusAI" / "settings.json"
    return Path.home() / ".focusai" / "settings.json"


def classification_identity(application, title, url):
    host = (urlsplit(str(url or "")).hostname or "").lower().removeprefix("www.")
    if host:
        return f"website:{host}"
    normalized_title = " ".join(str(title or "").casefold().split())
    return f"window:{str(application or 'unknown').casefold()}:{normalized_title}"


class UserSettings:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_settings_path()
        self._lock = threading.RLock()
        self._values = self._load()

    @staticmethod
    def _validate(data):
        result = dict(DEFAULTS)
        if not isinstance(data, dict):
            return result
        if data.get("theme") in THEMES:
            result["theme"] = data["theme"]
        for key in (
            "motivational_reminders_enabled",
            "unknown_prompt_enabled",
        ):
            if isinstance(data.get(key), bool):
                result[key] = data[key]
        for key in (
            "first_reminder_minutes",
            "repeat_reminder_minutes",
            "unknown_prompt_minutes",
        ):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value in ALLOWED_DELAYS:
                result[key] = value
        classifications = data.get("classifications")
        if isinstance(classifications, dict):
            result["classifications"] = {
                str(identity): category
                for identity, category in classifications.items()
                if isinstance(identity, str)
                and identity
                and category in ALLOWED_CATEGORIES
            }
        return result

    def _load(self):
        try:
            with self.path.open("r", encoding="utf-8") as settings_file:
                return self._validate(json.load(settings_file))
        except FileNotFoundError:
            return dict(DEFAULTS)
        except (OSError, json.JSONDecodeError):
            return dict(DEFAULTS)

    def get(self, key):
        with self._lock:
            return self._values.get(key, DEFAULTS.get(key))

    def snapshot(self):
        with self._lock:
            return {
                **self._values,
                "classifications": dict(self._values["classifications"]),
            }

    def set(self, key, value):
        with self._lock:
            updated = dict(self._values)
            updated[key] = value
            validated = self._validate(updated)
            if key not in DEFAULTS or validated[key] != value:
                raise ValueError(f"Invalid setting: {key}")
            self._write(validated)
            self._values = validated

    def set_classification(self, identity, category):
        if not identity or category not in ALLOWED_CATEGORIES:
            raise ValueError("A classification identity and valid category are required.")
        with self._lock:
            updated = dict(self._values)
            updated["classifications"] = dict(updated["classifications"])
            updated["classifications"][identity] = category
            self._write(updated)
            self._values = updated

    def remove_classification(self, identity):
        with self._lock:
            updated = dict(self._values)
            updated["classifications"] = dict(updated["classifications"])
            updated["classifications"].pop(identity, None)
            self._write(updated)
            self._values = updated

    def classification_for(self, identity):
        with self._lock:
            return self._values["classifications"].get(identity)

    def _write(self, values):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as settings_file:
                json.dump(values, settings_file, indent=2, ensure_ascii=True)
                settings_file.flush()
                os.fsync(settings_file.fileno())
            temporary_path.replace(self.path)
        except OSError:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
