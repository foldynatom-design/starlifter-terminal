# -*- coding: utf-8 -*-
"""
cstone_universal_scraper.py — Scrapes Cornerstone Universal Item Finder (finder.cstone.space)
across ALL categories, endpoints, and in-game shop locations.
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
    # Weapons
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

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(1.0)

def parse_location_string(loc_raw):
    # e.g. "Stanton - ArcCorp - Area18 - Retail plaza - Cubby Blast"
    # or "Nyx &gt; Pyro Jump Point - Pyro Gateway - Galleria - FPS Armor"
    s = loc_raw.replace("&gt;", ">").replace("&amp;", "&").replace("&#x27;", "'").replace(" - ", " > ")
    parts = [p.strip() for p in s.split(">") if p.strip()]
    
    sys_name = "Stanton"
    if parts:
        p0_low = parts[0].lower()
        if "pyro" in p0_low: sys_name = "Pyro"
        elif "nyx" in p0_low: sys_name = "Nyx"
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

def fetch_item_locations(detail_prefix, item_id, item_name):
    url = f"https://finder.cstone.space/{detail_prefix}/{item_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        tables = re.findall(r'<table\b[^>]*>(.*?)</table>', html, re.DOTALL)
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
        return item_id, item_name, loc_entries
    except Exception as e:
        return item_id, item_name, []

def main():
    print("=" * 70, flush=True)
    print("=== STARTING FULL CORNERSTONE (CSTONE.SPACE) DATA SCRAPING ===", flush=True)
    print("=" * 70, flush=True)

    all_items_to_fetch = []
    seen_ids = set()

    for url, prefix, cat_label in CATALOG_ENDPOINTS:
        try:
            items = fetch_json(url)
            sold_items = [it for it in items if it.get("Sold") == 1]
            print(f"[CATALOG] {cat_label:25s} -> {len(items)} items ({len(sold_items)} sold in game)", flush=True)
            for it in sold_items:
                i_id = it.get("ItemId")
                i_name = it.get("Name")
                if i_id and i_id not in seen_ids:
                    seen_ids.add(i_id)
                    all_items_to_fetch.append((prefix, i_id, i_name))
        except Exception as e:
            print(f"[ERR CATALOG] {cat_label}: {e}", flush=True)

    print(f"\n[TOTAL ITEMS TO CRAWL]: {len(all_items_to_fetch)} items sold in Star Citizen", flush=True)

    cstone_db = {}
    done_count = 0
    total = len(all_items_to_fetch)
    start_t = time.time()

    # Multi-threaded fetching (20 parallel workers)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_item_locations, p, i_id, name): (i_id, name) for p, i_id, name in all_items_to_fetch}
        for f in as_completed(futures):
            item_id, item_name, locs = f.result()
            done_count += 1
            if locs:
                cstone_db[item_name] = locs
                cstone_db[item_name.lower()] = locs

            if done_count % 50 == 0 or done_count == total:
                elapsed = time.time() - start_t
                rate = done_count / elapsed if elapsed > 0 else 0
                print(f"[PROGRESS] {done_count:4d}/{total:4d} items scraped ({len(cstone_db)//2} with verified stores) - {rate:.1f} items/sec", flush=True)

    # Save cstone_master_db.json
    out_cstone_path = os.path.join(RES_DIR, "cstone_master_db.json")
    with open(out_cstone_path, "w", encoding="utf-8") as f:
        json.dump(cstone_db, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Saved CStone Master Database -> {out_cstone_path} ({len(cstone_db)} entries)", flush=True)

    # Merge into sc_wiki_items_cache.json
    wiki_cache_path = os.path.join(RES_DIR, "sc_wiki_items_cache.json")
    try:
        with open(wiki_cache_path, "r", encoding="utf-8") as f:
            wiki_cache = json.load(f)
    except Exception:
        wiki_cache = {}

    for k, locs in cstone_db.items():
        wiki_cache[k] = locs

    with open(wiki_cache_path, "w", encoding="utf-8") as f:
        json.dump(wiki_cache, f, indent=2, ensure_ascii=False)
    print(f"[OK] Updated sc_wiki_items_cache.json with full CStone data ({len(wiki_cache)} entries)", flush=True)

    # Merge into uex_items_trade_db.json
    uex_path = os.path.join(RES_DIR, "uex_items_trade_db.json")
    try:
        with open(uex_path, "r", encoding="utf-8") as f:
            uex_db = json.load(f)
    except Exception:
        uex_db = {}

    for item_name, locs in cstone_db.items():
        if isinstance(locs, list) and locs:
            k_low = item_name.lower()
            uex_db[k_low] = {
                "name": item_name,
                "locations": [{"terminal": e["terminal"], "buy": e.get("price", 0), "sell": 0} for e in locs]
            }

    with open(uex_path, "w", encoding="utf-8") as f:
        json.dump(uex_db, f, indent=2, ensure_ascii=False)
    print(f"[OK] Updated uex_items_trade_db.json ({len(uex_db)} entries)", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("=== FULL CORNERSTONE DATA SYNC COMPLETED SUCCESSFULLY ===", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
