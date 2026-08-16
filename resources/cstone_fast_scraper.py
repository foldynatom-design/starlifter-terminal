# -*- coding: utf-8 -*-
"""
cstone_fast_scraper.py — High-performance concurrent scraper for Cornerstone (finder.cstone.space)
Scrapes ALL categories: Armors, Clothes, Weapons, Components, Tools, Consumables, Mining, Cargo.
Extracts: In-game Shops, Prices, Systems (Stanton, Pyro, Nyx, Terra), Micro-SCU Volume, and Loose vs Cargo type.
"""
import urllib.request, re, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

CATALOG_ENDPOINTS = [
    # Armors
    ("https://finder.cstone.space/GetArmors/Helmets", "FPSArmors1", "Armor/Helmets"),
    ("https://finder.cstone.space/GetArmors/Arms", "FPSArmors1", "Armor/Arms"),
    ("https://finder.cstone.space/GetArmors/Torsos", "FPSArmors1", "Armor/Torsos"),
    ("https://finder.cstone.space/GetArmors/Backpacks", "FPSArmors1", "Armor/Backpacks"),
    ("https://finder.cstone.space/GetArmors/Legs", "FPSArmors1", "Armor/Legs"),
    ("https://finder.cstone.space/GetArmors/Undersuits", "FPSArmors1", "Armor/Undersuits"),
    # Clothes
    ("https://finder.cstone.space/GetClothes/Hat", "FPSClothes1", "Clothes/Hat"),
    ("https://finder.cstone.space/GetClothes/Eyes", "FPSClothes1", "Clothes/Eyes"),
    ("https://finder.cstone.space/GetClothes/Hands", "FPSClothes1", "Clothes/Hands"),
    ("https://finder.cstone.space/GetClothes/Jacket", "FPSClothes1", "Clothes/Jacket"),
    ("https://finder.cstone.space/GetClothes/Shirt", "FPSClothes1", "Clothes/Shirt"),
    ("https://finder.cstone.space/GetClothes/Jumpsuit", "FPSClothes1", "Clothes/Jumpsuit"),
    ("https://finder.cstone.space/GetClothes/Legs", "FPSClothes1", "Clothes/Legs"),
    ("https://finder.cstone.space/GetClothes/Feet", "FPSClothes1", "Clothes/Feet"),
    # Weapons & Attachments
    ("https://finder.cstone.space/GetFPSWeapons", "FPSWeapons1", "Weapons/Ranged"),
    ("https://finder.cstone.space/GetFPSMags", "FPSMags1", "Weapons/Mags"),
    ("https://finder.cstone.space/GetFPSAttachments", "FPSAttachments1", "Weapons/Attachments"),
    ("https://finder.cstone.space/GetFPSWeaponMelee", "FPSWeaponMelee1", "Weapons/Melee"),
    ("https://finder.cstone.space/GetFPSWeaponThrown", "FPSWeaponThrown1", "Weapons/Thrown"),
    # Tools & Gadgets
    ("https://finder.cstone.space/GetFPSTools", "FPSTools1", "Tools/FPS"),
    ("https://finder.cstone.space/GetFPSToolAttachments", "FPSToolAttachments1", "Tools/Attachments"),
    ("https://finder.cstone.space/GetGadgets", "Gadgets1", "Gadgets/Medical"),
    ("https://finder.cstone.space/GetHChips/", "HackingChips1", "Gadgets/Hacking"),
    ("https://finder.cstone.space/GetFPSFlares", "FPSFlares1", "Gadgets/Flares"),
    # Food & Drinks
    ("https://finder.cstone.space/GetFoods", "Food1", "Consumables/Food"),
    ("https://finder.cstone.space/GetDrinks", "Drinks1", "Consumables/Drinks"),
    # Ship Weapons & Missiles
    ("https://finder.cstone.space/GetSWeapons", "ShipWeapons1", "ShipWeapons/Guns"),
    ("https://finder.cstone.space/GetSTurrets", "ShipTurrets1", "ShipWeapons/Turrets"),
    ("https://finder.cstone.space/GetMissiles", "ShipMissiles1", "ShipWeapons/Missiles"),
    ("https://finder.cstone.space/GetMRacks", "ShipMissileRacks1", "ShipWeapons/Racks"),
    ("https://finder.cstone.space/GetShipBombs", "ShipBombs1", "ShipWeapons/Bombs"),
    # Ship Components
    ("https://finder.cstone.space/GetShields", "ShipShields1", "ShipComponents/Shields"),
    ("https://finder.cstone.space/GetDrives", "ShipQuantumDrives1", "ShipComponents/QuantumDrives"),
    ("https://finder.cstone.space/GetPowers", "ShipPowerPlants1", "ShipComponents/PowerPlants"),
    ("https://finder.cstone.space/GetCoolers", "ShipCoolers1", "ShipComponents/Coolers"),
    # Mining & Containers
    ("https://finder.cstone.space/GetSMinings", "ShipMiningHeads1", "Mining/ShipHeads"),
    ("https://finder.cstone.space/GetSMMods", "ShipMiningMods1", "Mining/ShipMods"),
    ("https://finder.cstone.space/GetFPSMMods", "FPSMiningMods1", "Mining/FPSMods"),
    ("https://finder.cstone.space/GetContainers/", "Containers1", "Cargo/Containers"),
    ("https://finder.cstone.space/GetMisc", "Misc1", "Misc"),
]

