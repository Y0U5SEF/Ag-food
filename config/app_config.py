"""
Simple application config stored in user's AppData (Roaming).
Currently persists the last selected language.
"""

import json
import os
from typing import Any, Dict


class AppConfig:
    APP_DIR_NAME = "AGFood"
    CONFIG_FILENAME = "config.json"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._config_path = self._compute_config_path()
        self._load()

    def _compute_config_path(self) -> str:
        # Prefer Roaming AppData on Windows
        appdata = os.getenv("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
        app_dir = os.path.join(appdata, self.APP_DIR_NAME)
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, self.CONFIG_FILENAME)

    def _load(self) -> None:
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            else:
                self._config = {}
        except Exception:
            # If file is corrupted, reset to empty and overwrite on next save
            self._config = {}

    def save(self) -> None:
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception:
            # Silently ignore write errors for now
            pass

    # --- Language ---
    def get_language(self, default: str = "en") -> str:
        value = self._config.get("language")
        if isinstance(value, str):
            return value
        return default

    def set_language(self, lang: str) -> None:
        self._config["language"] = lang

