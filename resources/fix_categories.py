# -*- coding: utf-8 -*-
"""Fix miscategorized items in frequent_items.json.

Corrects items wrongly labeled as 'Commodities' that are actually
armor, clothing, helmets, undersuits, etc.
Also fixes units where possible.
"""
import json
import os

FREQ_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "frequent_items.json")

# Keywords that indicate armor/clothing items
ARMOR_NAME_KEYWORDS = [
    "helmet", "core", "arms", "legs", "backpack", "undersuit", "suit",
    "armor", "gloves", "glove", "visor", "gauntlets", "greaves", "chest",
    "aril", "adp", "orc-", "lynx", "macflex", "strata", "pab-",
    "morozov", "novikov", "pembroke", "stitcher", "paladin",
    "manticore", "geist", "chiron", "argus", "artimex", "aztalan",
    "bokto", "carrion", "clash", "monde", "wrecker", "arden",
    "gcd-army", "calva", "inquisitor", "overlord", "field recon",
    "omni-afs", "forceflex", "aves", "antium",
    "shirt", "goggles", "pumps", "pants", "jacket", "coat", "hat", "cap",
    "beanie", "boots", "shoes", "trousers", "dress", "vest", "beret",
    "sweater", "hoodie", "top", "scarf", "glasses", "mask", "eyewear",
    "belt", "harness", "holster"
]

WEAPON_NAME_KEYWORDS = [
    "rifle", "smg", "pistol", "shotgun", "sniper", "lmg", "cannon",
    "repeater", "gatling", "rangefinder", "scope", "attachment",
    "launcher", "railgun"
]

# Keywords that are NOT armor even if they match (ship components, etc.)
NOT_ARMOR_KEYWORDS = [
    "coolcore", "cooler", "power plant", "shield generator",
    "quantum drive", "radar", "size 1", "size 2", "size 3", "size 4",
    "cannon", "repeater", "gatling", "turret", "missile rack"
]

# Unit → correct category mapping
UNIT_CATEGORY_MAP = {
    "helmet": "Armor + Clothes",
    "core": "Armor + Clothes",
    "arms": "Armor + Clothes",
    "legs": "Armor + Clothes",
    "backpack": "Armor + Clothes",
    "undersuit": "Armor + Clothes",
    "suit": "Armor + Clothes",
    "armor": "Armor + Clothes",
    "gloves": "Armor + Clothes",
    "shirt": "Armor + Clothes",
    "pants": "Armor + Clothes",
    "jacket": "Armor + Clothes",
    "shoes": "Armor + Clothes",
    "hat": "Armor + Clothes",
}


def fix_categories():
    with open(FREQ_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    fixed_count = 0
    for item in items:
        name_low = item["name"].lower()
        cat = item.get("category", "")
        unit = item.get("unit", "")

        # Skip items that are correctly categorized
        if cat != "Commodities":
            continue

        # Skip ship components that happen to match armor keywords
        if any(k in name_low for k in NOT_ARMOR_KEYWORDS):
            continue

        # Check if item name or unit matches armor/weapon keywords
        is_armor = any(k in name_low for k in ARMOR_NAME_KEYWORDS)
        is_armor_unit = unit in UNIT_CATEGORY_MAP
        is_weapon = any(k in name_low for k in WEAPON_NAME_KEYWORDS)

        if is_armor or is_armor_unit:
            item["category"] = "Armor + Clothes"
            fixed_count += 1
        elif is_weapon:
            item["category"] = "weapons"
            fixed_count += 1

    # Save
    with open(FREQ_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    print(f"Fixed {fixed_count} miscategorized items in frequent_items.json")


if __name__ == "__main__":
    fix_categories()
