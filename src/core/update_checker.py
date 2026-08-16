# -*- coding: utf-8 -*-
"""
update_checker.py - Dynamic GitHub API Version check & AppData preservation

Checks GitHub for new releases. Thread-safe: uses app.after() for UI callbacks.
"""

import json
import urllib.request
import threading
import re

CURRENT_VERSION = "v0.6.1"
GITHUB_API_URL = "https://api.github.com/repos/foldynatom-design/starlifter-terminal/releases/latest"

def _parse_version(v_str):
    """Parse version string like 'v0.6.1' or '0.10.2' into a tuple of ints (0, 6, 1)."""
    nums = re.findall(r'\d+', str(v_str or ''))
    return tuple(map(int, nums)) if nums else (0,)

def _check_version_worker(app=None):
    """Worker thread that fetches the latest release from GitHub.
    
    Uses app.after() to show messagebox on the main thread (thread-safe).
    Falls back to direct messagebox if no app is provided.
    """
    try:
        req = urllib.request.Request(GITHUB_API_URL, headers={'User-Agent': 'Starlifter-Terminal'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get("tag_name", "")
            release_url = data.get("html_url", "https://github.com/foldynatom-design/starlifter-terminal/releases")
            
            if latest_version:
                latest_tuple = _parse_version(latest_version)
                current_tuple = _parse_version(CURRENT_VERSION)
                
                if latest_tuple > current_tuple:
                    msg = (
                        f"[SYSTEM NOTICE] Terminal Update Available: {latest_version}\n"
                        f"Newer release detected. Current: {CURRENT_VERSION}\n\n"
                        f"Download from GitHub:\n"
                        f"{release_url}"
                    )
                    if app is not None:
                        # Thread-safe: schedule on main Tkinter thread
                        try:
                            from tkinter import messagebox
                            app.after(0, lambda: messagebox.showinfo("Update Available", msg))
                        except Exception:
                            pass
                    else:
                        try:
                            from tkinter import messagebox
                            messagebox.showinfo("Update Available", msg)
                        except Exception:
                            pass
    except Exception as e:
        print(f"[UpdateChecker] Update check skipped or offline: {e}")


def check_for_updates(app=None):
    """Spawns a background thread to check for updates so the UI is not blocked."""
    t = threading.Thread(target=_check_version_worker, args=(app,), daemon=True)
    t.start()

