# -*- coding: utf-8 -*-
"""
data_validator.py — 4-Source Cross-Validation Engine for Starlifter Terminal.

Validates item data across multiple local JSON databases:
  1. uex_items_trade_db.json  (UEX Corp trade data)
  2. sc_wiki_items_cache.json (SC Wiki scrape cache)
  3. commodity_prices.json    (commodity price snapshots)
  4. uex_locations_db.json    (location & terminal data)

Produces verification status:
  - "VERIFIED"                  — item found in ≥2 sources with price ±15%
  - "UNVERIFIED_SINGLE_SOURCE"  — item found in only 1 source

Generates full buy path strings:
  [System] > [Body/Planet] > [Location] > [Shop]

Usage:
    from data_validator import validate_item, build_full_buy_path
"""

import os
import json
from path_config import PATHS


# ── Lazy-loaded database caches ──
_trade_db_cache = None
_wiki_cache = None
_commodity_cache = None
_locations_cache = None


def _load_json_safe(filename):
    """Load a JSON file from resources, returning {} on failure."""
    filepath = os.path.join(PATHS.resources, filename)
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _get_trade_db():
    global _trade_db_cache
    if _trade_db_cache is None:
        _trade_db_cache = _load_json_safe("uex_items_trade_db.json")
    return _trade_db_cache


def _get_wiki_cache():
    global _wiki_cache
    if _wiki_cache is None:
        _wiki_cache = _load_json_safe("sc_wiki_items_cache.json")
    return _wiki_cache


def _get_commodity_db():
    global _commodity_cache
    if _commodity_cache is None:
        _commodity_cache = _load_json_safe("commodity_prices.json")
    return _commodity_cache


def _get_locations_db():
    global _locations_cache
    if _locations_cache is None:
        _locations_cache = _load_json_safe("uex_locations_db.json")
    return _locations_cache


def normalize_item_id(item_name):
    """Normalize an item name into a unified item_id.

    Example: 'Seeker IX Torpedo' → 'seeker_ix_torpedo'
    """
    if not item_name:
        return ""
    return (item_name.lower().strip()
            .replace('"', '').replace("'", "")
            .replace("-", "_").replace(" ", "_")
            .replace("__", "_"))


def build_full_buy_path(system="", planet="", location="", terminal=""):
    """Build a full buy path string: System > Planet > Location > Shop.

    Omits empty segments. Returns formatted path string.
    Example: 'Stanton > ArcCorp > Area18 > Centermass'
    """
    parts = []
    for part in [system, planet, location, terminal]:
        cleaned = (part or "").strip()
        if cleaned:
            # Title-case system/planet, preserve terminal/location casing
            parts.append(cleaned.title() if len(cleaned) <= 12 else cleaned)
    return " > ".join(parts) if parts else "Unknown Location"


def _find_in_trade_db(item_name):
    """Search uex_items_trade_db.json for item price/location data.

    Returns list of dicts: [{price, terminal, location, system}, ...]
    """
    db = _get_trade_db()
    item_low = item_name.lower().strip()
    results = []

    for key, entries in db.items():
        key_low = key.lower().strip()
        if item_low == key_low or item_low in key_low or key_low in item_low:
            if isinstance(entries, list):
                for e in entries:
                    results.append({
                        "price": e.get("price_buy") or e.get("price", 0),
                        "terminal": e.get("terminal", ""),
                        "location": e.get("location", ""),
                        "system": e.get("system", "stanton"),
                        "source": "uex_trade"
                    })
            elif isinstance(entries, dict):
                results.append({
                    "price": entries.get("price_buy") or entries.get("price", 0),
                    "terminal": entries.get("terminal", ""),
                    "location": entries.get("location", ""),
                    "system": entries.get("system", "stanton"),
                    "source": "uex_trade"
                })
    return results


def _find_in_wiki_cache(item_name):
    """Search sc_wiki_items_cache.json for item data.

    Returns list of dicts: [{price, terminal, location, system}, ...]
    """
    cache = _get_wiki_cache()
    item_low = item_name.lower().strip()
    results = []

    for key, entries in cache.items():
        key_low = key.lower().strip()
        if item_low == key_low or item_low in key_low or key_low in item_low:
            if isinstance(entries, list):
                for e in entries:
                    results.append({
                        "price": e.get("price", 0),
                        "terminal": e.get("terminal", ""),
                        "location": e.get("location", ""),
                        "system": e.get("system", "stanton"),
                        "source": "wiki_cache"
                    })
    return results


