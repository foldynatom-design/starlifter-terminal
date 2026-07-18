# -*- coding: utf-8 -*-
"""Fetch ALL Star Citizen items from SC Wiki — comprehensive database build."""
import json, urllib.request, time

def fetch_wiki(query_part, limit=500):
    base = "https://starcitizen.tools/Special:Ask/"
    url = base + query_part + f"/format=json/limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Starlifter/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read().decode('utf-8'))
        results = {}
        for name, info in data.get("results", {}).items():
            if info.get("namespace", 0) != 0:
                continue
            results[name] = info.get("printouts", {})
        return results
    except Exception as e:
        print(f"  ERROR: {e}")
        return {}

# ══════════════════════════════════════════════════════════
# ALL categories to fetch
# ══════════════════════════════════════════════════════════
categories = {
    # ── Ordnance ──
    "missiles":          "-5B-5BCategory:Missiles-5D-5D/-3FSize/-3FSignal-20type",
    "torpedoes":         "-5B-5BCategory:Torpedoes-5D-5D/-3FSize/-3FSignal-20type",
    "bombs":             "-5B-5BCategory:Bombs-5D-5D/-3FSize",
    "countermeasures":   "-5B-5BCategory:Countermeasures-5D-5D/-3FSize",

    # ── FPS Weapons & Combat ──
    "personal_weapons":  "-5B-5BCategory:Personal-20weapons-5D-5D/-3FWeapon-20type",
    "grenades":          "-5B-5BCategory:Grenades-5D-5D/-3FWeapon-20type",
    "knives":            "-5B-5BCategory:Knives-5D-5D/-3FWeapon-20type",
    "mines":             "-5B-5BCategory:Mines-5D-5D/-3FWeapon-20type",

    # ── Armor & Clothing ──
    "armor_sets":        "-5B-5BCategory:Armor-20sets-5D-5D/-3FArmor-20type",
    "helmets":           "-5B-5BCategory:Helmets-5D-5D/-3FArmor-20type",
    "chest_armor":       "-5B-5BCategory:Chest-20armor-5D-5D/-3FArmor-20type",
    "arm_armor":         "-5B-5BCategory:Arm-20armor-5D-5D/-3FArmor-20type",
    "leg_armor":         "-5B-5BCategory:Leg-20armor-5D-5D/-3FArmor-20type",
    "undersuits":        "-5B-5BCategory:Undersuits-5D-5D/-3FArmor-20type",
    "backpacks":         "-5B-5BCategory:Backpacks-5D-5D/-3FArmor-20type",
    "clothing":          "-5B-5BCategory:Clothing-5D-5D/-3FItem-20type",

    # ── Medical & Consumables ──
    "medical":           "-5B-5BCategory:Medical-20supplies-5D-5D/-3FItem-20type",
    "consumables":       "-5B-5BCategory:Consumables-5D-5D/-3FItem-20type",
    "food":              "-5B-5BCategory:Food-5D-5D/-3FItem-20type",
    "drinks":            "-5B-5BCategory:Drinks-5D-5D/-3FItem-20type",

    # ── Tools & Utilities ──
    "utilities":         "-5B-5BCategory:Utilities-5D-5D/-3FItem-20type",
    "multitools":        "-5B-5BCategory:Multi-tools-5D-5D/-3FItem-20type",
    "gadgets":           "-5B-5BCategory:Gadgets-5D-5D/-3FItem-20type",
    "tractor_beams":     "-5B-5BCategory:Tractor-20beams-5D-5D/-3FItem-20type",

    # ── Mining ──
    "mining_equipment":  "-5B-5BCategory:Mining-20equipment-5D-5D/-3FItem-20type",
    "mining_gadgets":    "-5B-5BCategory:Mining-20gadgets-5D-5D/-3FItem-20type",
    "mining_heads":      "-5B-5BCategory:Mining-20heads-5D-5D/-3FSize",
    "mining_modules":    "-5B-5BCategory:Mining-20modules-5D-5D/-3FSize",

    # ── Ship Components ──
    "ship_weapons":      "-5B-5BCategory:Ship-20weapons-5D-5D/-3FSize/-3FWeapon-20type",
    "shields":           "-5B-5BCategory:Shield-20generators-5D-5D/-3FSize/-3FGrade",
    "power_plants":      "-5B-5BCategory:Power-20plants-5D-5D/-3FSize/-3FGrade",
    "coolers":           "-5B-5BCategory:Coolers-5D-5D/-3FSize/-3FGrade",
    "quantum_drives":    "-5B-5BCategory:Quantum-20drives-5D-5D/-3FSize/-3FGrade",
    "missile_racks":     "-5B-5BCategory:Missile-20racks-5D-5D/-3FSize",
    "turrets":           "-5B-5BCategory:Turrets-5D-5D/-3FSize",
    "radars":            "-5B-5BCategory:Radars-5D-5D/-3FSize/-3FGrade",

    # ── Ship Weapons by Type ──
    "ballistic_cannons": "-5B-5BCategory:Ballistic-20cannons-5D-5D/-3FSize",
    "ballistic_gatlings":"-5B-5BCategory:Ballistic-20Gatling-20guns-5D-5D/-3FSize",
    "ballistic_repeaters":"-5B-5BCategory:Ballistic-20repeaters-5D-5D/-3FSize",
    "laser_cannons":     "-5B-5BCategory:Laser-20cannons-5D-5D/-3FSize",
    "laser_repeaters":   "-5B-5BCategory:Laser-20repeaters-5D-5D/-3FSize",
    "distortion_cannons":"-5B-5BCategory:Distortion-20cannons-5D-5D/-3FSize",
    "scatterguns":       "-5B-5BCategory:Scatterguns-5D-5D/-3FSize",

    # ── Commodities & Materials ──
    "commodities":       "-5B-5BCategory:Commodities-5D-5D/-3FItem-20type",
}

