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


def load_volume_map():
    """Lazy-load item volume database from resources/item_volumes.json.

    Returns dict mapping item name (lowercase) -> SCU volume per unit.
    Contains 2300+ items: weapons, armor, food, mining, ship components,
    missiles, torpedoes, commodities, etc.
    """
    global _volume_map_cache
    if _volume_map_cache is not None:
        return _volume_map_cache

    vol_path = PATHS.resource("item_volumes.json")
    if os.path.isfile(vol_path):
        try:
            with open(vol_path, "r", encoding="utf-8") as f:
                _volume_map_cache = json.load(f)
            return _volume_map_cache
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: minimal built-in map
    _volume_map_cache = {
        "rifle": 0.025, "pistol": 0.010, "smg": 0.015,
        "shotgun": 0.025, "sniper": 0.035, "lmg": 0.030,
        "knife": 0.003, "grenade": 0.001, "magazine": 0.001,
        "medpen": 0.001, "medkit": 0.008, "battery": 0.002,
        "helmet": 0.010, "undersuit": 0.005, "backpack": 0.015,
    }
    return _volume_map_cache


# ── Ordnance keywords (missiles, torpedoes, bombs) ──
_ORDNANCE_KEYWORDS = [
    "missile", "torpedo", "bomb", "ammunition", "countermeasure",
    "seeker", "colossus", "stormburst", "pioneer i", "viper i",
    "spark i", "marksman ii", "tempest ii", "strikeforce ii",
    "ignite ii", "dominator ii", "arrester iii", "thunderbolt iii",
    "raptor iv", "stalker iv", "reaper v", "argus ix", "typhoon ix",
]

# ── Commodity keywords (raw/refined ores, mining output) ──
_COMMODITY_KEYWORDS = [
    "rmc", "recycled material", "quantainium", "quantanium",
    "silicon", "iron", "copper", "titanium", "gold", "laranite",
    "agricium", "bexlite", "taranite", "ore", "scrap",
    "hydrogen fuel", "quantum fuel", "construction materials",
]


def calculate_cargo_breakdown(items_list, volume_map=None):
    """Calculate cargo breakdown by category.

    Replaces 3 duplicate calculations in the old entry.py.

    Args:
        items_list: list of dicts with 'name' and 'qty' keys
        volume_map: optional dict mapping item name -> SCU volume.
                    Auto-loads from item_volumes.json if None.

    Returns:
        dict with:
            commodity_vol: SCU of raw materials/ores
            supply_vol: SCU of general supplies/equipment
            ordnance_vol: SCU of missiles/torpedoes/bombs
            total_vol: sum of all three
            blocks: list of {'name', 'qty', 'vol', 'category'} dicts
    """
    if volume_map is None:
        volume_map = load_volume_map()

    commodity_vol = 0.0
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

        # Determine volume per unit — vol_override (from box_size) first, then map
        vol_per = 1.0  # Default: 1 SCU
        if "vol_override" in item and item["vol_override"] > 0:
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


        total_item_vol = vol_per * qty

        # Categorize
        if any(kw in nm for kw in _ORDNANCE_KEYWORDS):
            category = "ordnance"
            ordnance_vol += total_item_vol
        elif any(kw in nm for kw in _COMMODITY_KEYWORDS):
            category = "commodity"
            commodity_vol += total_item_vol
        else:
            category = "supply"
            supply_vol += total_item_vol

        blocks.append({
            "name": name,
            "qty": qty,
            "vol": total_item_vol,
            "vol_per": vol_per,
            "category": category,
        })

    # Build structured sub-lists for grid renderer
    ordnance_items = []
    commodity_items = []
    supply_items = []

    for b in blocks:
        entry = {
            "name": b["name"],
            "qty": b["qty"],
            "scu_per_unit": b["vol_per"],
            "total_scu": b["vol"],
        }
        if b["category"] == "ordnance":
            ordnance_items.append(entry)
        elif b["category"] == "commodity":
            commodity_items.append(entry)
        else:
            supply_items.append(entry)

    # Auto-pack supply items into Stor-All boxes
    packing = pack_items(items_list, volume_map)
    stor_all_boxes = []
    if packing and packing.get("num_boxes", 0) > 0:
        for i, (box_contents, box_vol) in enumerate(zip(packing["boxes"], packing["box_vols"])):
            if box_contents:
                stor_all_boxes.append({
                    "label": f"STOR-ALL #{i+1} [{packing['box_label']}]",
                    "scu": packing.get("max_capacity", 1.0),
                    "items": box_contents,
                    "used_vol": box_vol,
                })

    return {
        "commodity_vol": commodity_vol,
        "supply_vol": supply_vol,
        "ordnance_vol": ordnance_vol,
        "total_vol": commodity_vol + supply_vol + ordnance_vol,
        "blocks": blocks,
        "ordnance_items": ordnance_items,
        "commodity_items": commodity_items,
        "supply_items": supply_items,
        "stor_all_boxes": stor_all_boxes,
    }


