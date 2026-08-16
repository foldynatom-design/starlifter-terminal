# -*- coding: utf-8 -*-
"""
rebuild_frequent_items_from_cstone.py — Rebuilds frequent_items.json directly
from cstone_master_db.json (Table 0 names), removing all duplicates and accurately
assigning categories.
"""
import json, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

def categorize_cstone_item(item_name, cat_label):
    cat_l = cat_label.lower()
    in_low = item_name.lower()

    if "armor/" in cat_l:
        return "FPS Armor"
    if "clothes/" in cat_l:
        return "Clothing"
    if "weapons/" in cat_l:
        if any(k in in_low for k in ["missile", "torpedo", "bomb"]):
            return "Ship Weapons & Missiles"
        return "Weapons"
    if "shipweapons/" in cat_l:
        return "Ship Weapons & Missiles"
    if "shipcomponents/" in cat_l:
        return "Ship Components"
    if "tools/" in cat_l or "mining/" in cat_l:
        return "Industrial Utilities"
    if "gadgets/" in cat_l:
        if any(k in in_low for k in ["medpen", "medkit", "paramed", "hemozal", "oxypen", "detoxpen", "adrenapen", "corticopen", "deconpen", "opiopen"]):
            return "Medical"
        return "Industrial Utilities"
    if "consumables/" in cat_l or "food" in cat_l or "drink" in cat_l:
        return "Food & Drinks"
    if "cargo/" in cat_l or "container" in cat_l or "ore" in in_low:
        return "Commodities & Cargo"
    if "paint" in in_low or "livery" in in_low or "cosmetic" in in_low:
        return "Ship Cosmetics"

    # Secondary heuristic by name
    if any(k in in_low for k in ["helmet", "core", "arms", "legs", "backpack", "undersuit"]):
        return "FPS Armor"
    if any(k in in_low for k in ["jacket", "shirt", "pants", "shoes", "gloves", "hat", "cap", "boots", "coat"]):
        return "Clothing"
    if any(k in in_low for k in ["shield", "cooler", "power plant", "quantum drive", "drive"]):
        return "Ship Components"
    if any(k in in_low for k in ["cannon", "repeater", "gatling", "missile", "torpedo", "turret", "rack"]):
        return "Ship Weapons & Missiles"
    if any(k in in_low for k in ["rifle", "pistol", "smg", "shotgun", "sniper", "lmg", "magazine", "scope", "sight", "suppressor", "compensator"]):
        return "Weapons"
    if any(k in in_low for k in ["tractor beam", "multi-tool", "cambio", "maxlift", "mining", "salvage", "battery"]):
        return "Industrial Utilities"

    return "Industrial Utilities"

def rebuild():
    master_path = os.path.join(RES_DIR, "cstone_master_db.json")
    uex_path = os.path.join(RES_DIR, "uex_items_trade_db.json")
    recipes_path = os.path.join(RES_DIR, "crafting_recipes.json")
    vol_path = os.path.join(RES_DIR, "item_volumes.json")

    seen_names = set()
    cleaned_items = []

    # 1. Add from CStone Master DB
    if os.path.exists(master_path):
        with open(master_path, "r", encoding="utf-8") as f:
            master_db = json.load(f)
        for k, v in master_db.items():
            if isinstance(v, dict):
                c_name = v.get("name", k).strip()
                if c_name and c_name.lower() not in seen_names:
                    seen_names.add(c_name.lower())
                    final_category = categorize_cstone_item(c_name, v.get("category", ""))
                    cleaned_items.append({
                        "name": c_name,
                        "category": final_category,
                        "price": v.get("price", 0),
                        "volume": v.get("volume", 0.01)
                    })

    # 2. Add from UEX Items Trade DB (includes all live PU trade items & flairs)
    if os.path.exists(uex_path):
        with open(uex_path, "r", encoding="utf-8") as f:
            uex_db = json.load(f)
        for k, v in uex_db.items():
            if isinstance(v, dict):
                u_name = v.get("name", k).strip()
                if u_name and u_name.lower() not in seen_names:
                    seen_names.add(u_name.lower())
                    final_category = categorize_cstone_item(u_name, v.get("packing_cat", ""))
                    locs = v.get("locations", [])
                    buys = [l.get("buy", 0) for l in locs if isinstance(l, dict) and l.get("buy", 0) > 0]
                    min_p = min(buys) if buys else 0
                    cleaned_items.append({
                        "name": u_name,
                        "category": final_category,
                        "price": min_p,
                        "volume": 0.01
                    })

    # 3. Add from Crafting Blueprints
    if os.path.exists(recipes_path):
        with open(recipes_path, "r", encoding="utf-8") as f:
            recipes_db = json.load(f)
        for k, v in recipes_db.get("specific_items", {}).items():
            r_name = v.get("name", k).strip()
            if r_name and r_name.lower() not in seen_names:
                seen_names.add(r_name.lower())
                final_category = categorize_cstone_item(r_name, v.get("category", ""))
                cleaned_items.append({
                    "name": r_name,
                    "category": final_category,
                    "price": 0,
                    "volume": 0.01
                })

    # Add official Stor-All cargo containers and common commodities if missing
    extra_essentials = [
        ("Stor-All 1 SCU Cargo Container", "Commodities & Cargo"),
        ("Stor-All 2 SCU Cargo Container", "Commodities & Cargo"),
        ("Stor-All 4 SCU Cargo Container", "Commodities & Cargo"),
        ("Stor-All 8 SCU Cargo Container", "Commodities & Cargo"),
        ("RMC (Recycled Material Composite)", "Commodities & Cargo"),
        ("Hydrogen Fuel", "Commodities & Cargo"),
        ("Quantum Fuel", "Commodities & Cargo"),
        ("Size 1 Ammunition", "Weapons"),
        ("Size 2 Ammunition", "Weapons"),
        ("Size 3 Ammunition", "Weapons"),
        ("Size 4 Ammunition", "Weapons"),
        ("Size 5 Ammunition", "Weapons"),
        ("Decoy Countermeasures", "Ship Weapons & Missiles"),
        ("Noise Countermeasures", "Ship Weapons & Missiles"),
    ]

    for item_name, cat in extra_essentials:
        low = item_name.lower()
        if low not in seen_names:
            seen_names.add(low)
            cleaned_items.append({
                "name": item_name,
                "category": cat
            })

    cleaned_items.sort(key=lambda x: (x.get("category", ""), x.get("name", "").lower()))

    out_path = os.path.join(RES_DIR, "frequent_items.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_items, f, indent=2, ensure_ascii=False)

    print(f"[REBUILD] Successfully rebuilt frequent_items.json with {len(cleaned_items)} unified items across all categories!")

if __name__ == "__main__":
    rebuild()
