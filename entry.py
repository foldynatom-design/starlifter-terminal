# -*- coding: utf-8 -*-
import sys
import os
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

sys.path.insert(0, base_path)

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
    """Animate TRANSMITTING UPLINK on button, then generate PDF in thread."""
    import threading, time
    btn = getattr(self, '_sr_btn', None)
    
    def _run():
        _play_sound("pdf_generated.wav")
        frames = [">> TRANSMITTING UPLINK...", ">> TRANSMITTING UPLINK.. ", ">> TRANSMITTING UPLINK.  ",
                  "   TRANSMITTING UPLINK...", ">> UPLINK ACTIVE <<<", ">> TRANSMITTING UPLINK..."]
        if btn:
            try:
                btn.configure(state="disabled", fg_color="#1a3a2a", text_color="#00ff88")
            except: pass
        for i in range(6):
            if btn:
                try: btn.configure(text=frames[i % len(frames)])
                except: pass
            time.sleep(0.3)
        
        try:
            generate_pdf_direct(self)
        except Exception as e:
            try: messagebox.showerror("Error", f"Failed to generate PDF: {e}")
            except: pass
        
        if btn:
            try:
                btn.configure(text="Generate Supply Route PDF", state="normal",
                              fg_color="#2a3a1a", text_color="#c8a84e")
            except: pass
    
    threading.Thread(target=_run, daemon=True).start()

main.RequisitionApp.generate_supply_route_pdf = _patched_generate_supply_route_pdf
main.RequisitionApp.animate_generate_supply_route_pdf = _patched_animate_generate
main.RequisitionApp.run_supply_route_generation = lambda self, items=None, warehouse='': generate_pdf_direct(self)

# ── Monkey-patch manifest generation: sync classification + sound ──
_orig_gen_req = main.RequisitionApp.generate_requisition_pdf
def _patched_generate_requisition_pdf(self):
    """Sync _classify_var → security_level_var before manifest generation."""
    # Guard: ALL = disabled, must select specific classification
    cls_val = self._classify_var.get().upper() if hasattr(self, '_classify_var') else "ALL"
    if cls_val == "ALL":
        from tkinter import messagebox
        messagebox.showwarning("Classification Required",
            "Select a specific classification (PUBLIC / SECURED / CLASSIFIED) before generating.")
        return
    cls_to_sec = {
        "CLASSIFIED": "OFFICERS_ONLY_ENCRYPTED",
        "SECURED": "RESTRICTED",
        "PUBLIC": "OPEN_PUBLIC",
    }
    sec_val = cls_to_sec.get(cls_val, "OFFICERS_ONLY_ENCRYPTED")
    if hasattr(self, 'security_level_var'):
        self.security_level_var.set(sec_val)
    _play_sound("pdf_generated.wav")
    try:
        return _orig_gen_req(self)
    except Exception as e:
        import traceback
        crash_log = os.path.join(PATHS.app_root, '_manifest_crash.log')
        with open(crash_log, 'w', encoding='utf-8') as f:
            f.write(f"Error: {e}\n\n")
            traceback.print_exc(file=f)
            f.write(f"\n\nsecurity_level_var: {self.security_level_var.get() if hasattr(self, 'security_level_var') else 'N/A'}\n")
            f.write(f"classify_var: {self._classify_var.get() if hasattr(self, '_classify_var') else 'N/A'}\n")
        print(f"[MANIFEST CRASH] {e}")
        traceback.print_exc()
        raise

main.RequisitionApp.generate_requisition_pdf = _patched_generate_requisition_pdf


# ══════════════════════════════════════════════════════════════════════════
# SECTION: Entry Point
# ══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    try:
        import customtkinter
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")
        app = main.RequisitionApp()
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
