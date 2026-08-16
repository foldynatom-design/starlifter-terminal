import tkinter as tk
import customtkinter as ctk
import json
import os
from tkinter import messagebox

from path_config import PATHS

_price_cache = {}

def get_package_item_price(item_name, config_data=None):
    """Lookup exact price for an item name from:
    1) frequent_items.json (or config_data['frequent_items'])
    2) uex_items_trade_db.json
    Returns numeric price (int/float) if > 0, otherwise 'Undefined'.
    """
    if not item_name:
        return "Undefined"
        
    iname_clean = str(item_name).strip()
    iname_low = iname_clean.lower()
    
    if iname_low in _price_cache:
        return _price_cache[iname_low]

    # 1. Lookup in frequent_items
    try:
        from path_config import load_frequent_items
        fi = load_frequent_items(config_data)
        for entry in fi:
            if isinstance(entry, dict):
                fn = str(entry.get("name", "")).strip().lower()
                if fn == iname_low:
                    try:
                        p = float(entry.get("price", 0))
                        if p > 0:
                            res = int(p) if p.is_integer() else p
                            _price_cache[iname_low] = res
                            return res
                    except Exception: pass
        for entry in fi:
            if isinstance(entry, dict):
                fn = str(entry.get("name", "")).strip().lower()
                if fn and (fn in iname_low or iname_low in fn):
                    try:
                        p = float(entry.get("price", 0))
                        if p > 0:
                            res = int(p) if p.is_integer() else p
                            _price_cache[iname_low] = res
                            return res
                    except Exception: pass
    except Exception: pass

    # 2. Lookup in uex_items_trade_db.json
    try:
        from path_config import PATHS
        uex_path = os.path.join(PATHS.resources, "uex_items_trade_db.json")
        if os.path.exists(uex_path):
            with open(uex_path, "r", encoding="utf-8") as f:
                uex_db = json.load(f)
            
            if iname_low in uex_db:
                locs = uex_db[iname_low].get("locations", [])
                prices = [l.get("buy", 0) for l in locs if isinstance(l, dict) and l.get("buy", 0) > 0]
                if prices:
                    p = min(prices)
                    res = int(p) if float(p).is_integer() else float(p)
                    _price_cache[iname_low] = res
                    return res
                    
            for k, val in uex_db.items():
                if isinstance(val, dict):
                    db_n = str(val.get("name", k)).strip().lower()
                    if db_n == iname_low or k == iname_low or (len(iname_low) > 4 and (db_n in iname_low or iname_low in db_n)):
                        locs = val.get("locations", [])
                        prices = [l.get("buy", 0) for l in locs if isinstance(l, dict) and l.get("buy", 0) > 0]
                        if prices:
                            p = min(prices)
                            res = int(p) if float(p).is_integer() else float(p)
                            _price_cache[iname_low] = res
                            return res
    except Exception: pass

    _price_cache[iname_low] = "Undefined"
    return "Undefined"


