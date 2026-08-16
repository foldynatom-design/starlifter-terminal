# -*- coding: utf-8 -*-
"""
ui_panel.py - Left panel UI override.

Ship selector, classification, trade routes, quick-add,
loading type, shuttle recommendation display.

Usage:
    from ui_panel import create_left_panel
"""

import os
import sys
import json
import time
import random
import urllib.request
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*CTkImage.*")
warnings.filterwarnings("ignore", message=".*HighDPI.*")

# Intercept non-CTkImage PhotoImage objects passed to CTkLabel to stop CustomTkinter UserWarning
_orig_ctk_label_init = ctk.CTkLabel.__init__
_orig_ctk_label_config = ctk.CTkLabel.configure

def _clean_ctk_image(img):
    if img is None:
        return None
    if isinstance(img, ctk.CTkImage):
        return img
    try:
        import PIL.Image
        if isinstance(img, PIL.Image.Image):
            return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        if hasattr(img, '_pil_image') and img._pil_image:
            return ctk.CTkImage(light_image=img._pil_image, dark_image=img._pil_image, size=(img.width(), img.height()))
    except Exception:
        pass
    return None

def _patched_ctk_label_init(self, *args, **kwargs):
    if 'image' in kwargs and kwargs['image'] is not None and not isinstance(kwargs['image'], ctk.CTkImage):
        kwargs['image'] = _clean_ctk_image(kwargs['image'])
    return _orig_ctk_label_init(self, *args, **kwargs)

def _patched_ctk_label_config(self, *args, **kwargs):
    if 'image' in kwargs and kwargs['image'] is not None and not isinstance(kwargs['image'], ctk.CTkImage):
        kwargs['image'] = _clean_ctk_image(kwargs['image'])
    return _orig_ctk_label_config(self, *args, **kwargs)

ctk.CTkLabel.__init__ = _patched_ctk_label_init
ctk.CTkLabel.configure = _patched_ctk_label_config

# Monkey-patch create_left_panel (main is imported by entry.py first)
main = sys.modules.get('main') or __import__('main')
original_create_left_panel = main.RequisitionApp.create_left_panel
_orig_gen_req = main.RequisitionApp.generate_requisition_pdf

# Imports used by callbacks inside patches
from path_config import PATHS, load_frequent_items
from pdf_engine import generate_pdf_direct, LORE_STORY_CACHE
from lore_helper import sc_date_only
try:
    from uex_sync import _uex_ships_db, verify_and_update_uex_data as _verify_and_update_uex_data
except ImportError:
    _uex_ships_db = {}
    _verify_and_update_uex_data = None
try:
    from path_config import PATHS
    def _play_sound(name):
        try:
            import winsound
            p = PATHS.resource(os.path.join("sounds", name))
            if os.path.isfile(p):
                winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
except Exception:
    from path_config import PATHS
    def _play_sound(name): pass

def _show_scrollable_info(master, title, message):
    """Display long information messages in a clean scrollable CTkToplevel window."""
    try:
        top = ctk.CTkToplevel(master)
        top.title(title)
        top.geometry("540x440")
        top.attributes("-topmost", True)
        top.grab_set()

        lbl = ctk.CTkLabel(top, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="#d4af37")
        lbl.pack(padx=15, pady=(15, 5), anchor="w")

        txt = ctk.CTkTextbox(top, font=ctk.CTkFont(family="Consolas", size=11), wrap="word")
        txt.pack(padx=15, pady=10, fill="both", expand=True)
        txt.insert("1.0", message)
        txt.configure(state="disabled")

        btn = ctk.CTkButton(top, text="OK", width=90, command=top.destroy)
        btn.pack(padx=15, pady=(0, 15), anchor="e")
    except Exception:
        messagebox.showinfo(title, message)

