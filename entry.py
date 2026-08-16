# -*- coding: utf-8 -*-
import sys
import os
import warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*CTkImage.*")
warnings.filterwarnings("ignore", message=".*HighDPI.*")
import re
import random
import threading
import urllib.request
import json
import math
import time
from tkinter import messagebox

# Explicitly import all packages used by the application to force PyInstaller's static analyzer to collect their C-extensions (.pyd files) and binary dependencies!
try:
    import cv2
except ImportError:
    cv2 = None  # Intro video will be skipped
import numpy
import fpdf
import PIL
import PIL.Image
import PIL.ImageTk
import customtkinter
import winsound
import main

# ── Extracted helper modules ──
from signature_helper import (
    get_signatures_dir, process_signature,
    process_r1_stamp, get_processed_barcode_path, extract_signature_from_sheet,
)
from lore_helper import (
    get_telemetry, sc_date_now, sc_date_only,
    get_cargo_context_sentence, rephrase_crew_text, apply_synonyms,
    LORE_STORY_CACHE, SC_YEAR_OFFSET, BG44_RANKS as _LH_BG44_RANKS,
    ore_quality_map, extract_rank as _lh_extract_rank,
    _story_rng, _SESSION_SEED,
)
from fleet_helper import _recommend_shuttle, _recommend_cargo_ship, can_shuttle_fit
from storall_packer import (
    pack_items, calculate_cargo_breakdown, load_volume_map,
    STOR_ALL_CATEGORIES, STOR_ALL_SIZES, _pick_box_size,
)

# ── Centrální cesty ──
from path_config import PATHS
PATHS.cleanup_temp('0.6')  # version marker + prune old cache

app_base = PATHS.app_root  # backward compat alias

# Dynamically add _internal and numpy.libs to DLL search path
numpy_libs_path = os.path.join(PATHS.internal, 'numpy.libs')
if os.path.exists(numpy_libs_path):
    try:
        os.add_dll_directory(numpy_libs_path)
    except Exception:
        pass

if os.path.isdir(PATHS.internal):
    try:
        os.add_dll_directory(PATHS.internal)
    except Exception:
        pass

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# app_root FIRST so loose .py patches (ui_panel, slang_helper) override bundled copies
sys.path.insert(0, PATHS.app_root)
sys.path.insert(1, base_path)

# ── Monkey-patch resource_path → delegates to PATHS.resource() ──
_orig_resource_path = getattr(main, 'resource_path', None)

def _patched_resource_path(relative_path):
    """Resolve via PATHS.resource(), then fall back to main.pyc original."""
    resolved = PATHS.resource(relative_path)
    if os.path.exists(resolved):
        return resolved
    if _orig_resource_path:
        return _orig_resource_path(relative_path)
    return resolved

main.resource_path = _patched_resource_path

# ── Sound effects utility ──
def _play_sound(sound_name):
    """Play a WAV from PATHS.sounds in background thread. Silently skips if missing."""
    import threading
    def _do_play():
        try:
            import winsound
            wav_path = os.path.join(PATHS.sounds, sound_name)
            if os.path.exists(wav_path):
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
        except Exception:
            pass
    threading.Thread(target=_do_play, daemon=True).start()


# ── SECTION 2: Lore System → moved to lore_helper.py ──
# ── SECTION 3: Image Processing → moved to signature_helper.py ──

# RP Stories — imported from rp_stories.py (uses {cargo_type} placeholder)
from rp_stories import stories
_stories_loaded = True

# Volume map: use storall_packer's 2371-entry database (from item_volumes.json)
# instead of old hardcoded dict. Loaded lazily on first access.
volume_map = load_volume_map()

# ── SECTION 4: PDF Helpers ──
# ── get_telemetry() → moved to lore_helper.py ──

# PDF Engine -> moved to pdf_engine.py
from pdf_engine import (
    PatchedMilitaryPDF, generate_pdf_direct,
    draw_report_paragraph, draw_signatures,
    _FONT_CACHE, _precache_fonts,
    LORE_STORY_CACHE, _story_rng, _SESSION_SEED,
    volume_map,
)

# ── UI Panel: all UI patches + interactions ──
from ui_panel import apply_all_patches
apply_all_patches(main)


# ── Wire Supply Route PDF generation ──
from pdf_engine import _patched_generate_supply_route_pdf