BUILT_IN_PACKAGES = {
    "All Uniform Sets": [
        {"name": "Aril Helmet", "qty": 1},
        {"name": "Aril Core", "qty": 1},
        {"name": "Aril Arms", "qty": 1},
        {"name": "Aril Legs", "qty": 1},
        {"name": "Aril Backpack", "qty": 1},
        {"name": "ORC-mkX Helmet Twilight", "qty": 1},
        {"name": "ORC-mkX Core Twilight", "qty": 1},
        {"name": "ORC-mkX Arms Twilight", "qty": 1},
        {"name": "ORC-mkX Legs Twilight", "qty": 1},
        {"name": "CSP-68M Backpack", "qty": 1},
        {"name": "ORC-mkX Helmet Woodland", "qty": 1},
        {"name": "ORC-mkX Core Woodland", "qty": 1},
        {"name": "ORC-mkX Arms Woodland", "qty": 1},
        {"name": "ORC-mkX Legs Woodland", "qty": 1},
        {"name": "ADP-mk4 Helmet Woodland", "qty": 1},
        {"name": "ADP-mk4 Core Woodland", "qty": 1},
        {"name": "ADP-mk4 Arms Woodland", "qty": 1},
        {"name": "ADP-mk4 Legs Woodland", "qty": 1},
        {"name": "CSP-68H Backpack", "qty": 1},
        {"name": "Field Recon Suit Helmet", "qty": 1},
        {"name": "Field Recon Suit Core", "qty": 1},
        {"name": "Field Recon Suit Arms", "qty": 1},
        {"name": "Field Recon Suit Legs", "qty": 1},
        {"name": "CSP-68L Backpack", "qty": 1},
        {"name": "TCS-4 Undersuit", "qty": 5},
        {"name": "Adiva Jacket Imperial", "qty": 1},
        {"name": "Adiva Jacket Dark Green", "qty": 1},
        {"name": "Adiva Jacket Blue", "qty": 1},
        {"name": "Adiva Jacket Red", "qty": 1},
        {"name": "Adiva Jacket White", "qty": 1},
        {"name": "Adiva Jacket Yellow", "qty": 1},
        {"name": "Lemarque Pants", "qty": 6},
        {"name": "Deo Black Shirt", "qty": 6},
        {"name": "Prim Black Shoes", "qty": 6},
        {"name": "Ventra Gloves Black", "qty": 6}
    ],
    "All Officer Casual Duty Uniform": [
        {"name": "Adiva Jacket Imperial", "qty": 1},
        {"name": "Adiva Jacket Dark Green", "qty": 1},
        {"name": "Adiva Jacket Blue", "qty": 1},
        {"name": "Adiva Jacket Red", "qty": 1},
        {"name": "Adiva Jacket White", "qty": 1},
        {"name": "Adiva Jacket Yellow", "qty": 1},
        {"name": "Lemarque Pants", "qty": 6},
        {"name": "Deo Black Shirt", "qty": 6},
        {"name": "Prim Black Shoes", "qty": 6},
        {"name": "Ventra Gloves Black", "qty": 6}
    ],
    "Starlifter uniform Set": [
        {"name": "Aril Helmet", "qty": 1},
        {"name": "Aril Core", "qty": 1},
        {"name": "Aril Arms", "qty": 1},
        {"name": "Aril Legs", "qty": 1},
        {"name": "Aril Backpack", "qty": 1},
        {"name": "TCS-4 Undersuit", "qty": 1}
    ],
    "Standart Navy uniform": [
        {"name": "ORC-mkX Helmet Twilight", "qty": 1},
        {"name": "ORC-mkX Core Twilight", "qty": 1},
        {"name": "ORC-mkX Arms Twilight", "qty": 1},
        {"name": "ORC-mkX Legs Twilight", "qty": 1},
        {"name": "CSP-68M Backpack", "qty": 1},
        {"name": "TCS-4 Undersuit", "qty": 1}
    ],
    "Marine medium": [
        {"name": "ORC-mkX Helmet Woodland", "qty": 1},
        {"name": "ORC-mkX Core Woodland", "qty": 1},
        {"name": "ORC-mkX Arms Woodland", "qty": 1},
        {"name": "ORC-mkX Legs Woodland", "qty": 1},
        {"name": "CSP-68M Backpack", "qty": 1},
        {"name": "TCS-4 Undersuit", "qty": 1}
    ],
    "marine heavy": [
        {"name": "ADP-mk4 Helmet Woodland", "qty": 1},
        {"name": "ADP-mk4 Core Woodland", "qty": 1},
        {"name": "ADP-mk4 Arms Woodland", "qty": 1},
        {"name": "ADP-mk4 Legs Woodland", "qty": 1},
        {"name": "CSP-68H Backpack", "qty": 1},
        {"name": "TCS-4 Undersuit", "qty": 1}
    ],
    "marine light": [
        {"name": "Field Recon Suit Helmet", "qty": 1},
        {"name": "Field Recon Suit Core", "qty": 1},
        {"name": "Field Recon Suit Arms", "qty": 1},
        {"name": "Field Recon Suit Legs", "qty": 1},
        {"name": "CSP-68L Backpack", "qty": 1},
        {"name": "TCS-4 Undersuit", "qty": 1}
    ],
    "Officer Casual Duty Uniform (Imperial)": [
        {"name": "Adiva Jacket Imperial", "qty": 1},
        {"name": "Lemarque Pants", "qty": 1},
        {"name": "Deo Black Shirt", "qty": 1},
        {"name": "Prim Black Shoes", "qty": 1},
        {"name": "Ventra Gloves Black", "qty": 1}
    ],
    "Officer Casual Duty Uniform (Dark Green)": [
        {"name": "Adiva Jacket Dark Green", "qty": 1},
        {"name": "Lemarque Pants", "qty": 1},
        {"name": "Deo Black Shirt", "qty": 1},
        {"name": "Prim Black Shoes", "qty": 1},
        {"name": "Ventra Gloves Black", "qty": 1}
    ],
    "Officer Casual Duty Uniform (Blue)": [
        {"name": "Adiva Jacket Blue", "qty": 1},
        {"name": "Lemarque Pants", "qty": 1},
        {"name": "Deo Black Shirt", "qty": 1},
        {"name": "Prim Black Shoes", "qty": 1},
        {"name": "Ventra Gloves Black", "qty": 1}
    ],
    "Officer Casual Duty Uniform (Red)": [
        {"name": "Adiva Jacket Red", "qty": 1},
        {"name": "Lemarque Pants", "qty": 1},
        {"name": "Deo Black Shirt", "qty": 1},
        {"name": "Prim Black Shoes", "qty": 1},
        {"name": "Ventra Gloves Black", "qty": 1}
    ],
    "Officer Casual Duty Uniform (White)": [
        {"name": "Adiva Jacket White", "qty": 1},
        {"name": "Lemarque Pants", "qty": 1},
        {"name": "Deo Black Shirt", "qty": 1},
        {"name": "Prim Black Shoes", "qty": 1},
        {"name": "Ventra Gloves Black", "qty": 1}
    ],
    "Squadron Pilot Uniform": [
        {"name": "Tailwind Flight Suit", "qty": 1},
        {"name": "Aril Helmet", "qty": 1},
        {"name": "P4-AR Rifle", "qty": 1},
        {"name": "P4-AR Magazine", "qty": 4},
        {"name": "Medpen", "qty": 2}
    ],
    "Officer Casual Duty Uniform (Yellow)": [
        {"name": "Adiva Jacket Yellow", "qty": 1},
        {"name": "Lemarque Pants", "qty": 1},
        {"name": "Deo Black Shirt", "qty": 1},
        {"name": "Prim Black Shoes", "qty": 1},
        {"name": "Ventra Gloves Black", "qty": 1}
    ]
}


