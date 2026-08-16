"""
SC Wiki Items Location Database — local cache reader for supply route PDFs.
Reads sc_wiki_items_cache.json and provides lookup functions.

This module is imported by pdf_engine.py and pdf_block_extract.py to resolve
item names to buy locations with prices, terminals, and system/planet data.
"""
import json, os
import path_config
import time
import threading

_CACHE_LOCK = threading.Lock()
_CACHE_PATH = os.path.join(path_config.PATHS.resources, "sc_wiki_items_cache.json")
_LOCATIONS_DB_PATH = os.path.join(path_config.PATHS.resources, "uex_locations_db.json")
_CACHE = None  # Lazy-loaded
_LOCATIONS_DB = None  # Lazy-loaded

MASTER_UNBUYABLE_PATTERNS = [
    # ── Unbuyable Military Grade A Components (Not sold in shops -> crafted via blueprints) ──
    "ts-2", "xl-1", "vk-00", "crossfield", "pontes",
    "fr-86", "fr-76", "fr-66",
    "js-500", "js-400", "js-300",
    "ultra-flow", "coolcore",

    # ── Industrial Fixtures & Crafting Machines (Non-commercial, unbuyable) ──
    "item fabricator", "fabricator", "redimake",
    
    # ── Heavy FPS Boss / Event Drops Only ──
    "scourge railgun", "animus missile launcher", "apocalypse arms scourge",
    "atzkav sniper", "yubarev pistol", "lightning bolt co", "wowblast",
    
    # ── Subscriber, Flair, Executive, Event & Custom Armor Sets ──
    "afterlife", "stoneface", "executive", "citizencon", "subscriber", "prototype",
    "golden ticket", "relic", "artifact", "trophy", "event exclusive", "overlord", "sangoma",
    "calva", "woodland custom", "desert shadow", "hazard-zone", "black cherry", "pyro rager",
    "thule", "redshift", "ironblood", "terracotta", "snowdrift", "lodestone", "canuto", "wildwood",
    "fireburst", "sunchaser", "raven", "rust society", "stinger", "switchback", "supernova", "riptide",
    "voidriot", "paladin helmet", "mandible helmet", "aves helmet", "neocutic helmet", "butcher helmet",
    "vanduul mask", "hill horror", "fieldsbury dark bear", "g-2 helmet", "centurion armor"
]

def is_unbuyable_item_name(name):
    """Check if an item name matches any unbuyable/craft/loot pattern."""
    if not name:
        return False
    nl = str(name).lower()
    return any(pat in nl for pat in MASTER_UNBUYABLE_PATTERNS)

def verify_cache_health(filepath, max_age_hours=720):
    """Verify cache file existence, age, and readability with diagnostic logging."""
    fname = os.path.basename(filepath)
    if not os.path.exists(filepath):
        print(f"[CACHE_CHECK_WARN] Cache file '{fname}' is missing.")
        return False, "missing"
    try:
        mtime = os.path.getmtime(filepath)
        age_hours = (time.time() - mtime) / 3600.0
        if age_hours > max_age_hours:
            print(f"[CACHE_CHECK_WARN] Cache file '{fname}' is STALE ({age_hours:.1f} hours old, max {max_age_hours}h).")
            return False, f"stale ({age_hours:.1f}h)"
        print(f"[CACHE_CHECK_OK] Cache file '{fname}' is FRESH ({age_hours:.1f} hours old).")
        return True, f"fresh ({age_hours:.1f}h)"
    except Exception as e:
        print(f"[CACHE_CHECK_ERROR] Exception inspecting cache file '{fname}': {e}")
        return False, f"error: {e}"

def _load_locations_db():
    global _LOCATIONS_DB
    with _CACHE_LOCK:
        if _LOCATIONS_DB is not None:
            return _LOCATIONS_DB
        healthy, status = verify_cache_health(_LOCATIONS_DB_PATH, max_age_hours=48)
        if os.path.exists(_LOCATIONS_DB_PATH):
            try:
                with open(_LOCATIONS_DB_PATH, "r", encoding="utf-8") as f:
                    _LOCATIONS_DB = json.load(f)
                print(f"[SC_WIKI_DB] Loaded {len(_LOCATIONS_DB)} location categories from uex_locations_db.json ({status}).")
            except Exception as e:
                print(f"[SC_WIKI_DB_ERROR] Failed to load uex_locations_db.json: {e}")
                _LOCATIONS_DB = {}
        else:
            _LOCATIONS_DB = {}
        return _LOCATIONS_DB

# ── Known system-to-system jump distances (minutes QT) ──
SYSTEM_DISTANCES = {
    ("stanton", "pyro"): 45,
    ("stanton", "nyx"): 55,
    ("pyro", "nyx"): 30,
}

# ── Intra-Stanton distances (planet-to-planet, minutes QT) ──
STANTON_PLANET_DISTANCES = {
    ("hurston", "crusader"): 8,
    ("hurston", "arccorp"): 10,
    ("hurston", "microtech"): 15,
    ("crusader", "arccorp"): 7,
    ("crusader", "microtech"): 12,
    ("arccorp", "microtech"): 9,
}

