# -*- coding: utf-8 -*-
"""
uex_sync.py - UEX API data synchronization and trade database access.

Provides lazy-loaded trade/location/ship databases from UEX JSON files.
Also provides verify_and_update_uex_data() for live API sync.

Usage:
    from uex_sync import (
        ensure_trade_dbs, verify_and_update_uex_data,
        uex_trade_db, uex_items_trade_db, uex_locations_db, uex_ships_db,
    )
"""

import os
import sys
import json as _json
import re
import urllib.request
import time

# ── Resource directory (via centralized PATHS) ──
from path_config import PATHS
_res_dir = PATHS.resources


# ── Eagerly loaded databases (needed at startup for autocomplete) ──
_uex_locations_db = {}
_loc_db_path = os.path.join(_res_dir, "uex_locations_db.json")
if os.path.exists(_loc_db_path):
    try:
        with open(_loc_db_path, "r", encoding="utf-8") as _f:
            _uex_locations_db = _json.load(_f)
    except Exception:
        pass

_uex_ships_db = {}
_ships_db_path = os.path.join(_res_dir, "uex_ships_db.json")
if os.path.exists(_ships_db_path):
    try:
        with open(_ships_db_path, "r", encoding="utf-8") as _f:
            _uex_ships_db = _json.load(_f)
    except Exception:
        pass

# ── Lazily loaded trade databases (loaded on first PDF generation) ──
_uex_trade_db = None
_uex_items_trade_db = None

# ── Concept ships set (shared with fleet_helper) ──
try:
    from fleet_helper import _CONCEPT_SHIPS
except ImportError:
    _CONCEPT_SHIPS = set()

# ── Public accessors (for other modules to import) ──
def uex_locations_db():
    """Return the locations database dict."""
    return _uex_locations_db

def uex_ships_db():
    """Return the ships database dict."""
    return _uex_ships_db

def uex_trade_db():
    """Return the trade database dict (lazy-loaded)."""
    ensure_trade_dbs()
    return _uex_trade_db

def uex_items_trade_db():
    """Return the items trade database dict (lazy-loaded)."""
    ensure_trade_dbs()
    return _uex_items_trade_db


def _ensure_trade_dbs():
    """Lazy-load trade databases on first use."""
    global _uex_trade_db, _uex_items_trade_db
    if _uex_trade_db is None:
        _uex_trade_db = {}
        _trade_db_path = os.path.join(_res_dir, "uex_trade_db.json")
        if os.path.exists(_trade_db_path):
            try:
                with open(_trade_db_path, "r", encoding="utf-8") as _f:
                    _uex_trade_db = _json.load(_f)
            except Exception: pass
    if _uex_items_trade_db is None:
        _uex_items_trade_db = {}
        _items_trade_path = os.path.join(_res_dir, "uex_items_trade_db.json")
        if os.path.exists(_items_trade_path):
            try:
                with open(_items_trade_path, "r", encoding="utf-8") as _f:
                    _uex_items_trade_db = _json.load(_f)
            except Exception: pass