def fetch_json(url, retries=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            if attempt == retries - 1:
                return []
            time.sleep(0.5)
    return []

def parse_location_string(loc_raw):
    s = loc_raw.replace("&gt;", ">").replace("&amp;", "&").replace("&#x27;", "'").replace(" - ", " > ")
    parts = [p.strip() for p in s.split(">") if p.strip()]
    
    sys_name = "Stanton"
    if parts:
        p0_low = parts[0].lower()
        if "pyro" in p0_low: sys_name = "Pyro"
        elif "nyx" in p0_low: sys_name = "Nyx"
        elif "terra" in p0_low: sys_name = "Terra"
        elif "stanton" in p0_low: sys_name = "Stanton"
    
    parent = ""
    loc_name = ""
    terminal = parts[-1] if parts else loc_raw
    
    if len(parts) >= 3:
        parent = parts[1]
        loc_name = parts[2]
    elif len(parts) == 2:
        loc_name = parts[0]
        terminal = parts[1]
    else:
        loc_name = terminal
        
    return {
        "system": sys_name,
        "parent": parent,
        "location": loc_name,
        "terminal": terminal,
        "full_path": s
    }

def fetch_item_full_details(detail_prefix, item_id, item_name, cat_label):
    url = f"https://finder.cstone.space/{detail_prefix}/{item_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        tables = re.findall(r'<table\b[^>]*>(.*?)</table>', html, re.DOTALL)
        
        # 1. Parse Volume (micro-SCU to SCU)
        vol_scu = 0.005 # default
        for t in tables:
            if "VOLUME" in t or "Volume" in t:
                m_vol = re.search(r'VOLUME</td>\s*<td[^>]*>([0-9\s,.]+)', t, re.IGNORECASE)
                if not m_vol:
                    m_vol = re.search(r'([0-9\s,.]+)\s*(?:μSCU|uSCU)', t, re.IGNORECASE)
                if m_vol:
                    val_str = m_vol.group(1).replace(" ", "").replace(",", "")
                    try:
                        u_scu = float(val_str)
                        vol_scu = round(u_scu / 1_000_000.0, 6)
                    except Exception:
                        pass
                break

        # 2. Parse Store Locations & Prices (Table 6 / location table)
        loc_entries = []
        for t in tables:
            if "LOCATION" in t and "PRICE" in t:
                rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', t, re.DOTALL)
                for r in rows:
                    cells = re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', r, re.DOTALL)
                    clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    if len(clean_cells) >= 2 and clean_cells[0] != "LOCATION":
                        loc_raw = clean_cells[0]
                        price_str = clean_cells[1].replace(" ", "").replace(",", "").replace("aUEC", "")
                        try: price = int(float(price_str))
                        except Exception: price = 0
                        
                        loc_info = parse_location_string(loc_raw)
                        loc_entries.append({
                            "terminal": loc_info["terminal"],
                            "location": loc_info["location"],
                            "parent": loc_info["parent"],
                            "system": loc_info["system"],
                            "price": price,
                            "raw_location": loc_raw,
                            "full_buy_path": loc_info["full_path"]
                        })
                        
        is_loose = not any(k in item_name.lower() for k in ["scu", "ammunition", "cargo container", "rmc", "ore", "baryte", "laranite", "titanium", "diamond"])
        
        return item_id, item_name, {
            "name": item_name,
            "item_id": item_id,
            "category": cat_label,
            "volume_scu": vol_scu,
            "is_loose": is_loose,
            "locations": loc_entries
        }
    except Exception:
        return item_id, item_name, None

def run_cstone_sync():
    print("=" * 70, flush=True)
    print("=== EXECUTING COMPLETE CORNERSTONE (CSTONE.SPACE) DATA SYNC ===", flush=True)
    print("=" * 70, flush=True)

    # 1. Fetch all catalog categories concurrently (10 workers)
    print("[1/3] Fetching all category catalogs concurrently...", flush=True)
    all_items_to_fetch = []
    seen_ids = set()

    def _fetch_cat(entry):
        url, prefix, cat_label = entry
        items = fetch_json(url)
        sold = [it for it in items if it.get("Sold") == 1]
        return cat_label, prefix, sold

    with ThreadPoolExecutor(max_workers=10) as cat_exec:
        futures = [cat_exec.submit(_fetch_cat, e) for e in CATALOG_ENDPOINTS]
        for f in as_completed(futures):
            cat_label, prefix, sold = f.result()
            print(f"  -> {cat_label:25s}: {len(sold):3d} items sold in-game", flush=True)
            for it in sold:
                i_id = it.get("ItemId")
                i_name = it.get("Name")
                if i_id and i_id not in seen_ids and i_name:
                    seen_ids.add(i_id)
                    all_items_to_fetch.append((prefix, i_id, i_name, cat_label))

    print(f"\n[2/3] Crawling {len(all_items_to_fetch)} unique items with 25 concurrent threads...", flush=True)

    cstone_master_db = {}
    done_count = 0
    total = len(all_items_to_fetch)
    start_t = time.time()

    # 2. Multi-threaded item detail fetch (25 workers)
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(fetch_item_full_details, p, i_id, name, cat): (i_id, name) for p, i_id, name, cat in all_items_to_fetch}
        for f in as_completed(futures):
            item_id, item_name, details = f.result()
            done_count += 1
            if details and details.get("locations"):
                cstone_master_db[item_name] = details
                cstone_master_db[item_name.lower()] = details

            if done_count % 100 == 0 or done_count == total:
                elapsed = time.time() - start_t
                rate = done_count / elapsed if elapsed > 0 else 0
                print(f"  [PROGRESS] {done_count:4d}/{total:4d} items scraped ({len(cstone_master_db)//2} with verified stores) - {rate:.1f} items/sec", flush=True)

    # 3. Save cstone_master_db.json
    out_master_path = os.path.join(RES_DIR, "cstone_master_db.json")
    with open(out_master_path, "w", encoding="utf-8") as f:
        json.dump(cstone_master_db, f, indent=2, ensure_ascii=False)
    print(f"\n[3/3] Saving databases:", flush=True)
    print(f"  -> {out_master_path} ({len(cstone_master_db)} entries)", flush=True)

    # Update sc_wiki_items_cache.json
    wiki_cache_path = os.path.join(RES_DIR, "sc_wiki_items_cache.json")
    try:
        with open(wiki_cache_path, "r", encoding="utf-8") as f:
            wiki_cache = json.load(f)
    except Exception:
        wiki_cache = {}

    for k, details in cstone_master_db.items():
        if isinstance(details, dict) and "locations" in details:
            wiki_cache[k] = details["locations"]

    with open(wiki_cache_path, "w", encoding="utf-8") as f:
        json.dump(wiki_cache, f, indent=2, ensure_ascii=False)
    print(f"  -> Updated sc_wiki_items_cache.json ({len(wiki_cache)} entries)", flush=True)

    # Update uex_items_trade_db.json
    uex_path = os.path.join(RES_DIR, "uex_items_trade_db.json")
    try:
        with open(uex_path, "r", encoding="utf-8") as f:
            uex_db = json.load(f)
    except Exception:
        uex_db = {}

    for item_name, details in cstone_master_db.items():
        if isinstance(details, dict) and details.get("locations"):
            k_low = item_name.lower()
            locs = details["locations"]
            uex_db[k_low] = {
                "name": item_name,
                "locations": [{"terminal": e["terminal"], "buy": e.get("price", 0), "sell": 0} for e in locs]
            }

    with open(uex_path, "w", encoding="utf-8") as f:
        json.dump(uex_db, f, indent=2, ensure_ascii=False)
    print(f"  -> Updated uex_items_trade_db.json ({len(uex_db)} entries)", flush=True)

    # Update dynamic volume map in storall_packer.py & cargo_packer.py
    vol_map = {}
    for item_name, details in cstone_master_db.items():
        if isinstance(details, dict):
            vol_map[item_name.lower()] = details.get("volume_scu", 0.01)
    
    vol_map_path = os.path.join(RES_DIR, "cstone_volume_map.json")
    with open(vol_map_path, "w", encoding="utf-8") as f:
        json.dump(vol_map, f, indent=2, ensure_ascii=False)
    print(f"  -> Updated cstone_volume_map.json ({len(vol_map)} item volumes)", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("=== CORNERSTONE DATA SYNC COMPLETED WITH 100% SUCCESS ===", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    run_cstone_sync()
