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
        vol_per = None
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

        if vol_per is None or vol_per <= 0:
            vol_per = 0.1  # Safe fallback default: 0.1 SCU per unit
            print(f"[VOL_FALLBACK_WARNING] Item '{name}' missing from item_volumes.json. Assigned default volume {vol_per} SCU.")

        total_item_vol = vol_per * qty

        # Categorize Category A / B
        grid_attach = False
        if any(kw in nm for kw in _ORDNANCE_KEYWORDS):
            category = "GRID_DIRECT"
            grid_attach = True
            ordnance_vol += total_item_vol
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
    commodity_items = []
    supply_items = []

    for b in blocks:
        entry = {
            "name": b["name"],
            "qty": b["qty"],
            "scu_per_unit": b["vol_per"],
            "total_scu": b["vol"],
        }
        if b["category"] == "GRID_DIRECT":
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
    (1.0,   "1 SCU",    1.00),
    (2.0,   "2 SCU",    2.00),
    (4.0,   "4 SCU",    4.00),
    (8.0,   "8 SCU",    8.00),
]

def _load_autoloader_rules():
    """Load autoloader rules from config.json["autoloader_rules"].

    Falls back to minimal built-in rules if config is unavailable.
    Each rule is a dict with:
        trigger        — substring to match (case-insensitive) in item name
        exclude        — list of substrings; if any present in name, skip rule
        adds           — list of {name, qty_multiplier, price} dicts
    """
    try:
        from path_config import PATHS
        import json as _json
        with open(PATHS.config, 'r', encoding='utf-8') as _f:
            _cfg = _json.load(_f)
        rules = _cfg.get('autoloader_rules', [])
        if isinstance(rules, list) and rules:
            return rules
    except Exception:
        pass

    # Built-in fallback (matches realistic 1:1 battery, 1:4 canister, 1:8 mag ratios)
    return [
        {"trigger": "p4-ar",       "exclude": ["magazine"],            "adds": [{"name": "P4-AR Magazine",          "qty_multiplier": 40, "price": 0}]},
        {"trigger": "s-38",        "exclude": ["magazine"],            "adds": [{"name": "S-38 Magazine",           "qty_multiplier": 10, "price": 0}]},
        {"trigger": "multitool",   "exclude": ["battery","attachment"],"adds": [{"name": "Cambio Multi-Tool Battery","qty_multiplier": 1, "price": 63},
                                                                                  {"name": "Tractor Beam Attachment",  "qty_multiplier": 1, "price": 0}]},
        {"trigger": "multi-tool",  "exclude": ["battery","attachment"],"adds": [{"name": "Cambio Multi-Tool Battery","qty_multiplier": 1, "price": 63},
                                                                                  {"name": "Tractor Beam Attachment",  "qty_multiplier": 1, "price": 0}]},
        {"trigger": "maxlift tractor beam","exclude": ["battery"],     "adds": [{"name": "Maxlift Tractor Beam Battery","qty_multiplier": 1,"price": 175}]},
        {"trigger": "cambio srt",  "exclude": ["canister", "battery"], "adds": [{"name": "Cambio Multi-tool Battery", "qty_multiplier": 1, "price": 63}, {"name": "Cambio SRT Canister", "qty_multiplier": 10, "price": 120}]},
        {"trigger": "paramed",     "exclude": ["refill"],              "adds": [{"name": "ParaMed Refill",          "qty_multiplier": 4,  "price": 0}]},
        {"trigger": "lifeguard",   "exclude": ["refill"],              "adds": [{"name": "LifeGuard Refill",        "qty_multiplier": 4,  "price": 0}]},
    ]


def _apply_autoloader(item_name, base_qty, autoloader_rules):
    """Apply matching autoloader rules to an item name.

    Returns a list of companion item dicts to append (may be empty).
    """
    extras = []
    name_lower = item_name.lower()
    for rule in autoloader_rules:
        trigger = rule.get('trigger', '').lower()
        if not trigger or trigger not in name_lower:
            continue
        exclude = [e.lower() for e in rule.get('exclude', [])]
        if any(ex in name_lower for ex in exclude):
            continue
        for add in rule.get('adds', []):
            companion_name = add.get('name', '')
            multiplier = int(add.get('qty_multiplier', 1))
            companion_price = add.get('price', 0)
            if companion_name:
                extras.append({
                    'name': companion_name,
                    'qty': str(base_qty * multiplier),
                    'box_size': 'Loose',
                    'price': str(companion_price),
                    'status': 'LOOSE',
                })
    return extras


