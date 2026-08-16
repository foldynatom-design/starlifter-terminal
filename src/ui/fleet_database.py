# -*- coding: utf-8 -*-
"""
fleet_database.py - Fleet Database / Databáze Flotily Manager.
Enables custom vessel naming, pairing with base ship models, and custom loadout persistence.
"""
import os
import json
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from path_config import PATHS
from src.utils.template_manager import TemplateManager

class FleetDatabaseModal(ctk.CTkToplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.title("Fleet Database / Databáze Flotily")
        self.geometry("780x580")
        self.configure(fg_color="#0e1319")
        self.attributes("-topmost", True)
        self.grab_set()

        self._load_custom_vessels()
        self._init_ui()

    def _load_custom_vessels(self):
        cfg_path = os.path.join(PATHS.config_dir, "config.json")
        self.custom_vessels = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.custom_vessels = data.get("custom_vessels", {})
            except Exception as e:
                print(f"[FleetDatabase] Error loading custom_vessels: {e}")

    def _save_custom_vessels(self):
        cfg_path = os.path.join(PATHS.config_dir, "config.json")
        data = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception: pass
        data["custom_vessels"] = self.custom_vessels
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            if hasattr(self.parent_app, 'config_data') and isinstance(self.parent_app.config_data, dict):
                self.parent_app.config_data["custom_vessels"] = self.custom_vessels

            self._sync_parent_ship_selector()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Fleet Database: {e}", parent=self)
            return False

    def _sync_parent_ship_selector(self):
        if hasattr(self.parent_app, 'ship_selector'):
            try:
                if hasattr(self.parent_app, 'config_data') and isinstance(self.parent_app.config_data, dict):
                    self.parent_app.config_data["custom_vessels"] = self.custom_vessels

                base_vessels = sorted(TemplateManager.load_vessels().keys())
                custom_names = sorted([f"{name} ({info.get('base_hull', '')})" for name, info in self.custom_vessels.items()])
                all_options = custom_names + [v for v in base_vessels if v not in custom_names]
                self.parent_app.ship_selector.configure(values=all_options[:10])
            except Exception as e:
                print(f"[FleetDatabase] Sync error: {e}")

    def _init_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="#161d26", corner_radius=8)
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        top_bar = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(10, 2))

        lbl_title = ctk.CTkLabel(
            top_bar, text="⚓ FLEET DATABASE / DATABÁZE FLOTILY",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#d4af37"
        )
        lbl_title.pack(side="left", anchor="w")

        btn_export = ctk.CTkButton(
            top_bar, text="📤 Export Loadouts (JSON)", width=150, height=28,
            fg_color="#1e293b", hover_color="#334155", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_export_loadouts
        )
        btn_export.pack(side="right", padx=(6, 0))

        btn_import = ctk.CTkButton(
            top_bar, text="📥 Import Loadouts (JSON)", width=150, height=28,
            fg_color="#0f766e", hover_color="#115e59", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_import_loadouts
        )
        btn_import.pack(side="right", padx=0)

        lbl_sub = ctk.CTkLabel(
            header_frame, text="Register custom ship names, pair with base hulls, manage loadouts & export/import across PCs.",
            font=ctk.CTkFont(size=12), text_color="#8a99a8"
        )
        lbl_sub.pack(anchor="w", padx=15, pady=(0, 10))

        # Main Layout (Left: Register New, Right: Active Fleet List)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=15, pady=5)

        # Left Column - Form
        form_frame = ctk.CTkFrame(body, fg_color="#161d26", corner_radius=8, width=320)
        form_frame.pack(side="left", fill="both", padx=(0, 10), pady=0)
        form_frame.pack_propagate(False)

        form_title = ctk.CTkLabel(form_frame, text="Register / Edit Vessel", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8")
        form_title.pack(anchor="w", padx=12, pady=(12, 8))

        # Input: Custom Ship Name
        ctk.CTkLabel(form_frame, text="Custom Vessel Name (e.g. UEE Helios):", font=ctk.CTkFont(size=11), text_color="#cbd5e1").pack(anchor="w", padx=12, pady=(5, 2))
        self.name_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter custom vessel callsign...", fg_color="#0e1319", text_color="#f8fafc")
        self.name_entry.pack(fill="x", padx=12, pady=(0, 10))

        def _clear_name_selection(event=None):
            try:
                if hasattr(self.name_entry, 'selection_clear'):
                    self.name_entry.selection_clear()
                if hasattr(self.name_entry, 'icursor'):
                    self.name_entry.icursor('end')
            except Exception: pass

        self.name_entry.bind("<FocusIn>", lambda e: self.after(10, _clear_name_selection), add="+")
        self.name_entry.bind("<Button-1>", lambda e: self.after(10, _clear_name_selection), add="+")

        # Input: Base Hull Model (FULL 331 Ships Database)
        ctk.CTkLabel(form_frame, text="Base Hull Model (Full DB Pairing):", font=ctk.CTkFont(size=11), text_color="#cbd5e1").pack(anchor="w", padx=12, pady=(5, 2))
        
        try:
            from fleet_helper import _load_uex_ships_db
            db_ships = getattr(self.parent_app, '_all_ship_names', [])
            if not db_ships:
                _s_db = _load_uex_ships_db()
                db_ships = sorted(set(v.get("name", v.get("short_name", k)) for k, v in _s_db.items() if v.get("name") or v.get("short_name"))) if _s_db else []
            loadout_ships = sorted(self.parent_app.config_data.get("vessels", {}).keys())
            base_models = sorted(set(loadout_ships + db_ships))
        except Exception:
            base_models = sorted(self.parent_app.config_data.get("vessels", {}).keys())

        if not base_models:
            base_models = ["Aegis Idris-M", "Aegis Idris-P", "Polaris", "Perseus", "Hammerhead", "Reclaimer", "Drake Caterpillar"]

        self.base_hull_combo = ctk.CTkComboBox(form_frame, values=base_models[:10], fg_color="#0e1319", dropdown_fg_color="#161d26")
        self.base_hull_combo.pack(fill="x", padx=12, pady=(0, 15))
        self.base_hull_combo.set("")  # Start empty — user must type or select

        _orig_fh_configure = self.base_hull_combo.configure
        def _capped_fh_configure(*args, **kwargs):
            if 'values' in kwargs and isinstance(kwargs['values'], (list, tuple)):
                kwargs['values'] = list(kwargs['values'])[:10]
            return _orig_fh_configure(*args, **kwargs)
        self.base_hull_combo.configure = _capped_fh_configure

        _orig_fh_open = getattr(self.base_hull_combo, '_open_dropdown_menu', None)
        def _position_fh_dropdown(*args, **kwargs):
            typed = self.base_hull_combo.get().strip()
            typed_low = typed.lower()
            words = typed_low.split()
            if words:
                filtered = [s for s in base_models if all(w in s.lower() for w in words)]
                _orig_fh_configure(values=filtered[:10] if filtered else base_models[:10])
            else:
                _orig_fh_configure(values=base_models[:10])
            if _orig_fh_open:
                try: _orig_fh_open(*args, **kwargs)
                except Exception: pass
            try:
                if hasattr(self.base_hull_combo, '_dropdown_menu') and self.base_hull_combo._dropdown_menu:
                    rx = self.base_hull_combo.winfo_rootx()
                    h = self.base_hull_combo.winfo_height()
                    ry = self.base_hull_combo.winfo_rooty() + h + 2
                    self.base_hull_combo._dropdown_menu.geometry(f"+{rx}+{ry}")
                    self.base_hull_combo._dropdown_menu.lift()
            except Exception: pass

        self.base_hull_combo._open_dropdown_menu = _position_fh_dropdown

        # Live filter base_hull_combo values as user types (150ms debounced + auto-open dropdown popup!)
        def _on_fleet_combo_key(event=None):
            if event and getattr(event, 'keysym', None) in ['Return', 'Tab', 'Up', 'Down', 'Escape']:
                return
            if hasattr(self.base_hull_combo, '_search_timer') and self.base_hull_combo._search_timer:
                try: self.base_hull_combo.after_cancel(self.base_hull_combo._search_timer)
                except Exception: pass

            def _do_fleet_filter():
                typed = self.base_hull_combo.get().strip()
                typed_low = typed.lower()
                if not typed:
                    _orig_fh_configure(values=base_models[:10])
                else:
                    words = typed_low.split()
                    matches = [s for s in base_models if all(w in s.lower() for w in words)]
                    _orig_fh_configure(values=matches[:10])
                try:
                    _position_fh_dropdown()
                except Exception: pass

            self.base_hull_combo._search_timer = self.base_hull_combo.after(150, _do_fleet_filter)

        self.base_hull_combo.bind('<KeyRelease>', _on_fleet_combo_key)
        try:
            if hasattr(self.base_hull_combo, '_entry') and self.base_hull_combo._entry:
                self.base_hull_combo._entry.bind('<KeyRelease>', _on_fleet_combo_key)
        except Exception: pass

        # Action Buttons
        btn_save = ctk.CTkButton(
            form_frame, text="Save to Fleet Database", command=self._on_save_vessel,
            fg_color="#0284c7", hover_color="#0369a1", font=ctk.CTkFont(weight="bold")
        )
        btn_save.pack(fill="x", padx=12, pady=(5, 5))

        btn_copy_current = ctk.CTkButton(
            form_frame, text="Import Current UI Loadout", command=self._on_import_current_loadout,
            fg_color="#334155", hover_color="#475569"
        )
        btn_copy_current.pack(fill="x", padx=12, pady=(5, 10))

        # Right Column - Registered Fleet List
        list_frame = ctk.CTkFrame(body, fg_color="#161d26", corner_radius=8)
        list_frame.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        list_title = ctk.CTkLabel(list_frame, text="Registered Vessels in Fleet", font=ctk.CTkFont(size=13, weight="bold"), text_color="#e2e8f0")
        list_title.pack(anchor="w", padx=12, pady=(12, 8))

        self.scroll_list = ctk.CTkScrollableFrame(list_frame, fg_color="#0e1319", corner_radius=6)
        self.scroll_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._refresh_fleet_list()

    def _refresh_fleet_list(self):
        for child in list(self.scroll_list.winfo_children()):
            try: child.destroy()
            except Exception: pass

        if not self.custom_vessels:
            lbl_empty = ctk.CTkLabel(self.scroll_list, text="No custom vessels registered yet.", text_color="#64748b")
            lbl_empty.pack(padx=10, pady=20)
            return

        for ship_name, info in sorted(self.custom_vessels.items()):
            row = ctk.CTkFrame(self.scroll_list, fg_color="#1e293b", corner_radius=6)
            row.pack(fill="x", padx=5, pady=4)

            base_model = info.get("base_hull", "Unknown")
            loadout_cnt = len(info.get("loadout", []))

            info_lbl = ctk.CTkLabel(
                row, text=f"🚢 {ship_name}  [{base_model}]  •  {loadout_cnt} items",
                font=ctk.CTkFont(size=12, weight="bold"), text_color="#f1f5f9"
            )
            info_lbl.pack(side="left", padx=10, pady=8)

            btn_del = ctk.CTkButton(
                row, text="Delete", width=55, fg_color="#991b1b", hover_color="#b91c1c",
                command=lambda name=ship_name: self._on_delete_vessel(name)
            )
            btn_del.pack(side="right", padx=(5, 10), pady=6)

            btn_load = ctk.CTkButton(
                row, text="Select", width=55, fg_color="#0284c7", hover_color="#0369a1",
                command=lambda name=ship_name, b_model=base_model: self._on_select_vessel(name, b_model)
            )
            btn_load.pack(side="right", padx=5, pady=6)

    def _on_save_vessel(self):
        callsign = self.name_entry.get().strip()
        base_hull = self.base_hull_combo.get().strip()

        if not callsign:
            messagebox.showerror("Error", "Please enter a custom vessel callsign.", parent=self)
            return

        if not base_hull:
            messagebox.showerror("Error", "Please select a base hull model.", parent=self)
            return

        # Fetch default loadout from base hull if available
        all_vessels = TemplateManager.load_vessels()
        base_loadout = all_vessels.get(base_hull, [])

        self.custom_vessels[callsign] = {
            "base_hull": base_hull,
            "loadout": base_loadout
        }

        if self._save_custom_vessels():
            messagebox.showinfo("Success", f"Vessel '{callsign}' registered cleanly as {base_hull}!", parent=self)
            self.name_entry.delete(0, 'end')
            self._refresh_fleet_list()

    def _on_import_current_loadout(self):
        callsign = self.name_entry.get().strip()
        base_hull = self.base_hull_combo.get().strip()

        if not callsign:
            messagebox.showerror("Error", "Please enter custom vessel name first.", parent=self)
            return

        current_rows = []
        if hasattr(self.parent_app, 'cargo_rows'):
            for row in getattr(self.parent_app, 'cargo_rows', []):
                try:
                    name_v = row.get('name_var', None)
                    qty_v = row.get('qty_var', None)
                    box_v = row.get('box_size_var', None)
                    unit_v = row.get('unit_var', None)
                    price_v = row.get('price_var', None)
                    courtesy_v = row.get('courtesy_var', None)

                    if name_v and name_v.get().strip():
                        current_rows.append({
                            "name": name_v.get().strip(),
                            "qty": qty_v.get() if qty_v else "",
                            "box_size": box_v.get() if box_v else "1 SCU",
                            "unit": unit_v.get() if unit_v else "",
                            "price": price_v.get() if price_v else 0,
                            "courtesy": courtesy_v.get() if courtesy_v else False
                        })
                except Exception: pass

        self.custom_vessels[callsign] = {
            "base_hull": base_hull,
            "loadout": current_rows
        }

        if self._save_custom_vessels():
            messagebox.showinfo("Success", f"Imported {len(current_rows)} cargo items from current UI into '{callsign}'!", parent=self)
            self._refresh_fleet_list()

    def _on_delete_vessel(self, callsign):
        if callsign in self.custom_vessels:
            del self.custom_vessels[callsign]
            self._save_custom_vessels()
            self._refresh_fleet_list()

    def _on_select_vessel(self, callsign, base_hull):
        if hasattr(self.parent_app, 'ship_selector'):
            formatted_name = f"{callsign} ({base_hull})"
            if hasattr(self.parent_app, 'config_data') and isinstance(self.parent_app.config_data, dict):
                self.parent_app.config_data["custom_vessels"] = self.custom_vessels

            vals = list(self.parent_app.ship_selector.cget("values"))
            if formatted_name not in vals:
                vals.insert(0, formatted_name)
                self.parent_app.ship_selector.configure(values=vals)
            self.parent_app.ship_selector.set(formatted_name)

            if hasattr(self.parent_app, 'load_vessel_loadout'):
                try: self.parent_app.load_vessel_loadout(formatted_name)
                except Exception as e: print(f"[FleetDatabase] load_vessel_loadout error: {e}")
            elif hasattr(self.parent_app, 'on_ship_changed'):
                try: self.parent_app.on_ship_changed(formatted_name)
                except Exception as e: print(f"[FleetDatabase] on_ship_changed error: {e}")

        self.destroy()

    def _on_export_loadouts(self):
        fpath = filedialog.asksaveasfilename(
            parent=self,
            title="Export Fleet Loadouts to JSON",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialfile="starlifter_fleet_loadouts.json"
        )
        if not fpath:
            return
        
        ok, res = TemplateManager.export_vessels_to_json(fpath)
        if ok:
            messagebox.showinfo("Export Successful", f"Successfully exported {res} fleet loadouts and configurations to:\n{fpath}", parent=self)
        else:
            messagebox.showerror("Export Failed", f"Could not export loadouts: {res}", parent=self)

    def _on_import_loadouts(self):
        fpath = filedialog.askopenfilename(
            parent=self,
            title="Import Fleet Loadouts from JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not fpath:
            return
        
        ok, res = TemplateManager.import_vessels_from_json(fpath)
        if ok:
            self._load_custom_vessels()
            self._refresh_fleet_list()
            self._sync_parent_ship_selector()
            messagebox.showinfo("Import Successful", f"Successfully imported {res} fleet loadouts and templates!\nAll ship models and configurations are now ready.", parent=self)
        else:
            messagebox.showerror("Import Failed", f"Could not import loadouts: {res}", parent=self)