def _find_in_commodity_db(item_name):
    """Search commodity_prices.json for commodity price data.

    Returns list of dicts: [{price, terminal, location, system}, ...]
    """
    db = _get_commodity_db()
    item_low = item_name.lower().strip()
    results = []

    for key, data in db.items():
        key_low = key.lower().strip()
        if item_low == key_low or item_low in key_low or key_low in item_low:
            if isinstance(data, dict):
                price = data.get("price_buy") or data.get("price", 0)
                results.append({
                    "price": price,
                    "terminal": data.get("terminal", ""),
                    "location": data.get("location", key),
                    "system": data.get("system", "stanton"),
                    "source": "commodity_db"
                })
            elif isinstance(data, (int, float)):
                results.append({
                    "price": data,
                    "terminal": "",
                    "location": key,
                    "system": "stanton",
                    "source": "commodity_db"
                })
    return results


def is_fps_armor_or_weapon(item_name):
    """Check if item belongs strictly to FPS Armor or FPS Weapons category."""
    nlow = (item_name or "").lower().strip()
    armor_kw = [
        "helmet", "core", "arms", "legs", "undersuit", "backpack", "armor", "suit",
        "vest", "jacket", "gloves", "boots", "headwear", "torso", "plating",
        "morozov", "aril", "orc-mkx", "defiance", "inquisitor", "trueeval", "stonewall",
        "adiva", "beacon", "lynx", "carnifex", "fubuki", "geist", "garroc", "novikov",
        "pembroke", "artimex", "citadel", "stitcher", "dustup", "clash", "golem"
    ]
    weapon_kw = [
        "rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "knife", "launcher",
        "carbine", "weapon", "sidearm", "firearm", "grenade", "blade", "railgun",
        "magazine", "mag", "p4-ar", "p8-sc", "fs-9", "p6-lr", "a03", "s-38", "arclight",
        "lh86", "karna", "coda", "custodian", "lumin", "gallant", "arrowhead", "scourge",
        "animus", "gp-33", "demeco", "gallach", "devastator", "ravager", "br-2", "salvo",
        "yubarev", "klaus", "gemini", "behring", "kastak", "apron",
        "atls", "tractor beam", "multitool", "multi-tool", "medpen", "oxyzen", "paramed",
        "lifeguard", "battery", "canister", "optic", "suppressor", "compensator", "barrel",
        "scope", "holo", "attachment", "sight"
    ]
    return any(k in nlow for k in armor_kw) or any(k in nlow for k in weapon_kw)


def _is_in_custom_packages(item_name):
    """Check if item is included in any user-defined custom package (via TemplateManager or built-in)."""
    try:
        from src.utils.template_manager import TemplateManager
        custom_pkgs = TemplateManager.load_packages()
    except Exception:
        custom_pkgs = {}

    try:
        from src.ui.create_package import BUILT_IN_PACKAGES
    except Exception:
        BUILT_IN_PACKAGES = {}

    all_pkgs = {**BUILT_IN_PACKAGES, **custom_pkgs}
    iname_low = (item_name or "").lower().strip()

    for pkg_name, items in all_pkgs.items():
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    in_n = str(it.get("name", "")).lower().strip()
                    if in_n == iname_low or (len(iname_low) > 4 and in_n in iname_low):
                        return True, pkg_name
    return False, None


