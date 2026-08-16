import tkinter as tk
import customtkinter as ctk
import json
import os
from tkinter import messagebox

from path_config import PATHS, load_frequent_items

CATEGORY_ITEMS_MAP = {
    "FPS Armor": [
        "Aril Helmet", "Aril Core", "Aril Arms", "Aril Legs", "Aril Backpack",
        "Aril Helmet Hazard", "Aril Core Hazard", "Aril Arms Hazard", "Aril Legs Hazard", "Aril Backpack Hazard",
        "TCS-4 Undersuit", "CSP-68H Backpack", "CSP-68M Backpack", "CSP-68L Backpack",
        "ORC-mkX Helmet Twilight", "ORC-mkX Core Twilight", "ORC-mkX Arms Twilight", "ORC-mkX Legs Twilight",
        "ADP-mk4 Helmet Woodland", "ADP-mk4 Core Woodland", "ADP-mk4 Arms Woodland", "ADP-mk4 Legs Woodland",
        "Field Recon Helmet", "Field Recon Core"
    ],
    "Clothing": [
        "Adiva Jacket Imperial", "Adiva Jacket Yellow", "Adiva Jacket White", "Adiva Jacket Blue", "Adiva Jacket Red", "Adiva Jacket Dark Green",
        "Lemarque Pants", "Deo Shirt Black", "Prim Shoes Black", "Ventra Gloves Black", "Tailwind Flight Suit"
    ],
    "Weapons": [
        "P4-AR Rifle", "FS-9 LMG", "S-38 Pistol", "P8-SC SMG", "P6-LR Sniper Rifle", "BR-2 Shotgun",
        "Arclight Pistol", "C54 SMG", "Gallant Rifle", "Custodian SMG", "Devastator Shotgun",
        "Size 1 Ammunition", "Size 2 Ammunition", "Size 3 Ammunition", "Size 4 Ammunition", "Size 5 Ammunition"
    ],
    "Ship Weapons & Missiles": [
        "M7A Laser Cannon (Size 5)", "M6A Laser Cannon (Size 4)", "M5A Laser Cannon (Size 3)", "M4A Laser Cannon (Size 2)",
        "CF-557 Giga-Panther Repeater (Size 5)", "CF-447 Rhino Laser Repeater (Size 4)", "CF-337 Panther Laser Repeater (Size 3)", "CF-227 Badger Laser Repeater (Size 2)", "CF-117 Bulldog Laser Repeater (Size 1)",
        "Argus IX Torpedo", "Typhoon IX Torpedo", "Seeker IX Torpedo", "Dominator II Missile", "Tempest II Missile", "Arrester III Missile", "Stalker IV Missile",
        "Decoy Countermeasures", "Noise Countermeasures"
    ],
    "Ship Components": [
        "FR-86 Shield Generator (Size 3)", "FR-76 Shield Generator (Size 2)", "FR-66 Shield Generator (Size 1)",
        "Crossfield Quantum Drive (Size 2)", "VK-00 Quantum Drive (Size 1)", "Atlas Quantum Drive (Size 1)", "TS-2 Quantum Drive (Size 3)",
        "JS-500 Power Plant (Size 3)", "JS-400 Power Plant (Size 2)", "JS-300 Power Plant (Size 1)",
        "CoolCore Industrial Cooler (Size 3)", "Eridani Cooler (Size 2)", "Ultra-Flow Cooler (Size 1)"
    ],
    "Industrial Utilities": [
        "MaxLift Tractor Beam", "MaxLift Tractor Beam Battery", "Cambio SRT", "Cambio SRT Canister",
        "Pyro Multi-Tool", "OreBit Mining Attachment", "TruHold Tractor Beam Attachment",
        "Hofstede S1 Mining Head", "Helix S1 Mining Head", "Lancet MH1 Mining Head", "Arbor MH1 Mining Head",
        "BoreMax Mining Gadget", "OptiMax Mining Gadget", "WaveShift Mining Gadget", "Sabir Mining Gadget", "Stampede Mining Gadget"
    ],
    "Food & Drinks": [
        "CRUZ Lux", "CRUZ Dark", "CRUZ Flow", "Tormenta Energy Drink", "Pips Drink", "Burrito", "ReadyMeal"
    ],
    "Medical": [
        "MedPen (Hemozal)", "OxyPen", "DetoxPen", "AdrenaPen", "CorticoPen", "Paramed Medical Device", "Refill Canister (Hemozal)"
    ],
    "Commodities & Cargo": [
        "Stor-All 1 SCU Cargo Container", "Stor-All 2 SCU Cargo Container", "Stor-All 4 SCU Cargo Container", "Stor-All 8 SCU Cargo Container",
        "RMC (Recycled Material Composite)", "Hydrogen Fuel", "Quantum Fuel", "Quantainium (Ore)", "Laranite", "Titanium", "Gold"
    ],
    "Ship Cosmetics": [
        "100 Series Blue Ametrine Livery", "400I Deck The Hull Livery", "Arrow Lovestruck Livery", "300 Series White Lightning Paint"
    ]
}

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
    i_low = str(iname).lower().strip()
    return any(x in i_low for x in [
        "package:", "package", "category", "---", "==="
    ])