# ── Location → planet mapping (known stations/cities/moons/outposts/logistics) ──
_LOC_PLANET_MAP = {
    # ArcCorp & Moons
    "area18": "arccorp", "area 18": "arccorp", "arccorp": "arccorp",
    "io tower": "arccorp", "io-tower": "arccorp", "io north tower": "arccorp", "io south tower": "arccorp",
    "area 18 io tower": "arccorp", "area18 io tower": "arccorp", "io tower (area 18)": "arccorp",
    "cubby blast": "arccorp", "cubby": "arccorp", "cubby-blast": "arccorp",
    "astro armada": "arccorp", "apx": "arccorp", "g-loc": "arccorp", "g-loc bar": "arccorp",
    "dumper's depot": "arccorp", "dumpers depot": "arccorp", "dumper depot": "arccorp",
    "casaba (area 18)": "arccorp", "casaba area 18": "arccorp", "casaba outlet (area 18)": "arccorp",
    "center mass - area18": "arccorp", "center mass (area18)": "arccorp", "center mass area 18": "arccorp",
    "baijini": "arccorp", "baijini point": "arccorp", "wala": "arccorp", "lyria": "arccorp",
    "samson": "arccorp", "samson & son": "arccorp", "samson & son's salvage center": "arccorp",
    "humboldt": "arccorp", "loveridge": "arccorp", "mining area": "arccorp",
    "arc-l1": "arccorp", "arc-l2": "arccorp", "arc-l3": "arccorp", "arc-l4": "arccorp", "arc-l5": "arccorp",

    # Hurston & Moons
    "lorville": "hurston", "hurston": "hurston", "everus": "hurston", "everus harbor": "hurston",
    "arial": "hurston", "ita": "hurston", "magda": "hurston", "aberdeen": "hurston",
    "orinth": "hurston", "reclamation & disposal orinth": "hurston", "reclamation & disposal": "hurston",
    "hdms": "hurston", "tammany": "hurston", "tammany and sons": "hurston", "tammany & sons": "hurston",
    "new deal": "hurston", "new deal shipyard": "hurston", "m&v bar": "hurston",
    "hur-l1": "hurston", "hur-l2": "hurston", "hur-l3": "hurston", "hur-l4": "hurston", "hur-l5": "hurston",

    # microTech & Moons
    "new babbage": "microtech", "microtech": "microtech", "babbage": "microtech",
    "port tressler": "microtech", "tressler": "microtech",
    "calliope": "microtech", "clio": "microtech", "euterpe": "microtech",
    "devlin": "microtech", "devlin scrap": "microtech", "devlin scrap & salvage": "microtech",
    "sakura sun": "microtech", "golden meadows": "microtech", "greycat logistics": "microtech",
    "shubin": "microtech", "shubin interstellar": "microtech", "the commons": "microtech", "commons": "microtech",
    "omega pro": "microtech", "wally's": "microtech", "apres ski": "microtech",
    "rayari": "microtech", "astor": "microtech", "astor's clearing": "microtech",
    "mic-l1": "microtech", "mic-l2": "microtech", "mic-l3": "microtech", "mic-l4": "microtech", "mic-l5": "microtech",

    # Crusader & Moons
    "orison": "crusader", "crusader": "crusader", "seraphim": "crusader", "seraphim station": "crusader",
    "port olisar": "crusader", "grimhex": "crusader", "grim hex": "crusader", "kareah": "crusader",
    "yela": "crusader", "cellin": "crusader", "daymar": "crusader",
    "brio's breaker yard": "crusader", "brios breaker yard": "crusader", "brio": "crusader",
    "covalex": "crusader", "covalex distribution center": "crusader", "jumptown": "crusader",
    "kel-to": "crusader", "skutters": "crusader", "skutter": "crusader", "kc trending": "crusader", "technotic": "crusader",
    "old '38": "crusader", "old 38": "crusader",
    "providence surplus": "crusader", "providence": "crusader", "providence platform": "crusader", "makau": "crusader", "cousin crow's": "crusader", "cousin crow": "crusader",
    "cru-l1": "crusader", "cru-l2": "crusader", "cru-l3": "crusader", "cru-l4": "crusader", "cru-l5": "crusader",

    # Stanton Gateways
    "nyx gateway (stanton)": "stanton", "pyro gateway (stanton)": "stanton", "terra gateway (stanton)": "stanton", "magnus gateway (stanton)": "stanton",

    # Pyro System
    "pyro": "pyro", "ruin": "pyro", "ruin station": "pyro",
    "checkmate": "pyro", "checkmate station": "pyro", "monox": "pyro",
    "jackson's swap": "pyro", "jacksons swap": "pyro", "jackson swap": "pyro", "yang's place": "pyro", "ostler's claim": "pyro", "sunset mesa": "pyro", "gaslight": "pyro", "arid reach": "pyro",
    "bloom": "pyro", "patchcity": "pyro", "patch city": "pyro", "orbituary": "pyro", "starlight service station": "pyro",
    "starlight": "pyro", "megastructure": "pyro", "ignis": "pyro", "vance": "pyro", "adamo": "pyro",
    "terminus": "pyro", "pram": "pyro", "rustville": "pyro", "dudley & daughters": "pyro", "guns dudley": "pyro", "dudley": "pyro", "rod's fuel": "pyro", "guns megumi": "pyro", "megumi": "pyro",
    "stanton gateway (pyro)": "pyro", "nyx gateway (pyro)": "pyro",

    # Nyx System
    "nyx": "nyx", "levski": "nyx", "delamar": "nyx", "grand barter": "nyx",
    "conscientious objects": "nyx", "conscientious": "nyx", "cordry's": "nyx", "cordry": "nyx", "cordrys": "nyx",
    "teach's ship shop": "nyx", "teach's": "nyx", "teach": "nyx", "cafe musain": "nyx",
    "glaciem": "nyx", "glaciem ring": "nyx", "keeger": "nyx", "keeger belt": "nyx",
    "nyx i": "nyx", "nyx ii": "nyx", "nyx iii": "nyx", "porphyr": "nyx", "vanguard": "nyx",
    "station alpha": "nyx", "station delta": "nyx", "station theta": "nyx", "station lambda": "nyx", "station kappa": "nyx",
    "pssa": "nyx", "pssd": "nyx", "psst": "nyx", "pssl": "nyx", "pssk": "nyx",
    "qv breaker": "nyx", "qv services": "nyx", "gold horizon": "nyx", "kepler": "nyx",
    "nyx-l1": "nyx", "nyx-l2": "nyx", "nyx-l3": "nyx", "nyx-l4": "nyx", "nyx-l5": "nyx",
    "stanton gateway (nyx)": "nyx", "pyro gateway (nyx)": "nyx", "bremen gateway (nyx)": "nyx", "castra gateway (nyx)": "nyx",
}