all_data = {}
for cat_name, query in categories.items():
    print(f"Fetching {cat_name:25s}...", end=" ", flush=True)
    results = fetch_wiki(query)
    all_data[cat_name] = results
    print(f"{len(results):4d} items")
    time.sleep(0.3)

# ── Save raw ──
with open('resources/sc_wiki_items_raw.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════════════════
# BUILD item_volumes.json — pattern → SCU volume
# ══════════════════════════════════════════════════════════
item_volumes = {}

# FPS Weapons — strip skins, keep base names
for name in all_data.get("personal_weapons", {}):
    base = name
    if '"' in name:
        parts = name.split('"')
        base = parts[0].strip() + " " + parts[-1].strip()
        base = base.strip()
    nl = base.lower()
    if "sniper" in nl or "lmg" in nl or "railgun" in nl:
        item_volumes[nl] = 0.035
    elif "rifle" in nl or "shotgun" in nl or "launcher" in nl:
        item_volumes[nl] = 0.025
    elif "smg" in nl:
        item_volumes[nl] = 0.015
    elif "pistol" in nl:
        item_volumes[nl] = 0.010
    elif "knife" in nl:
        item_volumes[nl] = 0.003

for name in all_data.get("knives", {}):
    item_volumes[name.lower()] = 0.003

for name in all_data.get("grenades", {}):
    item_volumes[name.lower()] = 0.001

for name in all_data.get("mines", {}):
    item_volumes[name.lower()] = 0.005

# Armor pieces
for name in all_data.get("helmets", {}):
    nl = name.lower()
    if '"' in name: continue  # skip skins
    item_volumes[nl] = 0.010

for name in all_data.get("chest_armor", {}):
    nl = name.lower()
    if '"' in name: continue
    item_volumes[nl] = 0.012

for name in all_data.get("arm_armor", {}):
    nl = name.lower()
    if '"' in name: continue
    item_volumes[nl] = 0.008

for name in all_data.get("leg_armor", {}):
    nl = name.lower()
    if '"' in name: continue
    item_volumes[nl] = 0.008

for name in all_data.get("undersuits", {}):
    nl = name.lower()
    if '"' in name: continue
    item_volumes[nl] = 0.005

for name in all_data.get("backpacks", {}):
    nl = name.lower()
    if '"' in name: continue
    item_volumes[nl] = 0.015

# Clothing
for name in all_data.get("clothing", {}):
    nl = name.lower()
    if '"' in name: continue
    if "jacket" in nl or "coat" in nl:
        item_volumes[nl] = 0.006
    elif "shirt" in nl or "top" in nl:
        item_volumes[nl] = 0.002
    elif "pants" in nl or "trousers" in nl:
        item_volumes[nl] = 0.002
    elif "shoes" in nl or "boots" in nl:
        item_volumes[nl] = 0.002
    elif "gloves" in nl:
        item_volumes[nl] = 0.001
    elif "hat" in nl or "beanie" in nl:
        item_volumes[nl] = 0.001
    else:
        item_volumes[nl] = 0.003

# Medical
for name in all_data.get("medical", {}):
    nl = name.lower()
    if "medpen" in nl or "pen" in nl:
        item_volumes[nl] = 0.001
    elif "medkit" in nl or "medical device" in nl:
        item_volumes[nl] = 0.008
    elif "canister" in nl:
        item_volumes[nl] = 0.050
    else:
        item_volumes[nl] = 0.002

# Food & Drinks
for name in all_data.get("food", {}):
    item_volumes[name.lower()] = 0.0005
for name in all_data.get("drinks", {}):
    item_volumes[name.lower()] = 0.0005

# Tools & Utilities
for name in all_data.get("utilities", {}):
    nl = name.lower()
    if "extinguisher" in nl:
        item_volumes[nl] = 0.010
    elif "flashlight" in nl or "flare" in nl:
        item_volumes[nl] = 0.0005
    else:
        item_volumes[nl] = 0.005
for name in all_data.get("multitools", {}):
    item_volumes[name.lower()] = 0.005
for name in all_data.get("tractor_beams", {}):
    item_volumes[name.lower()] = 0.010

# Mining
for name in all_data.get("mining_equipment", {}):
    item_volumes[name.lower()] = 0.030
for name in all_data.get("mining_gadgets", {}):
    item_volumes[name.lower()] = 0.030
for name in all_data.get("mining_heads", {}):
    info = all_data["mining_heads"][name]
    size = info.get("Size", [0])
    s = size[0] if size else 1
    item_volumes[name.lower()] = max(0.05, s * 0.05)
for name in all_data.get("mining_modules", {}):
    info = all_data["mining_modules"][name]
    size = info.get("Size", [0])
    s = size[0] if size else 1
    item_volumes[name.lower()] = max(0.02, s * 0.02)

# Gadgets
for name in all_data.get("gadgets", {}):
    item_volumes[name.lower()] = 0.005

# Missiles/Torpedoes/Bombs — SCU by size
SIZE_SCU = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 7: 4, 9: 8, 10: 16, 12: 32}
for cat in ["missiles", "torpedoes", "bombs"]:
    for name, info in all_data.get(cat, {}).items():
        sizes = info.get("Size", [])
        s = sizes[0] if sizes else 1
        item_volumes[name.lower()] = SIZE_SCU.get(s, max(1, s))

