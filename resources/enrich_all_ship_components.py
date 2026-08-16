# -*- coding: utf-8 -*-
"""
enrich_all_ship_components.py — Comprehensive sync & enrichment of all SC Ship Components.
Imports Shields, Power Plants, Coolers, Quantum Drives, Ship Weapons, Missiles, Torpedoes,
Turrets, Missile Launchers, and Radars directly from Star Citizen Wiki API and local resources.
Populates:
  - resources/frequent_items.json
  - resources/item_volumes.json
  - resources/sc_wiki_items_cache.json
  - resources/uex_items_trade_db.json
"""
import json
import os
import sys
import time
import urllib.request
import ssl

ctx = ssl._create_unverified_context()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

def load_json(filename, default=None):
    p = os.path.join(RES_DIR, filename)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(filename, data):
    p = os.path.join(RES_DIR, filename)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {filename} ({len(data)} entries).")

def fetch_api_type(item_type, limit=200):
    all_items = []
    page = 1
    while True:
        url = f"https://api.star-citizen.wiki/api/v2/items?filter[type]={item_type}&page[size]={limit}&page[number]={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 StarlifterTerminal/0.7"})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
                items = data.get("data", [])
                if not items:
                    break
                all_items.extend(items)
                meta = data.get("meta", {})
                current_page = meta.get("current_page", page)
                last_page = meta.get("last_page", 1)
                if current_page >= last_page:
                    break
                page += 1
                time.sleep(0.15)
        except Exception as e:
            print(f"[WARN] Error fetching {item_type} page {page}: {e}")
            break
    return all_items

def get_component_volume(item_type, size):
    try:
        s = int(size)
    except (ValueError, TypeError):
        s = 1
    
    if item_type in ["Shield", "PowerPlant", "Cooler", "QuantumDrive"]:
        if s == 1: return 1.0, "1 SCU"
        elif s == 2: return 2.0, "2 SCU"
        elif s == 3: return 4.0, "4 SCU"
        else: return 8.0, "8 SCU"
    elif item_type == "WeaponGun":
        if s <= 2: return 1.0, "1 SCU"
        elif s <= 4: return 2.0, "2 SCU"
        elif s == 5: return 4.0, "4 SCU"
        elif s == 6: return 8.0, "8 SCU"
        elif s == 7: return 12.0, "12 SCU"
        elif s == 8: return 16.0, "16 SCU"
        elif s == 9: return 24.0, "24 SCU"
        else: return 32.0, "32 SCU"
    elif item_type == "Missile":
        if s >= 9: return 4.0, "4 SCU"
        elif s >= 5: return 4.0, "4 SCU"
        elif s == 4: return 2.0, "2 SCU"
        elif s == 3: return 1.0, "1 SCU"
        elif s == 2: return 0.5, "0.5 SCU"
        else: return 0.25, "0.25 SCU"
    elif item_type in ["Turret", "TurretBase"]:
        if s <= 1: return 1.0, "1 SCU"
        elif s == 2: return 2.0, "2 SCU"
        elif s == 3: return 4.0, "4 SCU"
        elif s == 4: return 8.0, "8 SCU"
        else: return 12.0, "12 SCU"
    elif item_type in ["MissileLauncher", "Radar"]:
        if s <= 2: return 1.0, "1 SCU"
        elif s == 3: return 2.0, "2 SCU"
        else: return 4.0, "4 SCU"
    return 1.0, "1 SCU"

