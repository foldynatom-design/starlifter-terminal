# -*- coding: utf-8 -*-
"""
storall_packer.py - Stor-All auto-boxing logic + cargo breakdown.

Automatically packs loose items into Stor-All containers.
Categories whitelist, box size selection, manifest building.
Unified cargo volume breakdown (commodity/supply/ordnance).
Loads item volumes from resources/item_volumes.json (2300+ items).

Usage:
    from storall_packer import pack_items, calculate_cargo_breakdown
    from storall_packer import load_volume_map, STOR_ALL_CATEGORIES
"""

import math
import os
import json
from path_config import PATHS


# ── Lazy-loaded volume map ──
_volume_map_cache = None

def reload_volume_map():
    """Force reload item_volumes.json from disk into memory cache."""
    global _volume_map_cache
    _volume_map_cache = None
    return load_volume_map()

def load_volume_map():
    """Lazy-load item volume database from resources/cstone_volume_map.json and item_volumes.json."""
    global _volume_map_cache
    if _volume_map_cache is not None:
        return _volume_map_cache

    _volume_map_cache = {}
    
    # 1. Load legacy item_volumes.json
    vol_path = PATHS.resource("item_volumes.json")
    if os.path.isfile(vol_path):
        try:
            with open(vol_path, "r", encoding="utf-8") as f:
                _volume_map_cache.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Merge verified Cornerstone micro-SCU volume map
    cstone_vol_path = PATHS.resource("cstone_volume_map.json")
    if os.path.isfile(cstone_vol_path):
        try:
            with open(cstone_vol_path, "r", encoding="utf-8") as f:
                _volume_map_cache.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    if _volume_map_cache:
        return _volume_map_cache

    # Fallback: minimal built-in map
    _volume_map_cache = {
        "rifle": 0.025, "pistol": 0.010, "smg": 0.015,
        "shotgun": 0.025, "sniper": 0.035, "lmg": 0.030,
        "knife": 0.003, "grenade": 0.001, "magazine": 0.001,
        "medpen": 0.001, "medkit": 0.008, "battery": 0.002,
        "helmet": 0.010, "undersuit": 0.005, "backpack": 0.015,
    }
    return _volume_map_cache


# ── Ordnance keywords (missiles, torpedoes, bombs, ammo) ──
_ORDNANCE_KEYWORDS = [
    "missile", "torpedo", "bomb", "ammunition", "countermeasure",
    "seeker", "colossus", "stormburst", "pioneer i", "viper i",
    "spark i", "marksman ii", "tempest ii", "strikeforce ii",
    "ignite ii", "dominator ii", "arrester iii", "thunderbolt iii",
    "raptor iv", "stalker iv", "reaper v", "argus ix", "typhoon ix",
]

# ── Ship Weapon keywords ──
_SHIP_WEAPON_KEYWORDS = [
    "repeater", "cannon", "gatling", "distortion", "laser repeater", "laser cannon",
    "ballistic repeater", "ballistic cannon", "ballistic gatling", "scattergun",
    "cf-117", "cf-227", "cf-337", "cf-447", "cf-557", "panther", "badger", "rhino",
    "bulldog", "galdiseen", "omnisky", "tarantula", "mantis gt-220", "revenant",
    "deadbolt", "attrition", "quarreler", "broadsword", "fl-33", "mass driver",
]

# ── Ship Component & Fabricator keywords ──
_SHIP_COMPONENT_KEYWORDS = [
    "shield generator", "power plant", "cooler", "quantum drive", "jump drive",
    "fabricator", "salvage module", "tractor beam module", "fr-86", "fr-76", "fr-66",
    "js-400", "js-300", "atlas", "goliath", "siren", "crossfield", "voyage",
    "polaris cooler", "ts-2", "avalanche", "thermal flex", "glacier", "quadracell",
    "superluminal",
]

# ── Raw / Refined Ores & Precious Minerals ──
# NOTE: Use full keywords (min 5 chars) to prevent false positives.
# 'corundum' must NOT be shortened — 'cor' matches 'core' in armor names.
_ORE_KEYWORDS = [
    "quantainium", "quantanium", "bexlite", "taranite", "laranite", "agricium",
    "hephaestanite", "borase", "beryl", "tungsten", "corundum", "diamond",
    "quartz", "gold ore", "titanium ore", "copper ore", "iron ore", "aluminum ore", "tin ore",
    "hadanite", "dolivine", "aphirite", "janalite",
]

