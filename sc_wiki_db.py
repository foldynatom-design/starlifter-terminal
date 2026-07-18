"""
SC Wiki Items Location Database — local cache reader for supply route PDFs.
Reads sc_wiki_items_cache.json and provides lookup functions.

This module is imported by pdf_engine.py and pdf_block_extract.py to resolve
item names to buy locations with prices, terminals, and system/planet data.
"""
import json, os

_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "resources", "sc_wiki_items_cache.json")
_CACHE = None  # Lazy-loaded

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

# ── Location → planet mapping (known stations/cities) ──
_LOC_PLANET_MAP = {
    # Stanton
    "area18": "arccorp", "area 18": "arccorp", "arccorp": "arccorp",
    "baijini point": "arccorp", "arc-l1": "arccorp",
    "lorville": "hurston", "hurston": "hurston",
    "everus harbor": "hurston", "hur-l1": "hurston", "hur-l2": "hurston",
    "hur-l3": "hurston", "hur-l4": "hurston", "hur-l5": "hurston",
    "new babbage": "microtech", "microtech": "microtech",
    "port tressler": "microtech", "mic-l1": "microtech", "mic-l2": "microtech",
    "mic-l3": "microtech", "mic-l4": "microtech",
    "orison": "crusader", "crusader": "crusader",
    "seraphim": "crusader", "seraphim station": "crusader",
    "port olisar": "crusader", "cru-l1": "crusader", "cru-l4": "crusader",
    "cru-l5": "crusader",
    # Pyro
    "ruin station": "pyro", "pyro": "pyro",
    "checkmate station": "pyro", "stanton gateway": "pyro",
    # Nyx
    "levski": "nyx", "delamar": "nyx", "nyx": "nyx",
    "pyro gateway": "nyx",
}

# ── L-point → System mapping ──
_LOC_SYSTEM_MAP = {
    "stanton": "stanton", "pyro": "pyro", "nyx": "nyx",
}


def _load_cache():
    """Lazy-load the cached SC Wiki items data."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
        except Exception:
            _CACHE = {}
    else:
        _CACHE = {}
    return _CACHE


def _guess_planet(location_name, parent_name=""):
    """Guess the planet from a location name or parent name."""
    for key in [location_name.lower(), parent_name.lower()]:
        if key in _LOC_PLANET_MAP:
            return _LOC_PLANET_MAP[key]
        for prefix, planet in _LOC_PLANET_MAP.items():
            if prefix in key:
                return planet
    return ""


def _guess_system(system_name, location_name=""):
    """Determine star system from explicit system name or location."""
    sys_low = system_name.lower().strip() if system_name else ""
    if sys_low in _LOC_SYSTEM_MAP:
        return sys_low
    loc_low = location_name.lower()
    if any(k in loc_low for k in ["pyro", "ruin", "checkmate"]):
        return "pyro"
    if any(k in loc_low for k in ["nyx", "levski", "delamar"]):
        return "nyx"
    return "stanton"


def estimate_qt_minutes(from_location, to_location,
                        from_system="stanton", to_system="stanton"):
    """Estimate QT travel time between two locations in minutes."""
    fs = from_system.lower().strip()
    ts = to_system.lower().strip()

    # Cross-system
    if fs != ts:
        pair = tuple(sorted([fs, ts]))
        return SYSTEM_DISTANCES.get(pair, 90)

    # Same system — compare planets
    fp = _guess_planet(from_location)
    tp = _guess_planet(to_location)

    if not fp or not tp:
        return 10  # Unknown planet, assume ~10 min
    if fp == tp:
        return 2  # Same planet/orbital
    pair = tuple(sorted([fp, tp]))
    return STANTON_PLANET_DISTANCES.get(pair, 12)


def lookup_item(item_name, from_location="", from_system="stanton"):
    """
    Look up buy locations for an item from the SC Wiki cache.

    Returns list of dicts sorted by estimated QT distance:
    [{"terminal", "price", "location", "parent", "system", "qt_min", "display"}, ...]
    """
    cache = _load_cache()
    item_low = item_name.lower().strip()

    # Try exact match first, then substring
    matches = []
    for key, entries in cache.items():
        key_low = key.lower()
        if item_low == key_low:
            matches = entries
            break
        if item_low in key_low or key_low in item_low:
            if not matches or len(entries) > len(matches):
                matches = entries

    if not matches:
        # Try partial word match
        item_words = [w for w in item_low.split() if len(w) > 2]
        for key, entries in cache.items():
            key_low = key.lower()
            if any(w in key_low for w in item_words):
                if not matches or len(entries) > len(matches):
                    matches = entries

    if not matches:
        return []

    results = []
    for entry in matches:
        loc_name = entry.get("location", "")
        parent = entry.get("parent", "")
        system = _guess_system(entry.get("system", "stanton"), loc_name)
        qt = estimate_qt_minutes(from_location, loc_name or parent,
                                 from_system, system)

        # Build display string — avoid redundant "System > System"
        terminal = entry.get('terminal', loc_name)
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
        })

    # Sort by distance, then price
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


def get_cache_stats():
    """Return stats about the cached data."""
    cache = _load_cache()
    total_items = len(cache)
    total_locations = sum(len(v) for v in cache.values())
    return {"items": total_items, "locations": total_locations}