# Countermeasures
for name in all_data.get("countermeasures", {}):
    item_volumes[name.lower()] = 1.0

# Ship ammunition
for i in range(1, 11):
    item_volumes[f"size {i} ammunition"] = 1.0

# Ship components — by size
COMP_SCU = {0: 0.5, 1: 1, 2: 2, 3: 4, 4: 8}
for cat in ["ship_weapons", "shields", "power_plants", "coolers", "quantum_drives",
            "missile_racks", "turrets", "radars",
            "ballistic_cannons", "ballistic_gatlings", "ballistic_repeaters",
            "laser_cannons", "laser_repeaters", "distortion_cannons", "scatterguns"]:
    for name, info in all_data.get(cat, {}).items():
        sizes = info.get("Size", [])
        s = sizes[0] if sizes else 1
        item_volumes[name.lower()] = COMP_SCU.get(s, max(1, s * 2))

# Commodities — always 1 SCU per unit
for name in all_data.get("commodities", {}):
    item_volumes[name.lower()] = 1.0

# ── Generic fallback patterns (for items not fetched) ──
patterns = {
    "magazine": 0.001,
    "battery": 0.002,
    "attachment": 0.005,
    "canister": 0.050,
    "container": 1.0,
    "ore": 1.0,
    "fuel": 1.0,
    "scrap": 1.0,
}
for pat, vol in patterns.items():
    item_volumes[pat] = vol

# ── Save ──
with open('resources/item_volumes.json', 'w', encoding='utf-8') as f:
    json.dump(item_volumes, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"item_volumes.json: {len(item_volumes)} entries")

# Category breakdown
cats_count = {"weapons": 0, "armor": 0, "medical": 0, "food": 0,
              "mining": 0, "tools": 0, "ordnance": 0, "ship_comp": 0,
              "commodity": 0, "clothing": 0, "other": 0}
for k, v in item_volumes.items():
    if any(w in k for w in ["rifle","pistol","shotgun","smg","lmg","sniper","knife","grenade","launcher","mine"]):
        cats_count["weapons"] += 1
    elif any(w in k for w in ["helmet","core","arms","legs","undersuit","backpack","armor"]):
        cats_count["armor"] += 1
    elif any(w in k for w in ["medpen","medkit","hemozal","adrena","cortico","decon","detox","opio","paramed"]):
        cats_count["medical"] += 1
    elif any(w in k for w in ["food","bar","drink","bottle","noodle","burrito","sandwich","ration","snack"]):
        cats_count["food"] += 1
    elif any(w in k for w in ["mining","gadget","waveshift","sabir","surge","brandt","optimum"]):
        cats_count["mining"] += 1
    elif any(w in k for w in ["multitool","tractor","extinguish","cambio","pyro"]):
        cats_count["tools"] += 1
    elif any(w in k for w in ["missile","torpedo","bomb","countermeasure","ammunition"]):
        cats_count["ordnance"] += 1
    elif any(w in k for w in ["shield","power plant","cooler","quantum","radar","cannon","repeater","gatling","turret","laser","distortion","scatter","rack"]):
        cats_count["ship_comp"] += 1
    elif any(w in k for w in ["jacket","shirt","pants","shoes","gloves","hat","coat","vest"]):
        cats_count["clothing"] += 1
    elif v >= 1.0:
        cats_count["commodity"] += 1
    else:
        cats_count["other"] += 1

for cat, n in sorted(cats_count.items(), key=lambda x:-x[1]):
    print(f"  {cat:15s}: {n:4d}")