# ── Armor / clothing exclusion guard (checked BEFORE ore keywords) ──
_ARMOR_GUARD_KEYWORDS = [
    "helmet", "core", "arms", "legs", "backpack", "undersuit", "jacket",
    "vest", "pants", "shirt", "shoes", "gloves", "boots", "suit", "hat",
    "aril", "orc-mk", "adp-mk", "field recon", "morozov", "stitcher",
    "csp-68", "tcs-4", "adiva", "lemarque", "deo ", "prim ", "ventra",
]

# ── Commodity keywords (manufactured goods, scrap, fuel, medical supplies) ──
_COMMODITY_KEYWORDS = [
    "rmc", "recycled material", "scrap", "construction materials",
    "hydrogen fuel", "quantum fuel", "fuel", "medical supplies",
    "processed food", "distilled spirits", "stims", "waste",
    "compboard", "agricultural supplies",
]


def _parse_box_scu(box_size_str):
    """Parse box_size string like '8 SCU' -> 8, or None if not a boxed item."""
    if not box_size_str:
        return None
    bs = str(box_size_str).lower().strip()
    if "loose" in bs or "unit" in bs or not bs:
        return None
    import re
    m = re.match(r'(\d+)\s*scu', bs)
    if m:
        return int(m.group(1))
    return None


# ── SCU box grid shapes: maps box SCU size to W×H×L grid footprint ──
# Based on Star Citizen cargo grid system (sc-cargo.space)
_SCU_BOX_SHAPES = {
    1:  {"w": 1, "h": 1, "l": 1, "scu": 1},
    2:  {"w": 1, "h": 1, "l": 2, "scu": 2},
    4:  {"w": 2, "h": 1, "l": 2, "scu": 4},
    8:  {"w": 2, "h": 2, "l": 2, "scu": 8},
    16: {"w": 2, "h": 2, "l": 4, "scu": 16},
    24: {"w": 2, "h": 2, "l": 6, "scu": 24},
    32: {"w": 2, "h": 2, "l": 8, "scu": 32},
}


