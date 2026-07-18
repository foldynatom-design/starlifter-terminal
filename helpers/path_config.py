# -*- coding: utf-8 -*-
"""
path_config.py — Centrální zdroj pravdy pro všechny cesty v Starlifter Terminal.

Žádný jiný modul nesmí konstruovat cesty ručně. Vše se importuje:
    from helpers.path_config import PATHS

Při prvním spuštění se automaticky vytvoří `starlifter_paths.json`
vedle EXE (frozen) nebo vedle entry.py (dev režim).
"""

import sys
import os
import json
import tempfile
from datetime import datetime


class _StarlifterPaths:
    """Singleton holding all resolved paths for the application."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._paths = {}
        self._config_file = None
        self._detect_and_load()

    # ── Public API ──────────────────────────────────────────────

    @property
    def is_frozen(self):
        """True when running as PyInstaller EXE."""
        return getattr(sys, 'frozen', False)

    @property
    def app_root(self):
        """Root directory of the application (next to EXE or entry.py)."""
        return self._paths.get("app_root", ".")

    @property
    def resources(self):
        """Directory containing JSON databases, sounds, signatures."""
        return self._paths.get("resources", os.path.join(self.app_root, "resources"))

    @property
    def fonts(self):
        """Directory containing TTF font files."""
        return self._paths.get("fonts", os.path.join(self.app_root, "fonts"))

    @property
    def signatures(self):
        """Directory containing signature/barcode PNG/JPEG files."""
        return self._paths.get("signatures", os.path.join(self.resources, "Podpisy"))

    @property
    def sounds(self):
        """Directory containing WAV sound effect files."""
        return self._paths.get("sounds", os.path.join(self.resources, "sounds"))

    @property
    def config(self):
        """Path to config.json."""
        return self._paths.get("config", os.path.join(self.app_root, "config.json"))

    @property
    def temp_dir(self):
        """Temp directory for processed images (signatures, barcodes, stamps)."""
        return self._paths.get("temp_dir",
                               os.path.join(tempfile.gettempdir(), "Starlifter"))

    @property
    def intro_video(self):
        """Path to intro_video.mp4."""
        return self._paths.get("intro_video",
                               os.path.join(self.app_root, "intro_video.mp4"))

    @property
    def internal(self):
        """Path to _internal/ (PyInstaller runtime)."""
        return self._paths.get("internal",
                               os.path.join(self.app_root, "_internal"))

    def resource(self, relative_path):
        """Resolve a relative path against the app root, then resources.

        Replaces the old `resource_path()` / `_patched_resource_path()`.
        Priority:
            1) app_root / relative_path   (files next to EXE)
            2) resources / relative_path   (files inside resources/)
            3) _MEIPASS / relative_path    (PyInstaller bundle fallback)
            4) return app_root / relative_path regardless (let caller handle missing)
        """
        # 1) Next to EXE / entry.py
        p = os.path.join(self.app_root, relative_path)
        if os.path.exists(p):
            return p

        # 2) Inside resources/
        p2 = os.path.join(self.resources, relative_path)
        if os.path.exists(p2):
            return p2

        # 3) PyInstaller _MEIPASS bundle
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            p3 = os.path.join(meipass, relative_path)
            if os.path.exists(p3):
                return p3

        # 4) Fallback — return the primary path even if missing
        return p

    def ensure_temp_dir(self):
        """Create the temp directory if it doesn't exist. Returns the path."""
        os.makedirs(self.temp_dir, exist_ok=True)
        return self.temp_dir

    def temp_file(self, filename):
        """Return full path to a temp file, ensuring temp_dir exists."""
        self.ensure_temp_dir()
        return os.path.join(self.temp_dir, filename)

    def cleanup_temp(self, app_version="0.6"):
        """Clean temp dir if version changed or files are older than 7 days.

        Called once at app startup. Writes a .version marker file.
        If the version doesn't match, wipes the entire temp dir for a clean start.
        Otherwise, removes individual files older than 7 days.
        """
        import shutil
        version_file = os.path.join(self.temp_dir, ".version")

        if os.path.isdir(self.temp_dir):
            # Check version marker
            current_version = ""
            if os.path.isfile(version_file):
                try:
                    with open(version_file, "r", encoding="utf-8") as f:
                        current_version = f.read().strip()
                except OSError:
                    pass

            if current_version != app_version:
                # Version mismatch — wipe everything for clean start
                try:
                    shutil.rmtree(self.temp_dir)
                except OSError:
                    pass
            else:
                # Same version — prune files older than 7 days
                import time
                max_age = 7 * 24 * 3600  # 7 days in seconds
                now = time.time()
                try:
                    for root, dirs, files in os.walk(self.temp_dir):
                        for fname in files:
                            if fname == ".version":
                                continue
                            fpath = os.path.join(root, fname)
                            try:
                                if now - os.path.getmtime(fpath) > max_age:
                                    os.remove(fpath)
                            except OSError:
                                pass
                except OSError:
                    pass

        # Ensure temp dir exists and write version marker
        self.ensure_temp_dir()
        try:
            with open(version_file, "w", encoding="utf-8") as f:
                f.write(app_version)
        except OSError:
            pass

    # ── Internal ────────────────────────────────────────────────

    def _detect_and_load(self):
        """Auto-detect paths or load from saved config."""
        # Determine app_root
        if self.is_frozen:
            app_root = os.path.dirname(sys.executable)
        else:
            # Dev mode: helpers/ is inside source/, so go up one level
            this_dir = os.path.dirname(os.path.abspath(__file__))
            app_root = os.path.dirname(this_dir)  # source/ directory

        self._config_file = os.path.join(app_root, "starlifter_paths.json")

        # Try loading saved config first
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Validate that critical paths still exist
                if os.path.isdir(saved.get("app_root", "")):
                    self._paths = saved
                    self._paths["is_frozen"] = self.is_frozen
                    # Re-validate resources dir exists
                    if not os.path.isdir(self._paths.get("resources", "")):
                        self._paths["resources"] = self._find_resources(app_root)
                    return
            except (json.JSONDecodeError, OSError):
                pass  # Fall through to auto-detect

        # Auto-detect everything
        self._auto_detect(app_root)
        self._save_config()

    def _auto_detect(self, app_root):
        """Detect all paths from scratch."""
        self._paths["app_root"] = app_root
        self._paths["is_frozen"] = self.is_frozen

        # Resources directory
        self._paths["resources"] = self._find_resources(app_root)

        # Fonts directory
        fonts_candidates = [
            os.path.join(app_root, "fonts"),
            os.path.join(self._paths["resources"], "fonts"),
        ]
        self._paths["fonts"] = self._first_existing_dir(fonts_candidates,
                                                         os.path.join(app_root, "fonts"))

        # Signatures directory (Podpisy)
        sig_candidates = [
            os.path.join(self._paths["resources"], "Podpisy"),
            os.path.join(app_root, "Podpisy"),
            os.path.join(app_root, "resources", "Podpisy"),
        ]
        sig_dir = self._first_existing_dir(sig_candidates,
                                            os.path.join(self._paths["resources"], "Podpisy"))
        os.makedirs(sig_dir, exist_ok=True)
        self._paths["signatures"] = sig_dir

        # Sounds directory
        self._paths["sounds"] = os.path.join(self._paths["resources"], "sounds")

        # Config file
        config_candidates = [
            os.path.join(app_root, "config.json"),
            os.path.join(self._paths["resources"], "config.json"),
        ]
        self._paths["config"] = self._first_existing_file(config_candidates,
                                                           os.path.join(app_root, "config.json"))

        # Temp directory — unique per app, not polluting global temp
        self._paths["temp_dir"] = os.path.join(tempfile.gettempdir(), "Starlifter")

        # Intro video
        video_candidates = [
            os.path.join(app_root, "intro_video.mp4"),
            os.path.join(app_root, "má_to_být_animace_při_spoušte.mp4"),
        ]
        self._paths["intro_video"] = self._first_existing_file(
            video_candidates, os.path.join(app_root, "intro_video.mp4"))

        # _internal (PyInstaller runtime)
        self._paths["internal"] = os.path.join(app_root, "_internal")

    def _find_resources(self, app_root):
        """Find the resources directory."""
        candidates = [
            os.path.join(app_root, "resources"),
            os.path.join(app_root, "source", "resources"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        # Default — create it
        default = os.path.join(app_root, "resources")
        os.makedirs(default, exist_ok=True)
        return default

    def _first_existing_dir(self, candidates, fallback):
        """Return the first candidate directory that exists, or fallback."""
        for c in candidates:
            if os.path.isdir(c):
                return c
        return fallback

    def _first_existing_file(self, candidates, fallback):
        """Return the first candidate file that exists, or fallback."""
        for c in candidates:
            if os.path.isfile(c):
                return c
        return fallback

    def _save_config(self):
        """Persist detected paths to starlifter_paths.json."""
        save_data = {
            "version": 1,
            "created": datetime.now().isoformat(),
            **self._paths,
        }
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # Non-critical — app works without saved config

    def __repr__(self):
        return (
            f"StarlifterPaths(\n"
            f"  app_root    = {self.app_root}\n"
            f"  resources   = {self.resources}\n"
            f"  fonts       = {self.fonts}\n"
            f"  signatures  = {self.signatures}\n"
            f"  sounds      = {self.sounds}\n"
            f"  config      = {self.config}\n"
            f"  temp_dir    = {self.temp_dir}\n"
            f"  intro_video = {self.intro_video}\n"
            f"  is_frozen   = {self.is_frozen}\n"
            f")"
        )


# ── Module-level singleton ──────────────────────────────────────
# Import this in all other modules:
#     from helpers.path_config import PATHS
PATHS = _StarlifterPaths()