def unpack_packages_and_autoload(name, qty, box_size, price, status):
    """Expand packages into individual items and apply universal autoloader rules.

    Autoloader rules are read dynamically from config.json["autoloader_rules"].
    Companion items already defined inside a package are not double-added.

    Returns a list of item dicts ready to pass to add_cargo_row_to_ui.
    """
    from src.ui.create_package import BUILT_IN_PACKAGES

    # Normalise qty
    try:
        qty = int(float(qty))
    except (ValueError, TypeError):
        qty = 1
    if qty <= 0:
        qty = 1

    # Load custom packages from packages.json
    import json as _json
    from path_config import PATHS
    custom_packages = {}
    pkg_file = os.path.join(PATHS.config_dir, 'packages.json')
    if os.path.exists(pkg_file):
        try:
            with open(pkg_file, 'r', encoding='utf-8') as f:
                custom_packages = _json.load(f)
        except Exception:
            pass

    all_packages = {**BUILT_IN_PACKAGES, **custom_packages}
    autoloader_rules = _load_autoloader_rules()
    unpacked_items = []

    if name in all_packages:
        # ── Package expansion ──
        pkg_items = all_packages[name]
        pkg_item_names = [it.get('name', '').lower().strip() for it in pkg_items]
        from src.ui.create_package import get_package_item_price
        for item in pkg_items:
            item_name = item.get('name', '')
            item_qty = int(item.get('qty', 1)) * qty
            item_price = item.get('price')
            if item_price is None or item_price == 0 or item_price == '0':
                item_price = get_package_item_price(item_name)
            unpacked_items.append({
                'name': item_name,
                'qty': str(item_qty),
                'box_size': 'Loose',
                'price': item_price,
                'status': 'LOOSE',
            })
            # Apply autoloader to each expanded item ONLY IF companion isn't already explicitly in the package
            extra_companions = _apply_autoloader(item_name, item_qty, autoloader_rules)
            for comp in extra_companions:
                if comp['name'].lower().strip() not in pkg_item_names:
                    c_price = comp.get('price')
                    if c_price is None or c_price == 0 or c_price == '0':
                        comp['price'] = get_package_item_price(comp['name'])
                    unpacked_items.append(comp)
    else:
        # ── Single item passthrough ──
        unpacked_items.append({
            'name': name,
            'qty': str(qty),
            'box_size': box_size,
            'price': price,
            'status': status,
        })
        # Apply autoloader to the single item
        unpacked_items.extend(_apply_autoloader(name, qty, autoloader_rules))

    return unpacked_items




def _pick_box_size(vol):
    """Pick the smallest Stor-All that fits ALL loose items in one box if possible."""
    for scu, label, cap in STOR_ALL_SIZES:
        if vol <= cap:
            return scu, label, cap
    return 8.0, "8 SCU", 8.00


def get_item_unit_volume(name, volume_map=None):
    """Retrieve exact unit SCU volume for an item name from volume_map."""
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

    # 3. Length-sorted key matching (longest matching key first)
    for k in sorted(volume_map.keys(), key=len, reverse=True):
        if len(k) >= 4 and k in name_low:
            return volume_map[k]

    return 0.005


def pack_items(items_list, volume_map=None, vessel=""):
    """Pack loose items into Stor-All boxes.

    Identifies items that match STOR_ALL_CATEGORIES (personal gear, food,
    tools) and packs them into optimally-sized Stor-All containers.

    Args:
        items_list: list of dicts with 'name', 'qty', 'box_size' keys
        volume_map: optional dict mapping item name -> SCU volume per unit
        vessel: vessel name (for capital ship 5-box breakdown)

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

    # Missiles, Torpedoes, and Bombs keywords that are grid-direct ordnance
    _GRID_DIRECT_ORDNANCE = [
        "missile", "torpedo", "bomb", "rocket", "warhead", "colossus", "stormburst",
        "pioneer i", "viper i", "spark i", "marksman", "tempest", "strikeforce",
        "ignite", "dominator", "arrester", "thunderbolt", "raptor", "stalker",
        "reaper", "argus", "typhoon"
    ]

    for item in items_list:
        name_low = item.get("name", "").lower()
        qty = item.get("qty", 1)
        if isinstance(qty, str):
            try:
                qty = int(qty)
            except ValueError:
                qty = 1

        # Skip grid-direct ordnance (Missiles, Torpedoes, Bombs) - they are transported directly on cargo grids
        if any(m in name_low for m in _GRID_DIRECT_ORDNANCE):
            continue

        # Only whitelist items need Stor-All
        is_stor_all = any(cat in name_low for cat in STOR_ALL_CATEGORIES)
        if not is_stor_all:
            continue

        # Skip items already in SCU boxes
        box = item.get("box_size", "").lower()
        if any(s in box for s in ["1 scu", "2 scu", "4 scu", "8 scu"]):
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
            "oversized": False,
        }

    # ── Capital Ship Multi-Box Logic ──
    v_low = str(vessel or "").lower()
    if "(" in v_low and ")" in v_low:
        v_low += " " + v_low[v_low.find("(")+1 : v_low.rfind(")")].strip()
    is_capital = any(c in v_low for c in ["idris", "polaris", "kraken", "javelin", "carrack", "890", "reclaimer", "hercules"])

    if is_capital:
        b_weapons, b_armor, b_tools, b_medfood, b_repair = [], [], [], [], []
        v_weapons, v_armor, v_tools, v_medfood, v_repair = 0.0, 0.0, 0.0, 0.0, 0.0

        weapon_kws = ["rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "magazine", "ammo", "grenade", "p4-ar", "fs-9", "s-38", "optic", "suppressor", "laser", "attachment", "repeater", "cannon", "ballistic"]
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
            "max_capacity": 2.00,
            "boxes": cap_boxes,
            "box_vols": cap_vols,
            "box_labels": box_labels,
            "total_loose_vol": total_loose_vol,
            "loose_items": loose_items,
        }

    # Determine box size and count
    if total_loose_vol > 0:
        box_scu, box_label, max_capacity = _pick_box_size(total_loose_vol)
        num_boxes = math.ceil(total_loose_vol / max_capacity)
        num_boxes = min(num_boxes, 3)  # Cap at 3 boxes
    else:
        return {
            "num_boxes": 0,
            "box_label": "1 SCU",
            "max_capacity": 1.00,
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