def get_default_price(item_type, size, grade="C"):
    try:
        s = int(size)
    except (ValueError, TypeError):
        s = 1
    g_mult = {"A": 1.5, "B": 1.2, "C": 1.0, "D": 0.8}.get(str(grade).upper(), 1.0)
    
    if item_type == "Shield":
        base = {1: 18000, 2: 55000, 3: 185000, 4: 550000}.get(s, 25000)
    elif item_type == "PowerPlant":
        base = {1: 22000, 2: 70000, 3: 240000, 4: 700000}.get(s, 30000)
    elif item_type == "Cooler":
        base = {1: 12500, 2: 40000, 3: 135000, 4: 400000}.get(s, 20000)
    elif item_type == "QuantumDrive":
        base = {1: 38000, 2: 90000, 3: 275000, 4: 850000}.get(s, 45000)
    elif item_type == "WeaponGun":
        base = {1: 4500, 2: 9500, 3: 18000, 4: 36000, 5: 75000, 6: 150000, 7: 300000}.get(s, 25000)
    elif item_type == "Missile":
        base = {1: 150, 2: 350, 3: 850, 4: 2100, 5: 5500, 9: 25000}.get(s, 500)
    elif item_type in ["Turret", "TurretBase"]:
        base = {1: 8000, 2: 16000, 3: 32000, 4: 64000, 5: 128000}.get(s, 20000)
    else:
        base = 15000
    return int(base * g_mult)