def calculate_cargo_breakdown(items_list, volume_map=None, vessel=None):
    """Calculate cargo breakdown by category and Stor-All allocations.

    Args:
        items_list: list of dicts with 'name', 'qty', and optionally 'box_size' keys
        volume_map: optional dict mapping item name -> SCU volume.
        vessel: optional vessel name for capital ship multi-box categorization & deck routing

    IMPORTANT: When box_size is 'X SCU', each unit is a physical X-SCU box on the
    cargo grid. The vol_per becomes X (not the loose-item volume from volume_map).
    Each box is rendered as a separate block with the correct grid shape (e.g. 2×2×2 for 8 SCU).
    """
    if volume_map is None:
        volume_map = load_volume_map()

    commodity_vol = 0.0
    ore_vol = 0.0
    ship_weapon_vol = 0.0
    ship_component_vol = 0.0
    supply_vol = 0.0
    ordnance_vol = 0.0
    blocks = []

    for item in items_list:
        name = item.get("name", "")
        nm = name.lower().strip()
        qty = item.get("qty", 1)
        if isinstance(qty, str):
            try:
                qty = int(qty)
            except ValueError:
                qty = 1

        # ── Check if this is a BOXED item (box_size = "X SCU") ──
        box_scu = _parse_box_scu(item.get("box_size", ""))

        if box_scu and box_scu > 0:
            # BOXED ITEM: each unit is a physical box of box_scu SCU
            vol_per = float(box_scu)
            total_item_vol = vol_per * qty
            grid_attach = True
            box_shape = _SCU_BOX_SHAPES.get(box_scu)

            # Categorize based on name
            if any(kw in nm for kw in _ORDNANCE_KEYWORDS):
                category = "GRID_DIRECT"
                ordnance_vol += total_item_vol
            elif any(kw in nm for kw in _SHIP_WEAPON_KEYWORDS):
                category = "SHIP_WEAPON"
                ship_weapon_vol += total_item_vol
            elif any(kw in nm for kw in _SHIP_COMPONENT_KEYWORDS):
                category = "SHIP_COMPONENT"
                ship_component_vol += total_item_vol
            elif any(kw in nm for kw in _COMMODITY_KEYWORDS):
                category = "commodity"
                commodity_vol += total_item_vol
            else:
                category = "commodity"  # Default for unknown boxed items
                commodity_vol += total_item_vol

            blocks.append({
                "name": name,
                "qty": qty,
                "vol": total_item_vol,
                "vol_per": vol_per,
                "category": category,
                "grid_attach": grid_attach,
                "box_scu": box_scu,
                "box_shape": box_shape,
            })
            continue

        # ── LOOSE ITEM: use volume_map lookup ──
        vol_per = None
        if any(m in nm for m in ["medpen", "hemozal", "oxypen", "adrenapen", "corticopen"]):
            vol_per = 0.001
        elif "vol_override" in item and item["vol_override"] > 0:
            vol_per = item["vol_override"]
        elif volume_map:
            # 1. Exact match
            if nm in volume_map:
                vol_per = volume_map[nm]
            else:
                # 2. Best substring match (longest key that matches)
                best_key = ""
                for vk, vv in volume_map.items():
                    if vk in nm and len(vk) > len(best_key):
                        best_key = vk
                        vol_per = vv

        if vol_per is None or vol_per <= 0:
            if any(k in nm for k in ["pants", "shirt", "shoes", "gloves", "jacket", "hat", "boots", "suit", "vest", "glove", "cap"]):
                vol_per = 0.005
            elif any(k in nm for k in ["rifle", "smg", "lmg", "pistol", "sniper", "shotgun", "beam"]):
                vol_per = 0.02
            else:
                vol_per = 0.1

        total_item_vol = vol_per * qty

        # Categorize loose items
        grid_attach = False
        # BUG #2 FIX: Check armor guard BEFORE ore keywords to prevent
        # 'core' in armor names matching 'corundum' substring
        is_armor_clothing = any(kw in nm for kw in _ARMOR_GUARD_KEYWORDS)

        if any(kw in nm for kw in _ORDNANCE_KEYWORDS):
            category = "GRID_DIRECT"
            grid_attach = True
            ordnance_vol += total_item_vol
        elif any(kw in nm for kw in _SHIP_WEAPON_KEYWORDS):
            category = "SHIP_WEAPON"
            grid_attach = True
            ship_weapon_vol += total_item_vol
        elif any(kw in nm for kw in _SHIP_COMPONENT_KEYWORDS):
            category = "SHIP_COMPONENT"
            grid_attach = True
            ship_component_vol += total_item_vol
        elif not is_armor_clothing and any(kw in nm for kw in _ORE_KEYWORDS):
            category = "ORE"
            ore_vol += total_item_vol
        elif any(kw in nm for kw in _COMMODITY_KEYWORDS):
            category = "commodity"
            commodity_vol += total_item_vol
        else:
            category = "CONTAINERIZED"
            supply_vol += total_item_vol

        blocks.append({
            "name": name,
            "qty": qty,
            "vol": total_item_vol,
            "vol_per": vol_per,
            "category": category,
            "grid_attach": grid_attach,
        })

    # Build structured sub-lists for grid renderer
    ordnance_items = []
    ship_weapon_items = []
    ship_component_items = []
    ore_items = []
    commodity_items = []
    supply_items = []

    for b in blocks:
        box_scu = b.get("box_scu")
        if box_scu:
            # BOXED items: each qty unit is a separate physical box
            entry = {
                "name": b["name"],
                "qty": b["qty"],
                "scu_per_unit": float(box_scu),
                "total_scu": b["vol"],
                "box_scu": box_scu,
                "box_shape": b.get("box_shape"),
            }
        else:
            entry = {
                "name": b["name"],
                "qty": b["qty"],
                "scu_per_unit": b["vol_per"],
                "total_scu": b["vol"],
            }

        if b["category"] == "GRID_DIRECT":
            ordnance_items.append(entry)
        elif b["category"] == "SHIP_WEAPON":
            ship_weapon_items.append(entry)
        elif b["category"] == "SHIP_COMPONENT":
            ship_component_items.append(entry)
        elif b["category"] == "ORE":
            ore_items.append(entry)
        elif b["category"] == "commodity":
            commodity_items.append(entry)
        else:
            supply_items.append(entry)

    # Auto-pack supply items into Stor-All boxes with vessel context
    packing = pack_items(items_list, volume_map, vessel=vessel)
    stor_all_boxes = []
    if packing and packing.get("num_boxes", 0) > 0:
        box_labels = packing.get("box_labels", [])
        for i, (box_contents, box_vol) in enumerate(zip(packing["boxes"], packing["box_vols"])):
            if box_contents:
                custom_label = box_labels[i] if i < len(box_labels) else packing.get('box_label', '1 SCU')
                stor_all_boxes.append({
                    "label": f"STOR-ALL #{i+1} [{custom_label}]",
                    "scu": packing.get("max_capacity", 1.0),
                    "items": box_contents,
                    "used_vol": box_vol,
                })

    return {
        "commodity_vol": commodity_vol,
        "ore_vol": ore_vol,
        "ship_weapon_vol": ship_weapon_vol,
        "ship_component_vol": ship_component_vol,
        "supply_vol": supply_vol,
        "ordnance_vol": ordnance_vol,
        "total_vol": commodity_vol + ore_vol + ship_weapon_vol + ship_component_vol + supply_vol + ordnance_vol,
        "blocks": blocks,
        "ordnance_items": ordnance_items,
        "ship_weapon_items": ship_weapon_items,
        "ship_component_items": ship_component_items,
        "ore_items": ore_items,
        "commodity_items": commodity_items,
        "supply_items": supply_items,
        "stor_all_boxes": stor_all_boxes,
    }


