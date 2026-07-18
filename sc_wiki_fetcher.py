"""
SC Wiki API item location fetcher.
Pulls item buy locations from https://api.star-citizen.wiki/api/v2/items
and caches them locally as a JSON lookup for supply route PDFs.

Usage:
    python sc_wiki_fetcher.py              # Fetch all common items
    python sc_wiki_fetcher.py "P4-AR"      # Fetch single item
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error

API_BASE = "https://api.star-citizen.wiki/api/v2/items"
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "resources", "sc_wiki_items_cache.json")

# Common items to fetch — weapons, tools, grenades, drinks, etc.
ITEMS_TO_FETCH = [
    # Weapons
    "P4-AR", "C54", "Custodian", "Demeco", "FS-9", "GP-33", "Karna",
    "LH86", "Lumin V", "P6-LR", "Ravager-212", "S71",
    # Grenades
    "Scorch", "Oxbite", "Frag Grenade", "Flash Grenade", "Impact Grenade",
    # Tools
    "MaxLift", "Cambio", "Pyro RYT", "TruHold",
    # Magazines / Ammo
    "P4-AR Magazine", "S71 Magazine",
    # Containers
    "Stor-All",
    # Food / Drink
    "CRUZ Lux", "Big Benny", "Burrito",
    # Medical
    "MedPen", "ParaMed",
    # Mining
    "Hofstede",
    # SRT / Canister
    "Cambio SRT",
    # Batteries
    "Battery",
    # Torpedoes / Missiles
    "Torpedo", "Missile", "Thunderbolt", "Vanquisher", "Arrester",
    "Reaper", "Typhoon", "Stalker", "Dominator", "Tempest",
    "Ignite", "Marksman", "Rattler", "Spark", "Pioneer",
    "Colossus", "Seeker",
]

def fetch_item(name: str) -> list:
    """Query the SC Wiki API for an item by name and extract buy locations."""
    params = urllib.parse.urlencode({"filter[name]": name})
    url = f"{API_BASE}?{params}"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "Starlifter-Terminal/1.0"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [WARN] Failed to fetch '{name}': {e}")
        return []

    results = []
    for item in data.get("data", []):
        item_name = item.get("name", "")
        # Extract buy locations from uex_prices.purchase
        for p in item.get("uex_prices", {}).get("purchase", []):
            price = p.get("price_buy", 0)
            if not price or price <= 0:
                continue
            loc = p.get("starmap_location", {})
            terminal = p.get("terminal_name", "UNKNOWN")
            results.append({
                "item": item_name,
                "price": price,
                "terminal": terminal,
                "location": loc.get("name", ""),
                "parent": loc.get("parent_name", ""),
                "system": loc.get("star_system_name", "Stanton"),
            })
    return results


def main():
    items = ITEMS_TO_FETCH
    if len(sys.argv) > 1:
        items = sys.argv[1:]

    # Load existing cache
    cache = {}
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    total = len(items)
    for i, name in enumerate(items):
        print(f"[{i+1}/{total}] Fetching: {name}...")
        locs = fetch_item(name)
        if locs:
            # Group by item name
            for loc in locs:
                key = loc["item"]
                if key not in cache:
                    cache[key] = []
                # Avoid duplicates
                existing = {(e["terminal"], e["price"]) for e in cache[key]}
                if (loc["terminal"], loc["price"]) not in existing:
                    cache[key].append({
                        "terminal": loc["terminal"],
                        "price": loc["price"],
                        "location": loc["location"],
                        "parent": loc["parent"],
                        "system": loc["system"],
                    })
            print(f"  -> Found {len(locs)} buy locations")
        else:
            print(f"  -> No buy locations found")
        time.sleep(0.3)  # Rate limiting

    # Save cache
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(cache)} items to {CACHE_PATH}")


if __name__ == "__main__":
    main()
