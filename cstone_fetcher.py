# -*- coding: utf-8 -*-
"""
CStone + SC Wiki location fetcher for frequent_items.json.

Fetches real buy locations for items that are missing location data.
Priority: 1) SC Wiki API  2) CStone HTML scrape  3) Skip

Usage:
    python cstone_fetcher.py                # Fetch locations for all items missing data
    python cstone_fetcher.py "Aril Core"    # Fetch single item
    python cstone_fetcher.py --dry-run      # Show what would be fetched
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
import re
import html

RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
FREQ_PATH = os.path.join(RESOURCES_DIR, "frequent_items.json")

# SC Wiki API
WIKI_API_BASE = "https://api.star-citizen.wiki/api/v2/items"

# SSL context for HTTPS
_SSL_CTX = ssl._create_unverified_context()

# Rate limiting
REQUEST_DELAY = 0.4  # seconds between requests

# ── Location hierarchy normalization ──
SYSTEM_MAP = {
    "stanton": "Stanton",
    "pyro": "Pyro",
    "nyx": "Nyx",
}

PLANET_MAP = {
    "hurston": "Hurston", "arccorp": "ArcCorp", "arcorp": "ArcCorp",
    "crusader": "Crusader", "microtech": "microTech", "microtech": "microTech",
    "monox": "Monox", "bloom": "Bloom", "terminus": "Terminus",
    "pyro iv": "Pyro IV", "pyro v": "Pyro V",
    "delamar": "Delamar",
}

CITY_MAP = {
    "lorville": "Lorville", "area 18": "Area 18", "area18": "Area 18",
    "new babbage": "New Babbage", "orison": "Orison",
    "levski": "Levski",
}


def _normalize_system(raw):
    """Normalize system name."""
    raw_low = (raw or "").lower().strip()
    return SYSTEM_MAP.get(raw_low, raw.strip().title() if raw else "Stanton")


def _normalize_planet(raw):
    """Normalize planet name."""
    raw_low = (raw or "").lower().strip()
    return PLANET_MAP.get(raw_low, raw.strip() if raw else "")


def _http_get_json(url, timeout=15):
    """HTTP GET returning parsed JSON."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 StarlifterTerminal/0.7"
    })
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def _http_get_html(url, timeout=15):
    """HTTP GET returning raw HTML text."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 StarlifterTerminal/0.7",
        "Accept": "text/html,application/xhtml+xml"
    })
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


# ════════════════════════════════════════════════════════════
# SOURCE 1: SC Wiki API (api.star-citizen.wiki)
# ════════════════════════════════════════════════════════════

def fetch_wiki_locations(item_name):
    """
    Fetch buy locations from SC Wiki API.
    Returns list of location dicts or empty list.
    """
    params = urllib.parse.urlencode({"filter[name]": item_name})
    url = f"{WIKI_API_BASE}?{params}"
    data = _http_get_json(url)
    if not data:
        return []

    results = []
    for item in data.get("data", []):
        for p in item.get("uex_prices", {}).get("purchase", []):
            price = p.get("price_buy", 0)
            if not price or price <= 0:
                continue
            loc = p.get("starmap_location", {})
            terminal = p.get("terminal_name", "")
            system_name = loc.get("star_system_name", "Stanton")
            parent_name = loc.get("parent_name", "")
            loc_name = loc.get("name", "")

            # Build structured location
            system = _normalize_system(system_name)
            planet = _guess_planet_from_terminal(terminal, parent_name, loc_name, system)
            city = _guess_city_from_terminal(terminal, loc_name, planet)
            station = loc_name if loc_name != city else ""
            shop = terminal

            results.append({
                "system": system,
                "planet": planet,
                "city": city,
                "station": station or loc_name,
                "shop": shop,
                "buy_price": price
            })

    return results


def _guess_planet_from_terminal(terminal, parent, loc_name, system):
    """Guess planet from terminal/location names."""
    combined = f"{terminal} {parent} {loc_name}".lower()

    # Stanton planets
    if any(k in combined for k in ["hurston", "lorville", "everus", "hdms", "arial", "aberdeen", "magda", "ita"]):
        return "Hurston"
    if any(k in combined for k in ["arccorp", "arc corp", "area 18", "area18", "baijini", "wala", "lyria"]):
        return "ArcCorp"
    if any(k in combined for k in ["crusader", "orison", "seraphim", "daymar", "yela", "cellin", "providence"]):
        return "Crusader"
    if any(k in combined for k in ["microtech", "babbage", "tressler", "calliope", "clio", "euterpe"]):
        return "microTech"

    # L-points
    if "hur-l" in combined: return "Hurston"
    if "arc-l" in combined: return "ArcCorp"
    if "cru-l" in combined: return "Crusader"
    if "mic-l" in combined: return "microTech"

    # Pyro
    if any(k in combined for k in ["monox", "checkmate", "sunset mesa"]): return "Monox"
    if any(k in combined for k in ["bloom", "orbituary", "patchcity", "starlight"]): return "Bloom"
    if any(k in combined for k in ["terminus", "ruin"]): return "Terminus"

    # Nyx
    if any(k in combined for k in ["delamar", "levski"]): return "Delamar"

    return ""


def _guess_city_from_terminal(terminal, loc_name, planet):
    """Guess the city/landing zone from terminal and location info."""
    combined = f"{terminal} {loc_name}".lower()
    if "lorville" in combined or (planet == "Hurston" and any(k in combined for k in ["tammany", "hd armor", "hd-armor", "live fire", "maria pure"])):
        return "Lorville"
    if "area 18" in combined or "area18" in combined or (planet == "ArcCorp" and any(k in combined for k in ["cubby blast", "centermass", "g-loc"])):
        return "Area 18"
    if "new babbage" in combined or "babbage" in combined or (planet == "microTech" and any(k in combined for k in ["shubin", "omega pro"])):
        return "New Babbage"
    if "orison" in combined or (planet == "Crusader" and any(k in combined for k in ["providence", "garrity", "voyager", "make shift"])):
        return "Orison"
    if "levski" in combined:
        return "Levski"
    return ""


# ════════════════════════════════════════════════════════════
# SOURCE 2: CStone Finder HTML scrape (2nd Priority Fallback)
# ════════════════════════════════════════════════════════════

def fetch_cstone_locations(item_name):
    """
    Search CStone finder for item and extract buy locations via HTML scrape.
    Used as 2nd priority fallback if SC Wiki returns no data.
    """
    query = urllib.parse.quote(item_name)
    url = f"https://finder.cstone.space/Search?q={query}"
    html_text = _http_get_html(url)
    if not html_text:
        return []

    results = []
    # Match location rows in html if present
    matches = re.findall(r'class="location-name">([^<]+)<.*?class="price">([0-9,]+)', html_text, re.DOTALL)
    for loc_raw, price_raw in matches:
        loc_str = html.unescape(loc_raw).strip()
        if "stanton cargo terminal" in loc_str.lower():
            continue
        try:
            price = int(price_raw.replace(",", ""))
        except ValueError:
            price = 0
        system = _normalize_system(_guess_system_from_str(loc_str))
        planet = _guess_planet_from_terminal(loc_str, "", loc_str, system)
        city = _guess_city_from_terminal(loc_str, loc_str, planet)
        results.append({
            "system": system,
            "planet": planet,
            "city": city,
            "station": loc_str,
            "shop": loc_str,
            "buy_price": price
        })
    return results


def _guess_system_from_str(s):
    s_low = s.lower()
    if "pyro" in s_low or "checkmate" in s_low or "ruin" in s_low:
        return "Pyro"
    if "nyx" in s_low or "levski" in s_low:
        return "Nyx"
    return "Stanton"


# ════════════════════════════════════════════════════════════
# MAIN LOGIC
# ════════════════════════════════════════════════════════════

def fetch_item_locations(item_name):
    """
    Try all sources to find buy locations for an item.
    Priority: 1) SC Wiki API  2) CStone Finder HTML  3) Clean variant fallback
    Returns list of location dicts.
    """
    # 1) SC Wiki API (Priority 1)
    locs = fetch_wiki_locations(item_name)
    if locs:
        return locs

    # 2) CStone Finder HTML (Priority 2 Fallback)
    locs = fetch_cstone_locations(item_name)
    if locs:
        return locs

    # 3) Try with simplified name (strip skin variants)
    clean_name = re.sub(r'\s*\([^)]*\)\s*', ' ', item_name).strip()
    clean_name = re.sub(r'\s*"[^"]*"\s*', ' ', clean_name).strip()
    clean_name = re.sub(r'\s+', ' ', clean_name)
    if clean_name != item_name:
        locs = fetch_wiki_locations(clean_name) or fetch_cstone_locations(clean_name)
        if locs:
            return locs

    # 4) Try base name only (e.g. "Aril Core Woodland" → "Aril Core")
    words = item_name.split()
    for end in range(len(words) - 1, 1, -1):
        base = " ".join(words[:end])
        locs = fetch_wiki_locations(base) or fetch_cstone_locations(base)
        if locs:
            return locs

    return []


def update_frequent_items(single_item=None, dry_run=False, max_items=None, missing_only=False):
    """
    Update frequent_items.json with location, price, and weight (mass) data.

    Args:
        single_item: If set, only fetch this one item name
        dry_run: If True, don't write changes
        max_items: Limit number of items to fetch (for testing)
        missing_only: If True, only fetch for items without location data.
                      Default False: processes ALL items as requested by user.
    """
    with open(FREQ_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    if single_item:
        to_fetch = [(i, item) for i, item in enumerate(items)
                     if item["name"].lower() == single_item.lower()]
    elif missing_only:
        to_fetch = [(i, item) for i, item in enumerate(items)
                     if not item.get("locations")]
    else:
        # Process ALL items by default
        to_fetch = list(enumerate(items))

    if max_items:
        to_fetch = to_fetch[:max_items]

    total = len(to_fetch)
    found = 0
    skipped = 0

    print(f"[FETCHER] Processing {total} items for location & price sync (SC Wiki -> CStone fallback)...")

    name_cache = {}  # base_name -> locations

    for idx, (i, item) in enumerate(to_fetch):
        name = item["name"]
        if idx % 100 == 0 and idx > 0:
            print(f"  Progress: {idx}/{total} ({found} updated/found, {skipped} skipped)")

        base_name = re.sub(r'\s*\([^)]*\)\s*', ' ', name).strip()
        base_name = re.sub(r'\s*"[^"]*"\s*', ' ', base_name).strip()
        base_name = re.sub(r'\s+', ' ', base_name)

        if base_name in name_cache:
            locs = name_cache[base_name]
        elif name in name_cache:
            locs = name_cache[name]
        else:
            locs = fetch_item_locations(name)
            name_cache[name] = locs
            name_cache[base_name] = locs
            time.sleep(REQUEST_DELAY)

        if locs:
            if not dry_run:
                items[i]["locations"] = locs
                # Sync best price if available
                best_p = min(l["buy_price"] for l in locs if l.get("buy_price", 0) > 0)
                if best_p:
                    items[i]["price"] = best_p
            found += 1
            if found <= 5:  # Show sample
                loc_str = f"{locs[0]['system']} > {locs[0].get('city','') or locs[0].get('station','')} > {locs[0]['shop']}"
                print(f"  + {name} -> {loc_str}")
        else:
            skipped += 1

    print(f"\n[RESULT] Found locations for {found}/{total} items ({skipped} not found)")

    if not dry_run and found > 0:
        with open(FREQ_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Updated {FREQ_PATH}")


if __name__ == "__main__":
    args = sys.argv[1:]

    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    max_items_arg = None
    for a in args:
        if a.startswith("--max="):
            max_items_arg = int(a.split("=")[1])
    args = [a for a in args if not a.startswith("--max=")]

    if args:
        # Single item mode
        item_name = " ".join(args)
        print(f"[FETCHER] Fetching locations for: {item_name}")
        update_frequent_items(single_item=item_name, dry_run=dry_run)
    else:
        # Bulk mode
        update_frequent_items(dry_run=dry_run, max_items=max_items_arg)
