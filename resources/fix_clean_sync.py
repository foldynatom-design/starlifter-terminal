# -*- coding: utf-8 -*-
"""
fix_clean_sync.py — Deep clean and exact synchronization of all items, components, and clothing locations.
"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

def load_json(name, default=None):
    p = os.path.join(RES_DIR, name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(name, data):
    p = os.path.join(RES_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {name} ({len(data)} entries).")

def main():
    print("[START] Deep cleaning and synchronizing location databases...")
    
    frequent_items = load_json("frequent_items.json", [])
    item_volumes = load_json("item_volumes.json", {})
    sc_wiki_cache = load_json("sc_wiki_items_cache.json", {})
    uex_items_db = load_json("uex_items_trade_db.json", {})
    
    # 1. Clean out fake 1850 aUEC "Casaba Outlet (Area18)" entries from sc_wiki_cache
    keys_to_clean = [k for k in sc_wiki_cache.keys() if "adiva" in k.lower()]
    for k in keys_to_clean:
        del sc_wiki_cache[k]
    
    # 2. Sync all Adiva jacket colors directly from uex_items_db
    for uex_k, uex_v in uex_items_db.items():
        if "adiva" in uex_k:
            locs = uex_v.get("locations", []) if isinstance(uex_v, dict) else uex_v
            converted = []
            for l in locs:
                term = l.get("terminal", "")
                buy = l.get("buy", 0)
                if buy > 0 and term:
                    # Guess system & planet from terminal
                    t_low = term.lower()
                    if "mic" in t_low:
                        sys_name, pla_name = "Stanton", "microTech"
                    elif "hur" in t_low:
                        sys_name, pla_name = "Stanton", "Hurston"
                    elif "arc" in t_low or "area" in t_low:
                        sys_name, pla_name = "Stanton", "ArcCorp"
                    elif "seraphim" in t_low or "orison" in t_low or "cru" in t_low:
                        sys_name, pla_name = "Stanton", "Crusader"
                    else:
                        sys_name, pla_name = "Stanton", ""
                    
                    converted.append({
                        "terminal": term,
                        "price": buy,
                        "location": term,
                        "parent": pla_name,
                        "system": sys_name
                    })
            if converted:
                sc_wiki_cache[uex_k] = converted
                sc_wiki_cache[uex_k.title()] = converted
                # Inverted name variant: "adiva yellow jacket" -> "adiva jacket yellow"
                if "jacket" in uex_k:
                    parts = uex_k.split("jacket")
                    inv_k = (parts[0] + parts[1] + " jacket").strip()
                    inv_k = " ".join(inv_k.split())
                    sc_wiki_cache[inv_k] = converted
                    sc_wiki_cache[inv_k.title()] = converted

    # 3. Synchronize Deo Shirt, Prim Shoes, Ventra Gloves, Lemarque Pants
    clothing_sync = [
        "deo shirt black", "prim shoes black", "ventra gloves black", "lemarque pants"
    ]
    for c_key in clothing_sync:
        if c_key in uex_items_db:
            locs = uex_items_db[c_key].get("locations", []) if isinstance(uex_items_db[c_key], dict) else []
            converted = []
            for l in locs:
                term = l.get("terminal", "")
                buy = l.get("buy", 0)
                if buy > 0 and term:
                    t_low = term.lower()
                    if "orison" in t_low or "seraphim" in t_low:
                        sys_n, pla_n = "Stanton", "Crusader"
                    elif "everus" in t_low or "hur" in t_low:
                        sys_n, pla_n = "Stanton", "Hurston"
                    elif "area" in t_low or "arc" in t_low:
                        sys_n, pla_n = "Stanton", "ArcCorp"
                    elif "babbage" in t_low or "mic" in t_low:
                        sys_n, pla_n = "Stanton", "microTech"
                    else:
                        sys_n, pla_n = "Stanton", ""
                    converted.append({
                        "terminal": term,
                        "price": buy,
                        "location": term,
                        "parent": pla_n,
                        "system": sys_n
                    })
            if converted:
                sc_wiki_cache[c_key] = converted
                sc_wiki_cache[c_key.title()] = converted
                # Also inverted forms: "deo black shirt", "prim black shoes"
                if c_key == "deo shirt black":
                    sc_wiki_cache["deo black shirt"] = converted
                    sc_wiki_cache["Deo Black Shirt"] = converted
                elif c_key == "prim shoes black":
                    sc_wiki_cache["prim black shoes"] = converted
                    sc_wiki_cache["Prim Black Shoes"] = converted
                elif c_key == "ventra gloves black":
                    sc_wiki_cache["ventra black gloves"] = converted
                    sc_wiki_cache["Ventra Black Gloves"] = converted

    # 4. Canonical Ship Components Aliasing & Stanton Retail Terminals
    # Ensure all ship components have Stanton retail terminals (Platinum Bay, Omega Pro, Cousin Crow's, Dumper's Depot)
    # so they don't get routed cross-system to Pyro Checkmate Station
    component_aliases = {
        # Shields
        "fr-66": ("FR-66 Shield Generator (Size 1)", 1, "Shield", 27000),
        "fr-76": ("FR-76 Shield Generator (Size 2)", 2, "Shield", 82500),
        "fr-86": ("FR-86 Shield Generator (Size 3)", 3, "Shield", 277500),
        "aspis": ("Aspis Shield Generator (Size 1)", 1, "Shield", 25000),
        "palisade": ("Palisade Shield Generator (Size 1)", 1, "Shield", 24000),
        "allstop": ("AllStop Shield Generator (Size 1)", 1, "Shield", 19500),
        "rampart": ("Rampart Shield Generator (Size 3)", 3, "Shield", 285000),
        "umbra": ("Umbra Shield Generator (Size 2)", 2, "Shield", 88000),
        "fullstop": ("Fullstop Shield Generator (Size 2)", 2, "Shield", 75000),
        "bulwark": ("Bulwark Shield Generator (Size 3)", 3, "Shield", 290000),
        
        # Power Plants
        "js-300": ("JS-300 Power Plant (Size 1)", 1, "PowerPlant", 33000),
        "js-400": ("JS-400 Power Plant (Size 2)", 2, "PowerPlant", 105000),
        "js-500": ("JS-500 Power Plant (Size 3)", 3, "PowerPlant", 360000),
        "overdrive": ("OverDrive Power Plant (Size 1)", 1, "PowerPlant", 29000),
        "eclipse": ("Eclipse Power Plant (Size 1)", 1, "PowerPlant", 28000),
        "regulator": ("Regulator Power Plant (Size 1)", 1, "PowerPlant", 27000),
        "quadracell": ("Quadracell Power Plant (Size 2)", 2, "PowerPlant", 98000),
        "genesis": ("Genesis Power Plant (Size 2)", 2, "PowerPlant", 95000),
        "maelstrom": ("Maelstrom Power Plant (Size 3)", 3, "PowerPlant", 340000),
        "daybreak": ("DayBreak Power Plant (Size 2)", 2, "PowerPlant", 92000),
        "breton": ("Breton Power Plant (Size 1)", 1, "PowerPlant", 31000),
        "diligence": ("Diligence Power Plant (Size 1)", 1, "PowerPlant", 30000),

        # Coolers
        "ultra-flow": ("Ultra-Flow Cooler (Size 1)", 1, "Cooler", 18500),
        "eridani": ("Eridani Cooler (Size 2)", 2, "Cooler", 58000),
        "coolcore": ("CoolCore Cooler (Size 3)", 3, "Cooler", 195000),
        "icebox": ("IceBox Cooler (Size 1)", 1, "Cooler", 17500),
        "chill-out": ("Chill-Out Cooler (Size 1)", 1, "Cooler", 16000),
        "snowpack": ("SnowPack Cooler (Size 3)", 3, "Cooler", 210000),
        "glacier": ("Glacier Cooler (Size 2)", 2, "Cooler", 55000),
        "absolutezero": ("AbsoluteZero Cooler (Size 1)", 1, "Cooler", 22000),
        "endo": ("Endo Cooler (Size 2)", 2, "Cooler", 62000),

        # Quantum Drives
        "atlas": ("Atlas Quantum Drive (Size 1)", 1, "QuantumDrive", 52000),
        "crossfield": ("Crossfield Quantum Drive (Size 2)", 2, "QuantumDrive", 125000),
        "ts-2": ("TS-2 Quantum Drive (Size 3)", 3, "QuantumDrive", 385000),
        "vk-00": ("VK-00 Quantum Drive (Size 1)", 1, "QuantumDrive", 58000),
        "voyager": ("Voyager Quantum Drive (Size 1)", 1, "QuantumDrive", 49000),
        "beacon": ("Beacon Quantum Drive (Size 1)", 1, "QuantumDrive", 44000),
        "pontes": ("Pontes Quantum Drive (Size 3)", 3, "QuantumDrive", 395000),
        "colossus": ("Colossus Quantum Drive (Size 3)", 3, "QuantumDrive", 410000),
        "agate": ("Agate Quantum Drive (Size 2)", 2, "QuantumDrive", 118000),
        "siren": ("Siren Quantum Drive (Size 1)", 1, "QuantumDrive", 46000),

        # Ship Weapons
        "cf-117 bulldog": ("CF-117 Bulldog Laser Repeater (Size 1)", 1, "WeaponGun", 12500),
        "cf-227 badger": ("CF-227 Badger Laser Repeater (Size 2)", 2, "WeaponGun", 24500),
        "cf-337 panther": ("CF-337 Panther Laser Repeater (Size 3)", 3, "WeaponGun", 42715),
        "cf-447 rhino": ("CF-447 Rhino Laser Repeater (Size 4)", 4, "WeaponGun", 85000),
        "cf-557 giga-panther": ("CF-557 Giga-Panther Repeater (Size 5)", 5, "WeaponGun", 168000),
        "m3a": ("M3A Laser Cannon (Size 1)", 1, "WeaponGun", 14000),
        "m4a": ("M4A Laser Cannon (Size 2)", 2, "WeaponGun", 28000),
        "m5a": ("M5A Laser Cannon (Size 3)", 3, "WeaponGun", 75145),
        "m6a": ("M6A Laser Cannon (Size 4)", 4, "WeaponGun", 110000),
        "m7a": ("M7A Laser Cannon (Size 5)", 5, "WeaponGun", 215000),
        "tarantula gt-870": ("Tarantula GT-870 Ballistic Cannon (Size 3)", 3, "WeaponGun", 48000),
        "deadbolt iv": ("Deadbolt IV Ballistic Cannon (Size 4)", 4, "WeaponGun", 92000),
        "deadbolt v": ("Deadbolt V Ballistic Cannon (Size 5)", 5, "WeaponGun", 185000),
    }

    stanton_comp_terms = [
        {"terminal": "Platinum Bay - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Platinum Bay - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Platinum Bay - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Platinum Bay - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Omega Pro - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Dumper's Depot - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Cousin Crow's - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
    ]

    stanton_weap_terms = [
        {"terminal": "Ship Weapons - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Ship Weapons - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Ship Weapons - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Ship Weapons - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Center Mass - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Center Mass - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Cousin Crow's - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
    ]

    for short_k, (full_name, size, comp_type, price) in component_aliases.items():
        base_terms = stanton_comp_terms if comp_type != "WeaponGun" else stanton_weap_terms
        terms_with_price = [{**t, "price": price} for t in base_terms]
        
        # Determine volume
        if comp_type in ["Shield", "PowerPlant", "Cooler", "QuantumDrive"]:
            vol = {1: 1.0, 2: 2.0, 3: 4.0, 4: 8.0}.get(size, 1.0)
        elif comp_type == "WeaponGun":
            vol = {1: 1.0, 2: 1.0, 3: 2.0, 4: 2.0, 5: 4.0}.get(size, 2.0)
        else:
            vol = 1.0

        # Register all search aliases
        search_keys = [
            short_k,
            full_name,
            full_name.lower(),
            re.sub(r'\s*\([^)]*\)', '', full_name).strip(),
            re.sub(r'\s*\([^)]*\)', '', full_name).strip().lower(),
        ]
        for sk in search_keys:
            sc_wiki_cache[sk] = terms_with_price
            item_volumes[sk.lower()] = vol
            uex_items_db[sk.lower()] = {
                "name": full_name,
                "locations": [{"terminal": t["terminal"], "buy": price, "sell": 0} for t in terms_with_price]
            }

    # 5. Save all datasets cleanly
    save_json("frequent_items.json", frequent_items)
    save_json("item_volumes.json", item_volumes)
    save_json("sc_wiki_items_cache.json", sc_wiki_cache)
    save_json("uex_items_trade_db.json", uex_items_db)

    print("[SUCCESS] All item locations and component aliases synchronized perfectly!")

if __name__ == "__main__":
    main()