# ── L-point / Outpost → System mapping ──
_LOC_SYSTEM_MAP = {
    "stanton": "stanton", "pyro": "pyro", "nyx": "nyx",
    "monox": "pyro", "bloom": "pyro", "ruin": "pyro", "checkmate": "pyro", "ignis": "pyro", "vance": "pyro", "adamo": "pyro", "terminus": "pyro",
    "sunset mesa": "pyro", "gaslight": "pyro", "jacksons swap": "pyro", "jackson's swap": "pyro", "yang's place": "pyro", "ostler's claim": "pyro", "arid reach": "pyro",
    "delamar": "nyx", "levski": "nyx", "glaciem": "nyx", "glaciem ring": "nyx", "keeger": "nyx", "keeger belt": "nyx",
    "nyx i": "nyx", "nyx ii": "nyx", "nyx iii": "nyx", "porphyr": "nyx", "vanguard": "nyx", "gold horizon": "nyx", "kepler": "nyx",
    "station alpha": "nyx", "station delta": "nyx", "station theta": "nyx", "station lambda": "nyx", "station kappa": "nyx",
    "pssa": "nyx", "pssd": "nyx", "psst": "nyx", "pssl": "nyx", "pssk": "nyx", "qv breaker": "nyx",
    "nyx-l1": "nyx", "nyx-l2": "nyx", "nyx-l3": "nyx", "nyx-l4": "nyx", "nyx-l5": "nyx",
    "hurston": "stanton", "arccorp": "stanton", "microtech": "stanton", "crusader": "stanton",
}


def reload_cache():
    """Force reload of sc_wiki_items_cache.json and uex_locations_db.json into memory."""
    global _CACHE, _LOCATIONS_DB
    with _CACHE_LOCK:
        _CACHE = None
        _LOCATIONS_DB = None
    return _load_cache()

