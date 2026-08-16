# -*- coding: utf-8 -*-
"""
fix_countermeasures_locations.py — Fixes Decoy and Noise Countermeasures store locations.
In Star Citizen, Countermeasures (Decoys & Noise) are Ship Defensive Ammunition
rearmed/purchased at Vehicle Maintenance / Refueling Stations and Platinum Bay.
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
    print("[START] Fixing Decoy and Noise Countermeasure locations...")

    sc_wiki_cache = load_json("sc_wiki_items_cache.json", {})
    uex_items_db = load_json("uex_items_trade_db.json", {})

    cm_terminals = [
        {"terminal": "Refueling & Maintenance - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Refueling & Maintenance - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Refueling & Maintenance - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Refueling & Maintenance - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Platinum Bay - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Platinum Bay - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Platinum Bay - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Platinum Bay - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Refueling & Maintenance - Grim HEX", "location": "Grim HEX", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Refueling & Maintenance - Levski", "location": "Levski", "parent": "Nyx", "system": "Nyx"},
        {"terminal": "Refueling & Maintenance - Checkmate Station", "location": "Checkmate Station", "parent": "Pyro", "system": "Pyro"},
        {"terminal": "Refueling & Maintenance - Ruin Station", "location": "Ruin Station", "parent": "Pyro", "system": "Pyro"},
    ]

    # Decoy: 150 aUEC
    decoy_entries = [{**t, "price": 150} for t in cm_terminals]
    for k in ["Decoy Countermeasures", "decoy countermeasures", "Decoy", "decoy", "Decoys", "decoys", "Chaff", "chaff"]:
        sc_wiki_cache[k] = list(decoy_entries)
        uex_items_db[k.lower()] = {
            "name": "Decoy Countermeasures",
            "locations": [{"terminal": t["terminal"], "buy": 150, "sell": 0} for t in decoy_entries]
        }

    # Noise: 300 aUEC
    noise_entries = [{**t, "price": 300} for t in cm_terminals]
    for k in ["Noise Countermeasures", "noise countermeasures", "Noise", "noise", "Flares", "flares"]:
        sc_wiki_cache[k] = list(noise_entries)
        uex_items_db[k.lower()] = {
            "name": "Noise Countermeasures",
            "locations": [{"terminal": t["terminal"], "buy": 300, "sell": 0} for t in noise_entries]
        }

    save_json("sc_wiki_items_cache.json", sc_wiki_cache)
    save_json("uex_items_trade_db.json", uex_items_db)

    print("[SUCCESS] Decoy and Noise Countermeasures accurately mapped to Refueling & Maintenance and Platinum Bay!")

if __name__ == "__main__":
    main()