def _verify_and_update_uex_data(status_callback=None):
    """Comprehensive verify: Wiki API + UEX API for ships, cargo grids, name linking.
    
    Returns dict with: added, updated, errors, total_api, total_local,
                       grids_added, grids_linked, warnings
    """
    import urllib.request
    global _uex_ships_db
    
    _SIZE_TO_PAD = {0: "GV", 1: "XS", 2: "S", 3: "M", 4: "L", 5: "XL"}
    result = {
        "added": [], "updated": [], "total_api": 0, "total_local": len(_uex_ships_db),
        "errors": [], "grids_added": [], "grids_linked": [], "warnings": [],
        "uex_total": 0, "wiki_total": 0,
    }
    
    def _normalize(name):
        return name.lower().replace("-", " ").replace("_", " ").strip()
    
    # 1) Fetch from Star Citizen Wiki API
    wiki_vehicles = []
    if status_callback:
        status_callback("Connecting to Star Citizen Wiki API...")
    try:
        url = "https://api.star-citizen.wiki/api/v2/vehicles?limit=500"
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        api_data = _json.loads(raw)
        wiki_vehicles = api_data.get("data", []) if isinstance(api_data, dict) else api_data
        result["wiki_total"] = len(wiki_vehicles)
    except Exception as e:
        result["warnings"].append(f"Wiki API: {e}")
    
    # 2) Fetch from UEX API
    uex_vehicles = []
    if status_callback:
        status_callback("Connecting to UEX API...")
    try:
        url2 = "https://uexcorp.space/api/2.0/vehicles"
        req2 = urllib.request.Request(url2, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
        with urllib.request.urlopen(req2, timeout=20) as resp2:
            raw2 = resp2.read().decode("utf-8")
        uex_data = _json.loads(raw2)
        uex_vehicles = uex_data.get("data", []) if isinstance(uex_data, dict) else uex_data
        result["uex_total"] = len(uex_vehicles)
    except Exception as e:
        result["warnings"].append(f"UEX API: {e}")
    
    if not wiki_vehicles and not uex_vehicles:
        result["errors"].append("Both APIs unreachable")
        return result
    
    result["total_api"] = max(result["wiki_total"], result["uex_total"])
    
    # 3) Process Wiki vehicles
    if status_callback:
        status_callback(f"Processing {len(wiki_vehicles)} Wiki + {len(uex_vehicles)} UEX vehicles...")
    
    for v in wiki_vehicles:
        name = v.get("name", "")
        if not name:
            continue
        key = _normalize(name)
        sizes = v.get("sizes", {}) or {}
        dim = v.get("dimension", {}) or {}
        sc = v.get("size_class", 0) or 0
        new_entry = {
            "name": v.get("game_name", name) or name,
            "short_name": name,
            "scu": v.get("cargo_capacity", 0) or 0,
            "length": sizes.get("length", dim.get("length", 0)) or 0,
            "width": sizes.get("beam", dim.get("width", 0)) or 0,
            "height": sizes.get("height", dim.get("height", 0)) or 0,
            "is_spaceship": 1 if v.get("is_spaceship") else 0,
            "is_ground_vehicle": 1 if v.get("is_vehicle") else 0,
            "size_class": sc,
        }
        if sc in _SIZE_TO_PAD:
            new_entry["pad_type"] = _SIZE_TO_PAD[sc]
        prod = v.get("production_status", {})
        if isinstance(prod, dict):
            new_entry["production_status"] = prod.get("en_EN", "")
        prod_str = str(new_entry.get("production_status", "")).lower()
        new_entry["is_concept"] = ("concept" in prod_str or "in development" in prod_str 
                                   or key in _CONCEPT_SHIPS)
        if key in _uex_ships_db:
            old = _uex_ships_db[key]
            changes = []
            for field in ["length", "width", "height"]:
                if (old.get(field, 0) or 0) == 0 and (new_entry.get(field, 0) or 0) > 0:
                    old[field] = new_entry[field]
                    changes.append(field)
            if not old.get("pad_type") and new_entry.get("pad_type"):
                old["pad_type"] = new_entry["pad_type"]
                changes.append("pad")
            if (old.get("scu", 0) or 0) == 0 and new_entry["scu"] > 0:
                old["scu"] = new_entry["scu"]
                changes.append("scu")
            for f in ["is_spaceship", "is_ground_vehicle", "size_class", "production_status", "is_concept"]:
                if f not in old or f == "is_concept":
                    old[f] = new_entry.get(f, 0)
            if changes:
                result["updated"].append(f"{name} ({', '.join(changes)})")
        else:
            _uex_ships_db[key] = new_entry
            result["added"].append(name)
    
    # 4) Process UEX vehicles (fill gaps)
    for v in uex_vehicles:
        name = v.get("name", "") or v.get("vehicle_name", "")
        if not name:
            continue
        key = _normalize(name)
        scu = v.get("scu", v.get("cargo", 0)) or 0
        pad = v.get("pad_type", v.get("size", "")) or ""
        
        if key in _uex_ships_db:
            old = _uex_ships_db[key]
            changes = []
            if (old.get("scu", 0) or 0) == 0 and scu > 0:
                old["scu"] = scu
                changes.append("scu")
            if not old.get("pad_type") and pad:
                old["pad_type"] = str(pad).upper()
                changes.append("pad")
            if changes and name not in str(result["updated"]):
                result["updated"].append(f"{name} (UEX: {', '.join(changes)})")
        else:
            new_entry = {
                "name": name, "short_name": name, "scu": scu,
                "is_spaceship": 1, "is_ground_vehicle": 0,
            }
            if pad:
                new_entry["pad_type"] = str(pad).upper()
            _uex_ships_db[key] = new_entry
            if name not in result["added"]:
                result["added"].append(f"{name} (UEX)")
    
    # 4b) Fetch sc-cargo.space grid layouts
    if status_callback:
        status_callback("Fetching cargo grids from sc-cargo.space...")
    
    sc_cargo_grids = {}
    sc_cargo_warnings = []
    try:
        # Fetch the SPA HTML to discover the current JS bundle hash
        html_req = urllib.request.Request("https://sc-cargo.space/", headers={
            "User-Agent": "StarlifterRequisitionTerminal/0.6",
        })
        with urllib.request.urlopen(html_req, timeout=15) as html_resp:
            html_text = html_resp.read().decode("utf-8")
        
        js_match = re.search(r'src="(/assets/index-[A-Za-z0-9_-]+\.js)"', html_text)
        if js_match:
            js_url = f"https://sc-cargo.space{js_match.group(1)}"
            if status_callback:
                status_callback("Downloading sc-cargo.space grid bundle...")
            js_req = urllib.request.Request(js_url, headers={
                "User-Agent": "StarlifterRequisitionTerminal/0.6",
            })
            with urllib.request.urlopen(js_req, timeout=30) as js_resp:
                js_content = js_resp.read().decode("utf-8", errors="replace")
            
            # Parse grid data from JS bundle: {capacity:NNN,groups:[...]}
            cap_pat = re.compile(r'\{capacity:(\d+),groups:\[')
            for m in cap_pat.finditer(js_content):
                start = m.start()
                cap = int(m.group(1))
                # Extract full object by brace counting
                brace_count = 0
                obj_end = start
                for i in range(start, min(start + 50000, len(js_content))):
                    c = js_content[i]
                    if c == '{': brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            obj_end = i + 1
                            break
                obj_str = js_content[start:obj_end]
                # Convert JS to JSON (add quotes around keys)
                json_str = re.sub(r'(\b)(x|y|z|width|height|length|capacity|groups|grids):', r'"\2":', obj_str)
                try:
                    grid_data = _json.loads(json_str)
                except _json.JSONDecodeError:
                    try:
                        json_str2 = re.sub(r'([{,])(\w+):', r'\1"\2":', obj_str)
                        grid_data = _json.loads(json_str2)
                    except Exception:
                        continue
                
                # Look back for manufacturer + ship name
                lookback = js_content[max(0, start - 500):start]
                strings = re.findall(r'"([^"]{2,50})"', lookback)
                skip_names = {"Module", "value", "default", "module", "exports",
                              "undefined", "function", "object", "string", "number", "boolean"}
                if len(strings) >= 2:
                    manufacturer, name = strings[-2], strings[-1]
                elif len(strings) == 1:
                    manufacturer, name = "Unknown", strings[-1]
                else:
                    continue
                if name in skip_names or manufacturer in skip_names:
                    alt = re.findall(r'="([A-Z][a-zA-Z0-9\- ]+)"', lookback)
                    if len(alt) >= 2:
                        manufacturer, name = alt[-2], alt[-1]
                    elif len(alt) == 1:
                        name = alt[-1]
                    else:
                        continue
                
                # Validate grid cells
                total_cells = 0
                for grp in grid_data.get("groups", []):
                    for g in grp.get("grids", []):
                        total_cells += (g.get("width", 0) or 0) * (g.get("height", 0) or 0) * (g.get("length", 0) or 0)
                if total_cells == 0:
                    continue
                
                ship_key = f"{manufacturer} {name}" if manufacturer != "Unknown" else name
                if ship_key in sc_cargo_grids:
                    if len(grid_data.get("groups", [])) <= len(sc_cargo_grids[ship_key].get("groups", [])):
                        continue
                sc_cargo_grids[ship_key] = {
                    "manufacturer": manufacturer,
                    "name": name,
                    "capacity": cap,
                    "groups": grid_data["groups"],
                    "_source": "sc-cargo.space",
                }
        else:
            sc_cargo_warnings.append("Could not find JS bundle URL in sc-cargo.space HTML")
    except Exception as e:
        sc_cargo_warnings.append(f"sc-cargo.space: {e}")
    
    result["sc_cargo_ships"] = len(sc_cargo_grids)
    if sc_cargo_warnings:
        result["warnings"].extend(sc_cargo_warnings)
    
    # 5) Cross-validate cargo grids (merge sc-cargo.space data first)
    if status_callback:
        status_callback("Cross-validating cargo grids...")
    
    grids_db = {}
    grids_path = os.path.join(_res_dir, "ship_grids_db.json")
    try:
        if os.path.exists(grids_path):
            with open(grids_path, "r", encoding="utf-8") as gf:
                grids_db = _json.load(gf)
    except Exception:
        pass
    
    grids_keys_norm = {_normalize(k): k for k in grids_db}
    grids_modified = False
    
    # Merge sc-cargo.space grids into DB (priority over auto-generated stubs)
    sc_grids_merged = 0
    for sc_key, sc_val in sc_cargo_grids.items():
        sc_norm = _normalize(sc_key)
        sc_name_norm = _normalize(sc_val.get("name", ""))
        
        # Find existing entry by normalized key
        existing_key = grids_keys_norm.get(sc_norm) or grids_keys_norm.get(sc_name_norm)
        if not existing_key:
            # Try substring match
            for gk_norm, gk_orig in grids_keys_norm.items():
                if sc_name_norm and (sc_name_norm in gk_norm or gk_norm in sc_name_norm):
                    existing_key = gk_orig
                    break
        
        if existing_key:
            old = grids_db[existing_key]
            # Only replace auto-generated stubs, never manually curated grids
            if old.get("_auto_generated"):
                grids_db[existing_key] = sc_val
                grids_modified = True
                sc_grids_merged += 1
        else:
            # New ship — add it
            grids_db[sc_key] = sc_val
            grids_keys_norm[sc_norm] = sc_key
            grids_modified = True
            sc_grids_merged += 1
    
    result["sc_grids_merged"] = sc_grids_merged
    
    for key, ship in _uex_ships_db.items():
        scu = ship.get("scu", 0) or 0
        if scu <= 0:
            continue
        if ship.get("is_ground_vehicle", 0):
            continue
        
        ship_name = ship.get("name", ship.get("short_name", key))
        
        # Try to find in grids — check exact, normalized, and substring matches
        grid_match = None
        ship_norm = _normalize(ship_name)
        key_norm = _normalize(key)
        # Words for word-overlap matching (filter short words)
        ship_words = set(w for w in ship_norm.split() if len(w) > 1)
        key_words = set(w for w in key_norm.split() if len(w) > 1)
        best_word_match = None
        best_word_score = 0
        
        for gk_norm, gk_orig in grids_keys_norm.items():
            # Exact match on normalized names
            if key_norm == gk_norm or ship_norm == gk_norm:
                grid_match = gk_orig
                break
            # Substring match: "idris m" in "aegis idris m"
            if ship_norm in gk_norm or gk_norm.endswith(ship_norm):
                grid_match = gk_orig
                break
            # Reverse: grid key in ship name (e.g., "caterpillar" in "caterpillar pirate")
            if gk_norm in ship_norm:
                grid_match = gk_orig
                break
            # Word overlap: check if core grid words appear in ship name
            # e.g., "cutlass black" words in "cutlass black pyam exec"
            gk_words = set(w for w in gk_norm.split() if len(w) > 1)
            # Skip if grid key has fewer than 2 significant words
            if len(gk_words) < 2:
                continue
            overlap = gk_words & (ship_words | key_words)
            # ALL grid key words must appear in the ship name
            if overlap == gk_words and len(overlap) >= 2:
                if len(overlap) > best_word_score:
                    best_word_score = len(overlap)
                    best_word_match = gk_orig
        
        if not grid_match and best_word_match:
            grid_match = best_word_match
        
        if not grid_match and scu >= 1 and scu <= 2000:
            # Auto-create stub grid
            w = max(1, int(scu ** 0.5))
            l = max(1, int(scu / w))
            auto_grid = {
                "manufacturer": ship.get("manufacturer", "Unknown"),
                "name": ship_name,
                "capacity": scu,
                "groups": [{"x": 0, "z": 0, "grids": [{"x": 0, "y": 0, "z": 0, "width": w, "height": 1, "length": l}]}],
                "_auto_generated": True
            }
            grids_db[ship_name] = auto_grid
            grids_keys_norm[_normalize(ship_name)] = ship_name
            result["grids_added"].append(f"{ship_name} ({scu} SCU)")
            grids_modified = True
        elif grid_match:
            result["grids_linked"].append(ship_name)
    
    if grids_modified:
        try:
            with open(grids_path, "w", encoding="utf-8") as gf:
                _json.dump(grids_db, gf, indent=2, ensure_ascii=False)
        except Exception as e:
            result["warnings"].append(f"Grid save: {e}")
    
    # 5b) Sync item volumes from SC Wiki API
    if status_callback:
        status_callback("Syncing item volumes from SC Wiki API...")
    
    vol_path = os.path.join(_res_dir, "item_volumes.json")
    item_volumes = {}
    try:
        if os.path.exists(vol_path):
            with open(vol_path, "r", encoding="utf-8") as vf:
                item_volumes = _json.load(vf)
    except Exception:
        pass
    
    vol_updated = 0
    vol_added = 0
    items_vol_warnings = []
    
    # Paginate through Wiki items API (page=1..N, 50 per page)
    page = 1
    max_pages = 30  # safety cap (~1500 items)
    wiki_items_total = 0
    
    while page <= max_pages:
        try:
            items_url = f"https://api.star-citizen.wiki/api/v2/items?page={page}&limit=50"
            req_items = urllib.request.Request(items_url, headers={
                "User-Agent": "StarlifterRequisitionTerminal/0.6",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req_items, timeout=25) as resp_items:
                raw_items = resp_items.read().decode("utf-8")
            items_data = _json.loads(raw_items)
            items_list = items_data.get("data", [])
            if not items_list:
                break
            
            for itm in items_list:
                wiki_items_total += 1
                iname = itm.get("name", "")
                if not iname:
                    continue
                
                dim = itm.get("dimension", {}) or {}
                vol = dim.get("volume", 0) or 0  # SCU
                
                if vol <= 0:
                    continue
                
                key = iname.lower().strip()
                old_vol = item_volumes.get(key, 0) or 0
                
                if key not in item_volumes:
                    item_volumes[key] = vol
                    vol_added += 1
                elif abs(vol - old_vol) > 0.0001 and vol > 0:
                    item_volumes[key] = vol
                    vol_updated += 1
            
            # Check if there are more pages
            meta = items_data.get("meta", {})
            last_page = meta.get("last_page", page)
            if page >= last_page:
                break
            page += 1
            
        except Exception as e:
            items_vol_warnings.append(f"Wiki items page {page}: {e}")
            break
    
    if vol_added > 0 or vol_updated > 0:
        try:
            with open(vol_path, "w", encoding="utf-8") as vf:
                _json.dump(item_volumes, vf, indent=2, ensure_ascii=False)
        except Exception as e:
            items_vol_warnings.append(f"Volume save: {e}")
    
    result["vol_added"] = vol_added
    result["vol_updated"] = vol_updated
    result["wiki_items_total"] = wiki_items_total
    if items_vol_warnings:
        result["warnings"].extend(items_vol_warnings)
    
    # 6) Save updated ship DB
    if result["added"] or result["updated"]:
        db_path = os.path.join(_res_dir, "uex_ships_db.json")
        try:
            with open(db_path, "w", encoding="utf-8") as f:
                _json.dump(_uex_ships_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            result["warnings"].append(f"Ship DB save: {e}")
    
    # 7) Ship names for autocomplete
    result["all_ship_names"] = sorted(set(
        v.get("name", v.get("short_name", k)) for k, v in _uex_ships_db.items()
        if v.get("is_spaceship", 1) and v.get("scu", 0) > 0
    ))
    
    if status_callback:
        status_callback(f"Done! Wiki:{result['wiki_total']} UEX:{result['uex_total']} "
                       f"+{len(result['added'])} ~{len(result['updated'])} "
                       f"grids:{result.get('sc_cargo_ships', 0)}sc/{len(result['grids_added'])}auto "
                       f"items:+{vol_added} ~{vol_updated}")
    
    return result


# ── UEX Category → cargo_type + packing_cat mapping ──────────────
# cargo_type: "loose" = goes into Stor-All, "grid" = placed on cargo grid (SCU), "skip" = digital/irrelevant
# packing_cat: for Stor-All boxing categorization
_UEX_CATEGORY_MAP = {
    # Weapons & attachments
    17: ("loose", "combat"),      # weapon attachments (scopes, barrels, magazines)
    18: ("loose", "combat"),      # personal weapons (pistols, rifles, SMGs)
    # Armor & clothing
    1:  ("loose", "armor"),       # arms armor
    2:  ("loose", "armor"),       # backpacks
    3:  ("loose", "armor"),       # helmets
    4:  ("loose", "armor"),       # legs armor
    5:  ("loose", "armor"),       # core armor
    8:  ("loose", "armor"),       # shoes/boots
    9:  ("loose", "armor"),       # gloves
    10: ("loose", "armor"),       # hats
    11: ("loose", "armor"),       # jackets
    13: ("loose", "armor"),       # pants
    14: ("loose", "armor"),       # shirts
    24: ("loose", "armor"),       # undersuits
    # Medical
    16: ("loose", "medical"),     # medpens, oxypens
    # Food & drink
    62: ("loose", "supply"),      # drinks
    63: ("loose", "supply"),      # food
    # Consumables / misc
    61: ("loose", "supply"),      # artifacts, collectibles
    73: ("loose", "supply"),      # mobiGlas casings
    75: ("loose", "supply"),      # furniture / hangar items
    107:("loose", "supply"),      # action figures
    109:("loose", "supply"),      # item fabricators
    # Ship components (grid-based)
    19: ("grid", "component"),    # coolers
    21: ("grid", "component"),    # power plants
    22: ("grid", "component"),    # quantum drives
    23: ("grid", "component"),    # shields
    25: ("grid", "component"),    # em module (?)
    26: ("grid", "component"),    # fuel scoops / intakes
    28: ("grid", "component"),    # scanners
    29: ("grid", "component"),    # mining lasers
    30: ("grid", "component"),    # utility modules
    31: ("grid", "component"),    # scraper/tractor modules
    67: ("grid", "component"),    # tractor beams S1
    110:("grid", "component"),    # tractor beams S3
    83: ("grid", "component"),    # quantum markers / nav beacons
    86: ("grid", "component"),    # jump modules
    # Ordnance (ship weapons)
    32: ("grid", "ordnance"),     # ship guns/cannons
    33: ("grid", "ordnance"),     # missile racks
    34: ("grid", "ordnance"),     # missiles
    35: ("grid", "ordnance"),     # turrets
    70: ("grid", "ordnance"),     # bombs
    90: ("grid", "ordnance"),     # bomb racks
    # Cargo containers
    64: ("grid", "supply"),       # Stor-All containers (1-32 SCU)
    65: ("grid", "supply"),       # ore pods, resource pods
    # Ship modules
    74: ("grid", "component"),    # ship modules (Retaliator cargo/torpedo)
    # Digital / skip
    20: ("skip", ""),             # liveries/paints
    82: ("skip", ""),             # flight blades (digital)
}


def _sync_commodity_trade_routes(status_callback=None):
    """Sync commodities_prices_all → uex_trade_db.json.
    
    Groups per commodity name → list of locations with buy/sell data.
    Returns result dict with stats.
    """
    from collections import defaultdict
    
    result = {"total": 0, "commodities": 0, "locations": 0, "errors": []}
    
    if status_callback:
        status_callback("Fetching commodity prices from UEX...")
    
    try:
        url = "https://uexcorp.space/api/2.0/commodities_prices_all"
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
        api_data = _json.loads(raw)
        records = api_data.get("data", [])
        result["total"] = len(records)
    except Exception as e:
        result["errors"].append(f"API fetch: {e}")
        return result
    
    if not records:
        result["errors"].append("No data returned")
        return result
    
    # Group per commodity
    commodity_map = defaultdict(list)
    for r in records:
        cname = r.get("commodity_name", "")
        tname = r.get("terminal_name", "")
        if not cname or not tname:
            continue
        commodity_map[cname.lower().strip()].append({
            "terminal": tname,
            "buy": r.get("price_buy", 0) or 0,
            "buy_avg": r.get("price_buy_avg", 0) or 0,
            "sell": r.get("price_sell", 0) or 0,
            "sell_avg": r.get("price_sell_avg", 0) or 0,
            "stock_buy": r.get("scu_buy", 0) or 0,
            "stock_sell": r.get("scu_sell_stock", 0) or 0,
        })
    
    result["commodities"] = len(commodity_map)
    result["locations"] = sum(len(v) for v in commodity_map.values())
    
    # Save
    trade_db_path = os.path.join(_res_dir, "uex_trade_db.json")
    try:
        with open(trade_db_path, "w", encoding="utf-8") as f:
            _json.dump(dict(commodity_map), f, indent=2, ensure_ascii=False)
    except Exception as e:
        result["errors"].append(f"Save: {e}")
    
    # Update lazy-loaded cache
    global _uex_trade_db
    _uex_trade_db = dict(commodity_map)
    
    if status_callback:
        status_callback(f"Trade routes: {result['commodities']} commodities, "
                       f"{result['locations']} price points")
    
    return result


def _sync_items_prices(status_callback=None):
    """Sync items_prices_all → uex_items_trade_db.json.
    
    Classifies items by cargo_type (loose/grid/skip) and packing_cat.
    Groups per item name → locations with prices.
    Returns result dict with stats.
    """
    from collections import defaultdict
    
    result = {
        "total": 0, "items": 0, "skipped": 0,
        "by_cargo_type": {"loose": 0, "grid": 0, "skip": 0},
        "by_packing_cat": {},
        "errors": [],
    }
    
    if status_callback:
        status_callback("Fetching item prices from UEX (6 MB)...")
    
    try:
        url = "https://uexcorp.space/api/2.0/items_prices_all"
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
        api_data = _json.loads(raw)
        records = api_data.get("data", [])
        result["total"] = len(records)
    except Exception as e:
        result["errors"].append(f"API fetch: {e}")
        return result
    
    if not records:
        result["errors"].append("No data returned")
        return result
    
    # Group per item with classification
    items_map = defaultdict(lambda: {"locations": [], "cargo_type": "loose", "packing_cat": "supply"})
    seen_items = {}  # name → first record for classification
    
    for r in records:
        iname = r.get("item_name", "")
        tname = r.get("terminal_name", "")
        cat_id = r.get("id_category", 0) or 0
        
        if not iname:
            continue
        
        key = iname.lower().strip()
        
        # Classify on first encounter
        if key not in seen_items:
            cargo_type, packing_cat = _UEX_CATEGORY_MAP.get(cat_id, ("loose", "supply"))
            seen_items[key] = (cargo_type, packing_cat)
            items_map[key]["cargo_type"] = cargo_type
            items_map[key]["packing_cat"] = packing_cat
            items_map[key]["name"] = iname  # preserve original casing
            items_map[key]["id_category"] = cat_id
        
        cargo_type = seen_items[key][0]
        if cargo_type == "skip":
            result["skipped"] += 1
            continue
        
        if tname:
            items_map[key]["locations"].append({
                "terminal": tname,
                "buy": r.get("price_buy", 0) or 0,
                "sell": r.get("price_sell", 0) or 0,
            })
    
    # Remove skipped items
    final_map = {k: v for k, v in items_map.items() if seen_items.get(k, ("skip",))[0] != "skip"}
    
    # Stats
    result["items"] = len(final_map)
    for item_data in final_map.values():
        ct = item_data.get("cargo_type", "loose")
        pc = item_data.get("packing_cat", "supply")
        result["by_cargo_type"][ct] = result["by_cargo_type"].get(ct, 0) + 1
        result["by_packing_cat"][pc] = result["by_packing_cat"].get(pc, 0) + 1
    
    # Save
    items_db_path = os.path.join(_res_dir, "uex_items_trade_db.json")
    try:
        with open(items_db_path, "w", encoding="utf-8") as f:
            _json.dump(final_map, f, indent=2, ensure_ascii=False)
    except Exception as e:
        result["errors"].append(f"Save: {e}")
    
    # Update lazy-loaded cache
    global _uex_items_trade_db
    _uex_items_trade_db = final_map
    
    if status_callback:
        status_callback(f"Items: {result['items']} classified ({result['skipped']} digital skipped)")
    
    return result


def _update_config_prices_from_uex(status_callback=None):
    """Update config.json frequent_items prices from uex_items_trade_db.
    
    For each config item, find matching UEX item and update price
    with the average buy price across all terminals.
    Returns result dict with stats.
    """
    result = {"matched": 0, "updated": 0, "not_found": [], "errors": []}
    
    # Ensure items DB is loaded
    _ensure_trade_dbs()
    if not _uex_items_trade_db:
        result["errors"].append("No items trade DB available")
        return result
    
    # Load config
    config_path = PATHS.config
    if not os.path.exists(config_path):
        result["errors"].append("config.json not found")
        return result
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = _json.load(f)
    except Exception as e:
        result["errors"].append(f"Config load: {e}")
        return result
    
    items = config.get("frequent_items", [])
    if not items:
        return result
    
    # Build lookup from UEX items
    uex_lookup = {}
    for key, data in _uex_items_trade_db.items():
        uex_lookup[key] = data
        # Also index by display name
        if "name" in data:
            uex_lookup[data["name"].lower().strip()] = data
    
    for item in items:
        iname = item.get("name", "").lower().strip()
        if not iname:
            continue
        
        # Try direct match, then fuzzy
        match = uex_lookup.get(iname)
        if not match:
            for ukey in uex_lookup:
                if iname in ukey or ukey in iname:
                    match = uex_lookup[ukey]
                    break
        
        if match:
            result["matched"] += 1
            locs = match.get("locations", [])
            buy_prices = [l["buy"] for l in locs if l.get("buy", 0) > 0]
            if buy_prices:
                avg_price = sum(buy_prices) / len(buy_prices)
                old_price = item.get("price", 0)
                if abs(avg_price - old_price) > 0.5:
                    item["price"] = round(avg_price)
                    item["_uex_updated"] = True
                    result["updated"] += 1
        else:
            result["not_found"].append(iname)
    
    # Save config if anything changed
    if result["updated"] > 0:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                _json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            result["errors"].append(f"Config save: {e}")
    
    if status_callback:
        status_callback(f"Config prices: {result['matched']} matched, {result['updated']} updated")
    
    return result


# ── Public aliases (without underscore) ──
ensure_trade_dbs = _ensure_trade_dbs
verify_and_update_uex_data = _verify_and_update_uex_data
sync_commodity_trade_routes = _sync_commodity_trade_routes
sync_items_prices = _sync_items_prices
update_config_prices_from_uex = _update_config_prices_from_uex