def _load_cache():
    """Lazy-load the cached SC Wiki items data and frequent_items.json locations."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    cache_data = {}
    healthy, status = verify_cache_health(_CACHE_PATH, max_age_hours=720)
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            print(f"[SC_WIKI_DB] Loaded {len(cache_data)} entries from sc_wiki_items_cache.json ({status}).")
        except Exception as e:
            print(f"[SC_WIKI_DB_ERROR] Failed to load sc_wiki_items_cache.json: {e}")
            cache_data = {}

    # Merge locations from frequent_items.json
    freq_path = os.path.join(path_config.PATHS.resources, "frequent_items.json")
    if os.path.exists(freq_path):
        try:
            with open(freq_path, "r", encoding="utf-8") as f:
                freq_items = json.load(f)
            freq_count = 0
            for item in freq_items:
                iname = item.get("name", "")
                locs = item.get("locations", [])
                if not iname or not locs:
                    continue
                converted = []
                for l in locs:
                    term = l.get("shop") or l.get("terminal") or l.get("station", "")
                    converted.append({
                        "terminal": term,
                        "price": l.get("buy_price") or l.get("price", 0),
                        "location": l.get("station") or l.get("city") or l.get("location", ""),
                        "parent": l.get("planet") or l.get("parent", ""),
                        "system": l.get("system", "Stanton"),
                    })
                if iname not in cache_data:
                    cache_data[iname] = converted
                    freq_count += 1
                else:
                    # Append non-duplicate terminals
                    existing_terms = {e.get("terminal", "") for e in cache_data[iname]}
                    for c in converted:
                        if c["terminal"] not in existing_terms:
                            cache_data[iname].append(c)
        except Exception as e:
            print(f"[SC_WIKI_DB_ERROR] Error merging frequent_items.json locations: {e}")

    # Merge locations from uex_items_trade_db.json (over 2,700+ real shop buy terminals)
    uex_trade_path = os.path.join(path_config.PATHS.resources, "uex_items_trade_db.json")
    if os.path.exists(uex_trade_path):
        try:
            with open(uex_trade_path, "r", encoding="utf-8") as f:
                uex_db = json.load(f)
            uex_count = 0
            for item_key, item_info in uex_db.items():
                if not isinstance(item_info, dict): continue
                iname = item_info.get("name") or item_key.title()
                if is_unbuyable_item_name(iname) or is_unbuyable_item_name(item_key):
                    continue
                locs = item_info.get("locations", [])
                if not iname or not locs: continue
                converted = []
                for l in locs:
                    if not isinstance(l, dict): continue
                    term = l.get("terminal") or l.get("shop") or ""
                    buy = l.get("buy", 0)
                    if buy > 0 and term:
                        converted.append({
                            "terminal": term,
                            "price": buy,
                            "location": term,
                            "parent": "",
                            "system": _guess_system("stanton", term)
                        })
                if converted:
                    if iname not in cache_data:
                        cache_data[iname] = converted
                        uex_count += 1
                    else:
                        existing_terms = {e.get("terminal", "") for e in cache_data[iname]}
                        for c in converted:
                            if c["terminal"] not in existing_terms:
                                cache_data[iname].append(c)
            print(f"[SC_WIKI_DB] Merged locations for {uex_count} items from uex_items_trade_db.json.")
        except Exception as e:
            print(f"[SC_WIKI_DB_ERROR] Error merging uex_items_trade_db.json: {e}")

    # Merge raw commodities, countermeasures and ores from uex_trade_db.json
    uex_raw_trade_path = os.path.join(path_config.PATHS.resources, "uex_trade_db.json")
    if os.path.exists(uex_raw_trade_path):
        try:
            with open(uex_raw_trade_path, "r", encoding="utf-8") as f:
                raw_trade = json.load(f)
            raw_count = 0
            for commodity_key, entries in raw_trade.items():
                if not isinstance(entries, list): continue
                converted = []
                for entry in entries:
                    if not isinstance(entry, dict): continue
                    term = entry.get("terminal", "")
                    buy = entry.get("buy", 0)
                    if buy > 0 and term:
                        converted.append({
                            "terminal": term,
                            "price": buy,
                            "location": term,
                            "parent": "",
                            "system": _guess_system("stanton", term)
                        })
                if converted:
                    # Aliases for commodity names
                    c_title = commodity_key.title()
                    aliases = [c_title, commodity_key]
                    if "recycled material composite" in commodity_key.lower():
                        aliases.extend(["Recycled Material Composite (RMC)", "RMC", "Recycled Material Composite"])
                    elif "decoy" in commodity_key.lower():
                        aliases.extend(["Decoy Countermeasures", "Ship Decoy Countermeasures", "Decoy"])
                    elif "noise" in commodity_key.lower():
                        aliases.extend(["Noise Countermeasures", "Ship Noise Countermeasures", "Noise"])
                    elif "hydrogen fuel" in commodity_key.lower():
                        aliases.extend(["Hydrogen Fuel", "Hydrogen Fuel (8 SCU)"])

                    for alias in aliases:
                        if alias not in cache_data:
                            cache_data[alias] = converted
                            raw_count += 1
                        else:
                            existing_terms = {e.get("terminal", "") for e in cache_data[alias]}
                            for c in converted:
                                if c["terminal"] not in existing_terms:
                                    cache_data[alias].append(c)
            print(f"[SC_WIKI_DB] Merged {raw_count} commodity & countermeasure aliases from uex_trade_db.json.")
        except Exception as e:
            print(f"[SC_WIKI_DB_ERROR] Error merging uex_trade_db.json: {e}")

    # Universal space station and landing zone supply network for standard supplies
    _ALL_STATIONS = [
        ("Seraphim", "Crusader", "stanton"), ("CRU-L1", "Crusader", "stanton"), ("CRU-L4", "Crusader", "stanton"), ("CRU-L5", "Crusader", "stanton"),
        ("Everus Harbor", "Hurston", "stanton"), ("HUR-L1", "Hurston", "stanton"), ("HUR-L2", "Hurston", "stanton"), ("HUR-L3", "Hurston", "stanton"), ("HUR-L4", "Hurston", "stanton"), ("HUR-L5", "Hurston", "stanton"),
        ("Port Tressler", "microTech", "stanton"), ("MIC-L1", "microTech", "stanton"), ("MIC-L2", "microTech", "stanton"), ("MIC-L3", "microTech", "stanton"), ("MIC-L4", "microTech", "stanton"), ("MIC-L5", "microTech", "stanton"),
        ("Baijini Point", "ArcCorp", "stanton"), ("ARC-L1", "ArcCorp", "stanton"), ("ARC-L2", "ArcCorp", "stanton"), ("ARC-L3", "ArcCorp", "stanton"), ("ARC-L4", "ArcCorp", "stanton"),
        ("Grim HEX", "Crusader", "stanton"), ("Orison", "Crusader", "stanton"), ("Lorville", "Hurston", "stanton"), ("Area18", "ArcCorp", "stanton"), ("New Babbage", "microTech", "stanton"),
        ("Checkmate", "Pyro", "pyro"), ("Orbituary", "Pyro", "pyro"), ("Ruin Station", "Pyro", "pyro"), ("PatchCity", "Pyro", "pyro"), ("Starlight", "Pyro", "pyro"),
        ("Gaslight", "Pyro", "pyro"), ("Megumi", "Pyro", "pyro"), ("Dudley", "Pyro", "pyro"), ("Rod's Fuel", "Pyro", "pyro"), ("Sunset Mesa", "Pyro", "pyro"), ("Jackson's Swap", "Pyro", "pyro"),
        ("Levski", "Delamar", "nyx"), ("Grand Barter", "Delamar", "nyx"), ("Teach's Levski", "Delamar", "nyx"), ("Conscientious Objects", "Delamar", "nyx")
    ]

    # 1. Ship Ammunition Sizes 1-7 (Commodity & Admin Terminals across all stations)
    for sz in range(1, 8):
        ammo_name = f"Size {sz} Ammunition"
        ammo_entries = [
            {"terminal": f"Admin Office - {st}", "price": 6000 + sz * 300, "location": st, "parent": parent, "system": sys}
            for st, parent, sys in _ALL_STATIONS
        ]
        if ammo_name not in cache_data or len(cache_data[ammo_name]) < 5:
            cache_data[ammo_name] = ammo_entries
        else:
            existing = {e.get("location", "") for e in cache_data[ammo_name]}
            for ae in ammo_entries:
                if ae["location"] not in existing:
                    cache_data[ammo_name].append(ae)

    # 2. Cargo Center Tools, Batteries, and Canisters (Cargo Center Supplies across all stations)
    cargo_tool_items = [
        ("MaxLift Tractor Beam Battery", 175),
        ("Cambio Multi-tool Battery", 63),
        ("Cambrio SRT Battery", 63),
        ("Cambio SRT Canister", 120),
        ("MaxLift Tractor Beam", 1975),
        ("Cambio SRT", 20155)
    ]
    for tool_name, tool_price in cargo_tool_items:
        tool_entries = [
            {"terminal": f"Cargo Center Supplies - {st}", "price": tool_price, "location": st, "parent": parent, "system": sys}
            for st, parent, sys in _ALL_STATIONS
        ]
        if tool_name not in cache_data or len(cache_data[tool_name]) < 5:
            cache_data[tool_name] = tool_entries
        else:
            existing = {e.get("location", "") for e in cache_data[tool_name]}
            for te in tool_entries:
                if te["location"] not in existing:
                    cache_data[tool_name].append(te)

    # 3. Standard Beverages (Food & Beverage / Convenience / Casaba across all stations)
    drink_items = [("CRUZ Lux", 6), ("CRUZ Dark", 6), ("CRUZ Flow", 6), ("CRUZ Pulse", 6)]
    for drink_name, drink_price in drink_items:
        drink_entries = [
            {"terminal": f"Food & Beverage Kiosk - {st}", "price": drink_price, "location": st, "parent": parent, "system": sys}
            for st, parent, sys in _ALL_STATIONS
        ]
        if drink_name not in cache_data or len(cache_data[drink_name]) < 5:
            cache_data[drink_name] = drink_entries
        else:
            existing = {e.get("location", "") for e in cache_data[drink_name]}
            for de in drink_entries:
                if de["location"] not in existing:
                    cache_data[drink_name].append(de)


    # 4. Standard Stor-All Storage Containers (Cargo Decks / Platinum Bay / Dumper's Depot - Max 8 SCU)
    container_items = [
        (["Stor-All 1 SCU Storage Container", "Stor-All 1 SCU", "Stor-All 1 SCU Cargo Container", "1 SCU Storage Container", "1 SCU Container"], 150),
        (["Stor-All 2 SCU Storage Container", "Stor-All 2 SCU", "Stor-All 2 SCU Cargo Container", "2 SCU Storage Container", "2 SCU Container"], 300),
        (["Stor-All 4 SCU Storage Container", "Stor-All 4 SCU", "Stor-All 4 SCU Cargo Container", "4 SCU Storage Container", "4 SCU Container"], 600),
        (["Stor-All 8 SCU Storage Container", "Stor-All 8 SCU", "Stor-All 8 SCU Cargo Container", "8 SCU Storage Container", "8 SCU Container"], 1200),
        (["Stor-All [TOOLS & UTILITY] Container", "Stor-All [MEDICAL & CONSUMABLES] Container", "Stor-All [WEAPONS & AMMO] Container", "Stor-All [ARMOR & CLOTHING] Container", "Stor-All [REPAIR & ENGINEERING] Container"], 4250),
    ]
    for names_list, c_price in container_items:
        c_entries = [
            {"terminal": f"Cargo Center Supplies - {st}", "price": c_price, "location": st, "parent": parent, "system": sys}
            for st, parent, sys in _ALL_STATIONS
        ]
        for cname in names_list:
            if cname not in cache_data or len(cache_data[cname]) < 5:
                cache_data[cname] = c_entries
            else:
                existing = {e.get("location", "") for e in cache_data[cname]}
                for ce in c_entries:
                    if ce["location"] not in existing:
                        cache_data[cname].append(ce)

    # 5. Standard Ordnance, Bombs, and Ship Weapons (Center Mass / Ship Weapons Showroom / Live Fire)
    ordnance_items = [
        (["Colossus Bomb", "S10 Colossus Bomb"], 150000),
        (["Stormburst Bomb", "S3 Stormburst Bomb", "S5 Stormburst Bomb"], 18500),
        (["Dominator II Missile", "Dominator II"], 3200),
        (["Tempest II Missile", "Tempest II"], 3200),
        (["Arrester III Missile", "Arrester III"], 5400),
        (["Stalker IV Missile", "Stalker IV"], 8900),
        (["Argus IX Torpedo", "Argus IX"], 48000),
        (["Seeker IX Torpedo", "Seeker IX"], 48000),
        (["Typhoon IX Torpedo", "Typhoon IX"], 48000),
        (["CF-447 Rhino Laser Repeater (Size 4)", "CF-447 Rhino", "CF-447"], 68000),
        (["CF-337 Panther Laser Repeater (Size 3)", "CF-337 Panther", "CF-337"], 34000),
        (["CF-227 Badger Laser Repeater (Size 2)", "CF-227 Badger", "CF-227"], 17000),
        (["CF-117 Bulldog Laser Repeater (Size 1)", "CF-117 Bulldog", "CF-117"], 8500),
        (["M7A Laser Cannon (Size 5)", "M7A Laser Cannon", "M7A"], 155000),
        (["M6A Laser Cannon (Size 4)", "M6A Laser Cannon", "M6A"], 72000),
        (["M5A Laser Cannon (Size 3)", "M5A Laser Cannon", "M5A"], 36000),
        (["M4A Laser Cannon (Size 2)", "M4A Laser Cannon", "M4A"], 18000),
    ]
    for names_list, ord_price in ordnance_items:
        ord_entries = [
            {"terminal": f"Ship Weapons Showroom - {st}", "price": ord_price, "location": st, "parent": parent, "system": sys}
            for st, parent, sys in _ALL_STATIONS if sys == "stanton"
        ]
        for oname in names_list:
            if oname not in cache_data or len(cache_data[oname]) < 5:
                cache_data[oname] = ord_entries
            else:
                existing = {e.get("location", "") for e in cache_data[oname]}
                for oe in ord_entries:
                    if oe["location"] not in existing:
                        cache_data[oname].append(oe)

    _CACHE = cache_data
    return _CACHE


def _guess_planet(location_name, parent_name=""):
    """Guess the planet from a location name or parent name using UEX DB + fallback dictionary."""
    loc_low = (location_name or "").lower().strip()
    parent_low = (parent_name or "").lower().strip()

    # 1. Query _load_locations_db first
    locs_db = _load_locations_db()
    if locs_db:
        for cat_locs in locs_db.values():
            if isinstance(cat_locs, dict):
                for name, info in cat_locs.items():
                    nl = name.lower().strip()
                    if loc_low and (nl == loc_low or loc_low in nl or nl in loc_low):
                        pla = info.get("planet")
                        if pla:
                            return pla.lower().strip()
                        s = info.get("system")
                        if s:
                            return s.lower().strip()

    # 2. Hardcoded fallback dictionary
    for key in [loc_low, parent_low]:
        if key in _LOC_PLANET_MAP:
            return _LOC_PLANET_MAP[key]
        for prefix, planet in _LOC_PLANET_MAP.items():
            if prefix in key and len(prefix) > 2:
                return planet
    return ""


def _guess_system(system_name, location_name=""):
    """Determine star system from explicit system name or location using UEX DB + fallbacks."""
    loc_low = (location_name or "").lower().strip()
    sys_low = (system_name or "").lower().strip()

    # 0. Parenthetical system tags take highest priority (e.g. "Pyro Gateway (Stanton)" -> stanton)
    if "(stanton)" in loc_low:
        return "stanton"
    if "(pyro)" in loc_low:
        return "pyro"
    if "(nyx)" in loc_low:
        return "nyx"

    # Gateway destination names (without parenthetical override)
    if "pyro gateway" in loc_low:
        return "stanton"  # Gateway leading to Pyro is located in Stanton
    if "stanton gateway" in loc_low:
        return "pyro"     # Gateway leading to Stanton is located in Pyro
    if "nyx gateway" in loc_low:
        return "stanton"  # Gateway leading to Nyx is located in Stanton

    # Pure Stations / Outposts in Pyro
    if any(k in loc_low for k in ["checkmate", "ruin station", "patchcity", "orbituary", "starlight", "monox", "bloom"]):
        return "pyro"
    # Pure Stations / Outposts in Nyx
    if any(k in loc_low for k in ["nyx", "levski", "delamar", "glaciem", "porphyr", "vanguard", "gold horizon", "kepler", "nyx-l", "pssa", "psst", "pssl", "pssd", "pssk"]):
        return "nyx"
    # Pure Stations / Outposts in Stanton
    if any(x in loc_low for x in ["everus", "tressler", "baijini", "seraphim", "area18", "lorville", "babbage", "orison"]):
        return "stanton"

    # 1. Query _load_locations_db
    locs_db = _load_locations_db()
    if locs_db and loc_low:
        for cat_locs in locs_db.values():
            if isinstance(cat_locs, dict):
                for name, info in cat_locs.items():
                    nl = name.lower().strip()
                    if nl == loc_low or loc_low in nl or nl in loc_low:
                        s = info.get("system")
                        if s and s.lower().strip() in ["pyro", "nyx", "stanton"]:
                            return s.lower().strip()

    # 2. Fallback check in _LOC_PLANET_MAP & system lists
    for key, target in _LOC_PLANET_MAP.items():
        if key in loc_low and len(key) > 2:
            if target in ["pyro", "nyx", "stanton"]:
                return target
            return "stanton"

    if any(k in loc_low for k in ["nyx", "levski", "delamar", "glaciem"]):
        return "nyx"
    if any(k in loc_low for k in ["pyro", "ruin", "checkmate", "monox", "bloom", "patchcity", "orbituary", "starlight", "megastructure", "ignis", "vance", "adamo", "terminus", "pram"]):
        return "pyro"
    if any(k in loc_low for k in ["stanton", "arccorp", "hurston", "microtech", "crusader", "area18", "babbage", "lorville", "orison", "seraphim", "tressler"]):
        return "stanton"
    if sys_low in _LOC_SYSTEM_MAP:
        return sys_low
    return "stanton"


def estimate_qt_minutes(from_location, to_location,
                        from_system="stanton", to_system="stanton"):
    """Estimate QT travel time between two locations in minutes."""
    fs = _guess_system(from_system, from_location)
    ts = _guess_system(to_system, to_location)

    # Cross-system
    if fs != ts:
        pair = tuple(sorted([fs, ts]))
        return SYSTEM_DISTANCES.get(pair, 55)

    # Same system — compare planets
    fp = _guess_planet(from_location)
    tp = _guess_planet(to_location)

    if not fp or not tp:
        return 5
    if fp == tp:
        return 2
    pair = tuple(sorted([fp, tp]))
    return STANTON_PLANET_DISTANCES.get(pair, 10)


def lookup_item(item_name, from_location="", from_system="stanton"):
    """
    Look up buy locations for an item from the SC Wiki cache.
    Combines exact match + variant skin matches (e.g. P4-AR Rifle vs P4-AR "Boneyard" Rifle).
    """
    cache = _load_cache()
    import re
    item_low = item_name.lower().strip()
    # Strip quantity prefixes like '2x ', 'x2 ', '10x '
    item_low = re.sub(r'^\s*\d+\s*[xX*]\s*', '', item_low).strip()
    item_low = re.sub(r'^\s*[xX]\s*\d+\s*', '', item_low).strip()
    
    # Strip quotes and size tags like '(Size 4)' for clean matching
    clean_item = item_low.replace('"', '').replace("'", "")
    clean_no_size = re.sub(r'\s*\([^)]*\)', '', clean_item).strip()
    clean_no_noise = re.sub(r'\b(laser|ballistic|salvage|module)\b', '', clean_no_size).strip()
    clean_no_noise = ' '.join(clean_no_noise.split())

    if is_unbuyable_item_name(clean_item) or is_unbuyable_item_name(item_name):
        return []

    search_variants = [clean_item, clean_no_size, clean_no_noise]

    matches = []
    seen_terminals = set()

    # Pass 1: Strict exact matches
    for s_var in search_variants:
        if not s_var: continue
        for key, entries in cache.items():
            key_clean = key.lower().replace('"', '').replace("'", "")
            if s_var == key_clean:
                for entry in entries:
                    t_name = entry.get("terminal", "")
                    if t_name not in seen_terminals:
                        seen_terminals.add(t_name)
                        matches.append(entry)
        if matches:
            break

    # Pass 2: All query words contained in key (e.g. 'a03 magazine' -> 'A03 Sniper Rifle Magazine (15 Cap)')
    if not matches:
        for s_var in search_variants:
            if not s_var: continue
            item_words = [w for w in s_var.split() if len(w) >= 2]
            if not item_words: continue
            for key, entries in cache.items():
                key_clean = key.lower().replace('"', '').replace("'", "")
                if all(w in key_clean for w in item_words):
                    for entry in entries:
                        t_name = entry.get("terminal", "")
                        if t_name not in seen_terminals:
                            seen_terminals.add(t_name)
                            matches.append(entry)
            if matches:
                break

    if not matches and any(w in clean_item for w in ["stor-all", "container", "storage box"]):
        c_key = "Stor-All [TOOLS & UTILITY] Container" if "[" in clean_item else "Stor-All 1 SCU Storage Container"
        if c_key in cache:
            matches = list(cache[c_key])

    if not matches:
        return []

    from_sys_clean = _guess_system(from_system, from_location)

    # Get cross-validation status from data_validator
    try:
        from data_validator import validate_item as _validate, build_full_buy_path
        validation = _validate(item_name)
        v_status = validation.get("status", "UNVERIFIED_SINGLE_SOURCE")
        v_source_count = validation.get("source_count", 1)
    except Exception:
        v_status = "UNVERIFIED_SINGLE_SOURCE"
        v_source_count = 1
        build_full_buy_path = lambda s="", p="", l="", t="": f"{s} > {l} > {t}".strip(" > ")

    results = []
    is_ordnance = any(k in clean_item for k in ["torpedo", "missile", "bomb"])

    for entry in matches:
        terminal = entry.get('terminal', '')
        loc_name = entry.get("location", "")

        # Guard: Reject non-existent "Stanton Cargo Terminal"
        combined_loc = f"{terminal} {loc_name}".lower()
        if "stanton cargo terminal" in combined_loc:
            continue

        # Guard: Ordnance items (torpedoes, missiles, bombs) are not sold at Admin Offices or Checkmate Station
        if is_ordnance:
            t_low = (terminal or "").lower()
            l_low = (loc_name or "").lower()
            if "admin office" in t_low or "checkmate" in t_low or "checkmate" in l_low or "ruin station" in t_low:
                continue

        parent = entry.get("parent", "")
        system = _guess_system(entry.get("system", "stanton"), terminal or loc_name)
        qt = estimate_qt_minutes(from_location, terminal or loc_name,
                                 from_sys_clean, system)

        terminal = entry.get('terminal', loc_name)
        planet = _guess_planet(terminal or loc_name, parent)

        # Build full buy path: System > Planet > Location > Shop
        full_path = build_full_buy_path(system, planet, loc_name, terminal)
        if "stanton cargo terminal" in full_path.lower():
            continue

        if parent and system and parent.lower() != system.lower():
            display = f"{system.title()} > {parent} > {terminal}"
        elif system:
            display = f"{system.title()} > {terminal}"
        else:
            display = terminal

        results.append({
            "terminal": entry.get("terminal", ""),
            "price": entry.get("price", 0),
            "location": loc_name,
            "parent": parent,
            "system": system,
            "qt_min": qt,
            "display": display,
            "full_buy_path": full_path,
            "verification_status": v_status,
            "source_count": v_source_count,
        })

    results.sort(key=lambda x: (x["qt_min"], x["price"]))
    return results


def get_best_buy_location(item_name, from_location="", from_system="stanton"):
    """
    Get the single best (nearest + cheapest) buy location for an item.

    Returns dict with keys: terminal, price, location, parent, system, qt_min, display
    or None if not found.
    """
    results = lookup_item(item_name, from_location, from_system)
    if results:
        # Prefer same-system results
        same_sys = [r for r in results if r["system"] == from_system.lower()]
        if same_sys:
            return same_sys[0]
        return results[0]
    return None


def get_item_procurement_resolution(item_name, qty=1, from_location="", from_system="stanton"):
    """
    Comprehensive procurement resolution for an item:
    1. If item has commercial buy locations -> returns status 'BUYABLE' with candidate locations.
    2. If item is not commercially sold:
       - If blueprint/crafting recipe exists -> returns status 'NEED_TO_BE_CRAFTED' with blueprint and required ores/materials.
       - If no blueprint exists -> returns status 'UNOBTAINABLE_LOOT' (needs to be looted / field recovery).
    """
    buy_locations = lookup_item(item_name, from_location=from_location, from_system=from_system)
    if buy_locations:
        return {
            "status": "BUYABLE",
            "is_buyable": True,
            "buy_locations": buy_locations,
            "best_buy": buy_locations[0],
            "directive": buy_locations[0].get("full_buy_path") or buy_locations[0].get("display")
        }

    try:
        from src.core.crafting_helper import resolve_unbuyable_item
        craft_res = resolve_unbuyable_item(item_name, qty=qty)
        return {
            "status": craft_res["status"],
            "is_buyable": False,
            "can_craft": craft_res["can_craft"],
            "blueprint": craft_res.get("blueprint"),
            "materials": craft_res.get("materials", []),
            "category": craft_res.get("category", ""),
            "directive": craft_res.get("display_directive"),
            "directive_type": craft_res.get("directive_type")
        }
    except Exception as e:
        return {
            "status": "UNOBTAINABLE_LOOT",
            "is_buyable": False,
            "can_craft": False,
            "blueprint": None,
            "materials": [],
            "directive": "UNOBTAINABLE // NEEDS TO BE LOOTED (No vendor terminal & no blueprint available)",
            "directive_type": "LOOT"
        }


def get_cache_stats():
    """Return stats about the cached data."""
    cache = _load_cache()
    total_items = len(cache)
    total_locations = sum(len(v) for v in cache.values())
    return {"items": total_items, "locations": total_locations}