def main():
    print("[START] Synchronizing all Star Citizen Ship Components...")
    
    frequent_items = load_json("frequent_items.json", [])
    item_volumes = load_json("item_volumes.json", {})
    sc_wiki_cache = load_json("sc_wiki_items_cache.json", {})
    uex_items_db = load_json("uex_items_trade_db.json", {})
    
    # Track existing names in frequent items
    freq_map = {item.get("name", "").lower().strip(): item for item in frequent_items if isinstance(item, dict)}
    
    # Types to process
    types_to_fetch = [
        ("Shield", "Ship Components"),
        ("PowerPlant", "Ship Components"),
        ("Cooler", "Ship Components"),
        ("QuantumDrive", "Ship Components"),
        ("WeaponGun", "Ship Weapons"),
        ("Missile", "Ammo & Missiles"),
        ("Turret", "Ship Components"),
        ("Radar", "Ship Components"),
        ("MissileLauncher", "Ship Components"),
    ]
    
    total_added_freq = 0
    total_added_vols = 0
    total_added_locations = 0
    
    for api_type, target_category in types_to_fetch:
        print(f"\nFetching {api_type} from Star Citizen Wiki API...")
        items = fetch_api_type(api_type)
        print(f"-> Received {len(items)} {api_type} items.")
        
        for it in items:
            raw_name = it.get("name", "").strip()
            if not raw_name:
                continue
            
            size = it.get("size", 1)
            grade = it.get("grade", "C")
            
            # Format display name with Size tag if not present
            display_name = raw_name
            if size and f"(Size {size})" not in raw_name and f"S{size}" not in raw_name and api_type in ["Shield", "PowerPlant", "Cooler", "QuantumDrive", "WeaponGun"]:
                # If name does not end with item type, add it
                type_tag = {
                    "Shield": "Shield Generator",
                    "PowerPlant": "Power Plant",
                    "Cooler": "Cooler",
                    "QuantumDrive": "Quantum Drive",
                    "WeaponGun": "",
                }.get(api_type, "")
                if type_tag and type_tag.lower() not in raw_name.lower():
                    display_name = f"{raw_name} {type_tag} (Size {size})"
                else:
                    display_name = f"{raw_name} (Size {size})"
            
            # Extract purchase locations from uex_prices
            locations = []
            min_price = None
            for p in it.get("uex_prices", {}).get("purchase", []):
                p_buy = p.get("price_buy")
                term = p.get("terminal_name") or ""
                starmap = p.get("starmap_location") or {}
                if p_buy and p_buy > 0 and term:
                    if min_price is None or p_buy < min_price:
                        min_price = p_buy
                    sys_name = starmap.get("star_system_name") or "Stanton"
                    pla_name = starmap.get("parent_name") or ""
                    loc_name = starmap.get("name") or term
                    locations.append({
                        "terminal": term,
                        "price": p_buy,
                        "location": loc_name,
                        "parent": pla_name,
                        "system": sys_name,
                    })
            
            # Also check fallback locations by component type & size
            if not locations:
                # Default canonical retail terminals
                if api_type in ["Shield", "PowerPlant", "Cooler", "QuantumDrive"]:
                    default_terms = [
                        {"terminal": "Platinum Bay - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
                        {"terminal": "Platinum Bay - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
                        {"terminal": "Platinum Bay - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
                        {"terminal": "Platinum Bay - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
                        {"terminal": "Omega Pro - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
                        {"terminal": "Dumper's Depot - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
                        {"terminal": "Cousin Crow's - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
                    ]
                elif api_type == "WeaponGun":
                    default_terms = [
                        {"terminal": "Center Mass - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
                        {"terminal": "Center Mass - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
                        {"terminal": "Ship Weapons - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
                        {"terminal": "Ship Weapons - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
                        {"terminal": "Ship Weapons - Cousin Crow's - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
                    ]
                elif api_type == "Missile":
                    default_terms = [
                        {"terminal": "Ship Weapons - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
                        {"terminal": "Ship Weapons - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
                        {"terminal": "Center Mass - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
                    ]
                else:
                    default_terms = [
                        {"terminal": "Platinum Bay - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
                        {"terminal": "Dumper's Depot - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
                    ]
                
                est_price = get_default_price(api_type, size, grade)
                for dt in default_terms:
                    locations.append({
                        "terminal": dt["terminal"],
                        "price": est_price,
                        "location": dt["location"],
                        "parent": dt["parent"],
                        "system": dt["system"],
                    })
            
            final_price = min_price if min_price else get_default_price(api_type, size, grade)
            vol_val, box_str = get_component_volume(api_type, size)
            
            # 1. Update item_volumes
            for name_variant in [raw_name.lower(), display_name.lower()]:
                item_volumes[name_variant] = vol_val
            total_added_vols += 1
            
            # 2. Update sc_wiki_cache
            for name_variant in [raw_name, display_name]:
                if name_variant not in sc_wiki_cache:
                    sc_wiki_cache[name_variant] = locations
                    total_added_locations += 1
                else:
                    existing_terms = {l.get("terminal") for l in sc_wiki_cache[name_variant]}
                    for loc in locations:
                        if loc.get("terminal") not in existing_terms:
                            sc_wiki_cache[name_variant].append(loc)
            
            # 3. Update uex_items_db
            uex_key = raw_name.lower()
            if uex_key not in uex_items_db:
                uex_items_db[uex_key] = {
                    "name": display_name,
                    "locations": [{"terminal": l["terminal"], "buy": l["price"], "sell": 0} for l in locations]
                }
            
            # 4. Update frequent_items
            names_to_check = [display_name.lower(), raw_name.lower()]
            found = False
            for n in names_to_check:
                if n in freq_map:
                    entry = freq_map[n]
                    entry["category"] = target_category
                    entry["price"] = final_price
                    entry["box_size"] = box_str
                    found = True
                    break
            
            if not found:
                new_entry = {
                    "name": display_name,
                    "category": target_category,
                    "price": final_price,
                    "box_size": box_str,
                }
                frequent_items.append(new_entry)
                freq_map[display_name.lower()] = new_entry
                freq_map[raw_name.lower()] = new_entry
                total_added_freq += 1

    # Harmonize Armor Set Locations (e.g. Aril, ORC-mkX, ADP-mk4)
    # Remove stale conflicting single-location arrays so they use unified UEX / station locations
    for item in frequent_items:
        if isinstance(item, dict):
            iname = item.get("name", "")
            if iname in ["Aril Core", "Aril Helmet", "Aril Arms", "Aril Legs", "Aril Backpack"]:
                if "locations" in item:
                    del item["locations"]
    
    # Save all databases cleanly
    save_json("frequent_items.json", frequent_items)
    save_json("item_volumes.json", item_volumes)
    save_json("sc_wiki_items_cache.json", sc_wiki_cache)
    save_json("uex_items_trade_db.json", uex_items_db)
    
    print(f"\n[COMPLETE] Injected:")
    print(f"  - frequent_items.json: +{total_added_freq} items (Total: {len(frequent_items)})")
    print(f"  - item_volumes.json: {len(item_volumes)} entries")
    print(f"  - sc_wiki_items_cache.json: {len(sc_wiki_cache)} item keys")
    print(f"  - uex_items_trade_db.json: {len(uex_items_db)} item keys")

if __name__ == "__main__":
    main()