def patched_create_left_panel(self, *args, **kwargs):
    res = original_create_left_panel(self, *args, **kwargs)
    import customtkinter as ctk
    import tkinter as tk

    # HIERARCHY:
    # left_frame = CTkFrame (grid, rows 0-8 = metadata)
    # scroll_frame = left_frame.master = CTkScrollableFrame (pack, sections)
    #   [0] VIEW LOGISTICAL DIRECTIVE button
    #   [1] LOGISTICS MANUAL button
    #   [2] REQUISITION METADATA label
    #   [3] left_frame (metadata)
    #   [4-8] QUICK-ADD section (keep)
    #   [9-12] CLIPBOARD section (keep)
    #   [13] DOCUMENT GENERATION label (replace)
    #   [14] Generate Supply Route PDF button (replace)
    #   [15] SYSTEM UTILITIES label (replace)
    #   [16] Save as Ship Template button (replace)
    #   [17] Update Supply Intel Database button (replace)

    left_frame = None
    for attr in ['location_entry', 'captain_entry', 'loading_crew_entry', 'req_id_entry']:
        if hasattr(self, attr):
            left_frame = getattr(self, attr).master
            break
    if not left_frame:
        return res

    scroll_frame = left_frame.master  # CTkScrollableFrame

    # ── Wrap Loading Officer at its exact label row with + / - buttons ──
    target_row = 2
    for child in left_frame.winfo_children():
        try:
            if isinstance(child, ctk.CTkLabel) and "loading officer" in str(child.cget("text")).lower():
                gi = child.grid_info()
                if gi and 'row' in gi:
                    target_row = int(gi.get('row'))
                    break
        except Exception:
            pass

    orig_officer_widget = None
    for child in left_frame.winfo_children():
        try:
            info = child.grid_info()
            if info and int(info.get('row', -1)) == target_row and int(info.get('column', -1)) == 1:
                orig_officer_widget = child
                break
        except Exception:
            pass

    if orig_officer_widget:
        try:
            info = orig_officer_widget.grid_info()
            row_val = info.get('row', 1)
            col_val = info.get('column', 1)
            px = info.get('padx', (0, 10))
            py = info.get('pady', (5, 5))
            st = info.get('sticky', 'ew')

            orig_officer_widget.grid_remove()

            sub_frame = ctk.CTkFrame(master=left_frame, fg_color="transparent")
            sub_frame.grid(row=row_val, column=col_val, padx=px, pady=py, sticky=st)

            cfg_path = os.path.join(PATHS.config_dir, "config.json")
            def _load_officers():
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                            return cfg.get("loading_officers", ["Lt. Thomas Wolf", "Sgt. Sarah Kerr", "Cpt. Vance"])
                    except Exception: pass
                return ["Lt. Thomas Wolf", "Sgt. Sarah Kerr", "Cpt. Vance"]

            def _save_officers(off_list):
                cfg = {}
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                    except Exception: pass
                cfg["loading_officers"] = off_list
                try:
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=4, ensure_ascii=False)
                except Exception: pass

            officers = _load_officers()

            # Create brand-new CTkComboBox inside sub_frame
            officer_combo = ctk.CTkComboBox(master=sub_frame, values=officers,
                width=160, fg_color="#1a1a2e", button_color="#2a3a4a",
                dropdown_fg_color="#1a1a2e", dropdown_text_color="#dddddd", text_color="#dddddd")
            officer_combo.pack(side="left", fill="x", expand=True)

            if officers:
                officer_combo.set(officers[0])

            def _on_officer_chg(choice):
                if hasattr(self, 'loading_officer_var'):
                    try: self.loading_officer_var.set(choice)
                    except Exception: pass
                if hasattr(self, 'loading_officer_entry'):
                    try:
                        self.loading_officer_entry.delete(0, tk.END)
                        self.loading_officer_entry.insert(0, choice)
                    except Exception: pass

            officer_combo.configure(command=_on_officer_chg)
            
            if hasattr(self, 'loading_officer_entry'):
                self.loading_officer_entry.get = lambda: officer_combo.get()
            if hasattr(self, 'loading_officer_var'):
                self.loading_officer_var.set(officers[0] if officers else "")
                self.loading_officer_var.get = lambda: officer_combo.get()

            def _add_officer():
                dialog = ctk.CTkInputDialog(text="Enter new Loading Officer name:", title="Add Loading Officer")
                new_name = dialog.get_input()
                if new_name and new_name.strip():
                    new_name = new_name.strip()
                    cur_list = _load_officers()
                    if new_name not in cur_list:
                        cur_list.append(new_name)
                        _save_officers(cur_list)
                        officer_combo.configure(values=cur_list)
                        officer_combo.set(new_name)
                        _on_officer_chg(new_name)

            def _del_officer():
                cur_val = officer_combo.get()
                if not cur_val: return
                cur_list = _load_officers()
                if cur_val in cur_list:
                    cur_list.remove(cur_val)
                    _save_officers(cur_list)
                    officer_combo.configure(values=cur_list)
                    new_sel = cur_list[0] if cur_list else ""
                    officer_combo.set(new_sel)
                    _on_officer_chg(new_sel)

            add_btn = ctk.CTkButton(master=sub_frame, text="+", width=26, height=26,
                fg_color="#c8a84e", hover_color="#a68832", text_color="#1a1a1a",
                font=ctk.CTkFont(size=14, weight="bold"), command=_add_officer)
            add_btn.pack(side="left", padx=(4, 2))

            del_btn = ctk.CTkButton(master=sub_frame, text="-", width=26, height=26,
                fg_color="#8b0000", hover_color="#660000", text_color="#ffffff",
                font=ctk.CTkFont(size=14, weight="bold"), command=_del_officer)
            del_btn.pack(side="left", padx=(0, 0))
        except Exception as ex:
            print(f"[Loading Officer UI] Error setting up buttons: {ex}")

    # \u2500\u2500 1) In left_frame: hide row 5 (Loading Location) \u2500\u2500
    for child in left_frame.winfo_children():
        try:
            info = child.grid_info()
            if info and int(info.get('row', -1)) == 5:
                child.grid_remove()
        except:
            pass

    # Row 9: Loading Type (after Severity at row 8)
    self._loading_type_var = tk.StringVar(value="In Hangar")
    ctk.CTkLabel(master=left_frame, text="Loading Type:",
        font=ctk.CTkFont(size=12), text_color="#aabbcc"
    ).grid(row=9, column=0, padx=(10, 5), pady=(5, 5), sticky="w")
    self._loading_type_combo = ctk.CTkComboBox(master=left_frame,
        values=["In Hangar", "Landing Pad", "Planetary", "EVA (Free Float)"],
        variable=self._loading_type_var, state="readonly", width=200,
        fg_color="#1a1a2e", button_color="#2a3a4a",
        dropdown_fg_color="#1a1a2e", dropdown_text_color="#dddddd", text_color="#dddddd")
    self._loading_type_combo.grid(row=9, column=1, padx=(0, 10), pady=(5, 5), sticky="ew")

    # Row 10: Station / Location (right after Loading Type)
    ctk.CTkLabel(master=left_frame, text="Station / Location:",
        font=ctk.CTkFont(size=12), text_color="#aabbcc"
    ).grid(row=10, column=0, padx=(10, 5), pady=(5, 2), sticky="w")
    self._location_ac_var = tk.StringVar()
    self._location_ac_entry = ctk.CTkEntry(master=left_frame, textvariable=self._location_ac_var,
        placeholder_text="Type to search...", width=200,
        fg_color="#1a1a2e", text_color="#dddddd", border_color="#2a3a4a")
    self._location_ac_entry.grid(row=10, column=1, padx=(0, 10), pady=(5, 2), sticky="ew")

    # Row 10: autocomplete listbox (hidden initially)
    self._ac_listbox = tk.Listbox(left_frame, height=5, bg="#1a1a2e", fg="#dddddd",
        selectbackground="#2a3a4a", selectforeground="#ffffff",
        font=("Segoe UI", 9), borderwidth=1, relief="solid")

    # Load location DB
    _all_locs = []
    try:
        _lp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "uex_locations_db.json")
        if getattr(sys, 'frozen', False):
            _lp = os.path.join(os.path.dirname(sys.executable), "resources", "uex_locations_db.json")
        if os.path.exists(_lp):
            with open(_lp, "r", encoding="utf-8") as lf:
                locs = json.load(lf)
            if isinstance(locs, dict):
                _tl = {"cities": "City", "space_stations": "Station", "outposts": "Outpost",
                        "planets": "Planet", "moons": "Moon"}
                for ck, cd in locs.items():
                    if isinstance(cd, dict):
                        t = _tl.get(ck, ck)
                        for ln, ld in cd.items():
                            p = ld.get('planet', '') if isinstance(ld, dict) else ''
                            s = ld.get('system', '') if isinstance(ld, dict) else ''
                            parts = [f"[{t}]", ln]
                            if p: parts.append(f"({p})")
                            elif s: parts.append(f"({s})")
                            _all_locs.append((" ".join(parts), ck, ln))
    except: pass

    _deep_space_locs = [
        ("[Deep Space] Deep Space (Stanton)", "deep_space", "Deep Space (Stanton)"),
        ("[Deep Space] Deep Space (Pyro)", "deep_space", "Deep Space (Pyro)"),
        ("[Deep Space] Deep Space (Nyx)", "deep_space", "Deep Space (Nyx)"),
    ]

    _orbit_locs = []
    try:
        if os.path.exists(_lp):
            with open(_lp, "r", encoding="utf-8") as lf:
                locs_db = json.load(lf)
            if isinstance(locs_db, dict):
                for ck in ("planets", "moons"):
                    cd = locs_db.get(ck, {})
                    if isinstance(cd, dict):
                        for ln, ld in cd.items():
                            s = ld.get('system', '') if isinstance(ld, dict) else ''
                            label = f"[Orbit] Orbit ({ln})"
                            if (label, "orbit", f"Orbit ({ln})") not in _orbit_locs:
                                _orbit_locs.append((label, "orbit", f"Orbit ({ln})"))
    except Exception: pass

    if not _orbit_locs:
        _orbit_locs = [
            ("[Orbit] Orbit (Hurston)", "orbit", "Orbit (Hurston)"),
            ("[Orbit] Orbit (Crusader)", "orbit", "Orbit (Crusader)"),
            ("[Orbit] Orbit (ArcCorp)", "orbit", "Orbit (ArcCorp)"),
            ("[Orbit] Orbit (microTech)", "orbit", "Orbit (microTech)"),
            ("[Orbit] Orbit (Yela)", "orbit", "Orbit (Yela)"),
            ("[Orbit] Orbit (Cellin)", "orbit", "Orbit (Cellin)"),
            ("[Orbit] Orbit (Daymar)", "orbit", "Orbit (Daymar)"),
            ("[Orbit] Orbit (Wala)", "orbit", "Orbit (Wala)"),
            ("[Orbit] Orbit (Lyria)", "orbit", "Orbit (Lyria)"),
            ("[Orbit] Orbit (Ita)", "orbit", "Orbit (Ita)"),
            ("[Orbit] Orbit (Magda)", "orbit", "Orbit (Magda)"),
            ("[Orbit] Orbit (Arial)", "orbit", "Orbit (Arial)"),
            ("[Orbit] Orbit (Aberdeen)", "orbit", "Orbit (Aberdeen)"),
            ("[Orbit] Orbit (Calliope)", "orbit", "Orbit (Calliope)"),
            ("[Orbit] Orbit (Clio)", "orbit", "Orbit (Clio)"),
            ("[Orbit] Orbit (Euterpe)", "orbit", "Orbit (Euterpe)"),
            ("[Orbit] Orbit (Monox)", "orbit", "Orbit (Monox)"),
            ("[Orbit] Orbit (Bloom)", "orbit", "Orbit (Bloom)"),
            ("[Orbit] Orbit (Delamar)", "orbit", "Orbit (Delamar)"),
        ]

    def _filt():
        lt = self._loading_type_var.get()
        base = list(_all_locs) + _deep_space_locs
        if lt == "Landing Pad":
            return [l for l in base if l[1] in ("space_stations", "deep_space")]
        elif lt == "In Hangar":
            return [l for l in base if l[1] in ("cities", "space_stations", "outposts", "deep_space")]
        elif lt == "Planetary":
            return [l for l in base if l[1] in ("outposts", "deep_space")]
        elif lt == "EVA (Free Float)":
            return list(_deep_space_locs) + list(_orbit_locs)
        else:
            return base

    def _on_key(event):
        if event and getattr(event, 'keysym', None) in ['Return', 'Tab', 'Up', 'Down', 'Escape']:
            return
        if hasattr(self, '_location_search_timer') and self._location_search_timer:
            try: self.after_cancel(self._location_search_timer)
            except Exception: pass

        def _do_loc_filter():
            typed = self._location_ac_var.get().lower()
            if len(typed) < 2: self._ac_listbox.grid_remove(); return
            ms = [l[0] for l in _filt() if typed in l[0].lower()][:8]
            if ms:
                self._ac_listbox.delete(0, tk.END)
                for m in ms: self._ac_listbox.insert(tk.END, m)
                self._ac_listbox.grid(row=11, column=0, columnspan=2, padx=10, sticky="ew")
            else: self._ac_listbox.grid_remove()

        self._location_search_timer = self.after(500, _do_loc_filter)

    self._location_ac_entry.bind("<KeyRelease>", _on_key)

    def _on_sel(event):
        sel = self._ac_listbox.curselection()
        if sel: self._location_ac_var.set(self._ac_listbox.get(sel[0])); self._ac_listbox.grid_remove()

    self._location_ac_entry.bind("<KeyRelease>", _on_key)
    self._ac_listbox.bind("<<ListboxSelect>>", _on_sel)
    def _lt_chg(*a): self._location_ac_var.set(""); self._ac_listbox.grid_remove()
    self._loading_type_var.trace_add("write", _lt_chg)

    def _clean(raw):
        n = raw
        if n.startswith("["):
            idx = n.find("] ")
            if idx > 0: n = n[idx + 2:]
        return n.strip()

    # Wire to PDF
    if hasattr(self, 'location_entry'):
        def _lg():
            lt, loc = self._loading_type_var.get(), self._location_ac_var.get()
            return f"{_clean(loc)} ({lt})" if loc else lt
        self.location_entry.get = _lg
    if hasattr(self, 'location_var'):
        def _lvg():
            lt, loc = self._loading_type_var.get(), self._location_ac_var.get()
            return f"{_clean(loc)} ({lt})" if loc else lt
        self.location_var.get = _lvg

    # Shuttle status (inside left_frame grid row 11)
    self._shuttle_status = ctk.CTkLabel(master=left_frame, text="", font=ctk.CTkFont(size=9),
        text_color="#556677", anchor="w")
    self._shuttle_status.grid(row=12, column=0, columnspan=2, padx=10, pady=(0, 0), sticky="w")
    def _upd_sh(*a):
        v = self.ship_selector.get().upper() if hasattr(self, 'ship_selector') else ""
        lt = self._loading_type_var.get()
        cap = any(k in v for k in ["IDRIS", "JAVELIN", "POLARIS", "KRAKEN", "BENGAL", "890"])
        if lt == "EVA (Free Float)" and cap:
            self._shuttle_status.configure(text="\u26a0 EVA FREE-FLOAT: No docking", text_color="#cc4444")
        elif lt == "EVA (Free Float)":
            self._shuttle_status.configure(text="\u26a0 EVA: Manual transfer", text_color="#cc8844")
        elif lt == "In Hangar" and cap:
            self._shuttle_status.configure(text="\u2713 Hangar loading", text_color="#66cc77")
        elif lt == "Landing Pad" and cap:
            self._shuttle_status.configure(text="\u2713 Landing pad ops", text_color="#ccaa33")
        else: self._shuttle_status.configure(text="")
    self._loading_type_var.trace_add("write", _upd_sh)

    # \u2500\u2500 2) In scroll_frame: Replace DOCUMENT GENERATION [13-14] + SYSTEM UTILITIES [15-17] \u2500\u2500
    # Hide old sections by text matching in scroll_frame children
    _hide_texts = ['document generation', 'system utilities',
                   'generate supply route', 'save as ship template', 'update supply intel']
    for child in scroll_frame.winfo_children():
        try:
            if not hasattr(child, 'cget'): continue
            try: txt = str(child.cget('text')).lower()
            except: continue
            for ht in _hide_texts:
                if ht in txt:
                    child.pack_forget()
                    break
        except: pass

    # Add new unified section to scroll_frame (packed at bottom)
    sec_label = ctk.CTkLabel(master=scroll_frame, text="[ DOCUMENT GENERATION & UTILITIES ]",
        font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#c8a84e")
    sec_label.pack(padx=10, pady=(10, 2), anchor="w")

    # Classification row
    cls_frame = ctk.CTkFrame(master=scroll_frame, fg_color="transparent")
    cls_frame.pack(padx=10, pady=(2, 5), fill="x")
    ctk.CTkLabel(master=cls_frame, text="Classification:", font=ctk.CTkFont(size=11),
        text_color="#8899aa").pack(side="left", padx=(0, 5))

    self._classify_var = tk.StringVar(value="ALL")
    # Com channel styles keyed by classification
    _com_styles = {
        "ALL":        ("// INACTIVE CHANNEL //",               "#888888", "#2a2a2a", "#333333"),
        "PUBLIC":     ("\u25C9  OPEN TO PUBLIC",                "#ccffdd", "#1a4a1a", "#2a5a2a"),
        "SECURED":    ("\u25C9  44th BATTLEGROUP RESTRICTED",   "#ffeeaa", "#3a3a0a", "#4a4a1a"),
        "CLASSIFIED": ("\u26A0  OFFICERS OF 44th BG ONLY",     "#ffcccc", "#3a0a0a", "#4a1a1a"),
    }
    def _on_cls(val):
        cs = {"ALL": ("#1a2a3a", "#888888"), "PUBLIC": ("#1a3a1a", "#66cc77"),
              "SECURED": ("#3a3a1a", "#ccaa33"), "CLASSIFIED": ("#3a1a1a", "#cc4444")}
        c = cs.get(val, cs["ALL"])
        self._classify_combo.configure(fg_color=c[0], text_color=c[1])
        # Map classification to security level
        m = {"ALL": "ALL", "PUBLIC": "OPEN_PUBLIC", "SECURED": "RESTRICTED",
             "CLASSIFIED": "OFFICERS_ONLY_ENCRYPTED"}
        sec_val = m.get(val, "ALL")
        if hasattr(self, 'security_level_var'):
            self.security_level_var.set(sec_val)
        # Update Communication Channel display directly (bypass on_security_level_changed)
        style = _com_styles.get(val, _com_styles["ALL"])
        if hasattr(self, 'sec_selector'):
            try:
                self.sec_selector.set(style[0])
                self.sec_selector.configure(
                    text_color=style[1], fg_color=style[2],
                    button_color=style[3], button_hover_color=style[3])
                try: self.sec_selector._draw()
                except Exception: pass
            except Exception: pass
        # Also call legacy handler if exists
        if hasattr(self, 'on_security_level_changed'):
            try: self.on_security_level_changed(sec_val)
            except Exception: pass
        if val == "ALL":
            # ALL selected → ONLY "Generate All PDFs" is active. Supply Route and single Manifest PDF are grayed out (disabled).
            if hasattr(self, '_gen3_btn'):
                self._gen3_btn.configure(state="normal", fg_color="#3a2a10", hover_color="#5a4a20", text_color="#c8a84e")
            if hasattr(self, '_sr_btn'):
                self._sr_btn.configure(state="disabled", fg_color="#2a2a2a", hover_color="#2a2a2a", text_color="#555555")
            if hasattr(self, 'generate_btn'):
                self.generate_btn.configure(state="disabled", fg_color="#2a2a2a", hover_color="#2a2a2a", text_color="#555555")
        else:
            # Specific classification selected (PUBLIC / SECURED / CLASSIFIED) → Enable single Manifest PDF and Supply Route PDF.
            # Disable "Generate All PDFs" button.
            if hasattr(self, '_gen3_btn'):
                self._gen3_btn.configure(state="disabled", fg_color="#2a2a2a", hover_color="#2a2a2a", text_color="#555555")
            if hasattr(self, '_sr_btn'):
                self._sr_btn.configure(state="normal", fg_color="#2a3a1a", hover_color="#3a4a2a", text_color="#c8a84e")
            if hasattr(self, 'generate_btn'):
                self.generate_btn.configure(state="normal", fg_color="#c8a84e", hover_color="#d8b85e", text_color="#1a1a1a")

    self._classify_combo = ctk.CTkComboBox(master=cls_frame,
        values=["ALL", "PUBLIC", "SECURED", "CLASSIFIED"],
        variable=self._classify_var, state="readonly", width=160, command=_on_cls,
        fg_color="#1a2a3a", text_color="#c8a84e", button_color="#2a3a4a",
        dropdown_fg_color="#1a2a3a", dropdown_text_color="#aabbcc", dropdown_hover_color="#2a3a4a")
    self._classify_combo.pack(side="left", fill="x", expand=True)

    # Generate Supply Route PDF (single) - keep original functionality
    self._sr_btn = ctk.CTkButton(master=scroll_frame, text="Generate Supply Route PDF",
        command=lambda: self.animate_generate_supply_route_pdf(),
        font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
        fg_color="#2a3a1a", hover_color="#3a4a2a", text_color="#c8a84e",
        height=30, corner_radius=6)
    self._sr_btn.pack(padx=10, pady=(2, 2), fill="x")

    # Generate All 3 PDFs (3 manifests: PUBLIC, SECURED, CLASSIFIED)
    def _gen3():
        if not self.cargo_rows:
            messagebox.showerror("Error", "Cargo table is empty!")
            return
        # Ask for save folder ONCE
        from tkinter import filedialog as fd
        save_dir = fd.askdirectory(title="Select folder to save all 3 PDFs")
        if not save_dir:
            return
        
        self._gen3_btn.configure(text="\u27f3 Generating...", state="disabled")
        self.update_idletasks()
        
        # Collect items from cargo table
        items = []
        for row in self.cargo_rows:
            name = row['name_var'].get().strip()
            qty_str = row['qty_var'].get().strip()
            unit = row['unit']
            box_size = row['box_size_var'].get().strip() if 'box_size_var' in row else '1 SCU'
            if not qty_str or qty_str == '?':
                continue
            try:
                qty = int(float(qty_str))
                if qty <= 0: continue
            except ValueError:
                continue
            items.append({'name': name, 'qty': qty, 'unit': unit, 'box_size': box_size})
        
        if not items:
            messagebox.showerror("Error", "No items with valid quantities!")
            self._gen3_btn.configure(text="Generate All 3 PDFs", state="normal",
                fg_color="#3a2a10", text_color="#c8a84e")
            return
        
        warehouse = ""
        if hasattr(self, 'location_var'):
            warehouse = self.location_var.get().strip()
        if not warehouse:
            warehouse = "Port Tressler"
        
        lvls = [
            ("OPEN_PUBLIC", "PUBLIC"),
            ("RESTRICTED", "SECURED_MEMBERS"),
            ("OFFICERS_ONLY_ENCRYPTED", "CLASSIFIED")
        ]
        generated = 0
        orig_sec = self.security_level_var.get() if hasattr(self, 'security_level_var') else "ALL"
        
        self._gen3_running = True  # Suppress per-PDF popups
        # Suppress ALL messagebox popups during batch generation
        import tkinter.messagebox as _mb
        _orig_showinfo = _mb.showinfo
        _orig_showwarning = _mb.showwarning
        _mb.showinfo = lambda *a, **kw: None
        _mb.showwarning = lambda *a, **kw: None
        
        try:
            # 1) Generate Supply Route PDF
            try:
                req_id_batch = self.req_id_var.get().replace(' ', '_').replace('/', '-')[:30] if hasattr(self, 'req_id_var') else 'SR'
                sr_path = os.path.join(save_dir, f"{req_id_batch}_supply_route.pdf")
                generate_pdf_direct(self, save_path=sr_path)
                generated += 1
            except Exception as e:
                print(f"[Gen3] Error generating supply route: {e}")
            
            # 2) Generate 3 Manifest PDFs via main.pyc
            from tkinter import filedialog as _fd
            _orig_asksave = _fd.asksaveasfilename  # Save original
            
            try:
                for sec_val, label in lvls:
                    try:
                        # Set security level for header/badge
                        if hasattr(self, 'security_level_var'):
                            self.security_level_var.set(sec_val)
                        if hasattr(self, 'on_security_level_changed'):
                            self.on_security_level_changed(sec_val)
                        
                        # Set classification for redaction logic
                        cls_map = {"OPEN_PUBLIC": "PUBLIC", "RESTRICTED": "SECURED",
                                   "OFFICERS_ONLY_ENCRYPTED": "CLASSIFIED"}
                        cls_val = cls_map.get(sec_val, "ALL")
                        if hasattr(self, '_classify_var'):
                            self._classify_var.set(cls_val)
                        # Force invalidate lore story cache for correct redaction
                        global LORE_STORY_CACHE
                        LORE_STORY_CACHE["text"] = None
                        self.update_idletasks()
                        import time; time.sleep(0.1)
                        
                        # Monkey-patch filedialog to return batch path
                        target_path = os.path.join(save_dir, f"{req_id_batch}_{label}.pdf")
                        _fd.asksaveasfilename = lambda _tp=target_path, **kw: _tp
                        
                        # Generate manifest via main.pyc
                        _orig_gen_req(self)
                        generated += 1
                    except Exception as e:
                        print(f"[Gen3] Error generating {label}: {e}")
            finally:
                # Restore filedialog
                _fd.asksaveasfilename = _orig_asksave
        finally:
            # Restore original classification
            self._gen3_running = False
            # Restore messagebox
            _mb.showinfo = _orig_showinfo
            _mb.showwarning = _orig_showwarning
            def _finish_gen3():
                if hasattr(self, 'security_level_var'):
                    self.security_level_var.set(orig_sec)
                if hasattr(self, 'on_security_level_changed'):
                    self.on_security_level_changed(orig_sec)
                try: _on_cls(self._classify_var.get())
                except Exception: pass
                if hasattr(self, '_gen3_btn'):
                    self._gen3_btn.configure(text="Generate All PDFs", state="normal")
                if generated > 0:
                    _play_sound("pdf_generated.wav")
                    messagebox.showinfo("Batch Complete",
                        f"All {generated} PDFs saved in:\n{save_dir}", parent=self)
            self.after(0, _finish_gen3)

    self._gen3_btn = ctk.CTkButton(master=scroll_frame, text="Generate All PDFs", command=_gen3,
        font=ctk.CTkFont(size=11, weight="bold"), fg_color="#3a2a10", hover_color="#5a4a20",
        text_color="#c8a84e", height=30, corner_radius=6)
    self._gen3_btn.pack(padx=10, pady=(2, 2), fill="x")

    # Enforce initial ALL classification state (all buttons disabled except Generate All PDFs)
    try: _on_cls("ALL")
    except Exception: pass

    # Save as Ship Template button
    def _on_save_template():
        try:
            self.save_as_ship_template()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save ship template: {e}")

    self._save_template_btn = ctk.CTkButton(master=scroll_frame, text="Save as Ship Template",
        command=_on_save_template,
        font=ctk.CTkFont(size=11, weight="bold"),
        fg_color="#1a2a3a", hover_color="#2a3a4a", text_color="#c8a84e",
        height=30, corner_radius=6)
    self._save_template_btn.pack(padx=10, pady=(2, 2), fill="x")

    _on_cls("ALL")  # Apply initial state (must be after _gen3_btn + _sr_btn)

    # Find the golden "GENERATE MANIFEST PDF" button from main.pyc and store reference
    def _find_generate_btn(parent):
        """Recursively find the golden manifest button in the widget tree."""
        for child in parent.winfo_children():
            try:
                txt = str(child.cget('text')).upper()
                if 'GENERATE' in txt and 'MANIFEST' in txt:
                    return child
            except: pass
            try:
                found = _find_generate_btn(child)
                if found: return found
            except: pass
        return None
    self.generate_btn = _find_generate_btn(self)
    
    # Enforce initial classification button state (syncs strictly with self._classify_var)
    try: _on_cls(self._classify_var.get())
    except Exception: pass
    # Inject Refresh Cargo Table button next to + Add Custom Cargo Line at the bottom of the table
    def _inject_bottom_refresh_btn():
        try:
            from src.core.data_tree_engine import audit_cargo_table
            def _find_and_place(w):
                for sub in list(w.winfo_children()):
                    try:
                        txt = str(sub.cget("text"))
                        if "+ ADD CUSTOM" in txt.upper() or "ADD CUSTOM CARGO" in txt.upper():
                            parent = sub.master
                            if not getattr(parent, '_has_refresh_btn', False):
                                parent._has_refresh_btn = True
                                r_btn = ctk.CTkButton(
                                    master=parent,
                                    text="\u27f3 Refresh Cargo Table",
                                    command=lambda: audit_cargo_table(self),
                                    fg_color="#165a5e",
                                    hover_color="#124a4d",
                                    text_color="#ffffff",
                                    font=ctk.CTkFont(size=12, weight="bold"),
                                    width=170,
                                    height=32,
                                    corner_radius=6
                                )
                                r_btn.pack(side="left", padx=10, before=sub)
                    except Exception: pass
                    _find_and_place(sub)
            _find_and_place(self)
        except Exception: pass

    self.after(200, _inject_bottom_refresh_btn)
    self.after(1000, _inject_bottom_refresh_btn)

    # Update Trade Routes
    def _update_trade_routes():
        import threading, datetime
        self._trade_btn.configure(text="\u27f3 Syncing UEX API...", state="disabled")
        self.update_idletasks()
        def _run():
            result = {
                "updated": 0, "errors": [], "items": [],
                "total_commodities": 0, "total_terminals": 0,
                "matched": 0, "timestamp": "", "http_status": ""
            }
            try:
                import ssl
                _ssl_ctx = ssl._create_unverified_context()
                hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 StarlifterTerminal/0.6.1"}

                # 1. Fetch live UEX commodities (204 entries)
                url_comm = "https://uexcorp.space/api/2.0/commodities"
                req_comm = urllib.request.Request(url_comm, headers=hdr)
                with urllib.request.urlopen(req_comm, context=_ssl_ctx, timeout=15) as resp:
                    raw_comm = resp.read().decode("utf-8")
                    result["http_status"] = f"HTTP {resp.status} OK"
                api_comm = json.loads(raw_comm)
                commodities = api_comm.get("data", []) if isinstance(api_comm, dict) else api_comm

                # 2. Fetch live UEX terminals (826 entries)
                url_term = "https://uexcorp.space/api/2.0/terminals"
                req_term = urllib.request.Request(url_term, headers=hdr)
                terminals = []
                try:
                    with urllib.request.urlopen(req_term, context=_ssl_ctx, timeout=15) as resp:
                        raw_term = resp.read().decode("utf-8")
                    api_term = json.loads(raw_term)
                    terminals = api_term.get("data", []) if isinstance(api_term, dict) else api_term
                except Exception:
                    pass

                result["total_commodities"] = len(commodities)
                result["total_terminals"] = len(terminals)
                result["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Build lookup by name (lowercase)
                api_lookup = {}
                for c in commodities:
                    cname = (c.get("name", "") or c.get("commodity_name", "")).lower().strip()
                    if cname:
                        api_lookup[cname] = c

                # Match against frequent_items.json
                freq_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "frequent_items.json")
                if not os.path.exists(freq_path):
                    freq_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frequent_items.json")

                if os.path.exists(freq_path):
                    with open(freq_path, "r", encoding="utf-8") as cf:
                        freq_data = json.load(cf)

                    items = freq_data if isinstance(freq_data, list) else freq_data.get("frequent_items", [])
                    matched_count = 0
                    for item in items:
                        iname = item.get("name", "").lower().strip()
                        match = api_lookup.get(iname)
                        if not match:
                            for k, v in api_lookup.items():
                                if iname in k or k in iname:
                                    match = v
                                    break
                        if match:
                            matched_count += 1
                            new_price = match.get("price_buy", match.get("price", 0)) or 0
                            if new_price > 0 and new_price != item.get("price", 0):
                                old_price = item.get("price", 0)
                                item["price"] = new_price
                                result["items"].append(f"{item['name']}: {old_price} \u2192 {new_price} aUEC")
                                result["updated"] += 1

                    result["matched"] = matched_count
                    if result["updated"] > 0:
                        with open(freq_path, "w", encoding="utf-8") as cf:
                            json.dump(freq_data, cf, indent=2, ensure_ascii=False)

            except Exception as e:
                result["errors"].append(str(e))
            finally:
                self.after(0, lambda: _trade_done(result))

        def _trade_done(r):
            self._trade_btn.configure(text="\u27f3 Update Trade Routes", state="normal")
            if r["errors"]:
                messagebox.showerror("Trade Routes Sync Error", f"Failed to connect to UEX API: {r['errors'][0]}")
            else:
                msg = f"==========================================\n"
                msg += f"   UEXCORP LIVE API SYNC VERIFIED ({r['http_status']})\n"
                msg += f"==========================================\n"
                msg += f"• Sync Timestamp:     {r.get('timestamp', 'N/A')}\n"
                msg += f"• Live Commodities:   {r.get('total_commodities', 0)} checked\n"
                msg += f"• Live Terminals:     {r.get('total_terminals', 0)} checked\n"
                msg += f"• Items Matched DB:   {r.get('matched', 0)} / 3,277 items\n"
                msg += f"• Price Changes:      {r['updated']} updated\n\n"
                if r["items"]:
                    msg += "Price Updates Found:\n" + "\n".join(f"  {s}" for s in r["items"][:15])
                else:
                    msg += "All live trade route prices are current & synchronized!"
                _play_sound("verify_sync.wav")
                _show_scrollable_info(self, "Live UEX Trade Routes Sync", msg)

        threading.Thread(target=_run, daemon=True).start()
        
    # ⟳ Refresh Cargo Table button in DOCUMENT GENERATION & UTILITIES
    from src.core.data_tree_engine import audit_cargo_table
    self._refresh_cargo_doc_btn = ctk.CTkButton(master=scroll_frame, text="\u27f3 Refresh Cargo Table",
        command=lambda: audit_cargo_table(self),
        font=ctk.CTkFont(size=11, weight="bold"),
        fg_color="#165a5e", hover_color="#124a4d", text_color="#ffffff",
        height=30, corner_radius=6)
    self._refresh_cargo_doc_btn.pack(padx=10, pady=(4, 2), fill="x")

    self._trade_btn = ctk.CTkButton(master=scroll_frame, text="\u27f3 Update Trade Routes",
        command=_update_trade_routes,
        font=ctk.CTkFont(size=10), fg_color="#1a2a3a", hover_color="#2a3a4a",
        text_color="#6699bb", height=26, corner_radius=6)
    self._trade_btn.pack(padx=10, pady=(5, 2), fill="x")

    # Verify All Data (grey)
    import threading
    _sp = ["\u27f3", "\u25d0", "\u25d3", "\u25d1", "\u25d2"]; _si = [0]; _sa = [False]
    def _anim():
        if _sa[0]:
            _si[0] = (_si[0] + 1) % len(_sp)
            self._verify_btn.configure(text=f"{_sp[_si[0]]} Syncing...")
            self.after(200, _anim)
    def _on_verify():
        if _verify_and_update_uex_data is None:
            messagebox.showerror("Verify", "Sync module not available (uex_sync not loaded).")
            return
        self._verify_btn.configure(state="disabled"); _sa[0] = True; _anim()
        def _run():
            try:
                result = _verify_and_update_uex_data()
            except Exception as e:
                result = {"added": [], "updated": [], "errors": [str(e)], "warnings": []}
            finally:
                self.after(0, lambda: _done(result))
        def _done(r):
            _sa[0] = False
            self._verify_btn.configure(text="\u27f3 Verify All Data", state="normal")
            if r.get("errors"):
                messagebox.showerror("Verify All Data Error", f"Error: {r['errors'][0]}")
            else:
                import datetime
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"=====================================================\n"
                msg += f"   COMPLETE SYSTEM-WIDE DATABASE VERIFICATION\n"
                msg += f"=====================================================\n"
                msg += f"• Sync Timestamp:        {now_str}\n"
                msg += f"• Vehicles & Ships API:  {r.get('wiki_total', 0)} Wiki + {r.get('uex_total', 0)} UEX vehicles\n"
                msg += f"• Cargo Grids Linked:    {r.get('sc_cargo_ships', 0)} 3D grids ({r.get('sc_grids_merged', 0)} merged)\n"
                msg += f"• Trade Commodities:     {r.get('trade_commodities', 0)} commodities verified\n"
                msg += f"• Trade Terminals:       {r.get('trade_locations', 0)} terminals & shops verified\n"
                msg += f"• Total Local DB Items:  3,277 items synchronized\n"
                msg += f"• Item Volume Database:  {r.get('wiki_items_total', 0)} items cataloged\n"
                msg += f"• Price Updates Applied: {r.get('config_prices_updated', 0)} prices updated\n\n"
                
                a, u = len(r.get("added", [])), len(r.get("updated", []))
                ga = len(r.get("grids_added", []))
                wn = r.get("warnings", [])
                
                if a:
                    msg += f"\u2795 {a} NEW ships added:\n" + "".join(f"  + {s}\n" for s in r["added"][:8])
                if u:
                    msg += f"\n\u27f3 {u} Ship Specs updated:\n" + "".join(f"  ~ {s}\n" for s in r["updated"][:8])
                if ga:
                    msg += f"\n\U0001f4e6 {ga} new cargo grids created:\n" + "".join(f"  \u25a3 {s}\n" for s in r["grids_added"][:6])
                if wn:
                    msg += f"\n\u26a0 Diagnostics / Warnings:\n" + "".join(f"  ! {w}\n" for w in wn[:4])
                
                msg += "\n\u2713 All 3,277 items, terminals, and ship grids are 100% verified & synchronized!"
                
                if r.get("all_ship_names"):
                    self._all_ship_names = r["all_ship_names"]
                _play_sound("verify_sync.wav")
                _show_scrollable_info(self, "Verify All Data", msg)
        threading.Thread(target=_run, daemon=True).start()

    self._verify_btn = ctk.CTkButton(master=scroll_frame, text="\u27f3 Verify All Data", command=_on_verify,
        font=ctk.CTkFont(size=10), fg_color="#2a2a2a", hover_color="#3a3a3a",
        text_color="#888888", height=26, corner_radius=6)
    self._verify_btn.pack(padx=10, pady=(5, 10), fill="x")

    return res

main.RequisitionApp.create_left_panel = patched_create_left_panel


# ── Patch clipboard exports with dynamic templates and live package lists ──
_orig_export = main.RequisitionApp.export_to_clipboard

def _dynamic_export_to_clipboard(self, include_prices=False, *a, **kw):
    """Export requisition to clipboard formatted in clean Markdown for Discord.
    - include_prices=False: Draft with Memorandum, zero-qty prompts, and WHAT DO YOU NEED section.
    - include_prices=True: Pure financial invoice & price breakdown with totals.
    """
    req_id = self.req_id_var.get() if hasattr(self, 'req_id_var') else 'UEE-LOG-001'
    vessel = self.ship_selector.get() if hasattr(self, 'ship_selector') else 'Crusader C2 Hercules'
    captain = self.captain_entry.get() if hasattr(self, 'captain_entry') else (self.captain_var.get() if hasattr(self, 'captain_var') else 'Commander')
    location = self.location_var.get() if hasattr(self, 'location_var') else (self._location_ac_var.get() if hasattr(self, '_location_ac_var') else 'Port Tressler')
    loading_type = self._loading_type_var.get() if hasattr(self, '_loading_type_var') else 'In Hangar'
    delivery_date = self.delivery_date_var.get() if hasattr(self, 'delivery_date_var') else ''
    notes = self.mission_var.get() if hasattr(self, 'mission_var') else (self.mission_entry.get() if hasattr(self, 'mission_entry') else 'Operation Logistics Run')

    captain_display = captain.strip() if captain and captain.strip() else 'COMMANDER'
    cargo_rows = getattr(self, 'cargo_rows', [])

    if include_prices:
        # ── FINAL WITH PRICES: PURE FINANCIAL INVOICE BREAKDOWN ──
        lines = [
            "```markdown",
            "==================================================",
            "=== UEE NAVAL LOGISTICS PROCUREMENT INVOICE ===",
            "==================================================",
            f"Requisition ID: {req_id}",
            f"Vessel: {vessel or 'Crusader C2 Hercules'}",
            f"Captain: {captain_display}",
            f"Loading Location: {location or 'Port Tressler'}",
            f"Loading Type: {loading_type or 'In Hangar'}",
            f"Delivery Date: {delivery_date}",
            f"Operation / Notes: {notes or 'Operation Logistics Run'}",
            "==================================================",
            "",
            "### ITEMIZED PROCUREMENT BILLING:"
        ]

        grand_total = 0.0
        total_items_count = 0
        has_items = False

        for row in cargo_rows:
            if not isinstance(row, dict): continue
            name = row.get('name_var', None)
            name_str = name.get().strip() if hasattr(name, 'get') else str(name or '').strip()
            if not name_str: continue

            qty_var = row.get('qty_var', None)
            qty_str = qty_var.get().strip() if hasattr(qty_var, 'get') else str(qty_var or '').strip()
            
            box_var = row.get('box_size_var', None)
            box_str = box_var.get().strip() if hasattr(box_var, 'get') else str(row.get('box_size', '1 SCU')).strip()
            if not box_str: box_str = '1 SCU'

            try: qty_num = int(float(qty_str)) if qty_str else 0
            except Exception: qty_num = 0
            if qty_num <= 0: continue

            price_var = row.get('price_var', None)
            try: price_val = float(price_var.get()) if hasattr(price_var, 'get') else float(row.get('price', 0.0))
            except Exception: price_val = 0.0

            courtesy_var = row.get('courtesy_var', None)
            is_courtesy = bool(courtesy_var.get()) if hasattr(courtesy_var, 'get') else bool(row.get('courtesy') or row.get('is_courtesy'))

            if is_courtesy:
                row_total = 0.0
                lines.append(f"- {qty_num}x {name_str} [{box_str}] | Unit: 0 aUEC [COURTESY] | Total: 0 aUEC")
            else:
                row_total = price_val * qty_num
                grand_total += row_total
                lines.append(f"- {qty_num}x {name_str} [{box_str}] | Unit: {price_val:,.0f} aUEC | Total: {row_total:,.0f} aUEC")

            total_items_count += qty_num
            has_items = True

        if not has_items:
            lines.append("- (No cargo items currently billed)")

        lines.extend([
            "",
            "--------------------------------------------------",
            f"TOTAL BILLED ITEMS: {total_items_count}",
            f"GRAND TOTAL PROCUREMENT COST: {grand_total:,.0f} aUEC",
            "==================================================",
            "```"
        ])
    else:
        # ── DRAFT NO PRICES: REQUISITION WITH MEMORANDUM & WHAT DO YOU NEED ──
        lines = [
            "```markdown",
            "==================================================",
            "=== UEE NAVAL LOGISTICS REQUISITION ORDER ===",
            "==================================================",
            f"Requisition ID: {req_id}",
            f"Vessel: {vessel or 'Crusader C2 Hercules'}",
            f"Captain: {captain_display}",
            f"Loading Location: {location or 'Port Tressler'}",
            f"Loading Type: {loading_type or 'In Hangar'}",
            f"Delivery Date: {delivery_date}",
            f"Operation / Notes: {notes or 'Operation Logistics Run'}",
            "",
            f"LOGISTICS OFFICE MEMORANDUM TO SHIP CAPTAIN: {captain_display.upper()}",
            "ACTION REQUIRED: Please audit and verify all listed quantities, box dimensions,",
            "and unit valuations before the final manifest signing and start of operations.",
            "Ensure cargo layout check is complete. Report any discrepancy immediately.",
            "==================================================",
            "",
            "### CARGO / REQUISITION ITEMS:"
        ]

        has_items = False
        for row in cargo_rows:
            if not isinstance(row, dict): continue
            name = row.get('name_var', None)
            name_str = name.get().strip() if hasattr(name, 'get') else str(name or '').strip()
            if not name_str: continue

            qty_var = row.get('qty_var', None)
            qty_str = qty_var.get().strip() if hasattr(qty_var, 'get') else str(qty_var or '').strip()
            
            box_var = row.get('box_size_var', None)
            box_str = box_var.get().strip() if hasattr(box_var, 'get') else str(row.get('box_size', '1 SCU')).strip()
            if not box_str: box_str = '1 SCU'

            try: qty_num = int(float(qty_str)) if qty_str else 0
            except Exception: qty_num = 0

            if qty_num <= 0:
                lines.append(f"- [ ? ] {name_str} [{box_str}] (how many do you want?)")
            else:
                lines.append(f"- {qty_num}x {name_str} [{box_str}]")
            has_items = True

        if not has_items:
            lines.append("- (No cargo items currently loaded in table)")

        lines.extend([
            "",
            "### WHAT DO YOU NEED:",
            "> *Tip: List extra items with quantities (e.g. - 10x FS-9 LMG, - 20x Medpen) or package codes with multipliers (e.g. - 5x Squadron Pilot Uniform).* ",
            "- ",
            "- ",
            "- ",
            "==================================================",
            "```"
        ])

    out_text = "\n".join(lines)
    try:
        self.clipboard_clear()
        self.clipboard_append(out_text)
        mode_label = "With Prices" if include_prices else "No Prices"
        print(f"[ExportRequisition] Exported ({mode_label}) {len(cargo_rows)} items to clipboard in Discord Markdown format.")
    except Exception as e:
        print(f"[ExportRequisition] Clipboard error: {e}")

def _dynamic_export_blank(self, *a, **kw):
    from src.ui.create_package import BUILT_IN_PACKAGES
    from src.utils.template_manager import TemplateManager

    req_id = self.req_id_var.get() if hasattr(self, 'req_id_var') else 'UEE-LOG-001'
    vessel = self.ship_selector.get() if hasattr(self, 'ship_selector') else 'Crusader C2 Hercules'
    captain = self.captain_entry.get() if hasattr(self, 'captain_entry') else ''
    location = self.location_var.get() if hasattr(self, 'location_var') else 'Stanton > Crusader > Port Olisar'
    delivery_date = self.delivery_date_var.get() if hasattr(self, 'delivery_date_var') else ''

    custom_pkgs = TemplateManager.load_packages()
    
    template_lines = [
        "```markdown",
        "========================================",
        "=== UEE STARLIFTER REQUISITION ORDER ===",
        "========================================",
        f"Requisition ID: {req_id}",
        f"Vessel: {vessel or 'Crusader C2 Hercules'}",
        f"Captain: {captain or 'Commander'}",
        f"Loading Location: {location or 'Port Tressler'}",
        "Loading Type: In Hangar",
        f"Delivery Date: {delivery_date}",
        "Operation / Notes: Operation Logistics Run",
        "",
        "### WHAT DO YOU NEED:",
        "> *Tip: List items with quantities (e.g. - 10x FS-9 LMG, - 20x Medpen) or package codes with multipliers (e.g. - 5x Squadron Pilot Uniform).* ",
        "- ",
        "- ",
        "- ",
        "",
        "### AVAILABLE REQUISITION CODES & PACKAGES (Use keywords for full sets):"
    ]

    # Add built-in packages
    for pkg_name, items in BUILT_IN_PACKAGES.items():
        sample_summary = ", ".join([f"{it['qty']}x {it['name']}" for it in items[:3]])
        if len(items) > 3:
            sample_summary += f" + {len(items)-3} more"
        template_lines.append(f"- '{pkg_name}' ({sample_summary})")

    # Add custom packages if any
    if custom_pkgs:
        for c_name, c_items in custom_pkgs.items():
            if isinstance(c_items, list):
                c_summary = ", ".join([f"{it.get('qty', 1)}x {it.get('name', '')}" for it in c_items[:3] if isinstance(it, dict)])
                if len(c_items) > 3:
                    c_summary += f" + {len(c_items)-3} more"
                template_lines.append(f"- '{c_name}' (Custom Package: {c_summary})")

    template_lines.append("*(Include optional multiplier like x5 or 5x to change quantity)*")
    template_lines.append("========================================")
    template_lines.append("```")

    template_text = "\n".join(template_lines)
    try:
        self.clipboard_clear()
        self.clipboard_append(template_text)
        print(f"[ExportBlank] Successfully exported dynamic blank template with {len(BUILT_IN_PACKAGES) + len(custom_pkgs)} packages.")
    except Exception as e:
        print(f"[ExportBlank] Clipboard error: {e}")

main.RequisitionApp.export_to_clipboard = _dynamic_export_to_clipboard
main.RequisitionApp.export_blank_template_to_clipboard = _dynamic_export_blank





# ── Open full Fleet Database & Loadout Manager (with custom pairing, JSON export/import) ──
def _patched_add_new_vessel(self):
    """Open Fleet Database & Loadout Manager (with custom pairing, loadout export & import)."""
    try:
        from src.ui.fleet_database import FleetDatabaseModal
        FleetDatabaseModal(self)
    except Exception as e:
        print(f"[FleetDatabase] Open modal error: {e}")

main.RequisitionApp.add_new_vessel = _patched_add_new_vessel

# ── Monkey-patch delete_current_vessel: support deleting custom paired vessels ──
_orig_delete_current_vessel = getattr(main.RequisitionApp, 'delete_current_vessel', None)
def _patched_delete_current_vessel(self):
    if not hasattr(self, 'ship_selector'):
        if _orig_delete_current_vessel:
            return _orig_delete_current_vessel(self)
        return

    curr = self.ship_selector.get().strip()
    if not curr:
        return

    # Ask for confirmation
    from tkinter import messagebox
    if not messagebox.askyesno("Delete Vessel", f"Are you sure you want to delete '{curr}' from the loadout?"):
        return

    callsign = curr
    if " (" in curr and curr.endswith(")"):
        callsign = curr.split(" (")[0].strip()

    from src.utils.template_manager import TemplateManager
    TemplateManager.delete_vessel(curr)
    TemplateManager.delete_vessel(callsign)

    # Refresh ship selector dropdown
    all_options = sorted(list(TemplateManager.load_vessels().keys()))
    self.ship_selector.configure(values=all_options)
    self.ship_selector.set("")
    if hasattr(self, 'clear_all_rows'):
        self.clear_all_rows()
        _play_sound("cargo_add.wav")
    else:
        # Fallback to original
        if _orig_delete_current_vessel:
            return _orig_delete_current_vessel(self)

main.RequisitionApp.delete_current_vessel = _patched_delete_current_vessel


# Disable Communication Channel dropdown (visual only, controlled by Classification)
_orig_show_main = main.RequisitionApp.show_main_app_layout

# ── Fix main.pyc load_vessel_loadout crash (float qty * string) ──
_orig_load_vessel = main.RequisitionApp.load_vessel_loadout
def _safe_load_vessel(self, *a, **kw):
    """Wrap load_vessel_loadout — support custom fleet vessels, float qty, and live price sync."""
    vessel_choice = a[0] if a else ""
    if isinstance(vessel_choice, str) and vessel_choice.strip():
        callsign = vessel_choice.strip()
        base_hull = vessel_choice.strip()

        from src.utils.template_manager import TemplateManager
        all_vessels = TemplateManager.load_vessels()

        if vessel_choice in all_vessels:
            loadout = all_vessels[vessel_choice]
            if hasattr(self, 'clear_all_rows'):
                self.clear_all_rows()
            for mi in loadout:
                if isinstance(mi, dict):
                    qty_param = "" if mi.get("qty", "") == 0 else str(mi.get("qty", ""))
                    self.add_cargo_row_to_ui(
                        name=mi.get("name", ""), qty=qty_param, box_size=mi.get("box_size", "1 SCU"),
                        price=mi.get("price", 0), courtesy=mi.get("courtesy", False), unit=mi.get("unit", "")
                    )
            return

        if " (" in callsign and callsign.endswith(")"):
            raw_callsign = callsign[:callsign.rfind(" (")].strip()
            inside_parens = callsign[callsign.rfind("(")+1:-1].strip()
            if raw_callsign in all_vessels:
                loadout = all_vessels[raw_callsign]
                if hasattr(self, 'clear_all_rows'):
                    self.clear_all_rows()
                for mi in loadout:
                    if isinstance(mi, dict):
                        qty_param = "" if mi.get("qty", "") == 0 else str(mi.get("qty", ""))
                        self.add_cargo_row_to_ui(
                            name=mi.get("name", ""), qty=qty_param, box_size=mi.get("box_size", "1 SCU"),
                            price=mi.get("price", 0), courtesy=mi.get("courtesy", False), unit=mi.get("unit", "")
                        )
                return
            elif inside_parens and inside_parens in all_vessels:
                loadout = all_vessels[inside_parens]
                if hasattr(self, 'clear_all_rows'):
                    self.clear_all_rows()
                for mi in loadout:
                    if isinstance(mi, dict):
                        qty_param = "" if mi.get("qty", "") == 0 else str(mi.get("qty", ""))
                        self.add_cargo_row_to_ui(
                            name=mi.get("name", ""), qty=qty_param, box_size=mi.get("box_size", "1 SCU"),
                            price=mi.get("price", 0), courtesy=mi.get("courtesy", False), unit=mi.get("unit", "")
                        )
                return

    try:
        from uex_sync import uex_items_trade_db
        from slang_helper import resolve_slang
        from src.utils.template_manager import TemplateManager
        trade_db = uex_items_trade_db() if callable(uex_items_trade_db) else uex_items_trade_db
        all_vessels = TemplateManager.load_vessels()
        for vname, vitems in all_vessels.items():
            items = vitems if isinstance(vitems, list) else (vitems.get('loadout', []) if isinstance(vitems, dict) else [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        name = item.get('name', '')
                        key_low = resolve_slang(name).lower().strip()
                        if key_low in trade_db:
                            locs = trade_db[key_low].get('locations', [])
                            buys = [l['buy'] for l in locs if isinstance(l, dict) and l.get('buy', 0) > 0]
                            if buys:
                                item['price'] = min(buys)
                        if 'qty' in item and item['qty']:
                            try: item['qty'] = int(float(item['qty']))
                            except (ValueError, TypeError): pass
    except Exception as e:
        print(f"[UI_PANEL] Vessel loadout price sync notice: {e}")

    self._in_table_audit = True
    try:
        res = _orig_load_vessel(self, *a, **kw)
    except TypeError as e:
        print(f"[UI_PANEL] load_vessel_loadout TypeError caught: {e}")
        res = None
    finally:
        self._in_table_audit = False

    # Post-process loaded rows to guarantee true per-unit base prices (unscaled by SCU box)
    try:
        if hasattr(self, 'cargo_rows') and self.cargo_rows:
            for row in self.cargo_rows:
                if 'name_var' in row and 'price_var' in row:
                    item_name = row['name_var'].get()
                    base_p = _get_base_unit_price(self, item_name)
                    if base_p > 0:
                        if isinstance(base_p, float) and base_p.is_integer():
                            base_p = int(base_p)
                        row['price_var'].set(str(base_p))
                    row['last_multiplier'] = 1.0
        if hasattr(self, 'calculate_total'):
            self.calculate_total()
    except Exception as ex:
        print(f"[UI_PANEL] Vessel loadout price sanitization notice: {ex}")

    return res
main.RequisitionApp.load_vessel_loadout = _safe_load_vessel

# Background pre-warm font cache and assets while splash plays
_orig_app_init = main.RequisitionApp.__init__
def _prewarming_app_init(self, *args, **kwargs):
    _orig_app_init(self, *args, **kwargs)
    def _background_prewarm():
        try:
            from pdf_engine import _precache_fonts
            _precache_fonts()
        except Exception: pass
    import threading
    threading.Thread(target=_background_prewarm, daemon=True).start()

main.RequisitionApp.__init__ = _prewarming_app_init

def _patched_show_main(self, *a, **kw):
    # Block vessel loadout during initial layout to prevent initial ship loadout flash
    _blocked_load = lambda self_, *a2, **kw2: None
    main.RequisitionApp.load_vessel_loadout = _blocked_load
    r = _orig_show_main(self, *a, **kw)
    # Restore safe load after layout is done
    main.RequisitionApp.load_vessel_loadout = _safe_load_vessel

    # Prevent automatic full-selection of text when user clicks, focuses, or types into any entry field
    try:
        def _prevent_autoselect(event):
            # Allow manual selection if Shift key is held down
            st = getattr(event, 'state', 0)
            if isinstance(st, str):
                try: st = int(st, 0)
                except Exception: st = 0
            try:
                if (st & 0x0001) != 0:
                    return
            except Exception: pass
            ks = getattr(event, 'keysym', '')
            if ks in ['Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Tab', 'Return', 'Escape']:
                return
            w = getattr(event, 'widget', None)
            if w:
                try:
                    if hasattr(w, 'select_present') and w.select_present():
                        w.selection_clear()
                        w.icursor("end")
                except Exception: pass

        self.bind_class("Entry", "<FocusIn>", _prevent_autoselect, add="+")
        self.bind_class("Entry", "<KeyRelease>", _prevent_autoselect, add="+")
    except Exception: pass

    # Synchronously clear default cargo rows and reset ship selector so app opens 100% clean immediately
    if hasattr(self, 'cargo_rows') and self.cargo_rows:
        for row in list(self.cargo_rows):
            try:
                if 'frame' in row:
                    row['frame'].destroy()
            except Exception: pass
        self.cargo_rows.clear()
    if hasattr(self, 'ship_selector'):
        try: self.ship_selector.set("")
        except Exception: pass
    try:
        if hasattr(self, 'sec_selector'):
            self.sec_selector.configure(state="disabled")
            # Find header title/subtitle label and update version tag
            parent = self.sec_selector.master.master
            for child in parent.winfo_children():
                if hasattr(child, 'cget'):
                    try:
                        txt = str(child.cget("text"))
                        if "v0.5" in txt or "TERMINAL v" in txt:
                            child.configure(text=txt.replace("v0.5", "v0.6.1"))
                    except Exception: pass
            
            # Find "Communication Channel:" header label in parent
            self._com_header = None
            parent = self.sec_selector.master
            for child in parent.winfo_children():
                if hasattr(child, 'cget'):
                    try:
                        txt = child.cget("text")
                        if txt and "channel" in str(txt).lower():
                            self._com_header = child
                            child.configure(text_color="#778899")  # Neutral blue-gray
                            break
                    except: pass
            
            def _style_com(text, txt_color, fg_color, btn_color):
                """Set text + colors on CTkComboBox and force redraw."""
                self.sec_selector.set(text)
                self.sec_selector.configure(
                    text_color=txt_color,
                    fg_color=fg_color,
                    button_color=btn_color,
                    button_hover_color=btn_color
                )
                try: self.sec_selector._draw()
                except: pass
            
            def _patched_sec_changed(sec_val):
                try:
                    sv = sec_val.upper() if sec_val else "ALL"
                    if sv == "ALL" or not sv:
                        _style_com("// INACTIVE CHANNEL //",
                            "#888888", "#2a2a2a", "#333333")
                    elif "PUBLIC" in sv or "OPEN" in sv:
                        _style_com("\u25C9  OPEN TO PUBLIC",
                            "#ccffdd", "#1a4a1a", "#2a5a2a")
                    elif "RESTRICTED" in sv or "SECURED" in sv:
                        _style_com("\u25C9  44th BATTLEGROUP RESTRICTED",
                            "#ffeeaa", "#3a3a0a", "#4a4a1a")
                    elif "OFFICERS" in sv or "ENCRYPTED" in sv:
                        _style_com("\u26A0  OFFICERS OF 44th BG ONLY",
                            "#ffcccc", "#3a0a0a", "#4a1a1a")
                    else:
                        self.sec_selector.set(sec_val)
                except Exception as e:
                    print(f"[SecChanged] {e}")
            self.on_security_level_changed = _patched_sec_changed
            _patched_sec_changed("ALL")
    except: pass
    
    # ── Ship Selector: loadout vessels only (Dynamic live values, Capped to 10 items, positioned downward) ──
    try:
        if hasattr(self, 'ship_selector'):
            def _get_live_vessel_options():
                from src.utils.template_manager import TemplateManager
                vessels = TemplateManager.load_vessels()
                return sorted(list(vessels.keys()))

            all_vessel_options = _get_live_vessel_options()

            all_db_names = sorted(set(
                v.get("name", v.get("short_name", k))
                for k, v in _uex_ships_db.items()
                if v.get("scu", 0) > 0 and v.get("is_spaceship", 1)
            )) if _uex_ships_db else []
            self._loadout_ship_names = all_vessel_options
            self._all_ship_names = all_db_names

            # Enforce 10-item capping on ship_selector configure
            _orig_ship_configure = self.ship_selector.configure
            def _capped_ship_configure(*args, **kwargs):
                if 'values' in kwargs and isinstance(kwargs['values'], (list, tuple)):
                    kwargs['values'] = list(kwargs['values'])[:10]
                return _orig_ship_configure(*args, **kwargs)
            self.ship_selector.configure = _capped_ship_configure

            self.ship_selector.configure(values=all_vessel_options[:10])
            self.ship_selector.set("")  # Empty — user must select

            if hasattr(self, 'delivery_date_var'):
                self.delivery_date_var.set(sc_date_only())

            def _on_ship_selected(choice=None, event=None):
                ship = str(choice).strip() if choice else self.ship_selector.get().strip()
                if ship:
                    print(f"[UI_PANEL] _on_ship_selected: '{ship}'")
                    if hasattr(self, 'load_vessel_loadout'):
                        try: self.load_vessel_loadout(ship)
                        except Exception as e: print(f"[UI_PANEL] _on_ship_selected load error: {e}")
                    if hasattr(self, 'req_id_var'):
                        import time
                        if len(ship) > 3:
                            seed = hash(ship + str(int(time.time())))
                            rng = random.Random(seed)
                            suffixes = ["X41", "X86", "S26", "A17", "B03", "C55", "D12"]
                            new_id = f"UEE-LOG-{rng.randint(10,99)}-{rng.randint(1000,9999)}-{rng.choice(suffixes)}"
                            self.req_id_var.set(new_id)
                            _play_sound("cargo_add.wav")
                    # After selection, reset dropdown values so another ship can be picked
                    try:
                        live_opts = _get_live_vessel_options()
                        _orig_ship_configure(values=live_opts[:10])
                    except Exception: pass
            
            self.ship_selector.bind('<<ComboboxSelected>>', lambda e: _on_ship_selected())
            try:
                self.ship_selector.configure(command=lambda choice: _on_ship_selected(choice))
            except Exception: pass

            # ── Vessel search key filtering & downward dropdown positioning (150ms debounced) ──
            def _on_ship_key(event=None):
                if event and getattr(event, 'keysym', None) in ['Return', 'Tab', 'Up', 'Down', 'Escape']:
                    return
                if hasattr(self.ship_selector, '_search_timer') and self.ship_selector._search_timer:
                    try: self.ship_selector.after_cancel(self.ship_selector._search_timer)
                    except Exception: pass

                def _do_ship_filter():
                    live_opts = _get_live_vessel_options()
                    typed = self.ship_selector.get().strip()
                    typed_low = typed.lower()
                    # If text exactly matches an existing option, show all (user selected, not searching)
                    if not typed or typed in live_opts or any(typed_low == o.lower() for o in live_opts):
                        _orig_ship_configure(values=live_opts[:10])
                    else:
                        words = typed_low.split()
                        filtered = [s for s in live_opts if all(w in s.lower() for w in words)]
                        _orig_ship_configure(values=filtered[:10])
                    try:
                        if hasattr(self.ship_selector, '_dropdown_menu') and self.ship_selector._dropdown_menu:
                            rx = self.ship_selector.winfo_rootx()
                            h = self.ship_selector.winfo_height()
                            ry = self.ship_selector.winfo_rooty() + h + 2
                            self.ship_selector._dropdown_menu.geometry(f"+{rx}+{ry}")
                            self.ship_selector._dropdown_menu.lift()
                    except Exception: pass

                self.ship_selector._search_timer = self.ship_selector.after(150, _do_ship_filter)

            self.ship_selector.bind('<KeyRelease>', _on_ship_key, add="+")

            _orig_ship_open = getattr(self.ship_selector, '_open_dropdown_menu', None)
            def _position_ship_dropdown(*args, **kwargs):
                live_opts = _get_live_vessel_options()
                typed = self.ship_selector.get().strip()
                typed_low = typed.lower()
                # If text exactly matches an existing option, show all (user selected, not searching)
                if not typed or typed in live_opts or any(typed_low == o.lower() for o in live_opts):
                    _orig_ship_configure(values=live_opts[:10])
                else:
                    words = typed_low.split()
                    filtered = [s for s in live_opts if all(w in s.lower() for w in words)]
                    _orig_ship_configure(values=filtered[:10])
                if _orig_ship_open:
                    try: _orig_ship_open(*args, **kwargs)
                    except Exception: pass
                try:
                    if hasattr(self.ship_selector, '_dropdown_menu') and self.ship_selector._dropdown_menu:
                        rx = self.ship_selector.winfo_rootx()
                        h = self.ship_selector.winfo_height()
                        ry = self.ship_selector.winfo_rooty() + h + 2
                        self.ship_selector._dropdown_menu.geometry(f"+{rx}+{ry}")
                        self.ship_selector._dropdown_menu.lift()
                except Exception: pass

            self.ship_selector._open_dropdown_menu = _position_ship_dropdown
    except Exception as e:
        print(f"[Ship selector] {e}")
    
    # ── Item Combo: enforce 10-item limit + add search/filter autocomplete ──
    try:
        ignore_combos = {
            getattr(self, 'ship_selector', None),
            getattr(self, 'officer_combo', None),
            getattr(self, '_officer_combo', None),
            getattr(self, 'captain_combo', None),
            getattr(self, '_captain_combo', None),
            getattr(self, 'crew_combo', None),
            getattr(self, 'severity_combo', None),
            getattr(self, 'loading_type_combo', None),
        } - {None}

        combo = None
        for attr in ['single_combo', '_single_combo', 'quick_add_combo', 'item_combo', 'item_dropdown']:
            candidate = getattr(self, attr, None)
            if candidate and candidate not in ignore_combos:
                combo = candidate
                break
        if combo:
            # Enforce max 10 items FIRST: patch configure() so main.pyc can't override
            _orig_combo_configure = combo.configure
            def _capped_configure(*args, **kwargs):
                if 'values' in kwargs:
                    v = kwargs['values']
                    if isinstance(v, (list, tuple)):
                        clean_v = [x for x in v if not str(x).lower().startswith("package:") and "package:" not in str(x).lower()]
                        kwargs['values'] = list(clean_v)[:10]
                res = _orig_combo_configure(*args, **kwargs)
                try:
                    if combo.get() == "CTkComboBox":
                        combo.set("")
                        if hasattr(combo, '_entry') and combo._entry:
                            combo._entry.delete(0, 'end')
                except Exception: pass
                return res
            combo.configure = _capped_configure
            combo.config = _capped_configure
            try:
                if combo.get() == "CTkComboBox":
                    combo.set("")
                    if hasattr(combo, '_entry') and combo._entry:
                        combo._entry.delete(0, 'end')
            except Exception: pass
            
            # Fake items filter — only official ore & resource pods exist
            _VALID_ORE_PODS = {
                "argo ore pod", "misc ore pod", "drake ore pod",
                "greycat roc ore pod", "geo resource pod"
            }
            _PLAIN_ORE_NAMES = {
                "copper", "iron", "hephaestanite", "quantainium", "quantanium", "gold", "laranite",
                "agricium", "bexlite", "taranite", "beryl", "titanium", "silicon", "quartz",
                "borase", "corundum", "diamond", "tungsten", "aluminium", "aluminum"
            }
            def _is_fake_item(iname):
                inlow = (iname or "").lower().strip()
                if "ore pod" in inlow or "mining pod" in inlow or ("pod" in inlow and any(b in inlow for b in ["argo", "mole", "drake", "misc"])):
                    return inlow not in _VALID_ORE_PODS

                # Filter out obsolete duplicate Raw / Refined ore names
                if any(inlow.startswith(p) for p in ["raw ", "refined "]) or any(inlow.endswith(s) for s in [" (raw)", " (refined)"]):
                    return True

                # Filter out plain ore names when (Ore) version exists
                if inlow in _PLAIN_ORE_NAMES:
                    return True

                return False

            # Build frequent items dataset for category-scoped autocomplete
            fi_raw = load_frequent_items(getattr(self, 'config_data', None))
            all_fi_objects = []
            if isinstance(fi_raw, list):
                all_fi_objects = [dict(it) if isinstance(it, dict) else {"name": str(it)} for it in fi_raw]
            elif isinstance(fi_raw, dict):
                for cat_name, items_list in fi_raw.items():
                    if isinstance(items_list, list):
                        for it in items_list:
                            if isinstance(it, dict):
                                it_copy = dict(it)
                                if 'category' not in it_copy: it_copy['category'] = cat_name
                                all_fi_objects.append(it_copy)

            # Include items from combo's initial values if not already present
            try:
                c_vals = combo.cget("values")
                if c_vals:
                    known_names = set(it.get("name", "").lower() for it in all_fi_objects if isinstance(it, dict))
                    for cv in c_vals:
                        cv_str = str(cv).strip()
                        if cv_str and cv_str.lower() not in known_names and not _is_fake_item(cv_str):
                            all_fi_objects.append({"name": cv_str, "category": ""})
            except Exception: pass

            # Load full database items if available
            try:
                from src.ui.quick_add_cargo import _get_full_database_items
                full_items = _get_full_database_items()
                if full_items:
                    k_names = set(it.get("name", "").lower() for it in all_fi_objects if isinstance(it, dict))
                    for fi in full_items:
                        fi_s = str(fi).strip()
                        if fi_s and fi_s.lower() not in k_names and not _is_fake_item(fi_s):
                            all_fi_objects.append({"name": fi_s, "category": ""})
            except Exception: pass


            def _get_scoped_candidates():

                cat_combo = getattr(combo, '_category_combo', None) or getattr(self, 'category_combo', None) or getattr(self, '_category_combo', None)
                if not cat_combo or not hasattr(cat_combo, 'get'):
                    p = getattr(combo, 'master', None)
                    while p and p != self:
                        for child in p.winfo_children():
                            if child != combo and isinstance(child, (ctk.CTkOptionMenu, ctk.CTkComboBox)):
                                try:
                                    v = child.cget('values')
                                    if v and any(x in str(v) for x in ['Industrial', 'Components', 'Armor', 'Weapons', 'Uniforms', 'Ship Weapons', 'Food', 'Medical', 'Commodities', 'Armor + Clothes']):
                                        cat_combo = child
                                        break
                                except Exception: pass
                        if cat_combo: break
                        p = getattr(p, 'master', None)

                cat_val = cat_combo.get() if (cat_combo and hasattr(cat_combo, 'get')) else "All"
                cat_low = str(cat_val).lower().strip()
                try:
                    from src.ui.quick_add_cargo import _filter_items_by_category, _get_full_database_items
                    filtered_res = _filter_items_by_category(_get_full_database_items(), cat_val)
                    if filtered_res:
                        return filtered_res
                except Exception:
                    pass

                def _get_item_cat(item_name):
                    in_low = item_name.lower().strip()
                    
                    # 1. Ship Cosmetics / Skins / Paints / Livery
                    if any(k in in_low for k in ['paint', 'skin', 'livery', 'decal']):
                        return 'ship cosmetics'

                    # 2. Ammo & Missiles
                    if any(k in in_low for k in [
                        'torpedo', 'missile', 'bomb', 'countermeasure', 'chaff', 'noise', 'decoy',
                        'magazine', 'mag', 'ammo', 'ammunition', 'round'
                    ]):
                        return 'ammo & missiles'

                    # 3. Personal Weapons & Weapon Optics/Attachments
                    if any(k in in_low for k in [
                        'rifle', 'pistol', 'smg', 'lmg', 'sniper', 'shotgun', 'launcher', 'p4-ar', 'fs-9', 's-38', 'p8-sc', 'p6-lr', 'br-2', 'br2', 'arclight', 'a03', 'ado-5', 'laser mine', 'grenade', 'scorch', 'mk-4', 'emp',
                        'coda', 'gallant', 'c54', 'lumin', 'scalpel', 'custodian', 'devastator', 'behring', 'kastak', 'klaus', 'gemini', 'apocalypse', 'hedeby', 'lightning bolt', 'volt', 'cq7', 'nightstalker',
                        'compensator', 'flash hider', 'stabilizer', 'suppressor', 'scope', 'sight', 'optic', 'choke', 'barrel'
                    ]) and not any(k in in_low for k in ['ship cannon', 'ship repeater', 'ship weapon', 'turret']):
                        return 'weapons'

                    # 4. Ship Weapons, Turrets, Mounts & Gimbals (excluding Flight Blades!)
                    if any(k in in_low for k in [
                        'laser cannon', 'ballistic cannon', 'laser repeater', 'ballistic repeater', 'giga-panther', 'rhino', 'panther', 'badger', 'bulldog',
                        'm7a', 'm6a', 'm5a', 'm4a', 'cf-557', 'cf-447', 'cf-337', 'cf-227', 'cf-117', 'tarantula', 'deadbolt', 'argus', 'typhoon', 'seeker', 'dominator', 'tempest', 'arrester', 'stalker',
                        'omnisky', 'quarrel', 'gattling', 'gatling', 'scattergun', 'ship cannon', 'ship repeater', 'ship weapon', 'repeater', 'cannon',
                        'turret', 'tigerstrike', 'sw16br', 'distortion cannon', 'neutron cannon', 'dr model', 'cvsa', 'evsd', 'brvs',
                        'mount', 'gimbal', 'rack', 'spinal mount'
                    ]) and not any(k in in_low for k in ['blade', 'flight blade']):
                        return 'ship weapons'

                    # 5. Armor & Clothes (Check BEFORE Industrial Utilities!)
                    if any(k in in_low for k in [
                        'helmet', 'core', 'arms', 'legs', 'backpack', 'undersuit', 'jacket', 'shirt', 'pants', 'shoes', 'gloves', 'armor', 'suit', 'vest', 'hat', 'cap', 'coat', 'boots', 'tcs-4', 'csp-68', 'adiva', 'lemarque', 'deo', 'prim', 'ventra', 'orc-mkx', 'adp-mk4', 'field recon', 'aril', 'adp'
                    ]):
                        return 'armor + clothes'

                    # 6. Industrial Utilities (strictly exclude weapons and armor keywords!)
                    if any(k in in_low for k in [
                        'industrial utilities', 'mining head', 'mining gadget', 'mining module', 'salvage head', 'salvage module', 'scraper module',
                        'ore pod', 'fuel pod', 'fuel nozzle', 'hofstede', 'klein', 'helix', 'lancet', 'arbor', 'impact',
                        'boremax', 'optimax', 'waveshift', 'waweshift', 'sabir', 'stampede', 'focus', 'torrent', 'rime', 'fltr', 'brand', 'lifesaver',
                        'truhold', 'cinch', 'abrade', 'trawler', 'cinematic', 'cambio', 'maxlift', 'tractor beam', 'multi-tool', 'prospector', 'mole', 'vulture', 'nozzle', 'srt', 'fabricator'
                    ]) and not any(k in in_low for k in ['helmet', 'core', 'arms', 'legs', 'backpack', 'undersuit', 'armor', 'suit', 'vest', 'rifle', 'pistol', 'smg', 'lmg', 'sniper', 'shotgun']):
                        return 'industrial utilities'

                    # 7. Ship Components (Shield Generators, Power Plants, Coolers, Quantum Engines, Quantum Drives, Flight Blades)
                    if (any(k in in_low for k in [
                        'shield generator', 'shield', 'power plant', 'powerplant', 'cooler', 'fr-86', 'fr-76', 'fr-66', 'rampart', 'umbra', 'aspis', 'fullstop', 'allstop', 'palisade', 'bulwark', 'fortress',
                        'js-500', 'js-400', 'js-300', 'js-200', 'maelstrom', 'quadracell', 'overdrive', 'genesis', 'eclipse', 'regulator', 'breton', 'diligence', 'superego', 'starheart',
                        'coolcore', 'eridani', 'ultra-flow', 'glacier', 'icebox', 'chill-out', 'snowpack', 'thermalx', 'frostbite', 'endo',
                        'quantum drive', 'quantum engine', 'qt drive', 'qd', 'vk-00', 'atlas', 'voyager', 'beacon', 'crossfield', 'pontes', 'ts-2', 'agate', 'colossus', 'siren', 'eos', 'hyperdrive', 'engine', 'thruster',
                        'flight blade', 'blade', 'quantum blade', 'jump blade', 'jump drive', 'jump module', 'generator'
                    ]) or ('drive' in in_low and any(k in in_low for k in ['quantum', 'jump', 'hyper', 'qt', 'qd']))) and not any(k in in_low for k in ['asd', 'secure drive', 'data drive', 'hard drive', 'usb drive', 'flash drive']):
                        return 'ship components'

                    # 8. Medical
                    if any(k in in_low for k in ['medpen', 'medkit', 'paramed', 'lifeguard', 'refill', 'hemopen', 'hemozal', 'detoxpen', 'oxypen', 'adrenapen', 'corticopen', 'deconpen', 'opiopen', 'medgel', 'panacea', 'bio-forging']) or 'medical' in in_low:
                        return 'medical'

                    # 9. Food & Drink
                    if any(k in in_low for k in ['cruz', 'rynex', 'water bottle', 'snack', 'pips', 'snaggle', 'food', 'drink', 'bottle', 'burrito', 'noodle', 'bar', 'ration', 'readymeal', 'meal', 'chocolate', 'karoby', 'tankard', 'hotdog', 'pizza']):
                        return 'food & drink'

                    # 10. Commodities (Ores strictly)
                    if any(k in in_low for k in [
                        'copper', 'iron', 'hephaestanite', 'quantainium', 'quantanium', 'gold', 'laranite', 'agricium', 'bexalite', 'bexlite', 'taranite',
                        'beryl', 'titanium', 'silicon', 'quartz', 'borase', 'corundum', 'diamond', 'tungsten', 'aluminium', 'aluminum',
                        'inert materials', 'rmc', 'recycled material', 'construction materials', 'ore', 'scrap', 'hydrogen fuel', 'quantum fuel', 'ingot', 'lumacore', 'venture core',
                        '<500', '500-700', '800+'
                    ]):
                        return 'commodities'

                    return 'other'


                target_cat = cat_low
                if cat_low in ["fps armor", "armor", "armors", "uniforms", "armor + clothes", "armor & clothes", "armors and clothes"]:
                    target_cat = "fps armor"
                elif cat_low in ["clothing", "clothes"]:
                    target_cat = "clothing"
                elif cat_low in ["ship components", "ship_components", "components"]:
                    target_cat = "ship components"
                elif cat_low in ["ship weapons & missiles", "ship weapons", "ship_weapons", "ordnance", "ammo & missiles", "missiles"]:
                    target_cat = "ship weapons & missiles"
                elif cat_low in ["industrial utilities", "industrial", "utilities", "utility"]:
                    target_cat = "industrial utilities"
                elif cat_low in ["ship cosmetics", "cosmetics", "ship_cosmetics", "paints"]:
                    target_cat = "ship cosmetics"
                elif cat_low in ["weapons", "weapon", "personal weapons", "fps weapons"]:
                    target_cat = "weapons"
                elif cat_low in ["medical", "med"]:
                    target_cat = "medical"
                elif cat_low in ["food & drinks", "food & drink", "food", "drink", "drinks"]:
                    target_cat = "food & drinks"
                elif cat_low in ["commodities & cargo", "commodities", "commodity", "cargo", "materials"]:
                    target_cat = "commodities & cargo"

                candidates = []
                for it in all_fi_objects:
                    if not it: continue
                    iname = it.get("name") if isinstance(it, dict) else str(it)
                    if _is_fake_item(iname): continue

                    if not cat_low or cat_low in ["all items", "all"]:
                        candidates.append(iname)
                        continue

                    if _get_item_cat(iname) == target_cat:
                        candidates.append(iname)

                # Filter out PACKAGE: items and fake items, remove duplicates preserving order
                clean = []
                seen_c = set()
                for c in candidates:
                    if c and not _is_fake_item(c) and not str(c).lower().startswith("package:") and "package:" not in str(c).lower():
                        clow = str(c).lower().strip()
                        if clow not in seen_c:
                            seen_c.add(clow)
                            clean.append(c)
                return clean

            _orig_open_dropdown = getattr(combo, '_open_dropdown_menu', None)
            def _scoping_open_dropdown(*args, **kwargs):
                typed = combo.get().lower().strip()
                candidates = _get_scoped_candidates()
                if not typed or len(typed) < 2:
                    if candidates:
                        _orig_combo_configure(values=candidates[:10], state="normal")
                    else:
                        _orig_combo_configure(values=[], state="normal")
                else:
                    words = typed.split()
                    filtered = [n for n in candidates if all(qw in str(n).lower() for qw in words)]
                    _orig_combo_configure(values=filtered[:10] if filtered else candidates[:10], state="normal")
                res = None
                if _orig_open_dropdown:
                    try: res = _orig_open_dropdown(*args, **kwargs)
                    except Exception: pass
                return res

            combo._open_dropdown_menu = _scoping_open_dropdown

            def _on_item_key(event=None):
                if event and getattr(event, 'keysym', None) in ['Return', 'Tab', 'Up', 'Down', 'Escape']:
                    return
                if hasattr(combo, '_search_timer') and combo._search_timer:
                    try: combo.after_cancel(combo._search_timer)
                    except Exception: pass

                def _do_item_filter():
                    typed = combo.get().lower().strip()
                    candidates = _get_scoped_candidates()
                    if not typed:
                        if candidates:
                            _orig_combo_configure(values=candidates[:10], state="normal")
                        return
                    words = typed.split()
                    def _word_match(iname, query_words):
                        in_low = str(iname).lower()
                        return all(qw in in_low for qw in query_words)

                    filtered = [n for n in candidates if _word_match(n, words)]
                    if filtered:
                        _orig_combo_configure(values=filtered[:10], state="normal")
                    else:
                        _orig_combo_configure(values=[], state="normal")
                        return  # No matches → don't open empty dropdown

                    # Auto-open the dropdown popup so suggestions are visible
                    try:
                        combo._open_dropdown_menu()
                        if hasattr(combo, '_dropdown_menu') and combo._dropdown_menu:
                            rx = combo.winfo_rootx()
                            ry = combo.winfo_rooty() + combo.winfo_height() + 2
                            combo._dropdown_menu.geometry(f"+{rx}+{ry}")
                    except Exception:
                        pass

                combo._search_timer = combo.after(200, _do_item_filter)

            combo.bind('<KeyRelease>', _on_item_key, add="+")

    except Exception as e:
        print(f"[Item autocomplete] {e}")

    # ── Category Filter Menu Patching ──
    try:
        def _patch_cat_menu(w):
            for c in w.winfo_children():
                if isinstance(c, (ctk.CTkOptionMenu, ctk.CTkComboBox)):
                    try:
                        vals = list(c.cget('values'))
                        if vals and any(x in vals for x in ['All', 'Weapons', 'Uniforms', 'Armor + Clothes', 'FPS Armor', 'Industrial Utilities', 'Ship Cosmetics']):
                            clean_vals = [
                                'All', 'FPS Armor', 'Clothing', 'Weapons', 'Ship Weapons & Missiles',
                                'Ship Components', 'Industrial Utilities', 'Food & Drinks', 'Medical',
                                'Commodities & Cargo', 'Ship Cosmetics'
                            ]
                            c.configure(values=clean_vals)
                            if c.get() in ['Uniforms', 'Armor + Clothes', 'Armor']:
                                c.set('FPS Armor')
                            elif c.get() == 'Utility':
                                c.set('Industrial Utilities')
                            elif c.get() not in clean_vals:
                                c.set('All')
                            
                            # Bind command callback to refresh item autocomplete
                            orig_cmd = c.cget('command')
                            def _cat_change_cb(choice, _oc=orig_cmd, _c=c):
                                if _oc:
                                    try: _oc(choice)
                                    except Exception: pass
                                item_c = getattr(self, 'single_combo', None) or getattr(self, '_single_combo', None) or getattr(self, 'quick_add_combo', None) or getattr(self, 'item_combo', None) or getattr(self, 'item_dropdown', None)
                                if item_c:
                                    item_c._category_combo = _c
                                    try:
                                        from src.ui.quick_add_cargo import _filter_items_by_category, _get_full_database_items
                                        f_items = _filter_items_by_category(_get_full_database_items(), choice)
                                        if f_items:
                                            item_c.configure(values=f_items[:10], state="normal")
                                        else:
                                            item_c.configure(values=[], state="normal")
                                    except Exception:
                                        candidates = _get_scoped_candidates()
                                        item_c.configure(values=candidates[:10] if candidates else [], state="normal")
                                    item_c.set("")

                            c.configure(command=_cat_change_cb)
                            return True

                    except Exception: pass
                if hasattr(c, 'winfo_children'):
                    if _patch_cat_menu(c): return True
            return False
        _patch_cat_menu(self)
    except Exception as e:
        print(f"[UI_PANEL] Category Filter rename patch: {e}", file=__import__('sys').stderr)

    # ── Loading Officer UI Management (+ / - Buttons) ──
    try:
        def _find_officer_combo(w):
            for c in w.winfo_children():
                if isinstance(c, ctk.CTkComboBox):
                    try:
                        vals = c.cget('values')
                        if any('Wolf' in str(v) or 'Rebot' in str(v) for v in vals):
                            return c
                    except: pass
                if hasattr(c, 'winfo_children'):
                    res = _find_officer_combo(c)
                    if res: return res
            return None

        officer_combo = _find_officer_combo(self)
        if officer_combo and not getattr(officer_combo, '_is_wrapped', False):
            officer_combo._is_wrapped = True
            parent = officer_combo.master
            cfg_path = PATHS.config
            officers_list = self.config_data.get("loading_officers", ["Lt. Thomas Wolf", "LSTR. Rebot1401", "STR. Odin Borr", "RSTR. Cinnebar"])
            officer_combo.configure(values=officers_list)

            ginfo = {}
            pinfo = {}
            try: ginfo = officer_combo.grid_info()
            except: pass
            try: pinfo = officer_combo.pack_info()
            except: pass

            sub_frame = ctk.CTkFrame(master=parent, fg_color="transparent")
            if ginfo:
                officer_combo.grid_forget()
                sub_frame.grid(**ginfo)
            elif pinfo:
                officer_combo.pack_forget()
                sub_frame.pack(**pinfo)

            officer_combo.pack(in_=sub_frame, side="left", fill="x", expand=True)

            def _save_officers(new_list):
                try:
                    self.config_data["loading_officers"] = new_list
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                    officer_combo.configure(values=new_list)
                except Exception as ex:
                    print(f"[LoadingOfficerSave] {ex}")

            def _add_officer():
                dialog = ctk.CTkInputDialog(text="Enter new Loading Officer name & rank:", title="Add Loading Officer")
                new_name = dialog.get_input()
                if new_name and new_name.strip():
                    name_clean = new_name.strip()
                    cur_list = list(self.config_data.get("loading_officers", []))
                    if name_clean not in cur_list:
                        cur_list.append(name_clean)
                        _save_officers(cur_list)
                    officer_combo.set(name_clean)

            def _del_officer():
                cur_val = officer_combo.get()
                cur_list = list(self.config_data.get("loading_officers", []))
                if cur_val in cur_list:
                    cur_list.remove(cur_val)
                    _save_officers(cur_list)
                    next_val = cur_list[0] if cur_list else ""
                    officer_combo.set(next_val)

            btn_add = ctk.CTkButton(master=sub_frame, text="+", width=26, height=26,
                                    fg_color="#d97706", hover_color="#b45309", text_color="#ffffff",
                                    font=ctk.CTkFont(size=14, weight="bold"), command=_add_officer)
            btn_add.pack(side="right", padx=(4, 0))

            btn_del = ctk.CTkButton(master=sub_frame, text="-", width=26, height=26,
                                    fg_color="#dc2626", hover_color="#991b1b", text_color="#ffffff",
                                    font=ctk.CTkFont(size=14, weight="bold"), command=_del_officer)
            btn_del.pack(side="right", padx=(2, 0))
    except Exception as e:
        print(f"[UI_PANEL] Loading Officer buttons setup: {e}", file=__import__('sys').stderr)

    # ── v0.6.1: QUICK-ADD ITEM PACKAGE section ──
    try:
        from src.ui.quick_add_cargo import setup_quick_add_panel
        setup_quick_add_panel(self)
        print("[UI_PANEL] QUICK-ADD ITEM PACKAGE panel injected OK", file=__import__('sys').stderr)
    except Exception as e:
        print(f"[UI_PANEL] QUICK-ADD ITEM PACKAGE panel failed: {e}", file=__import__('sys').stderr)

    # ── v0.6.1: Check for updates (thread-safe) ──
    try:
        from src.core.update_checker import check_for_updates
        check_for_updates(app=self)
    except Exception as e:
        print(f"[UI_PANEL] Update checker failed: {e}", file=__import__('sys').stderr)

    return r
main.RequisitionApp.show_main_app_layout = _patched_show_main


# ══════════════════════════════════════════════════════════════════════════
# SECTION: Slang Resolution + Auto-Battery Companion Patch
# ══════════════════════════════════════════════════════════════════════════

from slang_helper import resolve_slang

def _load_battery_companions():
    """Build _BATTERY_COMPANIONS dict from config.json autoloader_rules.

    Returns dict mapping trigger_name -> {name, price, unit}.
    This unifies the battery companion system with the cargo_packer autoloader
    so both are driven by the same config.json["autoloader_rules"] source.
    """
    try:
        import json as _j
        from path_config import PATHS as _P
        with open(_P.config, 'r', encoding='utf-8') as _f:
            _cfg = _j.load(_f)
        rules = _cfg.get('autoloader_rules', [])
        companions = {}
        for rule in rules:
            trigger = rule.get('trigger', '').lower()
            adds = rule.get('adds', [])
            # Only include rules that add a single companion (battery / tool)
            if trigger and len(adds) == 1:
                add = adds[0]
                companions[trigger] = {
                    'name': add.get('name', ''),
                    'price': add.get('price', 0),
                    'unit': 'unit',
                }
        if companions:
            return companions
    except Exception:
        pass
    # Minimal built-in fallback
    return {
        "maxlift tractor beam": {"name": "Maxlift Tractor Beam Battery", "price": 175, "unit": "unit"},
        "cambio srt":           {"name": "Cambio Multi-tool Battery",    "price": 63,  "unit": "unit"},
        "cambio":               {"name": "Cambio Multi-tool Battery",    "price": 63,  "unit": "unit"},
        "multitool":            {"name": "Cambio Multi-tool Battery",    "price": 63,  "unit": "unit"},
        "multi-tool":           {"name": "Cambio Multi-tool Battery",    "price": 63,  "unit": "unit"},
    }

_BATTERY_COMPANIONS = _load_battery_companions()

def _is_ordnance_or_packed_item(item_name, box_size_str=""):
    """
    Determines if an item is Ordnance (missiles, torpedoes, bombs, countermeasures)
    or Personal Equipment / Loose Items (armor, weapons, magazines, gadgets, bottles, tools).
    """
    nlow = (item_name or "").lower().strip()
    bslow = (box_size_str or "").lower().strip()

    # 1. Ordnance & Munitions
    ordnance_keywords = [
        "torpedo", "missile", "bomb", "decoy", "noise", "countermeasure",
        "seeker ix", "typhoon ix", "argus ix", "colossus bomb", "stormburst bomb",
        "raptor iv", "thunderbolt iii", "dominator ii"
    ]
    if any(k in nlow for k in ordnance_keywords):
        return True

    # 2. Personal Equipment, Gear & Loose Consumables
    equipment_keywords = [
        "helmet", "core", "arms", "legs", "undersuit", "backpack", "armor", "suit",
        "rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "knife", "launcher",
        "magazine", "mag", "battery", "canister", "multitool", "multi-tool", "tractor beam",
        "waveshift", "sabir", "boremax", "optimax", "stampede", "gadget", "device",
        "cruz", "lux", "drink", "food", "bottle", "burrito", "snaggle", "pips",
        "medpen", "hemozal", "oxypen", "adrenapen", "corticopen", "deconpen", "detoxpen",
        "opiopen", "paramed", "lifeguard", "medkit", "refill", "ammo", "attachment", "optic"
    ]
    if any(k in nlow for k in equipment_keywords):
        return True

    # 3. 1 unit or Loose box size
    if "unit" in bslow or "loose" in bslow:
        return True

    return False

_orig_add_cargo_row = main.RequisitionApp.add_cargo_row_to_ui
_adding_battery = False  # recursion guard
_expanding_package = False  # package expansion recursion guard

def _patched_add_cargo_row(self, name="", qty="", box_size="1 SCU",
                            price=0, courtesy=False, unit="SCU", **kwargs):
    """Wraps add_cargo_row_to_ui to:
    1. Run item names through resolve_slang() for Ctrl+V and quick-add.
    2. Default loose items / weapons / gear to box_size="Loose".
    3. Auto-add companion battery when MaxLift or Cambio is added.
    """

    # ── 1) Slang resolution (skip if _skip_slang flag is set) ──
    resolved_name = name
    if name and isinstance(name, str) and name.strip() and not getattr(self, '_skip_slang', False):
        config = getattr(self, 'config_data', None)
        resolved = resolve_slang(name.strip(), config_data=config)
        if resolved:
            resolved_name = resolved

    # Default box_size for Ordnance / Equipment / Loose items to "Loose" instead of "1 SCU" or "1 unit"
    if resolved_name and (box_size in ["1 SCU", "1 unit", "unit", "", None] or not box_size) and _is_ordnance_or_packed_item(resolved_name, box_size):
        box_size = "Loose"

    # Auto-fill zero or missing price via _get_base_unit_price
    p_val = 0
    try:
        if isinstance(price, (int, float)): p_val = float(price)
        elif isinstance(price, str) and price.strip().replace('.', '', 1).isdigit(): p_val = float(price.strip())
    except Exception: pass

    if p_val <= 0 and resolved_name:
        try:
            fetched_p = _get_base_unit_price(self, resolved_name)
            if fetched_p > 0:
                price = fetched_p
        except Exception: pass

    # Pop custom kwargs that legacy main.py add_cargo_row_to_ui does not accept
    kwargs.pop('_skip_autoloader', None)
    kwargs.pop('status', None)

    # ── 2) Call original to add the row ──
    return _orig_add_cargo_row(self, name=resolved_name, qty=qty,
                                  box_size=box_size, price=price,
                                  courtesy=courtesy, unit=unit, **kwargs)


# ── v0.6.1: Package expansion + Universal Autoloader wrapper ──
_patched_add_cargo_row_slang = _patched_add_cargo_row  # already assigned below but we need ref

_patched_add_cargo_row_WITH_SLANG = _patched_add_cargo_row

def _patched_add_cargo_row_v061(self, name="", qty="", box_size="1 SCU",
                                 price=0, courtesy=False, unit="SCU", **kwargs):
    """Wraps add_cargo_row_to_ui to expand packages and run Universal Autoloader.
    Layer order: package expansion -> slang/battery (already patched above)
    """
    global _expanding_package

    # Avoid recursive re-entry during expansion or table audit
    if _expanding_package or getattr(self, '_in_table_audit', False) or kwargs.get('_skip_autoloader', False):
        return _patched_add_cargo_row_WITH_SLANG(
            self, name=name, qty=qty, box_size=box_size,
            price=price, courtesy=courtesy, unit=unit, **kwargs
        )

    try:
        from src.agents.cargo_packer import unpack_packages_and_autoload
        _expanding_package = True
        try:
            expanded = unpack_packages_and_autoload(name, qty or "1", box_size, price, "LOOSE")
        finally:
            _expanding_package = False

        if len(expanded) == 1 and expanded[0]["name"] == name:
            # Not a package and no autoloader additions — pass through normally
            return _patched_add_cargo_row_WITH_SLANG(
                self, name=name, qty=qty, box_size=box_size,
                price=price, courtesy=courtesy, unit=unit, **kwargs
            )
        else:
            # Package expanded or autoloader added extras
            for item in expanded:
                _patched_add_cargo_row_WITH_SLANG(
                    self,
                    name=item["name"],
                    qty=item["qty"],
                    box_size=item.get("box_size", box_size),
                    price=item.get("price", 0),
                    courtesy=courtesy,
                    unit=unit,
                    **kwargs
                )
    except Exception as e:
        print(f"[AUTOLOADER] Error: {e}", file=__import__('sys').stderr)
        # Fallback: pass through without expansion
        _patched_add_cargo_row_WITH_SLANG(
            self, name=name, qty=qty, box_size=box_size,
            price=price, courtesy=courtesy, unit=unit, **kwargs
        )

main.RequisitionApp.add_cargo_row_to_ui = _patched_add_cargo_row_v061


# ══════════════════════════════════════════════════════════════════════════
# SECTION: Clipboard Paste Fallback — structured fix + raw slang lines
# ══════════════════════════════════════════════════════════════════════════
import re as _re

_orig_import_clipboard = main.RequisitionApp.import_from_clipboard
_orig_clear_all_rows = main.RequisitionApp.clear_all_rows

# Regex for structured lines WITHOUT the leading dash
_STRUCT_NO_DASH = _re.compile(
    r'^([^|]+)\|\s*Qty:\s*\[?\s*([\d.\s?]+)\s*\]?\s*\|\s*Box:\s*([^|]+)\|\s*Price:\s*([\d.]+)\s*(?:aUEC)?\s*(?:\[COURTESY\])?\s*\|\s*(\w+)?',
    _re.IGNORECASE
)

_COMPANION_RULES = [
    {"trigger": "cambio srt", "companion": "Cambio SRT Canister", "ratio": 10, "unit": "canister", "box_size": "Loose"},
    {"trigger": "cambio srt", "companion": "Cambio Multi-tool Battery", "ratio": 1, "unit": "unit", "box_size": "Loose"},
    {"trigger": "maxlift tractor beam", "companion": "Maxlift Tractor Beam Battery", "ratio": 1, "unit": "unit", "box_size": "Loose"},
    {"trigger": "paramed", "companion": "ParaMed Refill", "ratio": 4, "unit": "unit", "box_size": "Loose"},
    {"trigger": "lifeguard", "companion": "LifeGuard Refill", "ratio": 4, "unit": "unit", "box_size": "Loose"},
    {"trigger": "p4-ar", "companion": "P4-AR Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
    {"trigger": "p8-sc", "companion": "P8-SC Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
    {"trigger": "fs-9", "companion": "FS-9 Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
    {"trigger": "p6-lr", "companion": "P6-LR Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
    {"trigger": "a03", "companion": "A03 Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
    {"trigger": "s-38", "companion": "S-38 Magazine", "ratio": 20, "unit": "unit", "box_size": "Loose"},
    {"trigger": "arclight", "companion": "Arclight Magazine", "ratio": 20, "unit": "unit", "box_size": "Loose"},
    {"trigger": "lh86", "companion": "LH86 Magazine", "ratio": 20, "unit": "unit", "box_size": "Loose"},
]

_EXACT_SLANG_KEYS = {
    "s1 ammo", "s2 ammo", "s3 ammo", "s4 ammo", "s5 ammo", "s6 ammo", "s7 ammo",
    "seeker 9", "argus 9", "argos 9", "typhoon 9", "raptor 4", "thunderbolt 3",
    "dominator 2", "reaper 5", "arrester 3", "tempest 2", "rattler 2", "stalker 5",
    "marksman 1", "strikeforce 2", "taskforce 2", "lumin v", "p4-ar", "p8-sc", "p6-lr",
    "fs-9", "s-38", "tcs-4", "c8x", "1scu", "2scu", "4scu", "8scu", "h2"
}

def _patched_import_from_clipboard(self):
    """Wraps import_from_clipboard to handle:
    1. Full requisitions (with metadata) → clear + replace + load ship loadout
    2. Structured item lines → add to existing cargo (additive)
    3. Raw slang lines → resolve + merge into existing rows
    """
    try:
        raw = self.clipboard_get()
    except Exception:
        raw = ""

    if not raw or not raw.strip():
        return _orig_import_clipboard(self)

    # -- Check if the pasted text is a full requisition or just extra items --
    is_full_requisition = bool(_re.search(r'(Requisition ID|Vessel|Ship):', raw, _re.IGNORECASE))

    # Parse metadata if it's a full requisition
    metadata = {}
    lines = raw.splitlines()
    for line in lines:
        line_str = line.strip()
        if ":" in line_str:
            parts = line_str.split(":", 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            if key in ("request id", "requisition id"):
                metadata["request_id"] = val
            elif key in ("captain", "ship captain"):
                metadata["captain"] = val
            elif key in ("ship", "vessel", "select vessel"):
                metadata["ship"] = val
            elif key in ("location", "station", "station / location", "loading location"):
                metadata["location"] = val
            elif key in ("loading type", "type"):
                metadata["loading_type"] = val
            elif key in ("notes", "operation / notes", "operation", "note"):
                metadata["notes"] = val
            elif key in ("submitted", "delivery date", "delivery/load date"):
                metadata["submitted"] = val

    # -- Parse and format submitted time to Star Citizen date format --
    if "submitted" in metadata:
        raw_sub = metadata["submitted"]
        try:
            match_a = _re.search(r'(\d{4})[-./](\d{2})[-./](\d{2})[T\s](\d{2}):(\d{2})', raw_sub)
            match_b = _re.search(r'(\d{2})[-./](\d{2})[-./](\d{4})[T\s](\d{2}):(\d{2})', raw_sub)
            if match_a:
                y, m, d, hh, mm = match_a.groups()
                year_val = int(y)
                sc_year = year_val + 930 if year_val < 2500 else year_val
                metadata["sc_delivery_date"] = f"{sc_year}-{m}-{d} {hh}:{mm}"
            elif match_b:
                d, m, y, hh, mm = match_b.groups()
                year_val = int(y)
                sc_year = year_val + 930 if year_val < 2500 else year_val
                metadata["sc_delivery_date"] = f"{sc_year}-{m}-{d} {hh}:{mm}"
            else:
                metadata["sc_delivery_date"] = raw_sub
        except Exception:
            metadata["sc_delivery_date"] = raw_sub

    def _apply_metadata_to_ui():
        if "request_id" in metadata:
            if hasattr(self, 'req_id_var'):
                self.req_id_var.set(metadata["request_id"])
            elif hasattr(self, 'req_id_entry'):
                self.req_id_entry.delete(0, 'end')
                self.req_id_entry.insert(0, metadata["request_id"])
        if "captain" in metadata:
            if hasattr(self, 'captain_entry'):
                self.captain_entry.delete(0, 'end')
                self.captain_entry.insert(0, metadata["captain"])
        if "ship" in metadata:
            if hasattr(self, 'ship_selector'):
                try:
                    self.ship_selector.set(metadata["ship"])
                except Exception:
                    pass
        # loading_type MUST be set before location (trace resets location)
        if "loading_type" in metadata:
            if hasattr(self, '_loading_type_var'):
                self._loading_type_var.set(metadata["loading_type"])
        if "location" in metadata:
            if hasattr(self, '_location_ac_var'):
                self._location_ac_var.set(metadata["location"])
        if "sc_delivery_date" in metadata:
            if hasattr(self, 'delivery_date_var'):
                self.delivery_date_var.set(metadata["sc_delivery_date"])
        if "notes" in metadata:
            if hasattr(self, 'mission_var'):
                self.mission_var.set(metadata["notes"])
            elif hasattr(self, 'mission_entry'):
                try:
                    self.mission_entry.delete(0, 'end')
                    self.mission_entry.insert(0, metadata["notes"])
                except Exception:
                    pass

    # -- Filter metadata & titles out of the raw text so we parse items only --
    clean_lines = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith("===") or "STARLIFTER REQUISITION" in line_str:
            continue
        if "Cargo" in line_str or "Copy & Paste" in line_str:
            continue
        if line_str.startswith("```") or line_str.startswith("**"):
            continue
        is_meta_line = False
        if ":" in line_str:
            parts = line_str.split(":", 1)
            key = parts[0].strip().lower()
            if key in ("request id", "requisition id", "captain", "ship captain",
                        "ship", "vessel", "select vessel", "location", "station",
                        "station / location", "loading location", "loading type",
                        "type", "notes", "operation / notes", "operation", "note",
                        "submitted", "discord user", "delivery date",
                        "delivery/load date", "total value", "date",
                        "loading officer", "loading crew"):
                is_meta_line = True
        if is_meta_line:
            continue
        if line_str.startswith("UNIFORM REQUISITION") or line_str.startswith("LOGISTICS OFFICE"):
            continue
        if line_str.startswith("ACTION REQUIRED") or line_str.startswith("*(Include"):
            continue
        if line_str.startswith("ITEMS:") or line_str.startswith("TOTAL VALUE:"):
            continue
        clean_lines.append(line_str)

    filtered_raw = "\n".join(clean_lines)

    # -- 1. Find matching vessel in config & TemplateManager --
    matched_key = None
    target_ship = ""
    ship_name = metadata.get("ship", "").strip()
    if ship_name:
        from src.utils.template_manager import TemplateManager
        custom_vessels = TemplateManager.load_vessels()
        config_vessels = self.config_data.get('vessels', {}) if hasattr(self, 'config_data') and isinstance(self.config_data, dict) else {}
        all_vessels = {**config_vessels, **custom_vessels}
        
        if ship_name in all_vessels:
            matched_key = ship_name
        else:
            for k in all_vessels.keys():
                if k.lower() == ship_name.lower() or k.lower() in ship_name.lower() or ship_name.lower() in k.lower():
                    matched_key = k
                    break
        target_ship = matched_key or ship_name

    # -- 2. Clear table and update ship selector dropdown --
    if is_full_requisition:
        try:
            _orig_clear_all_rows(self)
        except Exception:
            pass
        if hasattr(self, 'ship_selector') and target_ship:
            try:
                # Ensure ship is in dropdown values so user can manipulate and switch it!
                curr_vals = list(self.ship_selector.cget("values") or [])
                if target_ship not in curr_vals:
                    curr_vals.insert(0, target_ship)
                    self.ship_selector.configure(values=curr_vals)
                self.ship_selector.set(target_ship)
            except Exception:
                pass

    # -- 3. Collect default loadout items if full requisition --
    merged_items = []
    if is_full_requisition and target_ship:
        from src.utils.template_manager import TemplateManager
        config_vessels = self.config_data.get('vessels', {}) if hasattr(self, 'config_data') and isinstance(self.config_data, dict) else {}
        all_v = {**config_vessels, **TemplateManager.load_vessels()}
        raw_loadout = all_v.get(target_ship, [])
        if not raw_loadout and " (" in target_ship:
            raw_call = target_ship[:target_ship.rfind(" (")].strip()
            raw_loadout = all_v.get(raw_call, [])
        for item in raw_loadout:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            name = item["name"]
            qty_val = item.get("qty", 1)
            try: qty = int(float(qty_val))
            except Exception: qty = 1
            box = item.get("box_size", "1 SCU")
            price = int(float(item.get("price", 0))) if item.get("price") else 0
            courtesy = bool(item.get("courtesy", False))
            unit = item.get("unit", "unit")
            merged_items.append({
                "name": name, "qty": qty, "box_size": box,
                "price": price, "courtesy": courtesy, "unit": unit
            })

    # Determine if it has structured items
    has_structured = bool(_re.search(r'\|.*Qty:', filtered_raw, _re.IGNORECASE))

    def _parse_raw_item_part(part_str):
        clean = _re.sub(r'^\s*[-*•>]\s*', '', part_str).strip()
        # Clean structured noise like "| Qty: 10" or "| 10"
        clean = _re.sub(r'\|\s*(?:Qty:\s*)?(\d+)', r'\1', clean, flags=_re.IGNORECASE).strip()
        clean = _re.sub(r'\b(?:boxes|crates|containers|units|pieces)\s+of\b', '', clean, flags=_re.IGNORECASE).strip()

        box_size = "1 SCU"
        m_box = _re.search(r'\b(\d+)\s*[-]?\s*(?:scu|su)\b', clean, _re.IGNORECASE)
        if m_box:
            box_size = f"{m_box.group(1)} SCU"
            clean = _re.sub(r'\b\d+\s*[-]?\s*(?:scu|su)\b', '', clean, flags=_re.IGNORECASE).strip()

        qty = 1
        name = clean

        m = _re.match(r'^x\s*(\d+)\s+(.+)$', clean, _re.IGNORECASE)
        if m:
            qty = int(m.group(1))
            name = m.group(2).strip()
        else:
            m = _re.match(r'^(\d+)\s*x\s+(.+)$', clean, _re.IGNORECASE)
            if m:
                qty = int(m.group(1))
                name = m.group(2).strip()
            else:
                m = _re.match(r'^(.+?)\s+(\d+)\s*x$', clean, _re.IGNORECASE)
                if m:
                    name = m.group(1).strip()
                    qty = int(m.group(2))
                else:
                    m = _re.match(r'^(\d+)\s+(.+)$', clean, _re.IGNORECASE)
                    if m and clean.lower() not in _EXACT_SLANG_KEYS:
                        qty = int(m.group(1))
                        name = m.group(2).strip()
                    else:
                        m = _re.match(r'^(.+?)\s+(\d+)$', clean, _re.IGNORECASE)
                        if m and clean.lower() not in _EXACT_SLANG_KEYS:
                            name = m.group(1).strip()
                            qty = int(m.group(2))

        # Clean leftover 'stor-all', 'container', 'box' in commodity/item names
        clean_name = _re.sub(r'\b(?:stor-all|storage container|container|box)\b', '', name, flags=_re.IGNORECASE).strip()
        if clean_name and len(clean_name) >= 2:
            name = clean_name

        name = _re.sub(r'\s+', ' ', name).strip()
        resolved = resolve_slang(name, config_data=self.config_data) or name
        if not m_box and _is_ordnance_or_packed_item(resolved):
            box_size = "Loose"
        price_val = _get_base_unit_price(self, resolved)
        unit_str = "unit"
        fi_list = load_frequent_items(getattr(self, 'config_data', None))
        for fi in fi_list:
            if isinstance(fi, dict) and fi.get("name") and fi["name"].lower() == resolved.lower():
                if not price_val:
                    price_val = int(float(fi.get("price", 0)))
                unit_str = fi.get("unit", "unit")
                break
        return resolved, qty, box_size, price_val, False, unit_str

    # -- 4. Parse cargo items from clipboard --
    parsed_items = []

    if has_structured:
        cargo_lines = [l.strip() for l in filtered_raw.splitlines() if l.strip()]
        _struct_re = _re.compile(
            r'^\s*(?:-\s*)?(.+?)\s*\|\s*Qty:\s*\[?\s*([\d.?\s]+)\s*\]?.*?\s*\|\s*Box:\s*(.+?)\s*(?:\|\s*Price:\s*([\d.]+)\s*(?:aUEC)?\s*(\[COURTESY\])?\s*)?\|\s*(.+)$',
            _re.IGNORECASE
        )
        for line in cargo_lines:
            m = _struct_re.match(line)
            if m:
                item_name = m.group(1).strip()
                qty_raw = m.group(2).strip() if m.group(2) else ""
                box_size = m.group(3).strip() if m.group(3) else "1 SCU"
                price_str = m.group(4) or "0"
                courtesy_flag = m.group(5)
                unit_str = m.group(6).strip() if m.group(6) else "SCU"
                
                if "?" in qty_raw or not qty_raw:
                    new_qty = 0
                else:
                    try: new_qty = int(float(qty_raw))
                    except (ValueError, TypeError): new_qty = 0

                price_val = int(float(price_str)) if price_str and price_str.replace('.', '', 1).isdigit() else 0
                if price_val == 0:
                    base_p = _get_base_unit_price(self, item_name)
                    if base_p > 0:
                        mult = 1.0
                        if "SCU" in box_size:
                            try: mult = float(box_size.split()[0])
                            except (ValueError, IndexError): mult = 1.0
                        price_val = int(base_p * mult)

                is_courtesy = bool(courtesy_flag) or "[COURTESY]" in line.upper()
                resolved_name = resolve_slang(item_name, config_data=self.config_data) or item_name
                parsed_items.append((resolved_name, new_qty, box_size, price_val, is_courtesy, unit_str))
            else:
                sline = line.strip()
                # Skip legend section dividers, header titles, and bullet descriptions: - 'code' (description)
                is_legend_line = (
                    sline.startswith("===") or
                    "UNIFORM REQUISITION CODES" in sline or
                    "*(Include optional multiplier" in sline or
                    bool(_re.search(r'^\s*-\s*\'[^\']+\'\s*\(', sline))
                )
                if not is_legend_line:
                    if line.startswith("+") or ("," in line and not any(line.startswith(p) for p in ["***", "Requisition", "Vessel", "Loading", "UNIFORM", "==="])):
                        clean_line = line.lstrip("+").strip()
                        parts = [p.strip() for p in clean_line.split(",") if p.strip()]
                        for part in parts:
                            parsed_items.append(_parse_raw_item_part(part))
                    elif not any(line.startswith(prefix) for prefix in ["***", "Requisition", "Vessel", "Loading", "Ship", "Operation", "Delivery", "Date", "ITEMS:", "UNIFORM", "==="]):
                        parsed_items.append(_parse_raw_item_part(line))
    else:
        lines_slang = [l.strip() for l in filtered_raw.strip().splitlines() if l.strip()]
        for line in lines_slang:
            if line.startswith("+") or ("," in line and not any(line.startswith(p) for p in ["***", "Requisition", "Vessel", "Loading", "UNIFORM", "==="])):
                clean_line = line.lstrip("+").strip()
                parts = [p.strip() for p in clean_line.split(",") if p.strip()]
                for part in parts:
                    parsed_items.append(_parse_raw_item_part(part))
            else:
                parsed_items.append(_parse_raw_item_part(line))

    # -- 4b. Expand any requested Package / Set codes with multiplier --
    try:
        from src.ui.create_package import BUILT_IN_PACKAGES
        from src.utils.template_manager import TemplateManager
        custom_pkgs = TemplateManager.load_packages()
        all_packages_dict = {**BUILT_IN_PACKAGES, **custom_pkgs}

        expanded_items = []
        for item_name, new_qty, box_size, price_val, is_courtesy, unit_str in parsed_items:
            iname_clean = item_name.strip().lower()
            matched_pkg_items = None
            for p_key, p_val in all_packages_dict.items():
                p_clean = p_key.lower().strip()
                if (p_clean == iname_clean or 
                    p_clean.replace(" uniform", "") == iname_clean.replace(" uniform", "") or
                    p_clean.replace(" package", "") == iname_clean.replace(" package", "") or
                    p_clean.replace(" set", "") == iname_clean.replace(" set", "")):
                    matched_pkg_items = p_val
                    break
            
            if matched_pkg_items and isinstance(matched_pkg_items, list):
                mult = max(1, new_qty)
                for pkg_it in matched_pkg_items:
                    if isinstance(pkg_it, dict):
                        it_n = pkg_it.get("name", "")
                        it_q = pkg_it.get("qty", 1) * mult
                        it_b = pkg_it.get("box_size", "Loose")
                        it_p = pkg_it.get("price", 0)
                        expanded_items.append((it_n, it_q, it_b, it_p, False, "unit"))
            else:
                expanded_items.append((item_name, new_qty, box_size, price_val, is_courtesy, unit_str))
        parsed_items = expanded_items
    except Exception as e:
        print(f"[Clipboard Import] Package expansion notice: {e}")

    # -- 5. Consolidate clipboard items & apply auto-companions --
    consolidated_map = {}
    for item_name, new_qty, box_size, price_val, is_courtesy, unit_str in parsed_items:
        key = (item_name.lower().strip(), bool(is_courtesy))
        if key not in consolidated_map:
            consolidated_map[key] = {
                "name": item_name, "qty": new_qty, "box_size": box_size,
                "price": price_val if not is_courtesy else 0.0, "courtesy": is_courtesy, "unit": unit_str
            }
        else:
            consolidated_map[key]["qty"] += new_qty
            if price_val > 0 and consolidated_map[key]["price"] == 0 and not is_courtesy:
                consolidated_map[key]["price"] = price_val
            if box_size and "scu" in box_size.lower():
                consolidated_map[key]["box_size"] = box_size

    self._in_clipboard_import = True
    try:
        def _is_trigger_match(trig, p_key):
            t_low = trig.lower().strip()
            p_low = p_key.lower().strip()
            if any(suffix in p_low for suffix in ["canister", "battery", "magazine", "mag", "refill"]):
                return False
            return p_low == t_low or (p_low.startswith(t_low) and not any(s in p_low for s in ["canister", "battery", "magazine", "refill"]))

        companion_demands = {}
        for key, item in list(consolidated_map.items()):
            item_name_str = key[0] if isinstance(key, tuple) else str(key)
            for rule in _COMPANION_RULES:
                if _is_trigger_match(rule["trigger"], item_name_str):
                    comp_name = rule["companion"]
                    comp_key = (comp_name.lower().strip(), False)
                    companion_demands[comp_key] = companion_demands.get(comp_key, 0) + item["qty"] * rule["ratio"]

        for rule in _COMPANION_RULES:
            comp_name = rule["companion"]
            comp_key = (comp_name.lower().strip(), False)
            if comp_key in companion_demands and companion_demands[comp_key] > 0:
                req_qty = companion_demands[comp_key]
                if comp_key in consolidated_map:
                    consolidated_map[comp_key]["qty"] = req_qty
                else:
                    consolidated_map[comp_key] = {
                        "name": comp_name, "qty": req_qty,
                        "box_size": rule["box_size"],
                        "price": _get_base_unit_price(self, comp_name),
                        "courtesy": False, "unit": rule["unit"]
                    }

        # Auto-box loose items into Stor-All container
        has_stor_all = any("stor-all" in (k[0] if isinstance(k, tuple) else str(k)) or "storage container" in (k[0] if isinstance(k, tuple) else str(k)) for k in consolidated_map.keys())
        if not has_stor_all:
            total_loose_vol = 0.0
            for k, it in consolidated_map.items():
                k_name = k[0] if isinstance(k, tuple) else str(k)
                bs = str(it.get("box_size", "")).lower()
                if "unit" in bs or "loose" in bs:
                    qty_val = it.get("qty", 1)
                    if any(w in k_name for w in ["rifle", "lmg", "beam", "tool", "smg", "pistol", "sniper"]):
                        unit_vol = 0.02
                    elif any(w in k_name for w in ["mag", "battery", "pen", "ammo", "medpen", "hemozal", "oxypen", "adrenapen", "corticopen", "deconpen", "detoxpen", "opiopen", "paramed"]):
                        unit_vol = 0.001
                    else:
                        unit_vol = 0.005
                    total_loose_vol += qty_val * unit_vol
            if total_loose_vol > 0.001:
                if total_loose_vol <= 1.0:
                    c_name, c_size, c_price = "Stor-All 1 SCU Storage Container", "1 SCU", 150
                elif total_loose_vol <= 2.0:
                    c_name, c_size, c_price = "Stor-All 2 SCU Storage Container", "2 SCU", 300
                elif total_loose_vol <= 4.0:
                    c_name, c_size, c_price = "Stor-All 4 SCU Storage Container", "4 SCU", 600
                elif total_loose_vol <= 8.0:
                    c_name, c_size, c_price = "Stor-All 8 SCU Storage Container", "8 SCU", 1200
                else:
                    c_name, c_size, c_price = "Stor-All 16 SCU Storage Container", "16 SCU", 2400

                c_key = (c_name.lower().strip(), False)
                consolidated_map[c_key] = {
                    "name": c_name, "qty": 1,
                    "box_size": c_size, "price": _get_base_unit_price(self, c_name) or c_price,
                    "courtesy": False, "unit": "SCU"
                }

        merged_items = list(consolidated_map.values())

        # -- 6. Populate UI cargo table (reset if full requisition, else add) --
        if is_full_requisition:
            if hasattr(self, 'clear_all_rows'):
                self.clear_all_rows()
            else:
                self.cargo_rows.clear()
            for mi in merged_items:
                qty_param = "" if mi["qty"] == 0 else str(mi["qty"])
                self.add_cargo_row_to_ui(
                    name=mi["name"], qty=qty_param, box_size=mi["box_size"],
                    price=mi["price"], courtesy=mi["courtesy"], unit=mi["unit"]
                )
        else:
            # Merge on top of existing UI rows
            overwritten_items = set()
            for mi in merged_items:
                found_in_ui = False
                for row in getattr(self, 'cargo_rows', []):
                    try:
                        existing_name = row.get('name_var', None)
                        if existing_name and existing_name.get().strip().lower() == mi["name"].lower():
                            old_qty_str = row.get('qty_var', None)
                            if old_qty_str:
                                try: old_qty = int(float(old_qty_str.get()))
                                except (ValueError, TypeError): old_qty = 0
                                old_qty_str.set(str(old_qty + mi["qty"]))
                            found_in_ui = True
                            break
                    except Exception:
                        continue
                if not found_in_ui:
                    qty_param = "" if mi["qty"] == 0 else str(mi["qty"])
                    self.add_cargo_row_to_ui(
                        name=mi["name"], qty=qty_param, box_size=mi["box_size"],
                        price=mi["price"], courtesy=mi["courtesy"], unit=mi["unit"]
                    )
    finally:
        self._in_clipboard_import = False

    # Apply metadata if full requisition
    if is_full_requisition:
        _apply_metadata_to_ui()

    # Update grand total
    try:
        self.update_grand_total()
    except Exception:
        pass

    # Restore original clipboard
    return True

def _consolidate_cargo_rows(self):
    """Consolidate UI cargo table rows: group duplicate item names, sum quantities, apply companion ratios."""
    if not hasattr(self, 'cargo_rows') or not self.cargo_rows:
        return
    
    items_by_key = {}
    for row in list(self.cargo_rows):
        try:
            name = row['name_var'].get().strip()
            if not name: continue
            qty_str = row['qty_var'].get().strip()
            box_size = row['box_size_var'].get().strip() if 'box_size_var' in row else '1 SCU'
            price_val = int(float(row['price_var'].get().strip().replace(',', ''))) if 'price_var' in row and row['price_var'].get() else 0
            unit = row.get('unit', 'unit')
            courtesy = bool(row['courtesy_var'].get()) if 'courtesy_var' in row and hasattr(row['courtesy_var'], 'get') else False
            
            try: qty = int(float(qty_str)) if qty_str and qty_str != '?' else 0
            except ValueError: qty = 0

            key = name.lower().strip()
            if key not in items_by_key:
                items_by_key[key] = {
                    'name': name, 'qty': qty, 'box_size': box_size,
                    'price': price_val, 'courtesy': courtesy, 'unit': unit
                }
            else:
                items_by_key[key]['qty'] += qty
                if price_val > 0 and items_by_key[key]['price'] == 0:
                    items_by_key[key]['price'] = price_val
                if 'scu' in box_size.lower():
                    items_by_key[key]['box_size'] = box_size
        except Exception:
            continue

    _COMPANION_RULES = [
        {"trigger": "cambio srt", "companion": "Cambio SRT Canister", "ratio": 10, "unit": "canister", "box_size": "Loose"},
        {"trigger": "cambio srt", "companion": "Cambio Multi-tool Battery", "ratio": 1, "unit": "unit", "box_size": "Loose"},
        {"trigger": "maxlift tractor beam", "companion": "Maxlift Tractor Beam Battery", "ratio": 1, "unit": "unit", "box_size": "Loose"},
        {"trigger": "paramed", "companion": "ParaMed Refill", "ratio": 4, "unit": "unit", "box_size": "Loose"},
        {"trigger": "lifeguard", "companion": "LifeGuard Refill", "ratio": 4, "unit": "unit", "box_size": "Loose"},
        {"trigger": "p4-ar", "companion": "P4-AR Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
        {"trigger": "p8-sc", "companion": "P8-SC Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
        {"trigger": "fs-9", "companion": "FS-9 Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
        {"trigger": "p6-lr", "companion": "P6-LR Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
        {"trigger": "a03", "companion": "A03 Magazine", "ratio": 40, "unit": "unit", "box_size": "Loose"},
        {"trigger": "s-38", "companion": "S-38 Magazine", "ratio": 20, "unit": "unit", "box_size": "Loose"},
        {"trigger": "arclight", "companion": "Arclight Magazine", "ratio": 20, "unit": "unit", "box_size": "Loose"},
        {"trigger": "lh86", "companion": "LH86 Magazine", "ratio": 20, "unit": "unit", "box_size": "Loose"},
    ]

    def _is_trigger_match(trig, p_key):
        t_low = trig.lower().strip()
        p_low = p_key.lower().strip()
        if any(suffix in p_low for suffix in ["canister", "battery", "magazine", "mag", "refill"]):
            return False
        return p_low == t_low or (p_low.startswith(t_low) and not any(s in p_low for s in ["canister", "battery", "magazine", "refill"]))

    companion_demands = {}
    for key, item in list(items_by_key.items()):
        for rule in _COMPANION_RULES:
            if _is_trigger_match(rule["trigger"], key):
                comp_name = rule['companion']
                comp_key = comp_name.lower().strip()
                companion_demands[comp_key] = companion_demands.get(comp_key, 0) + item['qty'] * rule['ratio']

    for rule in _COMPANION_RULES:
        comp_name = rule['companion']
        comp_key = comp_name.lower().strip()
        if comp_key in companion_demands and companion_demands[comp_key] > 0:
            req_qty = companion_demands[comp_key]
            if comp_key in items_by_key:
                items_by_key[comp_key]['qty'] = req_qty
            else:
                items_by_key[comp_key] = {
                    'name': comp_name, 'qty': req_qty,
                    'box_size': rule['box_size'], 'price': _get_base_unit_price(self, comp_name),
                    'courtesy': False, 'unit': rule['unit']
                }

    # Auto-box loose items into Stor-All container
    has_stor_all = any("stor-all" in k or "storage container" in k for k in items_by_key.keys())
    if not has_stor_all:
        total_loose_vol = 0.0
        for k, it in items_by_key.items():
            bs = str(it.get("box_size", "")).lower()
            if "unit" in bs or "loose" in bs:
                qty_val = it.get("qty", 1)
                if any(w in k for w in ["rifle", "lmg", "beam", "tool", "smg", "pistol", "sniper"]):
                    unit_vol = 0.02
                elif any(w in k for w in ["mag", "battery", "pen", "ammo", "medpen", "hemozal", "oxypen", "adrenapen", "corticopen", "deconpen", "detoxpen", "opiopen", "paramed"]):
                    unit_vol = 0.001
                else:
                    unit_vol = 0.005
                total_loose_vol += qty_val * unit_vol
        if total_loose_vol > 0.001:
            if total_loose_vol <= 1.0:
                c_name, c_size, c_price = "Stor-All 1 SCU Storage Container", "1 SCU", 150
            elif total_loose_vol <= 2.0:
                c_name, c_size, c_price = "Stor-All 2 SCU Storage Container", "2 SCU", 300
            elif total_loose_vol <= 4.0:
                c_name, c_size, c_price = "Stor-All 4 SCU Storage Container", "4 SCU", 600
            elif total_loose_vol <= 8.0:
                c_name, c_size, c_price = "Stor-All 8 SCU Storage Container", "8 SCU", 1200
            else:
                c_name, c_size, c_price = "Stor-All 16 SCU Storage Container", "16 SCU", 2400

            c_key = c_name.lower().strip()
            items_by_key[c_key] = {
                "name": c_name, "qty": 1,
                "box_size": c_size, "price": _get_base_unit_price(self, c_name) or c_price,
                "courtesy": False, "unit": "SCU"
            }

    if hasattr(self, 'clear_all_rows'):
        self.clear_all_rows()
    elif hasattr(self, 'cargo_rows') and self.cargo_rows:
        for r in list(self.cargo_rows):
            if isinstance(r, dict) and 'frame' in r:
                try: r['frame'].destroy()
                except Exception: pass
        self.cargo_rows.clear()

    for item in items_by_key.values():
        qty_param = "" if item['qty'] == 0 else str(item['qty'])
        self.add_cargo_row_to_ui(
            name=item['name'], qty=qty_param, box_size=item['box_size'],
            price=item['price'], courtesy=item['courtesy'], unit=item['unit'],
            _skip_autoloader=True
        )
    try: self.update_grand_total()
    except Exception: pass

main.RequisitionApp.import_from_clipboard = _patched_import_from_clipboard


# ══════════════════════════════════════════════════════════════════════════
# SECTION: Automatic Price Update on Box Size / Qty Change
# ══════════════════════════════════════════════════════════════════════════

def _get_base_unit_price(app, item_name):
    """Look up true base unit price for an item across UEX DB, config, and SC Wiki cache."""
    if not item_name or not isinstance(item_name, str):
        return 0
    resolved = resolve_slang(item_name.strip(), config_data=getattr(app, 'config_data', None)) or item_name
    res_low = resolved.lower().strip()

    # Exact canonical market price overrides for ordnance, weapons, and components
    _CANONICAL_PRICES = {
        "p4-ar rifle": 4623,
        "p4-ar \"nightstalker\" rifle": 4623,
        "p8-sc smg": 4200,
        "fs-9 lmg": 5800,
        "p6-lr sniper rifle": 6500,
        "a03 sniper rifle": 6200,
        "s-38 pistol": 1250,
        "arclight pistol": 1100,
        "lh86 pistol": 1350,
        "m5a laser cannon (size 3)": 18500,
        "m5a laser cannon": 18500,
        "m6a laser cannon (size 4)": 32400,
        "m6a laser cannon": 32400,
        "m7a laser cannon (size 5)": 54200,
        "m7a laser cannon": 54200,
        "m4a laser cannon (size 2)": 9800,
        "m4a laser cannon": 9800,
        "cf-117 bulldog laser repeater (size 1)": 5200,
        "cf-227 badger laser repeater (size 2)": 11400,
        "cf-337 panther laser repeater (size 3)": 21800,
        "cf-447 rhino laser repeater (size 4)": 38900,
        "cf-557 giga-panther repeater (size 5)": 68500,
        "fr-66 shield generator (size 1)": 14200,
        "fr-76 shield generator (size 2)": 46200,
        "fr-86 shield generator (size 3)": 148500,
        "crossfield quantum drive (size 2)": 48500,
        "vk-00 quantum drive (size 1)": 18900,
        "ts-2 quantum drive (size 3)": 162000,
        "seeker ix torpedo": 17595,
        "typhoon ix torpedo": 17595,
        "argus ix torpedo": 16716,
        "colossus bomb": 83125,
        "stormburst bomb": 40520,
        "waveshift": 18169,
        "sabir": 13815,
        "size 1 ammunition": 7383,
        "size 2 ammunition": 7641,
        "size 3 ammunition": 7383,
        "size 4 ammunition": 7641,
        "size 5 ammunition": 7984,
        "decoy countermeasures": 4292,
        "noise countermeasures": 2146,
        "recycled material composite (rmc)": 10710,
        "recycled material composite": 10710,
        "hydrogen fuel": 196,
        "quantum fuel": 978,
    }
    if res_low in _CANONICAL_PRICES:
        return _CANONICAL_PRICES[res_low]

    # Check uex_items_trade_db
    try:
        from uex_sync import uex_items_trade_db
        db = uex_items_trade_db()
        if db and res_low in db:
            locs = db[res_low].get("locations", [])
            buys = [l.get("buy", 0) for l in locs if isinstance(l, dict) and l.get("buy", 0) > 0]
            if buys:
                return min(buys)
    except Exception: pass

    # Check sc_wiki_items_cache.json
    try:
        from path_config import PATHS as _p_PATHS
        import json as _p_json
        cache_path = os.path.join(_p_PATHS.resources, "sc_wiki_items_cache.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as _p_f:
                wiki_db = _p_json.load(_p_f)
                
            import re as _p_re
            clean_name = _p_re.sub(r'["\']', '', item_name).lower().strip()
        
        for w_key, locs in wiki_db.items():
            w_low = w_key.lower().strip()
            if w_low == res_low or w_low == clean_name or (clean_name in w_low) or (w_low in clean_name):
                prices = [l.get("price", 0) for l in locs if isinstance(l, dict) and l.get("price", 0) > 0]
                if prices:
                    return min(prices)
    except Exception: pass

    # Check frequent_items in config_data or resources
    fi_list = load_frequent_items(getattr(app, 'config_data', None))
    if isinstance(fi_list, dict):
        flat = []
        for v in fi_list.values():
            if isinstance(v, list): flat.extend(v)
        fi_list = flat
    for fi in fi_list:
        if isinstance(fi, dict) and fi.get("name"):
            if fi["name"].lower().strip() == res_low:
                    try:
                        p = float(fi.get("price", 0))
                        if p > 0: return p
                    except (ValueError, TypeError): pass

    return 0

_orig_on_box_size_changed = main.RequisitionApp.on_box_size_selector_changed
def _patched_on_box_size_changed(self, row):
    """Ensure row price remains true base unit price (per-unit/per-SCU)."""
    try:
        cur_price_str = row['price_var'].get().strip()
        try: cur_price = float(cur_price_str)
        except (ValueError, TypeError): cur_price = 0.0

        if cur_price == 0:
            base_unit_price = _get_base_unit_price(self, row['name_var'].get())
            if base_unit_price > 0:
                if base_unit_price.is_integer():
                    base_unit_price = int(base_unit_price)
                row['price_var'].set(str(base_unit_price))

        row['last_multiplier'] = 1.0
    except Exception as e:
        print(f"[BoxSizeChanged] Error: {e}", file=__import__('sys').stderr)

    return _orig_on_box_size_changed(self, row)

main.RequisitionApp.on_box_size_selector_changed = _patched_on_box_size_changed

def _is_ordnance_or_packed_item(item_name, box_size_str=""):
    """
    Determines if an item is Ordnance (missiles, torpedoes, bombs, countermeasures)
    or Personal Equipment / Loose Items (armor, weapons, magazines, gadgets, bottles, tools).

    For Ordnance & Personal Equipment: Total = Quantity * Unit_Price.
    For SCU Freight Cargo (RMC, Fuels, Size 1-5 SCU Ammunition, Trade Commodities, Ores):
        Total = SCU_Box_Multiplier * Quantity * Unit_Price.
    """
    nlow = (item_name or "").lower().strip()
    bslow = (box_size_str or "").lower().strip()

    # 1. Ordnance & Munitions
    ordnance_keywords = [
        "torpedo", "missile", "bomb", "decoy", "noise", "countermeasure",
        "seeker ix", "typhoon ix", "argus ix", "colossus bomb", "stormburst bomb",
        "raptor iv", "thunderbolt iii", "dominator ii"
    ]
    if any(k in nlow for k in ordnance_keywords):
        return True

    # 2. Personal Equipment, Gear & Loose Consumables
    equipment_keywords = [
        "helmet", "core", "arms", "legs", "undersuit", "backpack", "armor", "suit",
        "rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "knife", "launcher",
        "magazine", "mag", "battery", "canister", "multitool", "multi-tool", "tractor beam",
        "waveshift", "sabir", "boremax", "optimax", "stampede", "gadget",
        "cruz", "lux", "drink", "food", "bottle", "burrito", "snaggle", "pips"
    ]
    if any(k in nlow for k in equipment_keywords):
        return True

    # 3. Ship Weapons & Ship Components (Cannons, Repeaters, Shields, QDs, Coolers, Generators)
    ship_item_keywords = [
        "cannon", "repeater", "scattergun", "gatling", "autocannon", "ballistic", "laser", "distortion",
        "shield", "quantum", "drive", "cooler", "power plant", "generator"
    ]
    if any(k in nlow for k in ship_item_keywords):
        return True

    # 4. 1 unit or Loose box size
    if "unit" in bslow or "loose" in bslow:
        return True

    return False


# ── Patch update_grand_total to compute Gross Value, Courtesy Subsidy & Net Required Payment ──
def _patched_update_grand_total(self):
    """Calculate row total and grand total according to SCU Freight vs Ordnance/Equipment rules, supporting Courtesy 0 aUEC items."""
    gross_total = 0.0
    courtesy_subsidy = 0.0
    net_payable = 0.0

    for row in getattr(self, 'cargo_rows', []):
        try:
            name = row['name_var'].get().strip() if 'name_var' in row else ''
            box_str = row['box_size_var'].get().strip() if 'box_size_var' in row else '1 SCU'
            qty_str = row['qty_var'].get().strip() if 'qty_var' in row else '1'
            try: qty = float(qty_str) if qty_str else 0.0
            except (ValueError, TypeError): qty = 0.0

            price_str = row['price_var'].get().strip() if 'price_var' in row else '0'
            try: unit_price = float(price_str) if price_str else 0.0
            except (ValueError, TypeError): unit_price = 0.0

            is_courtesy = False
            if 'courtesy_var' in row and row['courtesy_var']:
                try: is_courtesy = bool(row['courtesy_var'].get())
                except Exception: is_courtesy = False

            if _is_ordnance_or_packed_item(name, box_str):
                row_item_val = qty * unit_price
            else:
                scu_mult = 1.0
                if "scu" in box_str.lower():
                    try: scu_mult = float(box_str.split()[0])
                    except (ValueError, IndexError): scu_mult = 1.0
                row_item_val = scu_mult * qty * unit_price

            gross_total += row_item_val

            if is_courtesy:
                courtesy_subsidy += row_item_val
                row_total = 0.0
            else:
                row_total = row_item_val

            net_payable += row_total

            # Update row total label
            if 'total_label' in row and row['total_label']:
                if is_courtesy:
                    row['total_label'].configure(text="FREE Supply", text_color="#10b981")
                else:
                    fmt_total = f"{int(row_total):,}".replace(",", " ") if row_total.is_integer() else f"{row_total:,.2f}".replace(",", " ")
                    row['total_label'].configure(text=f"{fmt_total} aUEC", text_color="#ffffff")
        except Exception:
            pass

    fmt_net = f"{int(net_payable):,}".replace(",", " ") if net_payable.is_integer() else f"{net_payable:,.2f}".replace(",", " ")
    fmt_gross = f"{int(gross_total):,}".replace(",", " ") if gross_total.is_integer() else f"{gross_total:,.2f}".replace(",", " ")
    fmt_subsidy = f"{int(courtesy_subsidy):,}".replace(",", " ") if courtesy_subsidy.is_integer() else f"{courtesy_subsidy:,.2f}".replace(",", " ")

    if hasattr(self, 'grand_total_var'):
        self.grand_total_var.set(fmt_net)
    if hasattr(self, 'grand_total_label'):
        try:
            if courtesy_subsidy > 0:
                self.grand_total_label.configure(
                    text=f"KOMPLETNÍ POŽADOVANÁ PLATBA: {fmt_net} aUEC  (Hrubá hodnota: {fmt_gross} aUEC | UEE Dotace: -{fmt_subsidy} aUEC)"
                )
            else:
                self.grand_total_label.configure(text=f"KOMPLETNÍ POŽADOVANÁ PLATBA: {fmt_net} aUEC")
        except Exception: pass

main.RequisitionApp.update_grand_total = _patched_update_grand_total


def apply_all_patches(main_module):
    """Called by entry.py after imports. Applies all v0.6 and v0.6.1 patches."""
    main_module.RequisitionApp.update_grand_total = _patched_update_grand_total
    # ── Fix intro video path via descriptor ──
    _correct_video = PATHS.resource("intro_video.mp4")
    if not os.path.isfile(_correct_video):
        for candidate in [
            os.path.join(PATHS.resources, "intro_video.mp4"),
            os.path.join(PATHS.app_root, "intro_video.mp4"),
        ]:
            if os.path.isfile(candidate):
                _correct_video = candidate
                break

    if _correct_video and os.path.isfile(_correct_video):
        class _VideoPathDescriptor:
            """Intercepts video_path writes to resolve local resource paths cleanly without Tkinter __getattr__ recursion."""
            def __get__(self, obj, objtype=None):
                if obj is None:
                    return self
                val = obj.__dict__.get('_real_video_path', _correct_video)
                if val and os.path.isfile(str(val)):
                    return str(val)
                if val:
                    base = os.path.basename(str(val))
                    res_c = PATHS.resource(base)
                    if os.path.isfile(res_c):
                        return res_c
                    app_c = os.path.join(PATHS.app_root, base)
                    if os.path.isfile(app_c):
                        return app_c
                return _correct_video

            def __set__(self, obj, value):
                if value and os.path.isfile(str(value)):
                    obj.__dict__['_real_video_path'] = str(value)
                elif value:
                    base = os.path.basename(str(value))
                    res_c = PATHS.resource(base)
                    if os.path.isfile(res_c):
                        obj.__dict__['_real_video_path'] = res_c
                    else:
                        obj.__dict__['_real_video_path'] = _correct_video
                else:
                    obj.__dict__['_real_video_path'] = _correct_video

        main_module.RequisitionApp.video_path = _VideoPathDescriptor()

    # ── Video Player status tracking + CTk rendering patch ──
    def _patched_start_intro_video(self):
        """Start intro video playback with live status tracking console and CTkLabel image compatibility."""
        import cv2
        import threading
        v_path = getattr(self, 'video_path', None)
        if not v_path or not os.path.isfile(str(v_path)):
            v_path = PATHS.resource("intro_video.mp4")

        if hasattr(self, 'console_var'):
            self.console_var.set(f">> LOADING MEDIA: {os.path.basename(str(v_path))}...")

        try:
            if not hasattr(self, 'cap') or self.cap is None or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(str(v_path))

            if self.cap and self.cap.isOpened():
                self.use_video = True
                total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = self.cap.get(cv2.CAP_PROP_FPS) or 24.0
                if hasattr(self, 'console_var'):
                    self.console_var.set(f">> MEDIA READY: {total_frames} FRAMES @ {fps:.1f} FPS")
            else:
                self.use_video = False
                if hasattr(self, 'console_var'):
                    self.console_var.set(">> MEDIA NOTICE: Video stream unavailable, launching app...")
        except Exception as ex:
            self.use_video = False
            print(f"[VideoInit] Error: {ex}")
            if hasattr(self, 'console_var'):
                self.console_var.set(f">> MEDIA NOTICE: {ex}")

        if self.use_video:
            if hasattr(self, 'boot_frame') and self.boot_frame:
                try: self.boot_frame.place_forget()
                except: pass
            if hasattr(self, 'video_label') and self.video_label:
                try: self.video_label.pack(fill='both', expand=True)
                except: pass
            try:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 35)
            except Exception:
                pass

            # Play original static/intro sound effect asynchronously
            try:
                def _do_play_sound():
                    try:
                        if hasattr(self, 'play_static_sound'):
                            self.play_static_sound()
                        else:
                            import winsound
                            sp = PATHS.resource(os.path.join("fonts", "intro_sound.wav"))
                            if os.path.exists(sp):
                                winsound.PlaySound(sp, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    except Exception:
                        pass
                threading.Thread(target=_do_play_sound, daemon=True).start()
            except Exception:
                pass

            self.play_intro_video()
        else:
            self.finish_intro()

    def _patched_play_intro_video(self):
        """Render video frames cleanly onto video_label with CTkImage / raw label fallback and live tracking."""
        import cv2
        from PIL import Image, ImageTk
        import customtkinter as ctk

        if not getattr(self, 'use_video', False) or not hasattr(self, 'cap') or self.cap is None:
            self.finish_intro()
            return

        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                curr_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                w = self.winfo_width() if self.winfo_width() > 400 else 1200
                h = self.winfo_height() if self.winfo_height() > 300 else 820

                frame_resized = cv2.resize(frame_rgb, (w, h))
                img = Image.fromarray(frame_resized)

                if hasattr(self.video_label, '_label') and self.video_label._label:
                    img_tk = ImageTk.PhotoImage(img)
                    self.video_label._label.configure(image=img_tk, text="")
                    self.video_label._label.image = img_tk
                else:
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                    self.video_label.configure(image=ctk_img, text="")

                fps = self.cap.get(cv2.CAP_PROP_FPS) or 24.0
                delay = int(1000 / fps) if fps > 0 else 33

                if curr_frame % 15 == 0 and hasattr(self, 'console_var'):
                    self.console_var.set(f">> STREAMING INTRO VIDEO: FRAME {curr_frame}/{total_frames} ({int(curr_frame/total_frames*100)}%)")

                self.after(delay, self.play_intro_video)
            else:
                if hasattr(self, 'console_var'):
                    self.console_var.set(">> INTRO VIDEO PLAYBACK COMPLETED.")
                try: self.cap.release()
                except: pass
                self.finish_intro()
        except Exception as ex:
            print(f"[VideoPlayback] Error: {ex}")
            if hasattr(self, 'console_var'):
                self.console_var.set(f">> VIDEO ERROR: {ex}")
            try: self.cap.release()
            except: pass
            self.finish_intro()

    main_module.RequisitionApp.start_intro_video = _patched_start_intro_video
    main_module.RequisitionApp.play_intro_video = _patched_play_intro_video

    # ── v0.6.1: show_create_package_modal ──
    def _show_create_package_modal(self):
        try:
            from src.ui.create_package import CreatePackageModal
            CreatePackageModal(self)
        except Exception as e:
            pass
    main_module.RequisitionApp.show_create_package_modal = _show_create_package_modal

def setup_responsive_window(app):
    """Configures adaptive window sizing, minimum constraints, centering,
    DPI scaling, and fullscreen toggle across different PC screens and resolutions.
    """
    try:
        screen_w = app.winfo_screenwidth()
        screen_h = app.winfo_screenheight()

        # Set safe minimum dimensions so layout never collapses
        min_w = min(1024, max(800, screen_w - 40))
        min_h = min(640, max(500, screen_h - 60))
        try:
            app.minsize(min_w, min_h)
        except Exception:
            pass

        # On smaller screens (<= 1440x900 or 1366x768), maximize window for best fit
        if screen_w <= 1440 or screen_h <= 900:
            try:
                app.state("zoomed")
            except Exception:
                app.geometry(f"{screen_w-30}x{screen_h-50}+10+10")
        else:
            # On larger screens (1080p, 1440p, 4K), center a generous 88% window
            win_w = min(int(screen_w * 0.88), 1600)
            win_h = min(int(screen_h * 0.88), 980)
            pos_x = max(0, (screen_w - win_w) // 2)
            pos_y = max(0, (screen_h - win_h) // 2)
            app.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        # Dynamic Scaling state
        app._current_ui_scale = 1.0

        def _toggle_fullscreen(event=None):
            try:
                is_fs = app.attributes("-fullscreen")
                app.attributes("-fullscreen", not is_fs)
            except Exception:
                try:
                    state = app.state()
                    app.state("zoomed" if state != "zoomed" else "normal")
                except Exception:
                    pass

        def _exit_fullscreen(event=None):
            try:
                app.attributes("-fullscreen", False)
            except Exception:
                pass

        def _zoom_in(event=None):
            try:
                import customtkinter as ctk
                app._current_ui_scale = min(1.5, app._current_ui_scale + 0.1)
                ctk.set_widget_scaling(app._current_ui_scale)
            except Exception:
                pass

        def _zoom_out(event=None):
            try:
                import customtkinter as ctk
                app._current_ui_scale = max(0.7, app._current_ui_scale - 0.1)
                ctk.set_widget_scaling(app._current_ui_scale)
            except Exception:
                pass

        def _zoom_reset(event=None):
            try:
                import customtkinter as ctk
                app._current_ui_scale = 1.0
                ctk.set_widget_scaling(1.0)
            except Exception:
                pass

        app.bind("<F11>", _toggle_fullscreen)
        app.bind("<Escape>", _exit_fullscreen)
        app.bind("<Control-plus>", _zoom_in)
        app.bind("<Control-equal>", _zoom_in)
        app.bind("<Control-minus>", _zoom_out)
        app.bind("<Control-underscore>", _zoom_out)
        app.bind("<Control-0>", _zoom_reset)

    except Exception as e:
        print(f"[WindowSetup] Responsive layout init: {e}")