# ── Stor-All Auto-Boxing ──

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
    (1.0,   "1 SCU",    0.85),
    (2.0,   "2 SCU",    1.70),
    (4.0,   "4 SCU",    3.40),
    (8.0,   "8 SCU",    6.80),
]


def _pick_box_size(vol):
    """Pick the smallest Stor-All that fits ALL loose items in one box if possible."""
    for scu, label, cap in STOR_ALL_SIZES:
        if vol <= cap:
            return scu, label, cap
    return 8.0, "8 SCU", 6.80


def pack_items(items_list, volume_map=None):
    """Pack loose items into Stor-All boxes.

    Identifies items that match STOR_ALL_CATEGORIES (personal gear, food,
    tools) and packs them into optimally-sized Stor-All containers.

    Args:
        items_list: list of dicts with 'name', 'qty', 'box_size' keys
        volume_map: optional dict mapping item name -> SCU volume per unit

    Returns:
        dict with:
            num_boxes: int
            box_label: str (e.g. '1 SCU')
            max_capacity: float (usable SCU per box)
            boxes: list of lists of {'name', 'qty', 'vol'} dicts
            box_vols: list of floats (used volume per box)
            total_loose_vol: float (total loose volume before packing)
            loose_items: list of loose item dicts
    """
    if volume_map is None:
        volume_map = load_volume_map()

    total_loose_vol = 0.0
    loose_items = []

    for item in items_list:
        name_low = item.get("name", "").lower()
        qty = item.get("qty", 1)
        if isinstance(qty, str):
            try:
                qty = int(qty)
            except ValueError:
                qty = 1

        # Only whitelist items need Stor-All
        is_stor_all = any(cat in name_low for cat in STOR_ALL_CATEGORIES)
        if not is_stor_all:
            continue

        # Skip items already in SCU boxes
        box = item.get("box_size", "").lower()
        if any(s in box for s in ["1 scu", "2 scu", "4 scu", "8 scu"]):
            continue

        # Calculate volume — exact match first, then longest word-boundary substring
        unit_vol = 0.0
        if name_low in volume_map:
            unit_vol = volume_map[name_low]
        else:
            import re
            best_key = ""
            for k, vol in volume_map.items():
                # Require word-boundary match to prevent 'ore' matching 'core'
                if len(k) <= 4 and vol >= 0.5:
                    # Short keys with large volume (commodities) - require word boundary
                    pattern = r'(?:^|[\s\-_])' + re.escape(k) + r'(?:$|[\s\-_])'
                    if re.search(pattern, name_low) and len(k) > len(best_key):
                        best_key = k
                        unit_vol = vol
                elif k in name_low and len(k) > len(best_key):
                    best_key = k
                    unit_vol = vol
        if unit_vol == 0.0:
            unit_vol = 0.005  # Default: 5 mSCU for small items

        item_vol = qty * unit_vol
        total_loose_vol += item_vol
        loose_items.append({
            "name": item.get("name", "?"),
            "qty": qty,
            "unit_vol": unit_vol,
            "total_vol": item_vol,
        })

    # Determine box size and count
    if total_loose_vol > 0:
        box_scu, box_label, max_capacity = _pick_box_size(total_loose_vol)
        num_boxes = math.ceil(total_loose_vol / max_capacity)
        num_boxes = min(num_boxes, 3)  # Cap at 3 boxes
    else:
        return {
            "num_boxes": 0,
            "box_label": "1 SCU",
            "max_capacity": 0.85,
            "boxes": [],
            "box_vols": [],
            "total_loose_vol": 0.0,
            "loose_items": [],
        }

    # Pack items into boxes (first-fit)
    boxes = [[] for _ in range(num_boxes)]
    box_vols = [0.0] * num_boxes
    curr_box_idx = 0

    for item in loose_items:
        qty_remaining = item["qty"]
        while qty_remaining > 0 and curr_box_idx < num_boxes:
            space_left = max_capacity - box_vols[curr_box_idx]
            max_fit = int(space_left // item["unit_vol"]) if item["unit_vol"] > 0 else qty_remaining
            if max_fit <= 0:
                curr_box_idx += 1
                continue

            fit_qty = min(qty_remaining, max_fit)
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