# ── Stor-All Auto-Boxing (Personal Gear, Tools, Food, Meds, Ammo Magazines) ──

STOR_ALL_CATEGORIES = [
    "pistol", "rifle", "shotgun", "smg", "lmg", "sniper", "knife", "weapon",
    "grenade", "multitool", "tractor", "battery",
    "food", "burrito", "sandwich", "noodle", "drink", "bottle", "bar ", "ration",
    "medpen", "medkit", "oxypen", "adrenapen",
    "mining gadget", "mining attachment", "mining head", "mining module",
    "armor", "helmet", "undersuit", "backpack", "chest", "core", "legs", "arms",
    "flightsuit", "jacket", "vest", "gloves", "suit",
    "canister", "fire extinguisher",
    "lux", "flare", "magazine", "optic", "suppressor", "flashlight", "laser pointer",
    "attachment",
]

# Available Stor-All sizes: (nominal SCU, label, usable capacity SCU)
# Only 1+ SCU sizes — sub-1-SCU items don't occupy grid slots
STOR_ALL_SIZES = [
    (1.0,   "1 SCU",    1.00),
    (2.0,   "2 SCU",    2.00),
    (4.0,   "4 SCU",    4.00),
    (8.0,   "8 SCU",    8.00),
]


def _pick_box_size(vol):
    """Pick the smallest Stor-All that fits ALL loose items in one box if possible."""
    for scu, label, cap in STOR_ALL_SIZES:
        if vol <= cap:
            return scu, label, cap
    return 8.0, "8 SCU", 8.00


def get_item_unit_volume(name, volume_map=None):
    """Retrieve exact unit SCU volume for an item name from volume_map.

    Uses exact matching first, explicit medical/ammo/utility category guards second,
    and length-sorted key matching third to prevent partial substring miscalculations
    (e.g., 'oza' inside 'hemozal' matching 1.0 SCU instead of 0.001 SCU).
    """
    if volume_map is None:
        volume_map = load_volume_map()
    
    name_low = str(name).lower().strip()

    # 1. Multi-tool / Tractor Beam & Canister Overrides
    if "cambio" in name_low and "canister" in name_low:
        return 0.005
    if "cambio" in name_low:
        return 0.015
    if "maxlift" in name_low and "battery" not in name_low:
        return 0.015
    if "pyro multi-tool" in name_low or "pyro multitool" in name_low:
        return 0.015

    # 2. Exact match from volume_map
    if name_low in volume_map:
        return volume_map[name_low]
    if "battery" in name_low:
        return 0.002
    if any(k in name_low for k in ["canister", "attachment"]):
        return 0.005

    # 5. Length-sorted key matching (longest matching key first)
    for k in sorted(volume_map.keys(), key=len, reverse=True):
        if len(k) >= 4 and k in name_low:
            return volume_map[k]

    return 0.005