def _patched_animate_generate(self):
    """Generate Supply Route PDF directly on main thread."""
    _play_sound("pdf_generated.wav")
    try:
        generate_pdf_direct(self)
    except Exception as e:
        import traceback
        traceback.print_exc()
        try: messagebox.showerror("Error", f"Failed to generate PDF: {e}")
        except: pass
    finally:
        if hasattr(self, '_sr_btn'):
            try: self._sr_btn.configure(state="normal", text="Generate Supply Route PDF")
            except: pass
        if hasattr(self, 'generate_btn') and self.generate_btn:
            try: self.generate_btn.configure(state="normal", text="GENERATE MANIFEST PDF")
            except: pass

main.RequisitionApp.generate_supply_route_pdf = _patched_generate_supply_route_pdf
main.RequisitionApp.animate_generate_supply_route_pdf = _patched_animate_generate
main.RequisitionApp.run_supply_route_generation = lambda self, items=None, warehouse='': generate_pdf_direct(self)

# ── Monkey-patch manifest generation: sync classification + sound ──
_orig_gen_req = main.RequisitionApp.generate_requisition_pdf
def _patched_generate_requisition_pdf(self):
    """Sync _classify_var -> security_level_var before manifest generation."""
    cls_val = self._classify_var.get().upper() if hasattr(self, '_classify_var') else "PUBLIC"
    if cls_val == "ALL" or not cls_val:
        cls_val = "PUBLIC"
        if hasattr(self, '_classify_var'):
            try: self._classify_var.set("PUBLIC")
            except: pass
    cls_to_sec = {
        "CLASSIFIED": "OFFICERS_ONLY_ENCRYPTED",
        "SECURED": "RESTRICTED",
        "PUBLIC": "OPEN_PUBLIC",
    }
    sec_val = cls_to_sec.get(cls_val, "OPEN_PUBLIC")
    if hasattr(self, 'security_level_var'):
        try: self.security_level_var.set(sec_val)
        except: pass
    _play_sound("pdf_generated.wav")
    try:
        if _orig_gen_req:
            _orig_gen_req(self)
        else:
            generate_pdf_direct(self)
    except Exception as e:
        import traceback
        traceback.print_exc()
        try: messagebox.showerror("Error", f"Failed to generate PDF: {e}")
        except: pass
    finally:
        if hasattr(self, 'generate_btn') and self.generate_btn:
            try: self.generate_btn.configure(state="normal", text="GENERATE MANIFEST PDF")
            except: pass
        if hasattr(self, '_sr_btn'):
            try: self._sr_btn.configure(state="normal", text="Generate Supply Route PDF")
            except: pass

main.RequisitionApp.generate_requisition_pdf = _patched_generate_requisition_pdf
main.RequisitionApp.animate_generate_pdf = _patched_generate_requisition_pdf
main.RequisitionApp.animate_step = lambda self, *a, **kw: None


# ══════════════════════════════════════════════════════════════════════════
# SECTION: Entry Point
# ══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    def _background_preload():
        try:
            from path_config import load_frequent_items
            load_frequent_items()
            from fleet_helper import _load_uex_ships_db
            _load_uex_ships_db()
            from storall_packer import load_volume_map
            load_volume_map()
        except Exception:
            pass
    threading.Thread(target=_background_preload, daemon=True).start()

    try:
        import customtkinter
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")
        app = main.RequisitionApp()
        try:
            from ui_panel import setup_responsive_window
            setup_responsive_window(app)
        except Exception as ex:
            print(f"[Entry] Responsive window setup: {ex}")
        try:
            from src.utils.clipboard_helper import enable_universal_shortcuts
            enable_universal_shortcuts(app)
        except Exception as ex:
            print(f"[Entry] Clipboard helper init: {ex}")
        app.mainloop()
    except Exception as e:
        import traceback
        import tkinter as tk
        from tkinter import messagebox
        
        crash_log = os.path.join(PATHS.app_root, 'crash_log.txt')
        
        try:
            with open(crash_log, 'w', encoding='utf-8') as f:
                f.write("A critical error occurred while starting the application:\n\n")
                traceback.print_exc(file=f)
                f.write("\n\nPlease send this crash_log.txt to the developer.")
        except Exception:
            pass
            
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error",
                f"Application crashed on startup.\nSee {crash_log} for details.\n\nError: {str(e)}")
            root.destroy()
        except Exception:
            pass
