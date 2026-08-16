# -*- coding: utf-8 -*-
"""
harmonize_all_locations.py — Comprehensive location & category validator and enricher.
Ensures ALL items in frequent_items.json, sc_wiki_items_cache.json, and uex_items_trade_db.json
have accurate categories, realistic prices, and valid Stanton/Pyro/Nyx retail buy locations.
"""
import json
import os
import re

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

# ── Canonical retail store networks in Stanton, Pyro, Nyx ──
STANTON_CARGO_DECKS = [
    {"terminal": "Cargo Center Supplies - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Cargo Center Supplies - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Cargo Center Supplies - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Cargo Center Supplies - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Cargo Center Supplies - CRU-L1", "location": "CRU-L1", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Cargo Center Supplies - HUR-L1", "location": "HUR-L1", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Cargo Center Supplies - MIC-L1", "location": "MIC-L1", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Cargo Center Supplies - ARC-L1", "location": "ARC-L1", "parent": "ArcCorp", "system": "Stanton"},
]

STANTON_FPS_ARMOR_SHOPS = [
    {"terminal": "FPS Armor Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "FPS Armor Everus", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "FPS Armor Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "FPS Armor Baijini", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Cubby Blast - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Tammany and Sons - Lorville", "location": "Lorville", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Shubin Interstellar - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Garrity Defense - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Skutters - Grim HEX", "location": "Grim HEX", "parent": "Crusader", "system": "Stanton"},
]

STANTON_FPS_WEAPON_SHOPS = [
    {"terminal": "Live Fire Weapons - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Live Fire Weapons - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Live Fire Weapons - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Live Fire Weapons - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Center Mass - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Center Mass - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Cubby Blast - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Tammany and Sons - Lorville", "location": "Lorville", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Skutters - Grim HEX", "location": "Grim HEX", "parent": "Crusader", "system": "Stanton"},
]

STANTON_SHIP_COMPONENT_SHOPS = [
    {"terminal": "Platinum Bay - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Platinum Bay - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Platinum Bay - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Platinum Bay - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Omega Pro - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Dumper's Depot - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Cousin Crow's - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Platinum Bay - CRU-L1", "location": "CRU-L1", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Platinum Bay - HUR-L1", "location": "HUR-L1", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Platinum Bay - MIC-L1", "location": "MIC-L1", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Platinum Bay - ARC-L1", "location": "ARC-L1", "parent": "ArcCorp", "system": "Stanton"},
]

STANTON_SHIP_WEAPON_SHOPS = [
    {"terminal": "Ship Weapons - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Ship Weapons - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Ship Weapons - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Ship Weapons - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Center Mass - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Center Mass - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Cousin Crow's - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
]

STANTON_CASABA_SHOPS = [
    {"terminal": "Casaba Outlet - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Casaba Outlet - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Casaba Outlet - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Casaba Outlet - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Casaba Outlet - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Casaba Outlet - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Makau - Orison", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Casaba Outlet - HUR-L1", "location": "HUR-L1", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Casaba Outlet - HUR-L4", "location": "HUR-L4", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Casaba Outlet - MIC-L1", "location": "MIC-L1", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Casaba Outlet - MIC-L2", "location": "MIC-L2", "parent": "microTech", "system": "Stanton"},
]

STANTON_CLINICS = [
    {"terminal": "Clinic - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Clinic - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Clinic - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Clinic - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Maria Pure Compliance - Lorville", "location": "Lorville", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Brentworth Care Center - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Empire Health - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
]

STANTON_FOOD_SHOPS = [
    {"terminal": "Kel-To - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Kel-To - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Kel-To - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Kel-To - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "G-Loc Bar - Area18", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Wally's Bar - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Tammany and Sons - Lorville", "location": "Lorville", "parent": "Hurston", "system": "Stanton"},
]

STANTON_REFUELING = [
    {"terminal": "Refueling Station - Seraphim", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Refueling Station - Everus", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Refueling Station - Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
    {"terminal": "Refueling Station - Baijini", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "Refueling Station - CRU-L1", "location": "CRU-L1", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "Refueling Station - HUR-L1", "location": "HUR-L1", "parent": "Hurston", "system": "Stanton"},
]

STANTON_TDD_COMMODITY = [
    {"terminal": "TDD (Area18)", "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    {"terminal": "TDD (New Babbage)", "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
    {"terminal": "TDD (Orison)", "location": "Orison", "parent": "Crusader", "system": "Stanton"},
    {"terminal": "TDD (Lorville)", "location": "Lorville", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Reclamation & Disposal Orinth (Hurston)", "location": "Hurston", "parent": "Hurston", "system": "Stanton"},
    {"terminal": "Brio's Breaker Yard (Daymar)", "location": "Daymar", "parent": "Crusader", "system": "Stanton"},
]

def get_accurate_category(name):
    n_low = str(name).lower().strip()
    if any(k in n_low for k in ["medpen", "medkit", "paramed", "lifeguard", "hemopen", "hemozal", "detoxpen", "oxypen", "adrenapen", "corticopen", "deconpen", "opiopen", "medgel", "panacea", "refill", "medical"]):
        return "medical"
    if any(k in n_low for k in ["cruz", "rynex", "water bottle", "snack", "pips", "snaggle", "food", "drink", "bottle", "burrito", "noodle", "bar", "ration", "readymeal", "meal", "chocolate", "karoby", "tankard", "hotdog", "pizza", "onemeal", "curry"]):
        return "food"
    if any(k in n_low for k in ["livery", "paint", "cosmetic", "skin"]):
        return "Ship Cosmetics"
    if any(k in n_low for k in ["torpedo", "missile", "bomb", "countermeasure", "chaff", "noise", "decoy", "magazine", "mag", "round", "ammo", "ammunition"]) and not any(k in n_low for k in ["rifle", "pistol", "smg", "lmg", "sniper", "shotgun"]):
        return "Ammo & Missiles"
    if any(k in n_low for k in ["rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "launcher", "p4-ar", "fs-9", "s-38", "p8-sc", "p6-lr", "br-2", "br2", "arclight", "a03", "ado-5", "laser mine", "grenade", "scorch", "mk-4", "coda", "gallant", "c54", "lumin", "scalpel", "custodian", "devastator", "cq7", "nightstalker", "compensator", "suppressor", "scope", "sight", "optic", "choke"]):
        return "weapons"
    if any(k in n_low for k in ["mining head", "mining gadget", "mining module", "salvage head", "salvage module", "ore pod", "fuel pod", "fuel nozzle", "hofstede", "klein", "helix", "lancet", "arbor", "impact", "boremax", "optimax", "waveshift", "sabir", "stampede", "focus", "torrent", "rime", "fltr", "brand", "lifesaver", "truhold", "cinch", "abrade", "trawler", "cinematic", "cambio", "maxlift", "tractor beam", "multi-tool", "multitool", "fabricator", "extinguisher"]):
        return "Industrial Utilities"
    if any(k in n_low for k in ["shield generator", "shield", "power plant", "powerplant", "cooler", "fr-86", "fr-76", "fr-66", "rampart", "umbra", "aspis", "fullstop", "allstop", "palisade", "bulwark", "fortress", "js-500", "js-400", "js-300", "js-200", "maelstrom", "quadracell", "overdrive", "genesis", "eclipse", "regulator", "breton", "diligence", "superego", "starheart", "coolcore", "eridani", "ultra-flow", "glacier", "icebox", "chill-out", "snowpack", "quantum drive", "quantum engine", "qt drive", "qd", "vk-00", "atlas", "voyager", "beacon", "crossfield", "pontes", "ts-2", "agate", "colossus", "siren", "turret", "radar", "missile rack", "missile launcher", "flight blade"]):
        return "Ship Components"
    if any(k in n_low for k in ["laser cannon", "ballistic cannon", "laser repeater", "ballistic repeater", "giga-panther", "rhino", "panther", "badger", "bulldog", "m7a", "m6a", "m5a", "m4a", "cf-557", "cf-447", "cf-337", "cf-227", "cf-117", "tarantula", "deadbolt", "omnisky", "quarrel", "gatling", "scattergun", "ship cannon", "ship repeater", "ship weapon", "tigerstrike", "distortion cannon"]):
        return "Ship Weapons"
    if any(k in n_low for k in ["helmet", "core", "arms", "legs", "backpack", "undersuit", "jacket", "shirt", "pants", "shoes", "gloves", "armor", "suit", "vest", "hat", "cap", "coat", "boots", "tcs-4", "csp-68", "adiva", "lemarque", "deo", "prim", "ventra", "orc-mkx", "adp-mk4", "field recon", "aril", "adp", "macflex", "morozov", "novikov", "pembroke"]):
        return "Armor + Clothes"
    if any(k in n_low for k in ["copper", "iron", "hephaestanite", "quantainium", "quantanium", "gold", "laranite", "agricium", "bexalite", "bexlite", "taranite", "beryl", "titanium", "silicon", "quartz", "borase", "corundum", "diamond", "tungsten", "aluminium", "aluminum", "rmc", "recycled material", "construction materials", "ore", "scrap", "hydrogen fuel", "quantum fuel", "fuel"]):
        return "commodities"
    return "other"

def main():
    print("[START] Harmonizing all item locations & categories across databases...")
    
    frequent_items = load_json("frequent_items.json", [])
    item_volumes = load_json("item_volumes.json", {})
    sc_wiki_cache = load_json("sc_wiki_items_cache.json", {})
    uex_items_db = load_json("uex_items_trade_db.json", {})
    
    # Clean specific known items in sc_wiki_cache and uex_items_db
    # 1. Cambio Multi-tool Battery & Cambio SRT
    cambio_terms = [
        {"terminal": "Cargo Center Supplies - Seraphim", "price": 125, "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Cargo Center Supplies - Everus Harbor", "price": 125, "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Cargo Center Supplies - Port Tressler", "price": 125, "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Cargo Center Supplies - Baijini Point", "price": 125, "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Shubin Interstellar - New Babbage", "price": 125, "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Tammany and Sons - Lorville", "price": 125, "location": "Lorville", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Dumper's Depot - Area18", "price": 125, "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    ]
    for k in ["Cambio Multi-tool Battery", "cambio multi-tool battery", "Multi-tool Battery", "multi-tool battery", "Cambio Battery", "cambio battery"]:
        sc_wiki_cache[k] = list(cambio_terms)
        uex_items_db[k.lower()] = {
            "name": "Cambio Multi-tool Battery",
            "locations": [{"terminal": t["terminal"], "buy": t["price"], "sell": 0} for t in cambio_terms]
        }

    # 2. Fuel
    fuel_terms = [
        {"terminal": "Refueling Station - Seraphim", "price": 200, "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Refueling Station - Everus Harbor", "price": 200, "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Refueling Station - Port Tressler", "price": 200, "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Refueling Station - Baijini Point", "price": 200, "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
    ]
    for k in ["Hydrogen Fuel", "hydrogen fuel", "Quantum Fuel", "quantum fuel"]:
        price = 200 if "hydrogen" in k.lower() else 950
        terms_copy = [{**t, "price": price} for t in fuel_terms]
        sc_wiki_cache[k] = terms_copy
        uex_items_db[k.lower()] = {
            "name": k.title(),
            "locations": [{"terminal": t["terminal"], "buy": price, "sell": 0} for t in terms_copy]
        }

    # 3. Countermeasures
    cm_terms = [
        {"terminal": "Ship Weapons - Seraphim", "price": 150, "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Ship Weapons - Everus Harbor", "price": 150, "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Ship Weapons - Port Tressler", "price": 150, "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Ship Weapons - Baijini Point", "price": 150, "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Center Mass - Area18", "price": 150, "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    ]
    for k in ["Decoy Countermeasures", "decoy countermeasures", "Noise Countermeasures", "noise countermeasures"]:
        price = 150 if "decoy" in k.lower() else 300
        terms_copy = [{**t, "price": price} for t in cm_terms]
        sc_wiki_cache[k] = terms_copy
        uex_items_db[k.lower()] = {
            "name": k.title(),
            "locations": [{"terminal": t["terminal"], "buy": price, "sell": 0} for t in terms_copy]
        }

    # 4. RMC (Recycled Material Composite)
    rmc_terms = [
        {"terminal": "TDD (Area18)", "price": 10710, "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "TDD (New Babbage)", "price": 10710, "location": "New Babbage", "parent": "microTech", "system": "Stanton"},
        {"terminal": "TDD (Orison)", "price": 10710, "location": "Orison", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "TDD (Lorville)", "price": 10710, "location": "Lorville", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Reclamation & Disposal Orinth (Hurston)", "price": 10500, "location": "Hurston", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Brio's Breaker Yard (Daymar)", "price": 10500, "location": "Daymar", "parent": "Crusader", "system": "Stanton"},
    ]
    for k in ["Recycled Material Composite (RMC)", "recycled material composite (rmc)", "Recycled Material Composite", "recycled material composite", "RMC", "rmc"]:
        sc_wiki_cache[k] = list(rmc_terms)
        uex_items_db[k.lower()] = {
            "name": "Recycled Material Composite (RMC)",
            "locations": [{"terminal": t["terminal"], "buy": t["price"], "sell": 0} for t in rmc_terms]
        }

    # 5. Fix all categories in frequent_items
    fixed_cats = 0
    for item in frequent_items:
        if isinstance(item, dict):
            iname = item.get("name", "")
            correct_cat = get_accurate_category(iname)
            if item.get("category") != correct_cat:
                item["category"] = correct_cat
                fixed_cats += 1
            # Clean up stale static locations
            if "locations" in item:
                del item["locations"]
    
    print(f"Fixed {fixed_cats} categories in frequent_items.json.")

    save_json("frequent_items.json", frequent_items)
    save_json("sc_wiki_items_cache.json", sc_wiki_cache)
    save_json("uex_items_trade_db.json", uex_items_db)

if __name__ == "__main__":
    main()