def pack_items(items_list, volume_map=None, target_box_scu=None, vessel=None):
    """Pack a list of loose items into Stor-All boxes.

    Missiles, Torpedoes, and Bombs are loaded DIRECTLY on the cargo grid and
    are NEVER placed into Stor-All boxes.
    """
    if volume_map is None:
        volume_map = load_volume_map()

    loose_items = []
    total_loose_vol = 0.0

    # Missiles, Torpedoes, and Bombs keywords that are grid-direct ordnance
    _GRID_DIRECT_ORDNANCE = [
        "missile", "torpedo", "bomb", "rocket", "warhead", "colossus", "stormburst",
        "pioneer i", "viper i", "spark i", "marksman", "tempest", "strikeforce",
        "ignite", "dominator", "arrester", "thunderbolt", "raptor", "stalker",
        "reaper", "argus", "typhoon"
    ]

    for item in items_list:
        name_low = item.get("name", "").lower()
        qty = int(item.get("qty", 1))

        # Skip grid-direct ordnance (Missiles, Torpedoes, Bombs) - they are transported directly on cargo grids
        if any(m in name_low for m in _GRID_DIRECT_ORDNANCE):
            continue

        # Check whitelist categories
        is_whitelisted = any(cat in name_low for cat in STOR_ALL_CATEGORIES)
        if not is_whitelisted:
            continue

        # Skip Stor-All containers themselves
        if "stor" in name_low and ("all" in name_low or "storage" in name_low):
            continue

        # Skip items already in SCU boxes (except loose medical pens)
        box = item.get("box_size", "").lower()
        is_medpen = any(m in name_low for m in ["medpen", "hemozal", "oxypen", "adrenapen", "corticopen"])
        if not is_medpen and any(s in box for s in ["1 scu", "2 scu", "4 scu", "8 scu"]):
            continue

        unit_vol = get_item_unit_volume(item.get("name", ""), volume_map)
        item_vol = qty * unit_vol
        total_loose_vol += item_vol
        loose_items.append({
            "name": item.get("name", "?"),
            "qty": qty,
            "unit_vol": unit_vol,
            "total_vol": item_vol,
        })

    if total_loose_vol <= 0:
        return {
            "num_boxes": 0,
            "box_label": "1 SCU",
            "max_capacity": 1.00,
            "boxes": [],
            "box_vols": [],
            "total_loose_vol": 0.0,
            "loose_items": [],
        }

    # Check capital ship rule (IDRIS-M, IDRIS-P, IDRIS-K, Polaris, Kraken, Javelin, Liberator)
    v_low = str(vessel or "").lower().strip()
    is_capital = any(c in v_low for c in ["idris", "polaris", "kraken", "privateer", "javelin", "liberator"])

    if is_capital:
        # Dedicated 5-box category breakdown for capital ships
        b_weapons, b_armor, b_tools, b_medfood, b_repair = [], [], [], [], []
        v_weapons, v_armor, v_tools, v_medfood, v_repair = 0.0, 0.0, 0.0, 0.0, 0.0

        weapon_kws = ["rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "magazine", "ammo", "missile", "torpedo", "ordnance", "bomb", "rocket", "warhead", "grenade", "p4-ar", "fs-9", "s-38", "optic", "suppressor", "laser", "attachment", "repeater", "cannon", "ballistic", "raptor"]
        armor_kws = ["armor", "helmet", "undersuit", "backpack", "jacket", "vest", "pants", "gloves", "shoes", "suit", "core", "arms", "legs", "aril", "adp", "recon", "morozov", "stitcher"]
        tool_kws = ["multitool", "multi-tool", "tractor", "maxlift", "cambio", "battery", "canister", "srt", "gadget", "extinguisher", "head", "module"]
        medfood_kws = ["cruz", "lux", "food", "drink", "bottle", "ration", "burrito", "sandwich", "noodle", "medpen", "hemozal", "oxypen", "adrenapen", "corticopen", "medkit", "paramed"]
        repair_kws = ["repair", "fabricator", "r1", "spare", "salvage module", "scraper", "repair box"]

        for it in loose_items:
            n_low = it["name"].lower()
            if any(k in n_low for k in repair_kws):
                b_repair.append(it); v_repair += it["total_vol"]
            elif any(k in n_low for k in weapon_kws):
                b_weapons.append(it); v_weapons += it["total_vol"]
            elif any(k in n_low for k in armor_kws):
                b_armor.append(it); v_armor += it["total_vol"]
            elif any(k in n_low for k in tool_kws):
                b_tools.append(it); v_tools += it["total_vol"]
            else:
                b_medfood.append(it); v_medfood += it["total_vol"]

        cap_boxes, cap_vols, box_labels = [], [], []
        if b_weapons:
            cap_boxes.append(b_weapons); cap_vols.append(v_weapons); box_labels.append("WEAPONS & AMMUNITION")
        if b_armor:
            cap_boxes.append(b_armor); cap_vols.append(v_armor); box_labels.append("ARMOR & CLOTHING")
        if b_tools:
            cap_boxes.append(b_tools); cap_vols.append(v_tools); box_labels.append("TOOLS & UTILITY")
        if b_medfood:
            cap_boxes.append(b_medfood); cap_vols.append(v_medfood); box_labels.append("MEDICAL & CONSUMABLES")
        if b_repair or not cap_boxes:
            if not b_repair:
                b_repair.append({"name": "Repair Deck Spare Components & Gel", "qty": 1, "unit_vol": 0.1, "total_vol": 0.1})
                v_repair = 0.1
            cap_boxes.append(b_repair); cap_vols.append(v_repair); box_labels.append("REPAIR DECK 1 SCU BOX")

        return {
            "num_boxes": len(cap_boxes),
            "box_label": "CAPITAL MULTI-BOX",
            "max_capacity": 4.00,  # Capital ship Stor-All = 4 SCU box (2×1×2 grid)
            "boxes": cap_boxes,
            "box_vols": cap_vols,
            "box_labels": box_labels,
            "total_loose_vol": total_loose_vol,
            "loose_items": loose_items,
        }

    # Determine box size and count for non-capital ships
    box_scu, box_label, max_capacity = _pick_box_size(total_loose_vol)
    num_boxes = math.ceil(total_loose_vol / max_capacity)
    num_boxes = min(num_boxes, 3)  # Cap at 3 boxes

    # Pack items into boxes (first-fit)
    boxes = [[] for _ in range(num_boxes)]
    box_vols = [0.0] * num_boxes
    curr_box_idx = 0

    for item in loose_items:
        qty_remaining = item["qty"]
        while qty_remaining > 0 and curr_box_idx < num_boxes:
            space_left = max_capacity - box_vols[curr_box_idx]

            if space_left < item["unit_vol"]:
                curr_box_idx += 1
                continue

            max_fit = int(space_left // item["unit_vol"]) if item["unit_vol"] > 0 else qty_remaining
            fit_qty = min(qty_remaining, max_fit)

            if fit_qty <= 0:
                curr_box_idx += 1
                continue

            fit_vol = fit_qty * item["unit_vol"]
            boxes[curr_box_idx].append({
                "name": item["name"],
                "qty": fit_qty,
                "vol": fit_vol,
            })
            box_vols[curr_box_idx] += fit_vol
            qty_remaining -= fit_qty

            if box_vols[curr_box_idx] >= max_capacity:
                curr_box_idx += 1

    return {
        "num_boxes": num_boxes,
        "box_label": box_label,
        "max_capacity": max_capacity,
        "boxes": boxes,
        "box_vols": box_vols,
        "total_loose_vol": total_loose_vol,
        "loose_items": loose_items,
    }