def _clean_item_list(items):
    if not items:
        return []
    from src.ui.create_package import BUILT_IN_PACKAGES
    pkg_names = {k.lower() for k in BUILT_IN_PACKAGES.keys()}
    cleaned = []
    for it in items:
        s_it = str(it).strip()
        if s_it.lower() not in pkg_names and not s_it.lower().startswith("package:"):
            cleaned.append(s_it)
    return cleaned

def _get_item_category(item_name):
    in_low = str(item_name).lower().strip()

    # 1. Ship Cosmetics
    if any(k in in_low for k in ['livery', 'paint', 'cosmetic', 'skin']):
        return 'ship cosmetics'

    # 2. Medical
    if any(k in in_low for k in ['medpen', 'medkit', 'paramed', 'lifeguard', 'refill', 'hemopen', 'hemozal', 'detoxpen', 'oxypen', 'adrenapen', 'corticopen', 'deconpen', 'opiopen', 'medgel', 'panacea']) or 'medical' in in_low:
        return 'medical'

    # 3. FPS Armor
    if any(k in in_low for k in ['helmet', 'core', 'arms', 'legs', 'backpack', 'undersuit', 'armor', 'tcs-4', 'csp-68', 'orc-mkx', 'adp-mk4', 'field recon', 'aril', 'adp']):
        return 'fps armor'

    # 4. Clothing
    if any(k in in_low for k in ['jacket', 'shirt', 'pants', 'shoes', 'gloves', 'suit', 'vest', 'hat', 'cap', 'coat', 'boots', 'adiva', 'lemarque', 'deo', 'prim', 'ventra', 'tailwind']):
        return 'clothing'

    # 5. Weapons
    if any(k in in_low for k in [
        'rifle', 'pistol', 'smg', 'lmg', 'sniper', 'shotgun', 'launcher', 'p4-ar', 'fs-9', 's-38', 'p8-sc', 'p6-lr', 'br-2', 'br2', 'arclight', 'a03', 'ado-5', 'laser mine', 'grenade',
        'coda', 'gallant', 'c54', 'lumin', 'scalpel', 'custodian', 'devastator', 'behring', 'kastak', 'klaus', 'gemini', 'apocalypse', 'hedeby', 'volt', 'cq7',
        'compensator', 'flash hider', 'stabilizer', 'suppressor', 'scope', 'sight', 'optic', 'choke', 'barrel', 'magazine', 'ammunition'
    ]) and not any(k in in_low for k in ['ship cannon', 'ship repeater', 'ship weapon', 'turret', 'missile', 'torpedo']):
        return 'weapons'

    # 6. Ship Weapons & Missiles
    if any(k in in_low for k in [
        'torpedo', 'missile', 'bomb', 'countermeasure', 'chaff', 'noise', 'decoy',
        'laser cannon', 'ballistic cannon', 'laser repeater', 'ballistic repeater', 'giga-panther', 'rhino', 'panther', 'badger', 'bulldog',
        'm7a', 'm6a', 'm5a', 'm4a', 'cf-557', 'cf-447', 'cf-337', 'cf-227', 'cf-117', 'tarantula', 'deadbolt', 'argus', 'typhoon', 'seeker', 'dominator', 'tempest', 'arrester', 'stalker',
        'omnisky', 'quarrel', 'gattling', 'gatling', 'scattergun', 'ship cannon', 'ship repeater', 'ship weapon', 'repeater', 'cannon',
        'turret', 'tigerstrike', 'sw16br', 'mount', 'gimbal', 'rack'
    ]):
        return 'ship weapons & missiles'

    # 7. Ship Components
    if any(k in in_low for k in [
        'shield generator', 'shield', 'power plant', 'powerplant', 'cooler', 'fr-86', 'fr-76', 'fr-66', 'rampart', 'umbra', 'aspis', 'fullstop', 'allstop', 'palisade', 'bulwark', 'fortress',
        'js-500', 'js-400', 'js-300', 'js-200', 'coolcore', 'eridani', 'ultra-flow', 'glacier', 'icebox', 'chill-out', 'snowpack',
        'quantum drive', 'quantum engine', 'qt drive', 'qd', 'vk-00', 'atlas', 'voyager', 'beacon', 'crossfield', 'pontes', 'ts-2'
    ]):
        return 'ship components'

    # 8. Industrial Utilities
    if any(k in in_low for k in [
        'mining head', 'mining gadget', 'mining module', 'salvage head', 'salvage module', 'scraper module',
        'ore pod', 'fuel pod', 'fuel nozzle', 'hofstede', 'klein', 'helix', 'lancet', 'arbor', 'impact',
        'boremax', 'optimax', 'waveshift', 'waweshift', 'sabir', 'stampede', 'focus', 'torrent', 'rime', 'fltr', 'brand', 'lifesaver',
        'truhold', 'cinch', 'abrade', 'trawler', 'cinematic', 'cambio', 'maxlift', 'tractor beam', 'multi-tool', 'battery', 'attachment'
    ]):
        return 'industrial utilities'

    # 9. Food & Drinks
    if any(k in in_low for k in ['cruz', 'rynex', 'water bottle', 'snack', 'pips', 'snaggle', 'food', 'drink', 'bottle', 'burrito', 'noodle', 'bar', 'ration', 'readymeal', 'meal', 'chocolate', 'karoby', 'tankard', 'hotdog', 'pizza']):
        return 'food & drinks'

    # 10. Commodities & Cargo
    if any(k in in_low for k in [
        'stor-all', 'container', 'copper', 'iron', 'hephaestanite', 'quantainium', 'quantanium', 'gold', 'laranite', 'agricium', 'bexalite', 'bexlite', 'taranite',
        'beryl', 'titanium', 'silicon', 'quartz', 'borase', 'corundum', 'diamond', 'tungsten', 'aluminium', 'aluminum',
        'inert materials', 'rmc', 'recycled material', 'construction materials', 'ore', 'scrap', 'hydrogen fuel', 'quantum fuel'
    ]):
        return 'commodities & cargo'

    return 'commodities & cargo'