class CreatePackageModal(ctk.CTkToplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.title("Create Custom Package")
        self.geometry("520x620")
        self.parent_app = parent_app
        
        self.items = []
        self.valid_items = self._load_all_registered_items()
        self._build_ui()
        
    def _load_all_registered_items(self):
        items = []

        # 1. From parent_app config_data (registered database items)
        if hasattr(self.parent_app, 'config_data') and isinstance(self.parent_app.config_data, dict):
            fi = self.parent_app.config_data.get("frequent_items", [])
            for entry in fi:
                if isinstance(entry, dict) and entry.get("name"):
                    items.append(entry["name"])
                elif isinstance(entry, str) and entry.strip():
                    items.append(entry.strip())

        # 2. From comboboxes on parent_app
        for combo_attr in ['single_combo', '_single_combo', 'quick_add_combo', 'item_combo', 'item_dropdown']:
            c_widget = getattr(self.parent_app, combo_attr, None)
            if c_widget and hasattr(c_widget, 'cget'):
                try:
                    vals = c_widget.cget("values")
                    if vals:
                        items.extend([str(v) for v in vals if v])
                except Exception: pass

        # 3. Standard equipment & gear fallback list
        standard_items = [
            "Argo Ore Pod", "MISC Ore Pod", "Drake Ore Pod", "Greycat ROC Ore Pod", "GEO Resource Pod",
            "Bonito Fuel Pod", "CR-60 Fuel Pod", "Gargant Fuel Pod", "GSX-EX Fuel Pod", "GSX-HP Fuel Pod", "GSX-RF Fuel Pod", "Nemec Fuel Pod", "Rumford Fuel Pod",
            "Bendix Fuel Nozzle", "Ezra Fuel Nozzle", "Lindstrom Fuel Nozzle", "Marlin Fuel Nozzle", "Torrez Fuel Nozzle",
            "Hofstede S1 Mining Head", "Hofstede S2 Mining Head", "Klein S1 Mining Head", "Klein S2 Mining Head",
            "Helix S1 Mining Head", "Helix S2 Mining Head", "Lancet MH1 Mining Head", "Lancet MH2 Mining Head",
            "Arbor MH1 Mining Head", "Arbor MH2 Mining Head", "Impact I Mining Head", "Impact II Mining Head",
            "BoreMax Mining Gadget", "OptiMax Mining Gadget", "WaveShift Mining Gadget", "Sabir Mining Gadget", "Stampede Mining Gadget",
            "FLTR-XL Passive Mining Module", "Rime Active Mining Module", "Surge Active Mining Module", "Stampede Active Mining Module",
            "Focus Active Mining Module", "Torrent Active Mining Module", "Brand Passive Mining Module", "Lifesaver Passive Mining Module",
            "Cambio SRT", "Cambio SRT Canister", "TruHold Salvage Head", "Cinch Salvage Module", "Abrade Salvage Module", "Trawler Salvage Module", "Cinematic Salvage Module",
            "MaxLift Tractor Beam", "Maxlift Tractor Beam Battery", "TruHold Tractor Beam Attachment", "OreBit Mining Attachment", "Pyro Multi-Tool",
            "FR-86 Shield Generator (Size 3)", "FR-76 Shield Generator (Size 2)", "FR-66 Shield Generator (Size 1)",
            "Crossfield Quantum Drive (Size 2)", "VK-00 Quantum Drive (Size 1)", "Atlas Quantum Drive (Size 1)", "TS-2 Quantum Drive (Size 3)",
            "JS-500 Power Plant (Size 3)", "JS-400 Power Plant (Size 2)", "JS-300 Power Plant (Size 1)",
            "CoolCore Industrial Cooler (Size 3)", "Eridani Cooler (Size 2)", "Ultra-Flow Cooler (Size 1)",
            "M7A Laser Cannon (Size 5)", "M6A Laser Cannon (Size 4)", "M5A Laser Cannon (Size 3)", "M4A Laser Cannon (Size 2)",
            "CF-557 Giga-Panther Repeater (Size 5)", "CF-447 Rhino Laser Repeater (Size 4)", "CF-337 Panther Laser Repeater (Size 3)", "CF-227 Badger Laser Repeater (Size 2)", "CF-117 Bulldog Laser Repeater (Size 1)",
            "Tarantula GT-870 Ballistic Cannon (Size 3)", "Deadbolt IV Ballistic Cannon (Size 4)", "Deadbolt V Ballistic Cannon (Size 5)",
            "Argus IX Torpedo", "Typhoon IX Torpedo", "Seeker IX Torpedo", "Dominator II Missile", "Tempest II Missile", "Arrester III Missile", "Stalker IV Missile",
            "Aril Helmet", "Aril Core", "Aril Arms", "Aril Legs", "Aril Backpack",
            "TCS-4 Undersuit", "CSP-68H Backpack", "CSP-68M Backpack", "CSP-68L Backpack",
            "Adiva Imperial Jacket", "Adiva Yellow Jacket", "Adiva White Jacket", "Adiva Blue Jacket", "Adiva Red Jacket", "Adiva Dark Green Jacket",
            "Lemarque Pants", "Deo Black Shirt", "Prim Black Shoes", "Ventra Gloves Black",
            "ORC-mkX Helmet Twilight", "ORC-mkX Core Twilight", "ORC-mkX Arms Twilight", "ORC-mkX Legs Twilight",
            "ORC-mkX Helmet Woodland", "ORC-mkX Core Woodland", "ORC-mkX Arms Woodland", "ORC-mkX Legs Woodland",
            "ADP-mk4 Helmet Woodland", "ADP-mk4 Core Woodland", "ADP-mk4 Arms Woodland", "ADP-mk4 Legs Woodland",
            "Field Recon Suit Helmet", "Field Recon Suit Core", "Field Recon Suit Arms", "Field Recon Suit Legs",
            "P4-AR Nightstalker Rifle", "P4-AR Rifle", "FS-9 LMG", "S-38 Pistol", "P8-SC SMG", "P6-LR Sniper Rifle", "BR2 Shotgun"
        ]
        items.extend(standard_items)

        # Deduplicate & filter out invalid entries
        clean = []
        seen = set()
        for it in items:
            name = str(it).strip()
            if not name or name.lower().startswith("package:") or "package:" in name.lower(): continue
            if any(s in name.lower() for s in ["test_", "placeholder", "fake_"]): continue
            if name.lower() not in seen:
                seen.add(name.lower())
                clean.append(name)

        return sorted(clean)

    def _build_ui(self):
        # Top Header Bar with Export/Import
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(10, 5))
        
        lbl_title = ctk.CTkLabel(
            top_bar, text="📦 PACKAGE CREATOR",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#d4af37"
        )
        lbl_title.pack(side="left", anchor="w")

        btn_export = ctk.CTkButton(
            top_bar, text="📤 Export (JSON)", width=110, height=26,
            fg_color="#1e293b", hover_color="#334155", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_export_packages
        )
        btn_export.pack(side="right", padx=(5, 0))

        btn_import = ctk.CTkButton(
            top_bar, text="📥 Import (JSON)", width=110, height=26,
            fg_color="#0f766e", hover_color="#115e59", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_import_packages
        )
        btn_import.pack(side="right", padx=0)

        # Package Name
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(header_frame, text="Package Name:").pack(side="left")
        self.name_entry = ctk.CTkEntry(header_frame, width=320, placeholder_text="e.g. Squad Heavy Loadout...")
        self.name_entry.pack(side="left", padx=10)
        
        # Base Preset Selector
        preset_frame = ctk.CTkFrame(self, fg_color="transparent")
        preset_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(preset_frame, text="Load Preset:").pack(side="left")
        
        self.preset_var = tk.StringVar(value="None")
        presets = ["None"] + list(BUILT_IN_PACKAGES.keys())
        preset_combo = ctk.CTkComboBox(preset_frame, values=presets, variable=self.preset_var, command=self._load_preset)
        preset_combo.pack(side="left", padx=10)
        
        # Items Table
        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add Item Section with Autocomplete Dropdown
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.pack(fill="x", padx=10, pady=10)
        
        self.new_item_var = tk.StringVar()
        self.new_item_combo = ctk.CTkComboBox(add_frame, values=self.valid_items[:10], variable=self.new_item_var, width=260)
        self.new_item_combo.pack(side="left", padx=5)

        # Autocomplete keyboard handler (300ms debounced)
        def _on_custom_pkg_key(event=None):
            if event and getattr(event, 'keysym', None) in ['Return', 'Tab', 'Up', 'Down', 'Escape']:
                return
            if hasattr(self.new_item_combo, '_search_timer') and self.new_item_combo._search_timer:
                try: self.new_item_combo.after_cancel(self.new_item_combo._search_timer)
                except Exception: pass

            def _do_pkg_filter():
                typed = self.new_item_combo.get().strip().lower()
                if not typed or len(typed) < 1:
                    self.new_item_combo.configure(values=self.valid_items[:10], state="normal")
                    return
                import re
                words = typed.split()
                matched = [
                    item for item in self.valid_items
                    if all(re.search(r'(?:^|\b|\s|_|-)' + re.escape(w), item.lower()) for w in words)
                ]
                if matched:
                    self.new_item_combo.configure(values=matched[:10], state="normal")
                    try:
                        self.new_item_combo._open_dropdown_menu()
                        if hasattr(self.new_item_combo, '_dropdown_menu') and self.new_item_combo._dropdown_menu:
                            rx = self.new_item_combo.winfo_rootx()
                            ry = self.new_item_combo.winfo_rooty() + self.new_item_combo.winfo_height() + 2
                            self.new_item_combo._dropdown_menu.geometry(f"+{rx}+{ry}")
                    except Exception: pass
                else:
                    self.new_item_combo.configure(values=[], state="normal")

            self.new_item_combo._search_timer = self.new_item_combo.after(500, _do_pkg_filter)

        self.new_item_combo.bind('<KeyRelease>', _on_custom_pkg_key)
        
        self.new_qty_var = tk.StringVar(value="1")
        qty_entry = ctk.CTkEntry(add_frame, textvariable=self.new_qty_var, width=45)
        qty_entry.pack(side="left", padx=5)
        
        add_btn = ctk.CTkButton(add_frame, text="Add Item", width=75, command=self._add_item)
        add_btn.pack(side="left", padx=5)
        
        # Save Section
        save_btn = ctk.CTkButton(self, text="Save Custom Package", fg_color="#008b8b", hover_color="#00a8a8", command=self._save_package)
        save_btn.pack(pady=10)
        
        self._refresh_table()

    def _on_export_packages(self):
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Export Packages to JSON",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialfile="starlifter_packages_export.json"
        )
        if not filepath:
            return
        try:
            from src.utils.template_manager import TemplateManager
            ok, count = TemplateManager.export_packages_to_json(filepath)
            if ok:
                messagebox.showinfo("Export Successful", f"Successfully exported {count} packages to:\n{filepath}", parent=self)
            else:
                messagebox.showerror("Export Failed", f"Could not export packages:\n{count}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", f"Unexpected error: {e}", parent=self)

    def _on_import_packages(self):
        filepath = filedialog.askopenfilename(
            parent=self,
            title="Import Packages from JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        try:
            from src.utils.template_manager import TemplateManager
            ok, count = TemplateManager.import_packages_from_json(filepath)
            if ok:
                messagebox.showinfo("Import Successful", f"Successfully imported {count} packages from:\n{filepath}", parent=self)
                # Refresh parent app package combos
                if hasattr(self.parent_app, 'package_combo') and self.parent_app.package_combo:
                    try:
                        all_pkgs = list(TemplateManager.load_packages().keys())
                        self.parent_app.package_combo.configure(values=all_pkgs)
                    except Exception: pass
            else:
                messagebox.showerror("Import Failed", f"Could not import packages:\n{count}", parent=self)
        except Exception as e:
            messagebox.showerror("Import Error", f"Unexpected error: {e}", parent=self)

    def _load_preset(self, preset_name):
        if preset_name in BUILT_IN_PACKAGES:
            # Append preset items
            for preset_item in BUILT_IN_PACKAGES[preset_name]:
                self.items.append({"name": preset_item["name"], "qty": preset_item["qty"]})
            self._refresh_table()
            
    def _add_item(self):
        name = self.new_item_var.get().strip()
        try:
            qty = int(self.new_qty_var.get().strip())
        except ValueError:
            qty = 1
            
        if name and qty > 0:
            self.items.append({"name": name, "qty": qty})
            self._refresh_table()
            
    def _refresh_table(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()
            
        for i, item in enumerate(self.items):
            row_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            p_val = item.get("price")
            if p_val is None or p_val == 0 or p_val == "0":
                p_val = get_package_item_price(item["name"])
                item["price"] = p_val
            
            p_str = f"{p_val:,} aUEC" if isinstance(p_val, (int, float)) and p_val > 0 else str(p_val)
            
            ctk.CTkLabel(row_frame, text=item["name"], width=180, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=f"x{item['qty']}", width=35).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=p_str, width=100, anchor="e", text_color="#d4af37" if isinstance(p_val, (int, float)) else "#ff7777").pack(side="left", padx=5)
            
            del_btn = ctk.CTkButton(row_frame, text="X", width=30, fg_color="#cc4444", command=lambda idx=i: self._remove_item(idx))
            del_btn.pack(side="right", padx=5)
            
    def _remove_item(self, idx):
        if 0 <= idx < len(self.items):
            self.items.pop(idx)
            self._refresh_table()
            
    def _save_package(self):
        pkg_name = self.name_entry.get().strip()
        if not pkg_name:
            messagebox.showerror("Error", "Package Name cannot be empty.", parent=self)
            return
            
        if not self.items:
            messagebox.showerror("Error", "Package must contain at least one item.", parent=self)
            return
            
        try:
            from src.utils.template_manager import TemplateManager
            if not TemplateManager.save_package(pkg_name, self.items):
                messagebox.showerror("Error", "Failed to save package via TemplateManager.", parent=self)
                return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save package: {e}", parent=self)
            return
            
        # Update parent UI combo
        if hasattr(self.parent_app, 'package_combo') and self.parent_app.package_combo:
            try:
                current_vals = list(self.parent_app.package_combo.cget("values"))
                if pkg_name not in current_vals:
                    current_vals.append(pkg_name)
                    self.parent_app.package_combo.configure(values=current_vals)
            except Exception: pass
        if hasattr(self.parent_app, 'package_var') and self.parent_app.package_var is not None:
            try:
                self.parent_app.package_var.set(pkg_name)
            except Exception: pass
                
        messagebox.showinfo("Success", f"Package '{pkg_name}' saved successfully.", parent=self)
        self.destroy()

def open_create_package_modal(parent_app):
    CreatePackageModal(parent_app)
