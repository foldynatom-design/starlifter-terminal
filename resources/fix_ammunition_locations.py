# -*- coding: utf-8 -*-
"""
fix_ammunition_locations.py — Fixes all ship ballistic ammunition locations and prices.
Ship ammunition (Size 1–7 Ammunition) is sold at station Ship Weapons, Cargo Centers,
Center Mass, Cousin Crow's, Platinum Bay, and Admin Offices across Stanton, Pyro, and Nyx.
Removes bogus handheld Galleria gun shops / pharmacies in Ruin Station / Checkmate.
"""
import json
import os

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
    print("[START] Fixing ship ammunition locations and prices...")

    sc_wiki_cache = load_json("sc_wiki_items_cache.json", {})
    uex_items_db = load_json("uex_items_trade_db.json", {})
    item_volumes = load_json("item_volumes.json", {})

    ammo_prices = {
        1: 1500,
        2: 2500,
        3: 4500,
        4: 8500,
        5: 15000,
        6: 28000,
        7: 45000
    }

    ammo_volumes = {
        1: 1.0,
        2: 1.0,
        3: 2.0,
        4: 2.0,
        5: 4.0,
        6: 4.0,
        7: 8.0
    }

    stanton_ammo_terminals = [
        {"terminal": "Ship Weapons - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Cargo Center Supplies - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Ship Weapons - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Cargo Center Supplies - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Ship Weapons - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Cargo Center Supplies - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Ship Weapons - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Cargo Center Supplies - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Center Mass - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Dumper's Depot - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Center Mass - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Omega Pro - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Cousin Crow's - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Crusader Showroom - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Skutters - Grim HEX", "location": "Grim HEX", "parent": "Crusader", "system": "Stanton"},
    ]

    pyro_ammo_terminals = [
        {"terminal": "Cargo Center - Checkmate Station", "location": "Checkmate Station", "parent": "Pyro", "system": "Pyro"},
        {"terminal": "Cargo Center - Ruin Station", "location": "Ruin Station", "parent": "Pyro", "system": "Pyro"},
        {"terminal": "Cargo Center - Patch City", "location": "Patch City", "parent": "Pyro", "system": "Pyro"},
        {"terminal": "Admin Office - Orbituary", "location": "Orbituary", "parent": "Pyro", "system": "Pyro"},
    ]

    nyx_ammo_terminals = [
        {"terminal": "Admin Office - Levski", "location": "Levski", "parent": "Nyx", "system": "Nyx"},
        {"terminal": "Cordry's Shop - Levski", "location": "Levski", "parent": "Nyx", "system": "Nyx"},
    ]

    all_ammo_terminals = stanton_ammo_terminals + pyro_ammo_terminals + nyx_ammo_terminals

    for s, price in ammo_prices.items():
        vol = ammo_volumes[s]
        terms_with_price = [{**t, "price": price} for t in all_ammo_terminals]
        
        keys = [
            f"Size {s} Ammunition",
            f"size {s} ammunition",
            f"Size {s} Ammo",
            f"size {s} ammo",
            f"S{s} Ammunition",
            f"s{s} ammunition",
            f"S{s} Ammo",
            f"s{s} ammo",
        ]
        
        for k in keys:
            sc_wiki_cache[k] = list(terms_with_price)
            item_volumes[k.lower()] = vol
            uex_items_db[k.lower()] = {
                "name": f"Size {s} Ammunition",
                "locations": [{"terminal": t["terminal"], "buy": price, "sell": 0} for t in terms_with_price]
            }

    save_json("sc_wiki_items_cache.json", sc_wiki_cache)
    save_json("uex_items_trade_db.json", uex_items_db)
    save_json("item_volumes.json", item_volumes)

    print("[SUCCESS] All ship ammunition locations and prices have been repaired accurately!")

if __name__ == "__main__":
    main()