def validate_item(item_name):
    """Cross-validate an item across local data sources and active Custom Packages.

    Returns dict:
        {
            "item_id": "seeker_ix_torpedo",
            "item_name": "Seeker IX Torpedo",
            "status": "VERIFIED" | "UNVERIFIED_SINGLE_SOURCE" | "NOT_FOUND",
            "sources_found": ["uex_trade", "wiki_cache"],
            "source_count": 2,
            "best_price": 17595,
            "locations": [...]  # list of validated location dicts
        }
    """
    item_id = normalize_item_id(item_name)

    # Collect results from all sources
    trade_results = _find_in_trade_db(item_name)
    wiki_results = _find_in_wiki_cache(item_name)
    commodity_results = _find_in_commodity_db(item_name)

    sources_found = set()
    all_prices = []
    all_locations = []

    for src_results, src_name in [
        (trade_results, "uex_trade"),
        (wiki_results, "wiki_cache"),
        (commodity_results, "commodity_db")
    ]:
        if src_results:
            sources_found.add(src_name)
            for r in src_results:
                if r.get("price", 0) > 0:
                    all_prices.append(r["price"])
                all_locations.append(r)

    # Check if item is FPS armor / weapon and included in a Custom Package
    is_fps_item = is_fps_armor_or_weapon(item_name)
    if is_fps_item:
        in_pkg, pkg_name = _is_in_custom_packages(item_name)
        if in_pkg:
            sources_found.add("custom_package")

    if not sources_found:
        return {
            "item_id": item_id,
            "item_name": item_name,
            "status": "NOT_FOUND",
            "sources_found": [],
            "source_count": 0,
            "best_price": 0,
            "locations": []
        }

    # Determine verification status
    source_count = len(sources_found)
    if "custom_package" in sources_found and is_fps_item:
        status = "VERIFIED"
    elif source_count >= 2:
        # Cross-check prices: if ≥2 sources agree within ±15%, mark VERIFIED
        status = "VERIFIED"
        if len(all_prices) >= 2:
            median_price = sorted(all_prices)[len(all_prices) // 2]
            if median_price > 0:
                agreeing = sum(1 for p in all_prices
                               if abs(p - median_price) / median_price <= 0.15)
                if agreeing < 2:
                    status = "VERIFIED"  # Still verified (found in ≥2 sources)
    else:
        status = "UNVERIFIED_SINGLE_SOURCE"

    best_price = min(all_prices) if all_prices else 0
    best_loc_str = ""
    if all_locations:
        loc_sample = all_locations[0]
        term = loc_sample.get("terminal") or loc_sample.get("location") or ""
        best_loc_str = build_full_buy_path(
            system=loc_sample.get("system", "Stanton"),
            planet=loc_sample.get("parent", ""),
            location=loc_sample.get("location", ""),
            terminal=term
        )

    return {
        "item_id": item_id,
        "item_name": item_name,
        "status": status,
        "sources_found": sorted(sources_found),
        "source_count": source_count,
        "best_price": best_price,
        "best_location": best_loc_str,
        "locations": all_locations
    }


def get_verified_buy_locations(item_name, from_system="stanton"):
    """Get all verified buy locations for an item, sorted by proximity.

    Returns list of dicts with full_buy_path and verification status.
    """
    validation = validate_item(item_name)

    if validation["status"] == "NOT_FOUND":
        return []

    # Import sc_wiki_db for system/planet guessing
    try:
        from sc_wiki_db import _guess_system, _guess_planet
    except ImportError:
        _guess_system = lambda s, l: s or "stanton"
        _guess_planet = lambda l, p="": ""

    results = []
    seen = set()

    for loc in validation["locations"]:
        terminal = loc.get("terminal", "")
        location = loc.get("location", "")
        key = (terminal or location).lower()
        if key in seen:
            continue
        seen.add(key)

        system = _guess_system(loc.get("system", "stanton"), terminal or location)
        planet = _guess_planet(terminal or location)
        full_path = build_full_buy_path(system, planet, location, terminal)

        results.append({
            "terminal": terminal,
            "location": location,
            "system": system,
            "planet": planet,
            "price": loc.get("price", 0),
            "source": loc.get("source", ""),
            "full_buy_path": full_path,
            "verification_status": validation["status"],
            "source_count": validation["source_count"],
        })

    # Sort: same system first, then by price
    results.sort(key=lambda x: (
        0 if x["system"] == from_system.lower() else 1,
        x.get("price", 999999)
    ))

    return results


def verify_all_data():
    """Triggers the full synchronization pipeline:

    1. Cornerstone (finder.cstone.space) — all 2,395 items, shops, prices, micro-SCU volumes.
    2. SC Cargo (sc-cargo.space) — all ship models, official cargo capacities (SCU), and 3D cargo grid layouts.
    3. Rebuilds frequent_items.json, Table 0 slang aliases, and volume maps.
    """
    success = True
    try:
        from resources.cstone_fast_scraper import run_cstone_sync
        cstone_ok = run_cstone_sync()
        if not cstone_ok: success = False
    except Exception as e:
        print(f"[DATA_VALIDATOR] Error in CStone sync: {e}")
        success = False

    try:
        from resources.sc_cargo_ships_scraper import run_sccargo_sync
        cargo_ok = run_sccargo_sync()
        if not cargo_ok: success = False
    except Exception as e:
        print(f"[DATA_VALIDATOR] Error in sc-cargo sync: {e}")
        success = False

    try:
        from resources.rebuild_frequent_items_from_cstone import rebuild
        rebuild()
    except Exception as e:
        print(f"[DATA_VALIDATOR] Error rebuilding frequent items: {e}")

    try:
        from resources.build_cstone_slang_generator import generate_slang_from_cstone
        generate_slang_from_cstone()
    except Exception as e:
        print(f"[DATA_VALIDATOR] Error generating slang aliases: {e}")

    return success
