# -*- coding: utf-8 -*-
"""
unify_frequent_items.py — Master deduplicator and canonical unifier.
Unifies all duplicate clothing, weapon variants, magazines, and components into single clean entries.
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

def normalize_key(name):
    """Generate a clean deduplication key to group duplicate representations of the same item."""
    n = str(name).lower().strip()
    n = re.sub(r'[\ufffd\x80-\xff]', '', n)
    
    # 1. Magazines
    if "magazine" in n or " mag" in n:
        # e.g., 'p8-sc magazine (30 cap)', 'p8-sc smg magazine (45 cap)', 'p8-sc magazine' -> 'p8-sc magazine'
        for wep in ["p4-ar", "p8-sc", "fs-9", "s-38", "c54", "lumin", "coda", "gallant", "custodian", "scalpel", "p6-lr", "arclight", "a03", "br-2", "devastator", "karna", "demeco"]:
            if wep in n:
                return f"{wep}_magazine"
        base = re.sub(r'\(?\b\d+\s*cap\b\)?', '', n)
        base = re.sub(r'\b(smg|rifle|pistol|lmg|sniper|shotgun)\b', '', base)
        return " ".join(base.split())

    # 2. Weapons with skin editions in quotes vs base
    # e.g., 'p8-sc smg' vs 'p8-sc'
    for wep in ["p4-ar", "p8-sc", "fs-9", "s-38", "c54", "lumin", "coda", "gallant", "custodian", "scalpel", "p6-lr", "arclight", "a03", "br-2", "devastator", "karna", "demeco"]:
        if wep in n and not ("magazine" in n or " mag" in n):
            if '"' in name:
                match = re.search(r'\"([^\"]+)\"', name)
                if match:
                    return f"{wep}_skin_{match.group(1).lower()}"
            return f"{wep}_base_weapon"

    # 3. Clothing Inverted Names
    # e.g., 'adiva yellow jacket', 'adiva jacket yellow' -> 'adiva_jacket_yellow'
    cloth_match = re.match(r'^(adiva|lemarque|deo|prim|ventra)\s+(.*)\s+(jacket|pants|shirt|shoes|gloves)$', n)
    if cloth_match:
        brand, middle, ctype = cloth_match.groups()
        return f"{brand}_{ctype}_{middle.strip()}"
    cloth_match2 = re.match(r'^(adiva|lemarque|deo|prim|ventra)\s+(jacket|pants|shirt|shoes|gloves)\s+(.*)$', n)
    if cloth_match2:
        brand, ctype, middle = cloth_match2.groups()
        return f"{brand}_{ctype}_{middle.strip()}"

    # 4. Remove capacity and size annotations
    n = re.sub(r'\(?\b\d+\s*cap\b\)?', '', n)
    n = re.sub(r'\b(size\s*\d+)\b', '', n)
    n = re.sub(r'\s*\([^)]*\)', '', n)

    # 5. Standardize ship components & weapons
    for model in ["m3a", "m4a", "m5a", "m6a", "m7a", "cf-117", "cf-227", "cf-337", "cf-447", "cf-557",
                  "fr-66", "fr-76", "fr-86", "js-300", "js-400", "js-500", "ts-2", "vk-00",
                  "atlas", "crossfield", "voyager", "beacon", "pontes", "colossus", "ultra-flow",
                  "eridani", "coolcore", "icebox", "chill-out", "snowpack", "glacier", "endo",
                  "tarantula gt-870", "deadbolt iv", "deadbolt v", "argus ix", "typhoon ix", "seeker ix"]:
        if model in n and not any(x in n for x in ["skin", "paint", "livery", "atlasium"]):
            if '"' in name:
                match = re.search(r'\"([^\"]+)\"', name)
                if match:
                    return f"{model}_{match.group(1).lower()}"
            return model

    n = " ".join(n.split())
    return n

def get_preferred_name(items_group):
    """Given duplicate candidates, select the single cleanest canonical name."""
    def score_candidate(nm):
        score = 0
        if "(" in nm and ")" in nm and ("Size" in nm or "SCU" in nm):
            score += 50
        if "Laser Cannon" in nm or "Laser Repeater" in nm or "Shield Generator" in nm or "Power Plant" in nm or "Quantum Drive" in nm or "Cooler" in nm:
            score += 40
        if "Jacket" in nm or "Shirt" in nm or "Pants" in nm or "Shoes" in nm or "Gloves" in nm:
            score += 30
        if "SMG" in nm or "Rifle" in nm or "Sniper" in nm or "Shotgun" in nm or "Pistol" in nm:
            score += 25
        if "Magazine" in nm and "cap" not in nm.lower():
            score += 35
        # Penalize bare short models like "Fr-86" or "Js-500" or "Atlas" or "P8-SC"
        if len(nm) <= 7 and nm.lower() in ["fr-86", "fr-76", "fr-66", "js-500", "js-400", "js-300", "atlas", "ts-2", "vk-00", "m7a", "m5a", "m6a", "m4a", "m3a", "p8-sc", "p4-ar", "fs-9", "s-38"]:
            score -= 100
        # Penalize inverted names like "Adiva Yellow Jacket"
        if re.search(r'Adiva\s+(Yellow|White|Blue|Red|Dark Green|Imperial|Aqua|Black|Dark Red|Green|Grey)\s+Jacket', nm):
            score -= 50
        if nm and nm[0].isupper():
            score += 10
        return score

    sorted_candidates = sorted(items_group, key=score_candidate, reverse=True)
    return sorted_candidates[0]

def main():
    print("[START] Deep unification of all frequent items...")
    
    sc_wiki_cache = load_json("sc_wiki_items_cache.json", {})
    uex_items_db = load_json("uex_items_trade_db.json", {})
    
    all_raw_names = set()
    for k in sc_wiki_cache.keys():
        if k and not k.islower() and len(k) > 2:
            all_raw_names.add(k.strip())
    for k, v in uex_items_db.items():
        if isinstance(v, dict) and "name" in v:
            all_raw_names.add(v["name"].strip())
        elif isinstance(k, str) and len(k) > 2:
            all_raw_names.add(k.title().strip())

    grouped = {}
    for nm in all_raw_names:
        if not nm or any(x in nm for x in ["Package:", "PACKAGE:", "---", "==="]):
            continue
        nm_clean = re.sub(r'[\ufffd\x80-\xff]', '', nm).strip()
        if not nm_clean: continue
        
        key = normalize_key(nm_clean)
        grouped.setdefault(key, []).append(nm_clean)

    unified_list = []
    seen_names = set()

    for key, name_list in grouped.items():
        best_name = get_preferred_name(name_list)
        
        # Format clothing names canonically: Brand Jacket Color
        match = re.match(r'^(Adiva|Lemarque|Deo|Prim|Ventra)\s+([A-Za-z\s]+)\s+(Jacket|Pants|Shirt|Shoes|Gloves)$', best_name, re.IGNORECASE)
        if match:
            brand, col, ctype = match.groups()
            best_name = f"{brand.title()} {ctype.title()} {col.title()}"
        
        if best_name.lower() not in seen_names:
            seen_names.add(best_name.lower())
            cat = get_accurate_category(best_name)
            unified_list.append({
                "name": best_name,
                "category": cat
            })

    # Sort alphabetically by category and name
    unified_list.sort(key=lambda x: (x.get("category", ""), x.get("name", "")))

    print(f"Unified clean items count: {len(unified_list)}")

    save_json("frequent_items.json", unified_list)

    print("[SUCCESS] All frequent items successfully unified without duplicate search entries!")

if __name__ == "__main__":
    main()