def _get_full_database_items(config_data=None):
    db_items = []
    fi = load_frequent_items(config_data)
    for entry in fi:
        if isinstance(entry, dict) and entry.get("name"):
            db_items.append(entry["name"])
        elif isinstance(entry, str) and entry.strip():
            db_items.append(entry.strip())

    wiki_p = PATHS.resource('sc_wiki_items_cache.json')
    if os.path.isfile(wiki_p):
        try:
            with open(wiki_p, 'r', encoding='utf-8') as f:
                wdb = json.load(f)
                if isinstance(wdb, dict):
                    for k, v in wdb.items():
                        if isinstance(v, dict) and v.get('name'):
                            db_items.append(v['name'])
                        elif isinstance(k, str):
                            db_items.append(k)
        except Exception: pass

    uex_p = PATHS.resource('uex_items_trade_db.json')
    if os.path.isfile(uex_p):
        try:
            with open(uex_p, 'r', encoding='utf-8') as f:
                udb = json.load(f)
                if isinstance(udb, dict):
                    for k, v in udb.items():
                        if isinstance(v, dict) and v.get('name'):
                            db_items.append(v['name'])
        except Exception: pass

    vol_p = PATHS.resource('item_volumes.json')
    if os.path.isfile(vol_p):
        try:
            with open(vol_p, 'r', encoding='utf-8') as f:
                vmap = json.load(f)
                if isinstance(vmap, dict):
                    for k in vmap.keys():
                        db_items.append(k.title())
        except Exception: pass

    import re as _re
    # 1. First pass: collect all canonical items with size tags e.g. (Size 1), (Size 2), etc.
    sized_canonical_map = {}
    for item in db_items:
        if not item or _is_fake_item(item):
            continue
        m = _re.search(r'\(Size\s*\d+\)', item, _re.IGNORECASE)
        if m:
            root = _re.sub(r'\s*\(Size\s*\d+\)', '', item, flags=_re.IGNORECASE).strip().lower()
            sized_canonical_map[root] = item
            tokens = root.split()
            if tokens and len(tokens[0]) >= 2:
                sized_canonical_map[tokens[0]] = item

    # 2. Second pass: deduplicate, omitting plain items if a sized version exists
    seen = set()
    clean_list = []
    for item in db_items:
        if not item or _is_fake_item(item):
            continue
        inlow = item.lower().strip()
        m = _re.search(r'\(Size\s*\d+\)', item, _re.IGNORECASE)
        
        # If this item has NO size tag, but a sized canonical version exists, skip the unsized duplicate!
        if not m:
            if inlow in sized_canonical_map:
                canonical_item = sized_canonical_map[inlow]
                c_low = canonical_item.lower().strip()
                if c_low not in seen:
                    seen.add(c_low)
                    clean_list.append(canonical_item)
                continue

        if inlow not in seen:
            seen.add(inlow)
            clean_list.append(item)

    return clean_list

