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
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Monkey-patch create_left_panel (main is imported by entry.py first)
main = sys.modules.get('main') or __import__('main')
original_create_left_panel = main.RequisitionApp.create_left_panel
_orig_gen_req = main.RequisitionApp.generate_requisition_pdf

# Imports used by callbacks inside patches
from pdf_engine import generate_pdf_direct, LORE_STORY_CACHE
from lore_helper import sc_date_only
try:
    from uex_sync import _uex_ships_db, _verify_and_update_uex_data
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

    def _filt():
        lt = self._loading_type_var.get()
        if lt == "Landing Pad": return [l for l in _all_locs if l[1] == "space_stations"]
        elif lt == "In Hangar": return [l for l in _all_locs if l[1] in ("cities", "space_stations")]
        elif lt == "Planetary": return [l for l in _all_locs if l[1] == "outposts"]
        else:
            r = [l for l in _all_locs if l[1] in ("planets", "moons")]
            r.insert(0, ("[Deep Space] Open Orbit", "deep_space", "Deep Space"))
            return r

    def _on_key(event):
        typed = self._location_ac_var.get().lower()
        if len(typed) < 2: self._ac_listbox.grid_remove(); return
        ms = [l[0] for l in _filt() if typed in l[0].lower()][:8]
        if ms:
            self._ac_listbox.delete(0, tk.END)
            for m in ms: self._ac_listbox.insert(tk.END, m)
            self._ac_listbox.grid(row=11, column=0, columnspan=2, padx=10, sticky="ew")
        else: self._ac_listbox.grid_remove()

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
        if " (" in n: n = n[:n.rfind(" (")]
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
            if hasattr(self, '_gen3_btn'):
                self._gen3_btn.configure(state="normal", fg_color="#3a2a10", hover_color="#5a4a20", text_color="#c8a84e")
            if hasattr(self, '_sr_btn'):
                self._sr_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
            if hasattr(self, 'generate_btn'):
                self.generate_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
        else:
            if hasattr(self, '_gen3_btn'):
                self._gen3_btn.configure(state="disabled", fg_color="#2a2a2a", hover_color="#2a2a2a", text_color="#555555")
            if hasattr(self, '_sr_btn'):
                self._sr_btn.configure(state="normal", fg_color="#2a3a1a", text_color="#c8a84e")
            if hasattr(self, 'generate_btn'):
                self.generate_btn.configure(state="normal", fg_color="#c8a84e", text_color="#1a1a1a")

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
        
        # Restore filedialog
        _fd.asksaveasfilename = _orig_asksave
        
        # Restore original classification
        self._gen3_running = False
        # Restore messagebox
        _mb.showinfo = _orig_showinfo
        _mb.showwarning = _orig_showwarning
        if hasattr(self, 'security_level_var'):
            self.security_level_var.set(orig_sec)
        if hasattr(self, 'on_security_level_changed'):
            self.on_security_level_changed(orig_sec)
        self._gen3_btn.configure(text="Generate All PDFs", state="normal",
            fg_color="#3a2a10", text_color="#c8a84e")
        if generated > 0:
            _play_sound("pdf_generated.wav")
            messagebox.showinfo("Batch Complete",
                f"All {generated} PDFs saved in:\n{save_dir}")

    self._gen3_btn = ctk.CTkButton(master=scroll_frame, text="Generate All PDFs", command=_gen3,
        font=ctk.CTkFont(size=11, weight="bold"), fg_color="#3a2a10", hover_color="#5a4a20",
        text_color="#c8a84e", height=30, corner_radius=6)
    self._gen3_btn.pack(padx=10, pady=(2, 2), fill="x")
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
    
    # Initial state: ALL selected = disable manifest + SR, enable Gen All
    self._sr_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
    def _force_disable_golden():
        try:
            if self.generate_btn and self._classify_var.get().upper() == "ALL":
                self.generate_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
        except: pass
    if self.generate_btn:
        self.generate_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
    self.after(300, _force_disable_golden)
    self.after(1000, _force_disable_golden)
    self.after(2500, _force_disable_golden)

    # Update Trade Routes
    def _update_trade_routes():
        import threading
        self._trade_btn.configure(text="\u27f3 Updating...", state="disabled")
        self.update_idletasks()
        def _run():
            import urllib.request
            result = {"updated": 0, "errors": [], "items": []}
            try:
                # Fetch commodities from UEX API
                url = "https://uexcorp.space/api/2.0/commodities"
                req = urllib.request.Request(url, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = resp.read().decode("utf-8")
                api_data = json.loads(raw)
                commodities = api_data.get("data", []) if isinstance(api_data, dict) else api_data
                
                # Build lookup by name (lowercase)
                api_lookup = {}
                for c in commodities:
                    cname = (c.get("name", "") or c.get("commodity_name", "")).lower().strip()
                    if cname:
                        api_lookup[cname] = c
                
                # Match against config items
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
                if getattr(sys, 'frozen', False):
                    config_path = os.path.join(os.path.dirname(sys.executable), "config.json")
                
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as cf:
                        config = json.load(cf)
                    
                    items = config.get("frequent_items", [])
                    for item in items:
                        iname = item.get("name", "").lower().strip()
                        match = api_lookup.get(iname)
                        if not match:
                            for k, v in api_lookup.items():
                                if iname in k or k in iname:
                                    match = v
                                    break
                        if match:
                            new_price = match.get("price_buy", match.get("price", 0)) or 0
                            if new_price > 0 and new_price != item.get("price", 0):
                                old_price = item.get("price", 0)
                                item["price"] = new_price
                                result["items"].append(f"{item['name']}: {old_price} \u2192 {new_price} aUEC")
                                result["updated"] += 1
                    
                    if result["updated"] > 0:
                        with open(config_path, "w", encoding="utf-8") as cf:
                            json.dump(config, cf, indent=2, ensure_ascii=False)
                        if hasattr(self, 'config_data'):
                            self.config_data = config
                
                result["total_commodities"] = len(commodities)
                result["matched"] = sum(1 for item in items if any(
                    item.get("name","").lower().strip() in k or k in item.get("name","").lower().strip()
                    for k in api_lookup))
                
            except Exception as e:
                result["errors"].append(str(e))
            
            self.after(0, lambda: _trade_done(result))
        
        def _trade_done(r):
            self._trade_btn.configure(text="\u27f3 Update Trade Routes", state="normal")
            if r["errors"]:
                messagebox.showerror("Trade Routes", f"Error: {r['errors'][0]}")
            else:
                msg = f"UEX Commodities: {r.get('total_commodities', 0)}\n"
                msg += f"Matched items: {r.get('matched', 0)}\n"
                msg += f"Price updates: {r['updated']}\n\n"
                if r["items"]:
                    msg += "Changes:\n" + "\n".join(f"  {s}" for s in r["items"][:15])
                else:
                    msg += "All prices up to date!"
                _play_sound("verify_sync.wav")
                messagebox.showinfo("Trade Routes", msg)
        
        threading.Thread(target=_run, daemon=True).start()

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
            result = _verify_and_update_uex_data()
            self.after(0, lambda: _done(result))
        def _done(r):
            _sa[0] = False
            self._verify_btn.configure(text="\u27f3 Verify All Data", state="normal")
            if r["errors"]:
                messagebox.showerror("Verify", f"Error: {r['errors'][0]}")
            else:
                a, u = len(r["added"]), len(r["updated"])
                ga = len(r.get("grids_added", []))
                gl = len(r.get("grids_linked", []))
                wn = r.get("warnings", [])
                msg = f"Wiki API: {r.get('wiki_total', 0)} vehicles, {r.get('wiki_items_total', 0)} items\n"
                msg += f"UEX API: {r.get('uex_total', 0)} vehicles\n"
                msg += f"SC-Cargo: {r.get('sc_cargo_ships', 0)} grid layouts\n"
                msg += f"Local DB: {len(_uex_ships_db)} ships\n"
                scm = r.get("sc_grids_merged", 0)
                msg += f"Cargo grids: {gl} linked, {scm} from sc-cargo, {ga} auto-created\n\n"
                if a:
                    msg += f"\u2795 {a} NEW ships:\n" + "".join(f"  + {s}\n" for s in r["added"][:12])
                if u:
                    msg += f"\n\u27f3 {u} UPDATED:\n" + "".join(f"  ~ {s}\n" for s in r["updated"][:12])
                if ga:
                    msg += f"\n\U0001f4e6 {ga} new cargo grids:\n" + "".join(f"  \u25a3 {s}\n" for s in r["grids_added"][:8])
                va = r.get("vol_added", 0)
                vu = r.get("vol_updated", 0)
                if va or vu:
                    msg += f"\n\u2696 Item volumes: +{va} new, ~{vu} updated\n"
                if wn:
                    msg += f"\n\u26a0 Warnings:\n" + "".join(f"  ! {w}\n" for w in wn[:5])
                if not a and not u and not ga and not va and not vu:
                    msg += "\u2713 All databases up to date!"
                # Update internal ship names cache but keep selector showing loadout vessels only
                if r.get("all_ship_names"):
                    self._all_ship_names = r["all_ship_names"]
                    # Do NOT override selector — keep it showing loadout vessels only
                    # self.ship_selector.configure(values=r["all_ship_names"])
                _play_sound("verify_sync.wav")
                messagebox.showinfo("Verify All Data", msg)
        threading.Thread(target=_run, daemon=True).start()

    self._verify_btn = ctk.CTkButton(master=scroll_frame, text="\u27f3 Verify All Data", command=_on_verify,
        font=ctk.CTkFont(size=10), fg_color="#2a2a2a", hover_color="#3a3a3a",
        text_color="#888888", height=26, corner_radius=6)
    self._verify_btn.pack(padx=10, pady=(5, 10), fill="x")

    # Patch clipboard exports to not show messagebox
    _orig_export = main.RequisitionApp.export_to_clipboard
    _orig_export_blank = main.RequisitionApp.export_blank_template_to_clipboard
    def _silent_export(s, *a, **kw):
        _orig_showinfo = messagebox.showinfo
        messagebox.showinfo = lambda *a, **kw: None
        try: _orig_export(s, *a, **kw)
        finally: messagebox.showinfo = _orig_showinfo
    def _silent_export_blank(s, *a, **kw):
        _orig_showinfo = messagebox.showinfo
        messagebox.showinfo = lambda *a, **kw: None
        try: _orig_export_blank(s, *a, **kw)
        finally: messagebox.showinfo = _orig_showinfo
    main.RequisitionApp.export_to_clipboard = _silent_export
    main.RequisitionApp.export_blank_template_to_clipboard = _silent_export_blank

    return res

main.RequisitionApp.create_left_panel = patched_create_left_panel


# â”€â”€ Monkey-patch add_new_vessel: custom autocomplete dialog â”€â”€
_orig_add_new_vessel = main.RequisitionApp.add_new_vessel
def _patched_add_new_vessel(self):
    """Custom 'Add New Vessel' dialog with autocomplete from ship DB."""
    import tkinter as tk
    
    all_ships = getattr(self, '_all_ship_names', [])
    if not all_ships and _uex_ships_db:
        all_ships = sorted(set(
            v.get("name", v.get("short_name", k))
            for k, v in _uex_ships_db.items()
            if v.get("scu", 0) > 0 and v.get("is_spaceship", 1)
        ))
    
    result = [None]
    
    dlg = tk.Toplevel(self)
    dlg.title("Add New Vessel")
    dlg.geometry("380x340")
    dlg.configure(bg="#1a1a2e")
    dlg.transient(self)
    dlg.grab_set()
    
    tk.Label(dlg, text="Enter new vessel/ship name:", fg="#cccccc", bg="#1a1a2e",
             font=("Segoe UI", 10)).pack(padx=15, pady=(15, 5), anchor="w")
    
    entry_var = tk.StringVar()
    entry = tk.Entry(dlg, textvariable=entry_var, font=("Segoe UI", 11),
                     bg="#0d1117", fg="#ffffff", insertbackground="#ffffff",
                     relief="solid", bd=1)
    entry.pack(padx=15, pady=(0, 5), fill="x")
    entry.focus_set()
    
    tk.Label(dlg, text="Suggestions from database:", fg="#888888", bg="#1a1a2e",
             font=("Segoe UI", 8)).pack(padx=15, pady=(5, 2), anchor="w")
    
    listbox = tk.Listbox(dlg, height=10, bg="#0d1117", fg="#dddddd",
                         selectbackground="#2a3a4a", selectforeground="#ffffff",
                         font=("Segoe UI", 9), relief="solid", bd=1)
    listbox.pack(padx=15, pady=(0, 10), fill="both", expand=True)
    
    def _filter(*args):
        typed = entry_var.get().lower().strip()
        listbox.delete(0, tk.END)
        if len(typed) < 2:
            for s in all_ships[:30]:
                listbox.insert(tk.END, s)
            return
        words = typed.split()
        matches = [s for s in all_ships if all(w in s.lower() for w in words)]
        if not matches:
            matches = [s for s in all_ships if typed in s.lower()]
        for s in matches[:30]:
            listbox.insert(tk.END, s)
    
    entry_var.trace_add("write", _filter)
    _filter()
    
    def _on_select(event):
        sel = listbox.curselection()
        if sel:
            entry_var.set(listbox.get(sel[0]))
    
    def _on_dblclick(event):
        sel = listbox.curselection()
        if sel:
            entry_var.set(listbox.get(sel[0]))
            _ok()
    
    listbox.bind("<<ListboxSelect>>", _on_select)
    listbox.bind("<Double-1>", _on_dblclick)
    
    btn_frame = tk.Frame(dlg, bg="#1a1a2e")
    btn_frame.pack(padx=15, pady=(0, 15), fill="x")
    
    def _ok():
        name = entry_var.get().strip()
        if name:
            result[0] = name
        dlg.destroy()
    
    def _cancel():
        dlg.destroy()
    
    tk.Button(btn_frame, text="OK", command=_ok, width=12,
              bg="#2a3a4a", fg="#ffffff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
    tk.Button(btn_frame, text="Cancel", command=_cancel, width=12,
              bg="#333333", fg="#cccccc", font=("Segoe UI", 9)).pack(side="left")
    
    entry.bind("<Return>", lambda e: _ok())
    entry.bind("<Escape>", lambda e: _cancel())
    
    dlg.wait_window()
    
    new_name = result[0]
    if not new_name:
        return
    
    # Check duplicate
    existing = list(self.config_data.get("vessels", {}).keys())
    if new_name in existing:
        messagebox.showerror("Error", f"Vessel '{new_name}' already exists!")
        return
    
    # Add to config
    self.config_data.setdefault("vessels", {})[new_name] = {}
    self.save_config_file()
    vessel_options = list(self.config_data.get("vessels", {}).keys())
    self.ship_selector.configure(values=sorted(vessel_options))
    self.ship_selector.set(new_name)
    self.on_vessel_changed()
    _play_sound("cargo_add.wav")

main.RequisitionApp.add_new_vessel = _patched_add_new_vessel

# Disable Communication Channel dropdown (visual only, controlled by Classification)
_orig_show_main = main.RequisitionApp.show_main_app_layout

# ── Fix main.pyc load_vessel_loadout crash (float qty * string) ──
_orig_load_vessel = main.RequisitionApp.load_vessel_loadout
def _safe_load_vessel(self, *a, **kw):
    """Wrap load_vessel_loadout — fix float qty causing TypeError in main.pyc."""
    # Pre-fix: ensure all loadout quantities are int
    try:
        if hasattr(self, 'config_data') and 'vessels' in self.config_data:
            for vname, vdata in self.config_data['vessels'].items():
                if isinstance(vdata, dict) and 'loadout' in vdata:
                    for item in vdata['loadout']:
                        if isinstance(item, dict) and 'qty' in item:
                            item['qty'] = int(float(item['qty']))
    except Exception:
        pass
    try:
        return _orig_load_vessel(self, *a, **kw)
    except TypeError as e:
        print(f"[UI_PANEL] load_vessel_loadout TypeError caught: {e}")
        return None
main.RequisitionApp.load_vessel_loadout = _safe_load_vessel

print(f"[UI_PANEL] Monkey-patching show_main_app_layout...", file=__import__('sys').stderr)
def _patched_show_main(self, *a, **kw):
    print(f"[UI_PANEL] _patched_show_main called!", file=__import__('sys').stderr)
    # Block vessel loadout during initial layout to prevent Idris flash
    _blocked_load = lambda self_, *a2, **kw2: None
    main.RequisitionApp.load_vessel_loadout = _blocked_load
    r = _orig_show_main(self, *a, **kw)
    # Restore safe load after layout is done
    main.RequisitionApp.load_vessel_loadout = _safe_load_vessel
    try:
        if hasattr(self, 'sec_selector'):
            self.sec_selector.configure(state="disabled")
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
    
    # â”€â”€ Ship Selector: loadout vessels only â”€â”€
    try:
        if hasattr(self, 'ship_selector'):
            loadout_vessels = sorted(self.config_data.get("vessels", {}).keys())
            all_db_names = sorted(set(
                v.get("name", v.get("short_name", k))
                for k, v in _uex_ships_db.items()
                if v.get("scu", 0) > 0 and v.get("is_spaceship", 1)
            )) if _uex_ships_db else []
            self._loadout_ship_names = loadout_vessels
            self._all_ship_names = all_db_names
            self.ship_selector.configure(values=loadout_vessels)
            self.ship_selector.set("")  # Empty â€” user must select
            # Clear default loadout cargo that main.pyc loaded
            if hasattr(self, 'cargo_rows') and self.cargo_rows:
                for row in list(self.cargo_rows):
                    try:
                        if 'frame' in row:
                            row['frame'].destroy()
                    except: pass
                self.cargo_rows.clear()
            # Single quick clear — load_vessel_loadout is blocked during
            # show_main so no aggressive delayed clears needed anymore.
            def _force_empty_ship():
                try:
                    self.ship_selector.set("")
                except: pass
            self.after(200, _force_empty_ship)
            # Set delivery date to SC format (year + 930)
            if hasattr(self, 'delivery_date_var'):
                self.delivery_date_var.set(sc_date_only())
            # Regenerate req_id when ship changes
            def _on_ship_selected(event=None):
                if hasattr(self, 'req_id_var'):
                    import time
                    ship = self.ship_selector.get().strip()
                    if ship and len(ship) > 3:
                        seed = hash(ship + str(int(time.time())))
                        rng = random.Random(seed)
                        suffixes = ["X41", "X86", "S26", "A17", "B03", "C55", "D12"]
                        new_id = f"UEE-LOG-{rng.randint(10,99)}-{rng.randint(1000,9999)}-{rng.choice(suffixes)}"
                        self.req_id_var.set(new_id)
                        _play_sound("cargo_add.wav")
            
            self.ship_selector.bind('<<ComboboxSelected>>', _on_ship_selected)
    except Exception as e:
        print(f"[Ship selector] {e}")
    
    # ── Item Combo: enforce 10-item limit + add search/filter autocomplete ──
    try:
        combo = getattr(self, 'quick_add_combo', None) or getattr(self, 'item_combo', None) or getattr(self, 'item_dropdown', None)
        if combo:
            # Enforce max 10 items FIRST: patch configure() so main.pyc can't override
            _orig_combo_configure = combo.configure
            def _capped_configure(*args, **kwargs):
                import sys as _sys
                if 'values' in kwargs:
                    v = kwargs['values']
                    n = len(v) if isinstance(v, (list, tuple)) else '?'
                    print(f"[CAP] configure(values=) called with {n} items", file=_sys.stderr)
                    if isinstance(v, (list, tuple)) and len(v) > 10:
                        print(f"[CAP] Trimming {len(v)} -> 10 items", file=_sys.stderr)
                        kwargs['values'] = list(v)[:10]
                else:
                    print(f"[CAP] configure() called WITHOUT values, kwargs={list(kwargs.keys())}", file=_sys.stderr)
                return _orig_combo_configure(*args, **kwargs)
            combo.configure = _capped_configure
            combo.config = _capped_configure
            print(f"[CAP] Patched quick_add_combo.configure OK", file=__import__('sys').stderr)
            
            # Build item names from config for autocomplete
            fi_data = self.config_data.get("frequent_items", {})
            all_item_names = []
            if isinstance(fi_data, dict):
                for cat, cat_items in fi_data.items():
                    if isinstance(cat_items, list):
                        for item in cat_items:
                            if isinstance(item, dict) and item.get("name"):
                                all_item_names.append(item["name"])
            elif isinstance(fi_data, list):
                for item in fi_data:
                    if isinstance(item, dict) and item.get("name"):
                        all_item_names.append(item["name"])
            if all_item_names:
                self._all_item_names = sorted(set(all_item_names))
                
                def _on_item_key(event=None):
                    typed = combo.get().lower().strip()
                    if not typed or len(typed) < 2:
                        combo.configure(values=self._all_item_names[:10])
                        return
                    words = typed.split()
                    filtered = [n for n in self._all_item_names if all(w in n.lower() for w in words)]
                    if not filtered:
                        filtered = [n for n in self._all_item_names if typed in n.lower()]
                    if filtered:
                        combo.configure(values=filtered[:10])
                        try: combo._open_dropdown_menu()
                        except: pass
                
                combo.bind('<KeyRelease>', _on_item_key)
    except Exception as e:
        print(f"[Item autocomplete] {e}")
    
    return r
main.RequisitionApp.show_main_app_layout = _patched_show_main
print(f"[UI_PANEL] show_main_app_layout patched OK", file=__import__('sys').stderr)


# ══════════════════════════════════════════════════════════════════════════
# SECTION: Slang Resolution + Auto-Battery Companion Patch
# ══════════════════════════════════════════════════════════════════════════

from slang_helper import resolve_slang

# Items that should auto-add a companion battery row
_BATTERY_COMPANIONS = {
    "maxlift tractor beam": {"name": "Maxlift Tractor Beam Battery", "price": 175, "unit": "unit"},
    "cambio srt":           {"name": "Cambio Multi-tool Battery",    "price": 63,  "unit": "unit"},
}

_orig_add_cargo_row = main.RequisitionApp.add_cargo_row_to_ui
_adding_battery = False  # recursion guard

def _patched_add_cargo_row(self, name="", qty="", box_size="1 SCU",
                            price=0, courtesy=False, unit="SCU", **kwargs):
    """Wraps add_cargo_row_to_ui to:
    1. Run item names through resolve_slang() for Ctrl+V and quick-add.
    2. Auto-add companion battery when MaxLift or Cambio is added.
    """
    global _adding_battery

    # ── 1) Slang resolution (skip if _skip_slang flag is set) ──
    resolved_name = name
    if name and isinstance(name, str) and name.strip() and not getattr(self, '_skip_slang', False):
        config = getattr(self, 'config_data', None)
        resolved = resolve_slang(name.strip(), config_data=config)
        if resolved:
            resolved_name = resolved

    # ── 2) Call original to add the row ──
    result = _orig_add_cargo_row(self, name=resolved_name, qty=qty,
                                  box_size=box_size, price=price,
                                  courtesy=courtesy, unit=unit, **kwargs)

    # ── 3) Auto-battery companion (skip if we're already adding a battery) ──
    if not _adding_battery:
        companion = _BATTERY_COMPANIONS.get(resolved_name.lower().strip())
        if companion:
            _adding_battery = True
            try:
                # Match battery qty to the parent item qty
                bat_qty = qty if qty else "1"
                _orig_add_cargo_row(
                    self,
                    name=companion["name"],
                    qty=bat_qty,
                    box_size="1 SCU",
                    price=companion["price"],
                    courtesy=False,
                    unit=companion["unit"],
                )
                print(f"[AUTO-BATTERY] Added {companion['name']} x{bat_qty}",
                      file=__import__('sys').stderr)
            except Exception as e:
                print(f"[AUTO-BATTERY] Error: {e}", file=__import__('sys').stderr)
            finally:
                _adding_battery = False

    return result

main.RequisitionApp.add_cargo_row_to_ui = _patched_add_cargo_row
print(f"[UI_PANEL] add_cargo_row_to_ui patched (slang + auto-battery) OK",
      file=__import__('sys').stderr)


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

    # -- 1. Find matching vessel in config --
    matched_key = None
    if "ship" in metadata and hasattr(self, 'config_data') and 'vessels' in self.config_data:
        ship_name = metadata["ship"]
        vessels_dict = self.config_data['vessels']
        if ship_name in vessels_dict:
            matched_key = ship_name
        else:
            for k in vessels_dict.keys():
                if k.lower() in ship_name.lower() or ship_name.lower() in k.lower():
                    matched_key = k
                    break

    # -- 2. Clear table if full requisition --
    if is_full_requisition:
        try:
            _orig_clear_all_rows(self)
        except Exception:
            pass
        if hasattr(self, 'ship_selector'):
            try:
                if matched_key:
                    self.ship_selector.set(matched_key)
                elif "ship" in metadata:
                    self.ship_selector.set(metadata["ship"])
            except Exception:
                pass

    # -- 3. Collect default loadout items if full requisition --
    merged_items = []
    if is_full_requisition and matched_key and hasattr(self, 'config_data') and 'vessels' in self.config_data:
        default_loadout = self.config_data['vessels'][matched_key]
        for item in default_loadout:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            name = item["name"]
            qty_val = item.get("qty")
            if qty_val == "" or qty_val is None:
                qty = 1
            else:
                try:
                    qty = int(float(qty_val))
                except (ValueError, TypeError):
                    qty = 1
            box = item.get("box_size", "1 SCU")
            price = 0
            try:
                price = int(float(item.get("price", 0)))
            except (ValueError, TypeError):
                pass
            courtesy = bool(item.get("courtesy", False))
            unit = item.get("unit", "unit")
            merged_items.append({
                "name": name, "qty": qty, "box_size": box,
                "price": price, "courtesy": courtesy, "unit": unit
            })

    # Determine if it has structured items
    has_structured = bool(_re.search(r'\|.*Qty:', filtered_raw, _re.IGNORECASE))

    # -- 4. Parse cargo items from clipboard --
    parsed_items = []

    if has_structured:
        cargo_lines = [l.strip() for l in filtered_raw.splitlines() if l.strip()]
        _struct_re = _re.compile(
            r'^\s*-\s*(.+?)\s*\|\s*Qty:\s*\[?\s*([\d.\s?]+)\s*\]?\s*\|\s*Box:\s*(.+?)\s*(?:\|\s*Price:\s*(\d+)\s*aUEC(?:\s*\[COURTESY\])?\s*)?\|\s*(.+)$',
            _re.IGNORECASE
        )
        for line in cargo_lines:
            m = _struct_re.match(line)
            if not m:
                continue
            item_name = m.group(1).strip()
            qty_str = m.group(2).strip()
            box_size = m.group(3).strip()
            price_str = m.group(4) or "0"
            unit_str = m.group(5).strip()
            new_qty = int(qty_str) if qty_str.isdigit() else 1
            price_val = int(price_str) if price_str.isdigit() else 0
            is_courtesy = "[COURTESY]" in line.upper()
            parsed_items.append((item_name, new_qty, box_size, price_val, is_courtesy, unit_str))
    else:
        # Raw slang parser
        lines_slang = [l.strip() for l in filtered_raw.strip().splitlines() if l.strip()]
        for line in lines_slang:
            qty = 1
            name = line
            m = _re.match(r'^(\d+)\s*x\s+(.+)$', line, _re.IGNORECASE)
            if m:
                qty = int(m.group(1))
                name = m.group(2).strip()
            else:
                m = _re.match(r'^(.+?)\s+x\s*(\d+)$', line, _re.IGNORECASE)
                if m:
                    name = m.group(1).strip()
                    qty = int(m.group(2))
                else:
                    tokens = line.split()
                    # Leading number without 'x': "20 arrester 3"
                    if len(tokens) > 1 and tokens[0].isdigit():
                        possible_qty = int(tokens[0])
                        possible_name = " ".join(tokens[1:])
                        resolved_test = resolve_slang(possible_name, config_data=self.config_data)
                        fi_list = self.config_data.get("frequent_items", [])
                        exists = any(
                            isinstance(fi, dict) and fi.get("name") and fi["name"].lower() == resolved_test.lower()
                            for fi in fi_list
                        )
                        if exists:
                            qty = possible_qty
                            name = possible_name
                    # Trailing number without 'x': "arrester 3 20"
                    elif len(tokens) > 1 and tokens[-1].isdigit():
                        possible_qty = int(tokens[-1])
                        possible_name = " ".join(tokens[:-1])
                        resolved_test = resolve_slang(possible_name, config_data=self.config_data)
                        fi_list = self.config_data.get("frequent_items", [])
                        exists = any(
                            isinstance(fi, dict) and fi.get("name") and fi["name"].lower() == resolved_test.lower()
                            for fi in fi_list
                        )
                        if exists:
                            qty = possible_qty
                            name = possible_name

            resolved = resolve_slang(name, config_data=self.config_data)
            price_val = 0
            unit_str = "unit"
            fi_list = self.config_data.get("frequent_items", [])
            for fi in fi_list:
                if isinstance(fi, dict) and fi.get("name") and fi["name"].lower() == resolved.lower():
                    price_val = int(float(fi.get("price", 0)))
                    unit_str = fi.get("unit", "unit")
                    break
            parsed_items.append((resolved, qty, "1 unit", price_val, False, unit_str))

    # -- 5. Merge clipboard items on top of defaults --
    for item_name, new_qty, box_size, price_val, is_courtesy, unit_str in parsed_items:
        resolved_name = item_name
        found = False
        for mi in merged_items:
            if mi["name"].lower() == resolved_name.lower():
                if is_full_requisition:
                    mi["qty"] = new_qty  # Overwrite for full requisition
                else:
                    mi["qty"] += new_qty  # Add for extra items
                if box_size: mi["box_size"] = box_size
                if price_val: mi["price"] = price_val
                mi["courtesy"] = is_courtesy
                if unit_str: mi["unit"] = unit_str
                found = True
                break
        if not found:
            merged_items.append({
                "name": resolved_name, "qty": new_qty, "box_size": box_size,
                "price": price_val, "courtesy": is_courtesy, "unit": unit_str
            })

    # -- 6. If NOT full requisition, also keep existing cargo rows --
    # Skip slang for structured items (names are already canonical)
    if has_structured:
        self._skip_slang = True
    if not is_full_requisition and merged_items:
        for mi in merged_items:
            found_in_ui = False
            for row in getattr(self, 'cargo_rows', []):
                try:
                    existing_name = row.get('name_var', None)
                    if existing_name and existing_name.get().strip().lower() == mi["name"].lower():
                        old_qty_str = row.get('qty_var', None)
                        if old_qty_str:
                            try:
                                old_qty = int(float(old_qty_str.get()))
                            except (ValueError, TypeError):
                                old_qty = 0
                            old_qty_str.set(str(old_qty + mi["qty"]))
                        found_in_ui = True
                        break
                except Exception:
                    continue
            if not found_in_ui:
                self.add_cargo_row_to_ui(
                    name=mi["name"], qty=str(mi["qty"]), box_size=mi["box_size"],
                    price=mi["price"], courtesy=mi["courtesy"], unit=mi["unit"]
                )
    else:
        # Full requisition: populate from merged_items
        for mi in merged_items:
            self.add_cargo_row_to_ui(
                name=mi["name"], qty=str(mi["qty"]), box_size=mi["box_size"],
                price=mi["price"], courtesy=mi["courtesy"], unit=mi["unit"]
            )

    # Reset slang skip flag
    self._skip_slang = False

    # Apply metadata if full requisition
    if is_full_requisition:
        _apply_metadata_to_ui()

    # Update grand total
    try:
        self.update_grand_total()
    except Exception:
        pass

    # Restore original clipboard
    try:
        self.clipboard_clear()
        self.clipboard_append(raw)
        self.update()
    except Exception:
        pass

    return True

main.RequisitionApp.import_from_clipboard = _patched_import_from_clipboard
print("[UI_PANEL] import_from_clipboard patched (structured + metadata + additive) OK",
      file=__import__('sys').stderr)



def apply_all_patches(main_module):
    """Called by entry.py after imports. Fix intro video path via descriptor."""
    _correct_video = None
    for candidate in [
        os.path.join(PATHS.resources, "intro_video.mp4"),
        os.path.join(PATHS.app_root, "intro_video.mp4"),
    ]:
        if os.path.isfile(candidate):
            _correct_video = candidate
            break

    if _correct_video:
        class _VideoPathDescriptor:
            """Intercepts video_path writes to fix hardcoded path."""
            def __get__(self, obj, objtype=None):
                if obj is None:
                    return self
                return getattr(obj, '_real_video_path', _correct_video)
            def __set__(self, obj, value):
                if value and 'Downloads' in str(value) and value.endswith('.mp4'):
                    object.__setattr__(obj, '_real_video_path', _correct_video)
                else:
                    object.__setattr__(obj, '_real_video_path', value)

        main_module.RequisitionApp.video_path = _VideoPathDescriptor()