def _filter_items_by_category(items, cat_name):
    if not items:
        items = _get_full_database_items()

    cat_low = str(cat_name).strip().lower()
    if not cat_low or cat_low in ["all items", "all"]:
        return sorted(list(dict.fromkeys([str(x).strip() for x in items if not _is_fake_item(x)])))

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

    matched = []
    seen_low = set()

    for it in items:
        iname = str(it).strip()
        if _is_fake_item(iname): continue
        if _get_item_category(iname) == target_cat:
            in_l = iname.lower()
            if in_l not in seen_low:
                seen_low.add(in_l)
                matched.append(iname)

    for key_cat, fallback_items in CATEGORY_ITEMS_MAP.items():
        if key_cat.lower() == target_cat:
            for fi in fallback_items:
                fi_l = fi.lower()
                if fi_l not in seen_low:
                    seen_low.add(fi_l)
                    matched.append(fi)

    matched.sort(key=lambda x: x.lower())
    return matched

def setup_quick_add_panel(self, *args, **kwargs):
    left_frame = None
    for attr in ['location_entry', 'captain_entry', 'loading_crew_entry', 'req_id_entry', '_location_entry', '_captain_entry']:
        if hasattr(self, attr) and getattr(self, attr):
            try:
                left_frame = getattr(self, attr).master
                break
            except Exception: pass

    if not left_frame:
        def _find_frame_with_entries(widget):
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkEntry):
                    return child.master
                res = _find_frame_with_entries(child)
                if res: return res
            return None
        left_frame = _find_frame_with_entries(self)

    if not left_frame:
        from src.ui.create_package import BUILT_IN_PACKAGES
        if not hasattr(self, 'package_combo'):
            self.package_combo = ctk.CTkComboBox(self, values=list(BUILT_IN_PACKAGES.keys()))
        if not hasattr(self, 'quick_add_combo'):
            self.quick_add_combo = ctk.CTkComboBox(self, values=["P4-AR Rifle", "Maxlift Tractor Beam"])
        return

    scroll_frame = left_frame.master if hasattr(left_frame, 'master') and left_frame.master else left_frame

    # Remove any existing quick add package frame to prevent duplicates on layout refresh
    for child in list(scroll_frame.winfo_children()):
        if getattr(child, '_is_quick_add_pkg_frame', False):
            try: child.destroy()
            except Exception: pass
        elif isinstance(child, ctk.CTkFrame):
            for sub in list(child.winfo_children()):
                if isinstance(sub, ctk.CTkLabel):
                    try:
                        if "QUICK-ADD ITEM PACKAGE" in str(sub.cget("text")):
                            child.destroy()
                            break
                    except Exception: pass

    # Locate comboboxes — deep recursive scan excluding left_frame and metadata fields
    single_combo = None
    category_combo = None

    _metadata_combos = set()
    for attr in ['ship_selector', 'officer_combo', '_officer_combo', 'captain_combo', '_captain_combo',
                 'crew_combo', 'loading_crew_combo', 'severity_combo', 'loading_type_combo',
                 'req_id_entry', 'location_entry', 'captain_entry', 'loading_crew_entry']:
        val = getattr(self, attr, None)
        if val:
            _metadata_combos.add(val)

    _CAT_KEYWORDS = {"All Items", "ALL", "All", "Weapons", "Uniforms", "Armors and Clothes", "Armor + Clothes"}
    _SKIP_VALUES = {"1 SCU", "2 SCU", "4 SCU", "8 SCU", "16 SCU", "In Hangar", "Loose"}

    def _scan_for_combos(widget, depth=0, max_depth=5):
        nonlocal single_combo, category_combo
        if depth > max_depth or widget == left_frame or widget in _metadata_combos:
            return
        for child in widget.winfo_children():
            if child == left_frame or child in _metadata_combos:
                continue
            if isinstance(child, (ctk.CTkOptionMenu, ctk.CTkComboBox)) and hasattr(child, 'cget'):
                try:
                    vals = child.cget('values')
                    if vals:
                        if any(x in vals for x in _CAT_KEYWORDS):
                            category_combo = child
                        elif not any(x in vals for x in _SKIP_VALUES):
                            first_v = str(vals[0]).lower()
                            if not any(title in first_v for title in ["lt.", "capt.", "cmdr.", "colonel", "aegis", "anvil", "drake", "rsi", "misc", "crusader", "origin"]):
                                if len(vals) > 3 or single_combo is None:
                                    single_combo = child
                except Exception:
                    pass
            if isinstance(child, (ctk.CTkFrame, tk.Frame)):
                _scan_for_combos(child, depth + 1, max_depth)

    _scan_for_combos(scroll_frame)

    # Fallback: check if main.pyc already assigned combo attributes to self
    if not single_combo:
        for attr in ['quick_add_combo', '_single_combo', 'single_combo', 'item_combo', '_item_combo']:
            candidate = getattr(self, attr, None)
            if candidate and candidate not in _metadata_combos and isinstance(candidate, (ctk.CTkOptionMenu, ctk.CTkComboBox)):
                try:
                    candidate.winfo_exists()
                    single_combo = candidate
                    print(f"[quick_add_cargo] Found single_combo via self.{attr}", file=__import__('sys').stderr)
                    break
                except Exception:
                    pass
    if not category_combo:
        for attr in ['category_combo', '_category_combo', 'cat_combo']:
            candidate = getattr(self, attr, None)
            if candidate and candidate not in _metadata_combos and isinstance(candidate, (ctk.CTkOptionMenu, ctk.CTkComboBox)):
                try:
                    candidate.winfo_exists()
                    category_combo = candidate
                    break
                except Exception:
                    pass

    if single_combo:
        print(f"[quick_add_cargo] single_combo FOUND: {single_combo}", file=__import__('sys').stderr)
    else:
        print(f"[quick_add_cargo] WARNING: single_combo NOT FOUND", file=__import__('sys').stderr)
    
    from src.ui.create_package import BUILT_IN_PACKAGES
    built_in_packages = list(BUILT_IN_PACKAGES.keys())
    
    custom_packages = []
    pkg_file = os.path.join(PATHS.config_dir, 'packages.json')
    if os.path.exists(pkg_file):
        try:
            with open(pkg_file, 'r', encoding='utf-8') as f:
                custom_packages = list(json.load(f).keys())
        except: pass
            
    all_packages = built_in_packages + custom_packages
    
    if single_combo:
        self.single_combo = single_combo
        self._single_combo = single_combo
        self.quick_add_combo = single_combo

    if category_combo:
        self.category_combo = category_combo
        self._category_combo = category_combo

    if single_combo and category_combo:
        single_combo._category_combo = category_combo
        category_combo._item_combo = single_combo

    # ── Quantity Entry Field & Add Cargo Item Button Layout ──
    if single_combo and single_combo not in _metadata_combos:
        parent_frame = single_combo.master
        for child in list(parent_frame.winfo_children()):
            if getattr(child, '_is_cargo_qty_frame', False):
                try: child.destroy()
                except Exception: pass

        qty_frame = ctk.CTkFrame(master=parent_frame, fg_color="transparent")
        qty_frame._is_cargo_qty_frame = True

        ginfo = {}
        try: ginfo = single_combo.grid_info()
        except Exception: pass

        if ginfo:
            r = ginfo.get("row", 0)
            c = ginfo.get("column", 0)
            cs = ginfo.get("columnspan", 1)
            qty_frame.grid(row=r+1, column=c, columnspan=cs, sticky="ew", pady=(4, 6))
        else:
            p_info = {}
            try: p_info = single_combo.pack_info()
            except Exception: pass
            px = p_info.get("padx", (0, 0)) if p_info else (0, 0)
            try:
                qty_frame.pack(fill="x", padx=px, pady=(4, 6), after=single_combo)
            except Exception:
                qty_frame.pack(fill="x", padx=px, pady=(4, 6))

        ctk.CTkLabel(master=qty_frame, text="Qty:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#c8a84e").pack(side="left", padx=(0, 4))
        qty_var = tk.StringVar(value="1")
        qty_entry = ctk.CTkEntry(master=qty_frame, textvariable=qty_var, width=45, height=32, fg_color="#1a1a2e", text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold"))
        qty_entry.pack(side="left", padx=(0, 6))

        # Find and hide any legacy/mispositioned add button from main.pyc
        def _find_add_btn_recursive(widget):
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    try:
                        txt = str(child.cget("text")).lower()
                        if ("add cargo" in txt or "add item" in txt or txt.strip() == "add") and child != getattr(self, 'package_add_btn', None):
                            return child
                    except Exception: pass
                res = _find_add_btn_recursive(child)
                if res: return res
            return None

        legacy_btn = _find_add_btn_recursive(parent_frame) or _find_add_btn_recursive(scroll_frame) or _find_add_btn_recursive(left_frame)
        if legacy_btn:
            try: legacy_btn.pack_forget()
            except Exception: pass
            try: legacy_btn.grid_forget()
            except Exception: pass

        def _do_add_cargo_item(event=None):
            try:
                q_val = int(qty_entry.get().strip())
                if q_val < 1: q_val = 1
            except Exception:
                q_val = 1

            selected_item = single_combo.get().strip() if single_combo else ""
            if selected_item and hasattr(self, 'add_cargo_row_to_ui'):
                def _get_item_box_size_dyn(iname):
                    if not iname: return "1 SCU"
                    in_low = str(iname).lower().strip()

                    # 1. Personal gear, infantry weapons, magazines, medpens -> Loose
                    if any(k in in_low for k in [
                        "rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "magazine", "refill",
                        "medpen", "medkit", "helmet", "core", "arms", "legs", "undersuit", "backpack",
                        "jacket", "pants", "cruz", "water", "snack", "grenade", "gadget", "multitool"
                    ]):
                        return "Loose"

                    # 2. Ship Weapons (Cannons, Repeaters, Scatterguns, Ballistics)
                    if any(k in in_low for k in ["cannon", "repeater", "scattergun", "gatling", "autocannon", "ballistic", "laser", "distortion"]):
                        if any(k in in_low for k in ["size 4", "size 5", "(size 4)", "(size 5)", "s4", "s5", "m6a", "m7a", "cf-447", "cf-557"]):
                            return "4 SCU"
                        if any(k in in_low for k in ["size 2", "size 3", "(size 2)", "(size 3)", "s2", "s3", "m4a", "m5a", "cf-227", "cf-337"]):
                            return "2 SCU"
                        return "1 SCU"

                    # 3. Ship Components (Quantum Drives, Shield Generators, Coolers, Power Plants)
                    if any(k in in_low for k in ["shield", "quantum", "drive", "cooler", "power plant", "generator"]):
                        if any(k in in_low for k in ["size 4", "size 5", "(size 4)", "(size 5)", "s4", "s5"]):
                            return "16 SCU"
                        if any(k in in_low for k in ["size 3", "(size 3)", "s3", "ts-2", "fr-86", "js-500"]):
                            return "8 SCU"
                        return "1 SCU"

                    return "1 SCU"

                dyn_box = _get_item_box_size_dyn(selected_item)
                dyn_price = 0
                try:
                    from ui_panel import _get_base_unit_price
                    dyn_price = _get_base_unit_price(self, selected_item)
                except Exception: pass

                self.add_cargo_row_to_ui(name=selected_item, qty=q_val, box_size=dyn_box, price=dyn_price)

                # Multitool & Battery Auto-Bundling (STROM 2 & Bod 6)
                in_low = str(selected_item).lower().strip()
                if "cambio srt" in in_low and "canister" not in in_low and "battery" not in in_low:
                    b_price1 = 0
                    b_price2 = 0
                    try:
                        from ui_panel import _get_base_unit_price
                        b_price1 = _get_base_unit_price(self, "Cambio SRT Canister")
                        b_price2 = _get_base_unit_price(self, "Cambio Multi-tool Battery")
                    except Exception: pass
                    self.add_cargo_row_to_ui(name="Cambio SRT Canister", qty=q_val * 10, box_size="Loose", price=b_price1)
                    self.add_cargo_row_to_ui(name="Cambio Multi-tool Battery", qty=q_val * 1, box_size="Loose", price=b_price2)
                elif ("maxlift" in in_low or "pyro multi-tool" in in_low or "pyro multitool" in in_low) and "battery" not in in_low and "canister" not in in_low:
                    b_price = 0
                    try:
                        from ui_panel import _get_base_unit_price
                        b_price = _get_base_unit_price(self, "Maxlift Tractor Beam Battery")
                    except Exception: pass
                    self.add_cargo_row_to_ui(name="Maxlift Tractor Beam Battery", qty=q_val * 1, box_size="Loose", price=b_price)
            elif legacy_btn and hasattr(legacy_btn, 'cget'):
                orig_cmd = legacy_btn.cget("command")
                if orig_cmd:
                    for _ in range(q_val):
                        orig_cmd()

        try:
            qty_entry.bind("<Return>", _do_add_cargo_item)
        except Exception: pass

        new_add_btn = ctk.CTkButton(
            master=qty_frame,
            text="+ Add Cargo Item",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#00a896",
            hover_color="#028090",
            width=65,
            height=32,
            corner_radius=6,
            command=_do_add_cargo_item
        )
        new_add_btn.pack(side="left", padx=(0, 0))

    clipboard_label = None
    for child in scroll_frame.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            text = child.cget("text")
            if text and "CLIPBOARD" in text.upper():
                clipboard_label = child
                break
    
    pkg_frame = ctk.CTkFrame(master=scroll_frame, fg_color="transparent")
    pkg_frame._is_quick_add_pkg_frame = True
    if clipboard_label:
        pkg_frame.pack(padx=10, pady=(10, 5), fill="x", anchor="n", before=clipboard_label)
    else:
        pkg_frame.pack(padx=10, pady=(10, 5), fill="x", anchor="n")
    
    ctk.CTkLabel(master=pkg_frame, text="[ QUICK-ADD ITEM PACKAGE ]", 
                 font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), 
                 text_color="#c8a84e").pack(anchor="w", pady=(0, 5))
                 
    # Package selection layout
    pkg_sel_frame = ctk.CTkFrame(master=pkg_frame, fg_color="transparent")
    pkg_sel_frame.pack(fill="x", pady=(0, 5))
    
    pkg_var = tk.StringVar(value=all_packages[0] if all_packages else "")
    pkg_combo = ctk.CTkComboBox(
        master=pkg_sel_frame, 
        values=all_packages,
        variable=pkg_var,
        width=140,
        fg_color="#1a1a2e", 
        button_color="#2a3a4a",
        text_color="#dddddd"
    )
    pkg_combo.pack(side="left", fill="x", expand=True, padx=(0, 4))
    self.package_combo = pkg_combo
    if hasattr(self, 'parent_app') and self.parent_app:
        try: self.parent_app.package_combo = pkg_combo
        except Exception: pass
    if hasattr(self, 'master') and self.master:
        try: setattr(self.master, 'package_combo', pkg_combo)
        except Exception: pass
    
    # Package Quantity Multiplier Entry Field
    ctk.CTkLabel(master=pkg_sel_frame, text="Qty:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#c8a84e").pack(side="left", padx=(4, 2))
    pkg_qty_var = tk.StringVar(value="1")
    pkg_qty_entry = ctk.CTkEntry(master=pkg_sel_frame, textvariable=pkg_qty_var, width=45, fg_color="#1a1a2e", text_color="#ffffff")
    pkg_qty_entry.pack(side="left", padx=(0, 6))

    def refresh_pkg_combo():
        c_pkgs = []
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file, 'r', encoding='utf-8') as f:
                    c_pkgs = list(json.load(f).keys())
            except: pass
        updated_all = built_in_packages + c_pkgs
        pkg_combo.configure(values=updated_all)
        if updated_all:
            if pkg_var.get() not in updated_all:
                pkg_var.set(updated_all[0])
        else:
            pkg_var.set("")

    def on_add_package():
        pkg_name = pkg_var.get()
        if not pkg_name:
            return
        try:
            set_mult = int(pkg_qty_entry.get().strip())
            if set_mult < 1: set_mult = 1
        except Exception:
            set_mult = 1

        from src.ui.create_package import BUILT_IN_PACKAGES
        c_pkgs_dict = {}
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file, 'r', encoding='utf-8') as f:
                    c_pkgs_dict = json.load(f)
            except Exception: pass
        
        from src.ui.create_package import get_package_item_price
        items_to_add = BUILT_IN_PACKAGES.get(pkg_name) or c_pkgs_dict.get(pkg_name)
        if items_to_add and isinstance(items_to_add, list):
            for _ in range(set_mult):
                for item in items_to_add:
                    iname = item.get("name", "")
                    iqty = item.get("qty", 1)
                    iprice = item.get("price")
                    if iprice is None or iprice == 0 or iprice == "0":
                        iprice = get_package_item_price(iname)
                    if iname:
                        self.add_cargo_row_to_ui(name=iname, qty=iqty, box_size="Loose", price=iprice, status="LOOSE")
        else:
            self.add_cargo_row_to_ui(name=pkg_name, qty=set_mult, box_size="1/8 SCU", price=0, status="LOOSE")
        
    add_btn = ctk.CTkButton(
        master=pkg_sel_frame, 
        text="Add", 
        width=45,
        command=on_add_package,
        fg_color="#127a7f", 
        hover_color="#0e5a5e"
    )
    add_btn.pack(side="left", padx=(0, 4))
    self.package_add_btn = add_btn

    def on_delete_package():
        pkg_name = pkg_var.get()
        if not pkg_name:
            messagebox.showwarning("Warning", "No package selected!")
            return
        
        c_pkgs_dict = {}
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file, 'r', encoding='utf-8') as f:
                    c_pkgs_dict = json.load(f)
            except: pass

        if pkg_name in c_pkgs_dict:
            if messagebox.askyesno("Delete Custom Package", f"Delete custom package '{pkg_name}' permanently?"):
                del c_pkgs_dict[pkg_name]
                try:
                    with open(pkg_file, 'w', encoding='utf-8') as f:
                        json.dump(c_pkgs_dict, f, indent=2)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete package: {e}")
                    return
                refresh_pkg_combo()
                messagebox.showinfo("Success", f"Custom package '{pkg_name}' deleted.")
        else:
            if messagebox.askyesno("Remove Package Items", f"Remove items of built-in package '{pkg_name}' from cargo table?"):
                from src.ui.create_package import BUILT_IN_PACKAGES
                items = BUILT_IN_PACKAGES.get(pkg_name, [])
                if items and hasattr(self, 'cargo_rows') and self.cargo_rows:
                    item_names = {i['name'].lower() for i in items}
                    rows_to_remove = []
                    for row in list(self.cargo_rows):
                        r_name = row['name_var'].get().strip().lower()
                        if r_name in item_names:
                            rows_to_remove.append(row)
                    for row in rows_to_remove:
                        try:
                            if 'frame' in row and hasattr(row['frame'], 'destroy'):
                                row['frame'].destroy()
                            if row in self.cargo_rows:
                                self.cargo_rows.remove(row)
                        except Exception: pass
                    if hasattr(self, 'calculate_total'):
                        self.calculate_total()
                    messagebox.showinfo("Removed", f"Removed {len(rows_to_remove)} items matching '{pkg_name}' from cargo table.")

    del_btn = ctk.CTkButton(
        master=pkg_sel_frame, 
        text="Delete", 
        width=55,
        command=on_delete_package,
        fg_color="#8b2626", 
        hover_color="#a83232"
    )
    del_btn.pack(side="right")
    
    def on_create_custom_package():
        if hasattr(self, 'show_create_package_modal'):
            self.show_create_package_modal()
        else:
            try:
                from src.ui.create_package import CreatePackageModal
                CreatePackageModal(self)
            except Exception as e:
                print(f"[QUICK-ADD] Failed to open package modal: {e}")
        
    create_btn = ctk.CTkButton(
        master=pkg_frame, 
        text="Create Custom Package", 
        command=on_create_custom_package,
        fg_color="#3a4a5a", 
        hover_color="#2a3a4a"
    )
    create_btn.pack(fill="x", pady=(5, 0))
