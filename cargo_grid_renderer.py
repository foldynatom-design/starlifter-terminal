# -*- coding: utf-8 -*-
"""
cargo_grid_renderer.py — Isometric 3D cargo grid visualization for PDF.

Loads ship grid data from ship_grids_db.json (SC-Cargo.space sourced),
performs fuzzy ship name matching, and renders isometric 3D cargo grids
with discrete cargo blocks (CMD/SUP/ORD/FREE) on the PDF.

Usage:
    from cargo_grid_renderer import load_ship_grid, render_full_grid_page
    from cargo_grid_renderer import render_grid_preview, render_cargo_directive

Data format (ship_grids_db.json):
    Each ship has groups (cargo bays), each group has grids (sub-volumes).
    Grid dimensions: width (x-axis), height (y-axis, stacking), length (z-axis).
    1 slot = 1 SCU.
"""

from path_config import PATHS

import os
import sys
import json
import math
from PIL import Image, ImageDraw, ImageFont

# ── Lazy-loaded ship grid database ──
_grid_db_cache = None

# ── Ship manufacturer prefixes for name cleaning ──
_MANUFACTURER_PREFIXES = [
    "Aegis", "Anvil", "Drake", "RSI", "Crusader", "MISC", "Origin",
    "Consolidated Outland", "Argo", "Mirai", "Gatac", "Esperia",
    "Aopoa", "Banu", "Tumbril", "Greycat", "Musashi",
]

# ── Category colors (R, G, B) for cargo types ──
COLORS = {
    "CMD":     (76, 175, 80),    # green   — commodities & manufactured cargo (RMC, Scrap, Fuel)
    "ORE":     (235, 165, 25),   # amber   — raw/refined ores & minerals (Quantainium, Gold, Laranite)
    "WPN":     (0, 180, 216),    # cyan    — ship weapons & turrets (CF-Series, Cannons, Gatlings)
    "CMP":     (156, 39, 176),   # purple  — ship components & fabricators (Shields, Coolers, QD)
    "MSL":     (255, 120, 20),   # orange  — missiles, torpedoes, bombs
    "AMM":     (220, 45, 45),    # crimson — naval ammunition & ballistic crates
    "BOX_ARM": (190, 60, 70),    # burgundy— Stor-All (Weapons & Ammo)
    "BOX_CLO": (45, 110, 185),   # steel bl— Stor-All (Armor & Clothing)
    "BOX_UTL": (240, 185, 30),   # gold    — Stor-All (Tools & Utility)
    "BOX_MED": (0, 180, 140),    # teal    — Stor-All (Medical & Consumables)
    "BOX_REP": (220, 105, 40),   # bronze  — Stor-All (Repair Deck Spares)
    "SUP":     (66, 133, 244),   # blue    — supply (General Stor-All)
    "ORD":     (255, 120, 20),   # fallback ordnance
    "FREE":    (158, 158, 158),  # grey    — empty space
}

# Darker shades for isometric right face
COLORS_DARK = {
    "CMD":     (56, 142, 60),
    "ORE":     (200, 135, 15),
    "WPN":     (0, 150, 199),
    "CMP":     (123, 31, 162),
    "MSL":     (220, 90, 10),
    "AMM":     (180, 30, 30),
    "BOX_ARM": (150, 40, 50),
    "BOX_CLO": (30, 85, 150),
    "BOX_UTL": (205, 150, 15),
    "BOX_MED": (0, 145, 110),
    "BOX_REP": (180, 80, 25),
    "SUP":     (48, 100, 200),
    "ORD":     (220, 90, 10),
    "FREE":    (117, 117, 117),
}

# Even darker for front face
COLORS_FRONT = {
    "CMD":     (46, 125, 50),
    "ORE":     (170, 110, 10),
    "WPN":     (3, 115, 160),
    "CMP":     (106, 27, 154),
    "MSL":     (190, 70, 5),
    "AMM":     (150, 20, 20),
    "BOX_ARM": (120, 25, 35),
    "BOX_CLO": (20, 65, 120),
    "BOX_UTL": (170, 120, 5),
    "BOX_MED": (0, 115, 85),
    "BOX_REP": (145, 60, 15),
    "SUP":     (40, 85, 170),
    "ORD":     (190, 70, 5),
    "FREE":    (97, 97, 97),
}

# ── Ordnance grid shapes: maps missile size class to WxHxL grid footprint & exact physical SCU ──
_ORDNANCE_GRID_SHAPES = {
    "S1":  {"w": 1, "h": 1, "l": 1, "scu": 1.0, "desc": "Size 1 Missile (~1.25m length, 1 SCU)"},
    "S2":  {"w": 1, "h": 1, "l": 1, "scu": 1.0, "desc": "Size 2 Missile (~1.75m length, 1 SCU)"},
    "S3":  {"w": 1, "h": 1, "l": 2, "scu": 2.0, "desc": "Size 3 Missile (~2.75m length, 2 SCU)"},
    "S4":  {"w": 1, "h": 1, "l": 2, "scu": 2.0, "desc": "Size 4 Missile (~3.50m length, 2 SCU)"},
    "S5":  {"w": 1, "h": 1, "l": 4, "scu": 4.0, "desc": "Size 5 Torpedo (~5.00m length, 4 SCU)"},
    "S7":  {"w": 1, "h": 2, "l": 4, "scu": 8.0, "desc": "Size 7 Torpedo (~7.50m length, 8 SCU)"},
    "S9":  {"w": 2, "h": 2, "l": 6, "scu": 24.0, "desc": "Size 9 Heavy Torpedo (~10.5m length, 24 SCU)"},
    "S10": {"w": 2, "h": 2, "l": 8, "scu": 32.0, "desc": "Size 10 MOAB Bomb / Capital Torpedo (~12-14m, 32 SCU)"},
    "S12": {"w": 2, "h": 2, "l": 8, "scu": 32.0, "desc": "Size 12 Capital Anti-Cap Torpedo (~14m, 32 SCU)"},
}

# ── Ship Weapon grid shapes: maps weapon size class to WxHxL grid footprint & exact physical SCU ──
_SHIP_WEAPON_GRID_SHAPES = {
    "S1":  {"w": 1, "h": 1, "l": 1, "scu": 1.0, "desc": "Size 1 Ship Weapon (~1.5m, 1 SCU)"},
    "S2":  {"w": 1, "h": 1, "l": 2, "scu": 2.0, "desc": "Size 2 Ship Weapon (~2.2m, 2 SCU)"},
    "S3":  {"w": 1, "h": 1, "l": 2, "scu": 2.0, "desc": "Size 3 Ship Weapon (~3.0m, 2 SCU)"},
    "S4":  {"w": 1, "h": 1, "l": 3, "scu": 3.0, "desc": "Size 4 Ship Weapon (~4.0m, 3 SCU)"},
    "S5":  {"w": 1, "h": 1, "l": 4, "scu": 4.0, "desc": "Size 5 Ship Weapon (~5.5m, 4 SCU)"},
    "S6":  {"w": 1, "h": 2, "l": 4, "scu": 8.0, "desc": "Size 6 Ship Weapon (~7.0m, 8 SCU)"},
    "S7":  {"w": 1, "h": 2, "l": 4, "scu": 8.0, "desc": "Size 7 Ship Weapon (~9.0m, 8 SCU)"},
    "S8":  {"w": 2, "h": 2, "l": 6, "scu": 24.0, "desc": "Size 8 Capital Cannon (~12m, 24 SCU)"},
}

# ── Ship Component & Fabricator grid shapes ──
_SHIP_COMPONENT_GRID_SHAPES = {
    "S1":  {"w": 1, "h": 1, "l": 1, "scu": 1.0, "desc": "Size 1 Small Component (1 SCU)"},
    "S2":  {"w": 1, "h": 1, "l": 2, "scu": 2.0, "desc": "Size 2 Medium Component (2 SCU)"},
    "S3":  {"w": 2, "h": 1, "l": 2, "scu": 4.0, "desc": "Size 3 Large Component (4 SCU)"},
    "S4":  {"w": 2, "h": 2, "l": 2, "scu": 8.0, "desc": "Size 4 Capital Component (8 SCU)"},
    "FAB": {"w": 2, "h": 1, "l": 2, "scu": 4.0, "desc": "Industrial Fabricator Module (4 SCU)"},
}

# ── Standard Cargo Container grid shapes (Star Citizen standard 32, 24, 16, 8, 4, 2, 1 SCU) ──
STANDARD_SCU_SHAPES = {
    32: [(2, 2, 8), (8, 2, 2)],  # podélně ||| nebo napříč ---- (výška vždy H=2)
    24: [(2, 2, 6), (6, 2, 2)],  # podélně ||| nebo napříč ---- (výška vždy H=2)
    16: [(2, 2, 4), (4, 2, 2)],  # podélně ||| nebo napříč ---- (výška vždy H=2)
    8:  [(2, 2, 2)],              # standardní krychle 2x2x2
    4:  [(2, 1, 2)],              # čtvercový půdorys 2x2 naležato (výška vždy H=1)
    2:  [(1, 1, 2), (2, 1, 1)],  # podélně ||| nebo napříč ---- (výška vždy H=1)
    1:  [(1, 1, 1)],
}

# Regex patterns to detect missile size class from item name
import re as _re
_SIZE_RE = _re.compile(
    r'(?:S|size\s*)(\d+)|'
    r'\b([IVX]+)\b.*?(?:missile|torpedo)',
    _re.IGNORECASE
)
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
          "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
          "XI": 11, "XII": 12}


def _get_ordnance_shape(name):
    """Detect missile/torpedo size class from name and return grid shape."""
    nm = name.upper().strip()

    for roman, arabic in sorted(_ROMAN.items(), key=lambda x: -x[1]):
        padded = f" {nm} "
        if (f" {roman} " in padded or
                f" {roman}-" in padded or
                nm.endswith(f" {roman}")):
            key = f"S{arabic}"
            if key in _ORDNANCE_GRID_SHAPES:
                return _ORDNANCE_GRID_SHAPES[key]

    if "BOMB" in nm:
        if "COLOSSUS" in nm:
            return _ORDNANCE_GRID_SHAPES["S10"]
        return _ORDNANCE_GRID_SHAPES["S3"]

    return None


def _get_ship_weapon_shape(name):
    """Detect ship weapon size class from name and return grid shape."""
    nm = name.upper().strip()
    for prefix, sz in [("CF-117", 1), ("CF-227", 2), ("CF-337", 3), ("CF-447", 4), ("CF-557", 5), ("AD4B", 4), ("AD5B", 5)]:
        if prefix in nm:
            return _SHIP_WEAPON_GRID_SHAPES[f"S{sz}"]
    if any(k in nm for k in ["RHINO", "SIZE 4", "S4"]):
        return _SHIP_WEAPON_GRID_SHAPES["S4"]
    if any(k in nm for k in ["PANTHER", "SIZE 3", "S3"]):
        return _SHIP_WEAPON_GRID_SHAPES["S3"]
    if any(k in nm for k in ["BADGER", "SIZE 2", "S2"]):
        return _SHIP_WEAPON_GRID_SHAPES["S2"]
    if any(k in nm for k in ["BULLDOG", "SIZE 1", "S1"]):
        return _SHIP_WEAPON_GRID_SHAPES["S1"]
    if any(k in nm for k in ["GALDISEEN", "SIZE 5", "S5"]):
        return _SHIP_WEAPON_GRID_SHAPES["S5"]
    return _SHIP_WEAPON_GRID_SHAPES["S2"]


def _get_ship_component_shape(name):
    """Detect ship component / fabricator size and return grid shape."""
    nm = name.upper().strip()
    if any(k in nm for k in ["FABRICATOR", "MODULE", "SALVAGE"]):
        return _SHIP_COMPONENT_GRID_SHAPES["FAB"]
    if any(k in nm for k in ["FR-86", "JS-400", "GOLIATH", "CAPITAL", "SIZE 4", "S4"]):
        return _SHIP_COMPONENT_GRID_SHAPES["S4"]
    if any(k in nm for k in ["FR-76", "JS-300", "SIREN", "CROSSFIELD", "LARGE", "SIZE 3", "S3"]):
        return _SHIP_COMPONENT_GRID_SHAPES["S3"]
    if any(k in nm for k in ["FR-66", "MEDIUM", "SIZE 2", "S2", "ATLAS", "VOYAGE"]):
        return _SHIP_COMPONENT_GRID_SHAPES["S2"]
    return _SHIP_COMPONENT_GRID_SHAPES["S1"]



def _load_grid_db():
    """Lazy-load ship grid database from ship_grids_db.json."""
    global _grid_db_cache
    if _grid_db_cache is not None:
        return _grid_db_cache

    db_path = PATHS.resource("ship_grids_db.json")
    if os.path.isfile(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                _grid_db_cache = json.load(f)
            return _grid_db_cache
        except (json.JSONDecodeError, OSError):
            pass

    _grid_db_cache = {}
    return _grid_db_cache


def _clean_vessel_name(vessel_name):
    """Strip manufacturer prefix from vessel name.

    'Aegis Idris' -> 'Idris', 'Drake Caterpillar' -> 'Caterpillar'
    """
    clean = vessel_name.strip()
    for prefix in _MANUFACTURER_PREFIXES:
        if clean.lower().startswith(prefix.lower()):
            rest = clean[len(prefix):].strip()
            if rest:
                return rest
    return clean


def load_ship_grid(vessel_name):
    """Load ship grid data by fuzzy-matching vessel name.

    Returns dict with 'capacity', 'groups' etc., or None if not found.
    Uses strict 4-tier model matching (ignores standalone manufacturer names).
    Automatically strips edition/variant suffixes to resolve to base hull.
    E.g. "Hammerhead Best in Show Edition" -> "Hammerhead" cargo grid.
    """
    db = _load_grid_db()
    if not db or not vessel_name:
        return None

    import re

    # ── Edition/Variant Suffix Stripping ──
    # Strip common edition/variant suffixes to extract the base hull name.
    # Examples:
    #   "Hammerhead Best in Show Edition" -> "Hammerhead"
    #   "Caterpillar Pirate Edition" -> "Caterpillar"
    #   "Avenger Titan Renegade" -> "Avenger Titan Renegade" (valid variant, kept)
    #   "600i Explorer IAE 2953 Edition" -> "600i Explorer"
    _EDITION_SUFFIXES = [
        r'\s+best\s+in\s+show\s+edition\b',
        r'\s+best\s+in\s+show\b',
        r'\s+bis\s+edition\b',
        r'\s+citizencon\s+\d{4}\s+edition\b',
        r'\s+citizencon\s+edition\b',
        r'\s+iae\s+\d{4}\s+edition\b',
        r'\s+iae\s+edition\b',
        r'\s+invictus\s+\d{4}\s+edition\b',
        r'\s+invictus\s+edition\b',
        r'\s+pirate\s+edition\b',
        r'\s+vindicator\s+edition\b',
        r'\s+foundation\s+festival\s+edition\b',
        r'\s+subscribers?\s+edition\b',
        r'\s+special\s+edition\b',
        r'\s+limited\s+edition\b',
        r'\s+anniversary\s+edition\b',
        r'\s+showdown\s+edition\b',
        r'\s+day1\s+edition\b',
        r'\s+2\s*nd\s+anniversary\s+edition\b',
        r'\s+\d{4}\s+edition\b',
        r'\s+edition\b',
    ]

    def _strip_edition(name):
        """Strip edition/variant suffixes from a vessel name."""
        stripped = name
        for pat in _EDITION_SUFFIXES:
            stripped = re.sub(pat, '', stripped, flags=re.IGNORECASE)
        return stripped.strip()

    base_hull_name = _strip_edition(vessel_name)

    inside_parens = re.findall(r'\((.*?)\)', vessel_name)
    model_inside = inside_parens[0].strip() if inside_parens else ""

    vessel_names_to_try = []
    if model_inside:
        stripped_model = _strip_edition(model_inside)
        vessel_names_to_try.append(stripped_model)
        vessel_names_to_try.append(_clean_vessel_name(stripped_model))
        if model_inside.lower() != stripped_model.lower():
            vessel_names_to_try.append(model_inside)

    # Stripped base hull name FIRST (highest priority for edition variants)
    if base_hull_name and base_hull_name.lower() != vessel_name.lower():
        vessel_names_to_try.append(base_hull_name)
        vessel_names_to_try.append(_clean_vessel_name(base_hull_name))

    vessel_names_to_try.append(vessel_name)

    no_parens = re.sub(r'\(.*?\)', '', vessel_name).strip()
    if no_parens and no_parens != vessel_name:
        stripped_no_parens = _strip_edition(no_parens)
        if stripped_no_parens and stripped_no_parens.lower() != no_parens.lower():
            vessel_names_to_try.append(stripped_no_parens)
            vessel_names_to_try.append(_clean_vessel_name(stripped_no_parens))
        vessel_names_to_try.append(no_parens)
        vessel_names_to_try.append(_clean_vessel_name(no_parens))

    _MANUFACTURERS_SET = {
        "aegis", "anvil", "drake", "rsi", "crusader", "misc", "origin",
        "consolidated outland", "argo", "mirai", "gatac", "esperia",
        "aopoa", "banu", "tumbril", "greycat", "musashi", "drake interplanetary",
        "roberts space industries", "musashi industrial", "crusader industries",
        "aegis dynamics", "anvil aerospace"
    }

    for vname in vessel_names_to_try:
        vessel_low = vname.lower().strip()
        vessel_clean_low = _clean_vessel_name(vname).lower().strip()

        # Strategy 1: Exact match on dictionary key or ship name/short_name
        for key, val in db.items():
            kl = key.lower()
            sname = (val.get("name") or "").lower()
            s_short = (val.get("short_name") or "").lower()
            if vessel_low == kl or vessel_clean_low == kl or vessel_low == sname or vessel_clean_low == s_short:
                return val

        # Strategy 2: Model name substring match (e.g. "ironclad" or "c2 hercules")
        raw_words = [w for w in vessel_clean_low.split() if w not in _MANUFACTURERS_SET and len(w) > 1]
        if not raw_words:
            raw_words = [w for w in vessel_low.split() if w not in _MANUFACTURERS_SET and len(w) > 1]
        if not raw_words:
            raw_words = vessel_clean_low.split()

        target_model = " ".join(raw_words)
        if target_model:
            for key, val in db.items():
                kl = key.lower()
                sname = (val.get("name") or "").lower()
                s_short = (val.get("short_name") or "").lower()
                if target_model == s_short or target_model == sname or target_model in kl or target_model in sname:
                    return val

        # Strategy 3: All model words match (e.g. "ironclad" and "assault")
        if raw_words:
            for key, val in db.items():
                kl = key.lower()
                if all(w in kl for w in raw_words):
                    return val

        # Strategy 4: Fallback single model word match (EXCLUDING generic manufacturer words)
        if raw_words:
            for key, val in db.items():
                kl = key.lower()
                if any(w in kl for w in raw_words):
                    return val

    return None


def _compute_grid_dimensions(ship_grid):
    """Compute total bounding box and per-group stats from grid data.

    Returns dict with:
        total_width, total_height, total_length,
        groups: [{grids, width, height, length, slots, offset_x, offset_z}]
    """
    groups_info = []
    for g in ship_grid.get("groups", []):
        gx = int(g.get("x", 0))
        gz = int(g.get("z", 0))
        grids = g.get("grids", [])

        # Compute bounding box for this group
        max_x = 0
        max_y = 0
        max_z = 0
        total_slots = 0
        for gr in grids:
            x = int(gr.get("x", 0))
            y = int(gr.get("y", 0))
            z = int(gr.get("z", 0))
            w = int(gr.get("width", 1))
            h = int(gr.get("height", 1))
            l = int(gr.get("length", 1))
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
            max_z = max(max_z, z + l)
            total_slots += w * h * l

        g_name = g.get("name", g.get("group_name", f"Bay {len(groups_info)+1}"))
        groups_info.append({
            "name": g_name,
            "group_name": g_name,
            "grids": grids,
            "width": max_x,
            "height": max_y,
            "length": max_z,
            "slots": total_slots,
            "offset_x": gx,
            "offset_z": gz,
        })

    return groups_info


def _build_slot_map(group_info):
    """Build 3D occupancy map for a group.

    Returns dict {(x,y,z): True} for all valid slots.
    """
    slot_map = {}
    for gr in group_info["grids"]:
        ox = int(gr.get("x", 0))
        oy = int(gr.get("y", 0))
        oz = int(gr.get("z", 0))
        for x in range(int(gr.get("width", 1))):
            for y in range(int(gr.get("height", 1))):
                for z in range(int(gr.get("length", 1))):
                    slot_map[(ox + x, oy + y, oz + z)] = True
    return slot_map


def _assign_blocks_to_slots(groups_info, breakdown, vessel_name=None):
    """Assign cargo blocks to grid slots using greedy bin-packing.

    Idris rules:
      - Light Deck / Hangar 1: RMC, Hydrogen Fuel, Quantum Fuel, Ordnance (missiles/torpedoes/bombs), Repair Box 1 SCU.
      - Cargo Deck / Main Hangar: Weapons, Armor, Tools, Medical Stor-All boxes and general cargo.

    Returns list of block assignments per group:
    [{slots: [(x,y,z)...], label, category, scu}]
    """
    # Collect all blocks to place
    blocks = []

    # Category priority: MSL first (cluster together), then AMM, WPN, CMP, ORE, CMD, SUP
    _CAT_PRIORITY = {"MSL": 0, "AMM": 1, "ORD": 1, "WPN": 2, "CMP": 3, "ORE": 4, "CMD": 5, "SUP": 6}

    # Ordnance: each unit is a separate block with proper grid shape
    for item in breakdown.get("ordnance_items", []):
        scu = item.get("scu_per_unit", 1)
        name = item.get("name", "ORDNANCE")
        box_scu = item.get("box_scu")
        box_shape = item.get("box_shape")
        shape = box_shape or _get_ordnance_shape(name)
        n_low = name.lower()
        is_ammo = any(k in n_low for k in ["ammo", "ammunition", "magazine", "battery", "countermeasure"])
        category = "AMM" if is_ammo else "MSL"
        
        if box_scu:
            # BOXED ordnance: each qty unit is a separate physical box
            for i in range(item.get("qty", 1)):
                blk = {
                    "label": f"{name.upper()} #{i+1}",
                    "category": category,
                    "scu": box_scu,
                }
                if shape:
                    blk["shape"] = shape
                blocks.append(blk)
        else:
            # Loose ordnance: EVERY missile/bomb/torpedo is an indivisible physical item
            # with its exact physical grid shape. Never decompose into generic crates.
            tot_units = int(item.get("qty", 1))
            unit_scu = max(int(shape["scu"]) if shape else max(int(scu), 1), 1)
            for i in range(tot_units):
                blk = {
                    "label": f"{name.upper()} #{i+1}",
                    "category": category,
                    "scu": unit_scu,
                }
                if shape:
                    blk["shape"] = shape
                blocks.append(blk)

    # Ship Weapons: each weapon is placed with proper physical grid shape
    for item in breakdown.get("ship_weapon_items", []):
        scu = item.get("scu_per_unit", 1)
        name = item.get("name", "SHIP WEAPON")
        box_scu = item.get("box_scu")
        box_shape = item.get("box_shape")
        shape = box_shape or _get_ship_weapon_shape(name)
        for i in range(item.get("qty", 1)):
            blk = {
                "label": f"{name.upper()} #{i+1}",
                "category": "WPN",
                "scu": box_scu or max(shape.get("scu", scu) if shape else scu, 1),
            }
            if shape:
                blk["shape"] = shape
            blocks.append(blk)

    # Ship Components & Fabricators
    for item in breakdown.get("ship_component_items", []):
        scu = item.get("scu_per_unit", 1)
        name = item.get("name", "SHIP COMPONENT")
        box_scu = item.get("box_scu")
        box_shape = item.get("box_shape")
        shape = box_shape or _get_ship_component_shape(name)
        for i in range(item.get("qty", 1)):
            blk = {
                "label": f"{name.upper()} #{i+1}",
                "category": "CMP",
                "scu": box_scu or max(shape.get("scu", scu) if shape else scu, 1),
            }
            if shape:
                blk["shape"] = shape
            blocks.append(blk)

    # Raw / Refined Ores & Precious Minerals
    for item in breakdown.get("ore_items", []):
        name = item.get("name", "ORE")
        box_scu = item.get("box_scu")
        box_shape = item.get("box_shape")
        if box_scu:
            for i in range(item.get("qty", 1)):
                blk = {
                    "label": f"{name.upper()} #{i+1}",
                    "category": "ORE",
                    "scu": box_scu,
                }
                if box_shape:
                    blk["shape"] = box_shape
                blocks.append(blk)
        else:
            scu_val = int(item.get("total_scu", item.get("qty", 1)))
            rem_scu = max(scu_val, 1)
            for c_size in [32, 24, 16, 8, 4, 2, 1]:
                while rem_scu >= c_size:
                    blocks.append({
                        "label": f"{name.upper()} ({c_size} SCU)",
                        "category": "ORE",
                        "scu": c_size,
                    })
                    rem_scu -= c_size

    # Commodities: auto-decompose loose items into standard Star Citizen containers (sc-cargo.space style)
    for item in breakdown.get("commodity_items", []):
        name = item.get("name", "COMMODITY")
        box_scu = item.get("box_scu")
        box_shape = item.get("box_shape")
        if box_scu:
            for i in range(item.get("qty", 1)):
                blk = {
                    "label": f"{name.upper()} #{i+1}",
                    "category": "CMD",
                    "scu": box_scu,
                }
                if box_shape:
                    blk["shape"] = box_shape
                blocks.append(blk)
        else:
            scu_val = int(item.get("total_scu", item.get("qty", 1)))
            rem_scu = max(scu_val, 1)
            for c_size in [32, 24, 16, 8, 4, 2, 1]:
                while rem_scu >= c_size:
                    blocks.append({
                        "label": f"{name.upper()} ({c_size} SCU)",
                        "category": "CMD",
                        "scu": c_size,
                    })
                    rem_scu -= c_size


    # Stor-All boxes with category-specific subdivision
    for box in breakdown.get("stor_all_boxes", []):
        lbl = str(box.get("label", "STOR-ALL")).upper()
        if "WEAPON" in lbl or "ARMORY" in lbl:
            b_cat = "BOX_ARM"
        elif "ARMOR" in lbl or "CLOTH" in lbl:
            b_cat = "BOX_CLO"
        elif "TOOL" in lbl or "UTIL" in lbl:
            b_cat = "BOX_UTL"
        elif "MED" in lbl or "CONSUM" in lbl:
            b_cat = "BOX_MED"
        elif "REPAIR" in lbl:
            b_cat = "BOX_REP"
        else:
            b_cat = "SUP"

        blocks.append({
            "label": box.get("label", "STOR-ALL"),
            "category": b_cat,
            "scu": max(box.get("scu", 1), 1),
        })

    # Sort by category priority, then group identical items together (base name), then SCU descending
    def _base_label(lbl):
        """Strip trailing ' #N' numbering to cluster identical items together."""
        s = str(lbl)
        idx = s.rfind(" #")
        return s[:idx].strip() if idx > 0 else s.strip()

    blocks.sort(key=lambda b: (_CAT_PRIORITY.get(b["category"], 9), _base_label(b["label"]), -b["scu"]))

    # Check Idris vessel deck assignment rule
    v_low = str(vessel_name or "").lower()
    if "(" in v_low and ")" in v_low:
        v_low += " " + v_low[v_low.find("(")+1 : v_low.rfind(")")].strip()
    is_idris = "idris" in v_low

    def is_idris_light_deck_block(blk):
        lbl = str(blk.get("label", "")).lower()
        cat = blk.get("category", "")
        if cat in ("BOX_REP", "MSL", "AMM", "ORD"):
            return True
        if any(k in lbl for k in ["repair", "rmc", "recycled material", "hydrogen fuel", "quantum fuel", "fuel"]):
            return True
        if cat == "CMD" and any(k in lbl for k in ["fuel", "rmc", "recycled", "hydrogen", "quantum"]):
            return True
        return False

    # Assign blocks to groups
    all_assignments = []
    remaining_blocks = list(blocks)

    for gi, ginfo in enumerate(groups_info):
        gname = str(ginfo.get("group_name", ginfo.get("name", ""))).lower()
        is_light_group = (is_idris and gi == 0) or any(k in gname for k in ["light", "hangar 1", "h1", "flight"])
        is_deck2_group = (is_idris and gi == 1) or any(k in gname for k in ["deck 2", "hangar 2", "h2", "cargo deck", "upper"])

        slot_map = _build_slot_map(ginfo)
        occupied = set()
        group_assignments = []

        for block in remaining_blocks[:]:
            if is_idris:
                wants_light = is_idris_light_deck_block(block)
                if is_light_group and not wants_light:
                    continue  # Hangar 1 reserved strictly for Repair Box, RMC, Fuel, Ordnance
                if is_deck2_group and wants_light and any(b for b in remaining_blocks if not is_idris_light_deck_block(b)):
                    continue  # Deck 2 prioritizes Fabricator, Med boxes, Armor, Tools, General Cargo

            needed = int(block["scu"])
            if needed <= 0:
                needed = 1

            explicit_shape = block.get("shape")
            placed_slots = []

            # Candidate shapes to try (explicit shape or standard SCU shapes)
            if explicit_shape:
                candidate_shapes = [(explicit_shape["w"], explicit_shape["h"], explicit_shape["l"])]
            elif needed in STANDARD_SCU_SHAPES:
                candidate_shapes = STANDARD_SCU_SHAPES[needed]
            else:
                candidate_shapes = [(1, 1, needed)]

            for sw, sh, sl in candidate_shapes:
                if sw > ginfo["width"] or sh > ginfo["height"] or sl > ginfo["length"]:
                    continue

                if is_idris and is_light_group:
                    # On Idris flight deck: large boxes prefer wall slots first, then fill linearly
                    if needed >= 8:
                        sx_cands = [0]
                        rw = ginfo["width"] - sw
                        if rw > 0 and rw not in sx_cands:
                            sx_cands.append(rw)
                        # Fill remaining positions linearly
                        for x_fill in range(ginfo["width"] - sw + 1):
                            if x_fill not in sx_cands:
                                sx_cands.append(x_fill)
                    else:
                        # Small items: sequential left-to-right for contiguous clustering
                        sx_cands = list(range(ginfo["width"] - sw + 1))
                else:
                    sx_cands = list(range(ginfo["width"] - sw + 1))

                placed = False
                for sy in range(ginfo["height"] - sh + 1):
                    for sz in range(ginfo["length"] - sl + 1):
                        for sx in sx_cands:
                            if sx + sw > ginfo["width"]:
                                continue
                            candidates = []
                            valid = True
                            for dy in range(sh):
                                for dz in range(sl):
                                    for dx in range(sw):
                                        pos = (sx + dx, sy + dy, sz + dz)
                                        if pos not in slot_map or pos in occupied:
                                            valid = False
                                            break
                                        candidates.append(pos)
                                    if not valid:
                                        break
                                if not valid:
                                    break
                            if valid and len(candidates) == needed:
                                placed_slots = candidates
                                placed = True
                                break
                        if placed:
                            break
                    if placed:
                        break
                if placed:
                    break

            if not placed_slots:
                # Fallback: greedy slot grab
                # SUP items prefer upper Y (upper storage), others bottom-up
                if block["category"] == "SUP":
                    y_range = range(ginfo["height"] - 1, -1, -1)  # top-down
                else:
                    y_range = range(ginfo["height"])  # bottom-up
                for y in y_range:
                    for z in range(ginfo["length"]):
                        for x in range(ginfo["width"]):
                            pos = (x, y, z)
                            if pos in slot_map and pos not in occupied:
                                placed_slots.append(pos)
                                if len(placed_slots) >= needed:
                                    break
                        if len(placed_slots) >= needed:
                            break
                    if len(placed_slots) >= needed:
                        break

            if len(placed_slots) >= needed:
                for s in placed_slots[:needed]:
                    occupied.add(s)
                group_assignments.append({
                    "slots": placed_slots[:needed],
                    "label": block["label"],
                    "category": block["category"],
                    "scu": block["scu"],
                })
                remaining_blocks.remove(block)

        # FREE slots: remaining unoccupied slots → pack as largest possible blocks
        free_slots = [s for s in slot_map if s not in occupied]
        free_scu = len(free_slots)
        if free_scu > 0:
            # Greedy: break into largest possible blocks
            free_remaining = free_scu
            for box_size in [32, 16, 8, 4, 2, 1]:
                while free_remaining >= box_size:
                    # Grab slots
                    take = min(box_size, len(free_slots))
                    if take > 0:
                        group_assignments.append({
                            "slots": free_slots[:take],
                            "label": f"FREE {take} SCU",
                            "category": "FREE",
                            "scu": take,
                        })
                        free_slots = free_slots[take:]
                        free_remaining -= take

        all_assignments.append(group_assignments)

    return all_assignments


# ── Isometric projection helpers ──

def _iso_x(x, z, cell_w):
    """Convert grid (x, z) to isometric screen X."""
    return (x - z) * cell_w * 0.5

def _iso_y(x, z, y, cell_w, cell_h):
    """Convert grid (x, z, y) to isometric screen Y."""
    return (x + z) * cell_w * 0.25 - y * cell_h


def render_grid_preview(pdf, ship_grid, area_x, area_y, area_w, area_h, security_level="CLASSIFIED"):
    """Render mini cargo grid preview box on Page 1 of PDF.

    Shows capacity, section count, and 'SEE PAGE 3' reference.
    For PUBLIC security, shows [REDACTED].
    """
    sec = security_level.upper()

    # Draw preview box
    pdf.set_line_width(0.15)
    pdf.set_draw_color(180, 190, 200)
    pdf.set_fill_color(235, 238, 242)
    pdf.rect(area_x, area_y, area_w, area_h, 'DF')

    if "PUBLIC" in sec or "OPEN" in sec:
        pdf.set_font("Roboto", "B", 6)
        pdf.set_text_color(140, 100, 30)
        pdf.text(area_x + 2, area_y + 4, "CARGO [REDACTED]")
    elif ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", "?")
        grps = len(ship_grid.get("groups", []))
        pdf.set_font("Roboto", "B", 6)
        pdf.set_text_color(140, 100, 30)
        pdf.text(area_x + 2, area_y + 4, "CARGO GRID")
        pdf.set_font("Roboto", "", 5.5)
        pdf.set_text_color(60, 70, 90)
        sfx = "s" if grps > 1 else ""
        pdf.text(area_x + 4, area_y + 10, f"{cap} SCU / {grps} section{sfx}")
        pdf.set_font("Roboto", "I", 5)
        pdf.set_text_color(100, 110, 140)
        pdf.text(area_x + 4, area_y + 16, "SEE PAGE 3")
        pdf.text(area_x + 4, area_y + 20, "FULL SCHEMATIC")
    else:
        pdf.set_font("Roboto", "I", 6.5)
        pdf.set_text_color(80, 90, 110)
        pdf.text(area_x + 4, area_y + 12, "NO GRID DATA")


def render_cargo_directive(ship_grid, vessel_name, location="", loading_type=""):
    """Generate cargo directive text string.

    Returns formatted directive like:
    'CARGO DIRECTIVE: 5 hold sections (576 SCU). Stack: 4h, 24 SCU max. ...'
    """
    loc_sfx = f" Staging: {location}." if location else ""
    type_sfx = f" Method: {loading_type}." if loading_type else ""

    if ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", 0)
        groups = ship_grid.get("groups", [])
        grp_count = len(groups)
        max_height = 1
        max_floor = 1
        for g in groups:
            for gr in g.get("grids", []):
                max_height = max(max_height, gr.get("height", 1))
                w = gr.get("width", 1)
                l = gr.get("length", 1)
                max_floor = max(max_floor, w * l)
        max_crate = min(32, max_floor)
        holds = f"{grp_count} hold section{'s' if grp_count > 1 else ''}"
        return f"CARGO DIRECTIVE: {holds} ({cap} SCU). Stack: {max_height}h, {max_crate} SCU max.{loc_sfx}{type_sfx} Clamps locked."
    else:
        return f"CARGO DIRECTIVE: Standard bay. Grid-lock all.{loc_sfx}{type_sfx} Verify clamp power."


def render_full_grid_page(pdf, ship_grid, breakdown, vessel_name,
                          security_level="CLASSIFIED", page_width=210, page_height=297):
    """Render full cargo grid visualization as a new LANDSCAPE PDF page."""
    sec = security_level.upper()

    # Add LANDSCAPE page (A4: 297mm wide x 210mm tall)
    pdf.add_page(orientation="L")
    lw = 297  # landscape width
    lh = 210  # landscape height
    # main.pyc header occupies ~45mm at top of every page
    header_h = 48

    if "PUBLIC" in sec or "OPEN" in sec:
        # Dark military header background box
        pdf.set_fill_color(25, 35, 56)
        pdf.rect(14, header_h + 10, 269, 120, 'F')
        pdf.set_draw_color(212, 175, 55)
        pdf.set_line_width(0.8)
        pdf.rect(14, header_h + 10, 269, 120, 'D')

        # Redacted classification text
        pdf.set_text_color(212, 175, 55)
        try: pdf.set_font("Roboto", "B", 13)
        except Exception: pdf.set_font("Helvetica", "B", 13)
        pdf.text(35, header_h + 45, "[CARGO GRID SCHEMATIC REDACTED -- PUBLIC UNCLASSIFIED CHANNEL]")

        pdf.set_text_color(200, 210, 225)
        try: pdf.set_font("Roboto", "", 9)
        except Exception: pdf.set_font("Helvetica", "", 9)
        pdf.text(35, header_h + 65, "Tactical 3D cargo layout, slot allocations, and ordnance placement schematics are classified.")
        pdf.text(35, header_h + 75, "Access is restricted to authorized UEE 44th Battlegroup logistics officers and ship command.")

        pdf.set_fill_color(180, 40, 40)
        pdf.rect(35, header_h + 90, 227, 10, 'F')
        pdf.set_text_color(255, 255, 255)
        try: pdf.set_font("Roboto", "B", 8)
        except Exception: pdf.set_font("Helvetica", "B", 8)
        pdf.text(75, header_h + 96.5, "SECURITY CLASSIFICATION: RESTRICTED / PUBLIC REDACTION ACTIVE")
        return

    if not ship_grid or "groups" not in ship_grid:
        pdf.set_font("Roboto", "I", 12)
        pdf.set_text_color(120, 130, 150)
        pdf.text(80, 80, "NO GRID DATA AVAILABLE FOR THIS VESSEL")
        return

    groups_info = _compute_grid_dimensions(ship_grid)

    # ── Overflow check: if cargo exceeds ship capacity, show empty grid + warning ──
    ship_cap = ship_grid.get("capacity", 0)
    total_cargo_scu = (
        breakdown.get("commodity_vol", 0) +
        breakdown.get("supply_vol", 0) +
        breakdown.get("ordnance_vol", 0)
    )
    # Count from blocks if vol totals are zero
    if total_cargo_scu < 0.01:
        for b in breakdown.get("blocks", []):
            total_cargo_scu += b.get("vol", 0)

    is_overflow = ship_cap > 0 and total_cargo_scu > ship_cap

    if is_overflow:
        # ── OVERFLOW: render empty grid + warning + cargo list ──
        # Render empty grid (all FREE)
        empty_breakdown = {
            "commodity_vol": 0, "supply_vol": 0, "ordnance_vol": 0,
            "total_vol": 0, "blocks": [], "ordnance_items": [],
            "commodity_items": [], "supply_items": [], "stor_all_boxes": [],
        }
        assignments = _assign_blocks_to_slots(groups_info, empty_breakdown, vessel_name=vessel_name)

        import tempfile
        import os
        img_path = _render_iso_image(groups_info, assignments, ship_grid, vessel_name)

        legend_y = lh - 22
        if img_path and os.path.exists(img_path):
            try:
                from PIL import Image as PILImage
                img = PILImage.open(img_path)
                iw, ih = img.size
                # Show grid on LEFT side (half page)
                avail_w = (lw - 16) * 0.5
                avail_h = lh - header_h - 28
                dpi = 150
                img_w_mm = iw / dpi * 25.4
                img_h_mm = ih / dpi * 25.4
                scale = min(avail_w / img_w_mm, avail_h / img_h_mm)
                img_w_mm *= scale
                img_h_mm *= scale
                img_x = 8
                img_y = header_h + (avail_h - img_h_mm) / 2
                pdf.image(img_path, x=img_x, y=img_y, w=img_w_mm, h=img_h_mm)
            except Exception as e:
                print(f"[GridPage] Image error: {e}")
            try:
                os.remove(img_path)
            except Exception:
                pass

        # ── WARNING text on RIGHT side ──
        warn_x = lw * 0.52
        warn_y = header_h + 5
        ovr_pct = int((total_cargo_scu / ship_cap - 1) * 100) if ship_cap > 0 else 0

        # Red warning box
        pdf.set_fill_color(255, 230, 230)
        pdf.set_draw_color(200, 40, 30)
        pdf.set_line_width(0.4)
        pdf.rect(warn_x - 2, warn_y - 3, lw - warn_x - 4, 12, 'DF')
        try: pdf.set_font("Roboto", "B", 8)
        except Exception: pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(180, 30, 20)
        pdf.text(warn_x, warn_y + 2,
                 f"CARGO EXCEEDS VESSEL CAPACITY")
        try: pdf.set_font("Roboto", "B", 6)
        except Exception: pdf.set_font("Helvetica", "B", 6)
        pdf.text(warn_x, warn_y + 7,
                 f"{total_cargo_scu:.0f} SCU vs {ship_cap} SCU MAX (+{ovr_pct}%)")

        # Instruction
        warn_y += 16
        try: pdf.set_font("Roboto", "B", 7)
        except Exception: pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(180, 30, 20)
        pdf.text(warn_x, warn_y,
                 "RECONSIDER LARGER SHIP OR REDUCE CARGO")
        try: pdf.set_font("Roboto", "I", 5.5)
        except Exception: pdf.set_font("Helvetica", "I", 5.5)
        pdf.set_text_color(120, 80, 60)
        pdf.text(warn_x, warn_y + 5,
                 "Cannot fit all items on cargo grid. Cargo bay shown empty.")

        # List all items that should have been loaded
        warn_y += 14
        try: pdf.set_font("Roboto", "B", 6)
        except Exception: pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(40, 50, 70)
        pdf.text(warn_x, warn_y, "ITEMS REQUIRING TRANSPORT:")
        warn_y += 5
        try: pdf.set_font("Roboto", "", 5)
        except Exception: pdf.set_font("Helvetica", "", 5)
        pdf.set_text_color(60, 70, 90)

        all_items = (
            breakdown.get("commodity_items", []) +
            breakdown.get("supply_items", []) +
            breakdown.get("ordnance_items", [])
        )
        for item in all_items[:25]:  # max 25 items
            name = item.get("name", "?")
            qty = item.get("qty", 1)
            scu = item.get("total_scu", item.get("scu_per_unit", 0) * qty)
            pdf.text(warn_x + 2, warn_y, f"• {name} x{qty}  ({scu:.1f} SCU)")
            warn_y += 3.5
            if warn_y > lh - 25:
                pdf.text(warn_x + 2, warn_y, "... and more items")
                break

        # Legend at bottom
        _draw_legend(pdf, breakdown, ship_grid, vessel_name, lh - 22)
        return

    assignments = _assign_blocks_to_slots(groups_info, breakdown, vessel_name=vessel_name)

    # ── Render isometric image with PIL ──
    import tempfile
    import os
    img_path = _render_iso_image(groups_info, assignments, ship_grid, vessel_name)

    legend_y = lh - 22  # default legend position
    if img_path and os.path.exists(img_path):
        try:
            from PIL import Image as PILImage
            img = PILImage.open(img_path)
            iw, ih = img.size
            # Available area: below header (48mm), above legend (194mm)
            avail_w = lw - 12  # 285mm
            avail_h = lh - header_h - 18  # 144mm
            dpi = 150
            img_w_mm = iw / dpi * 25.4
            img_h_mm = ih / dpi * 25.4
            scale = min(avail_w / img_w_mm, avail_h / img_h_mm)
            img_w_mm *= scale
            img_h_mm *= scale
            img_x = (lw - img_w_mm) / 2
            img_y = header_h + (avail_h - img_h_mm) / 2
            pdf.image(img_path, x=img_x, y=img_y, w=img_w_mm, h=img_h_mm)
            legend_y = lh - 18
        except Exception as e:
            print(f"[GridPage] Image error: {e}")
        try:
            os.remove(img_path)
        except Exception:
            pass

    # ── Legend + stats at bottom ──
    _draw_legend(pdf, breakdown, ship_grid, vessel_name, legend_y)


def _render_iso_image(groups_info, assignments, ship_grid, vessel_name):
    """Render isometric cargo grid as a PIL image matching sc-cargo.space style.

    Each SCU slot is rendered as an individual cube.  Grid paper extends
    beyond the cargo bays to give spatial context.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    # ── Build per-slot category + scu map ──
    # Maps (group_idx, x, y, z) -> (category, scu)
    slot_categories = {}
    for gi, (ginfo, gassgn) in enumerate(zip(groups_info, assignments)):
        for block in gassgn:
            cat = block["category"]
            scu = block.get("scu", 1)
            for sx, sy, sz in block["slots"]:
                slot_categories[(gi, sx, sy, sz)] = (cat, scu)

    # ── Compute bounding box across all groups ──
    all_max_x = 0
    all_max_z = 0
    all_max_y = 0
    for ginfo in groups_info:
        ox = ginfo.get("offset_x", 0)
        oz = ginfo.get("offset_z", 0)
        all_max_x = max(all_max_x, ox + ginfo["width"])
        all_max_z = max(all_max_z, oz + ginfo["length"])
        all_max_y = max(all_max_y, ginfo["height"])

    # Grid paper padding — tight around cargo to maximize cube size
    grid_pad = 1
    grid_w = all_max_x + grid_pad * 2
    grid_l = all_max_z + grid_pad * 2

    # Cell size — make cubes look cubic in isometric
    # For small grids (< 20 cells), use bigger cells for better visibility
    # Cell size — high resolution for large, crisp isometric grid rendering
    total_cells = grid_w + grid_l
    if total_cells <= 16:
        cell_px = max(60, min(96, 4800 // max(total_cells, 1)))
    elif total_cells <= 32:
        cell_px = max(44, min(68, 4200 // max(total_cells, 1)))
    else:
        cell_px = max(34, min(54, 3800 // max(total_cells, 1)))
    cell_h_px = cell_px // 2  # cubic proportions in iso

    # Image dimensions
    iso_w = (grid_w + grid_l) * cell_px
    iso_h = (grid_w + grid_l) * cell_px // 2 + all_max_y * cell_h_px + 60
    img_w = iso_w + 80
    img_h = iso_h + 80

    # Transparent background to allow tight getbbox() cropping
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Origin: top-center of isometric space
    ox_px = img_w // 2
    oy_px = 30 + all_max_y * cell_h_px

    def iso_x(x, z):
        return ox_px + (x - z) * cell_px // 2

    def iso_y(x, z, y=0):
        return oy_px + (x + z) * cell_px // 4 - y * cell_h_px

    def _draw_iso_tile(draw_obj, gx, gz, fill_col, outline_col):
        """Draw an isometric floor tile for cell (gx, gz) with exact vertex alignment."""
        p_back = (iso_x(gx, gz), iso_y(gx, gz, 0))
        p_right = (iso_x(gx + 1, gz), iso_y(gx + 1, gz, 0))
        p_front = (iso_x(gx + 1, gz + 1), iso_y(gx + 1, gz + 1, 0))
        p_left = (iso_x(gx, gz + 1), iso_y(gx, gz + 1, 0))
        draw_obj.polygon([p_back, p_right, p_front, p_left], fill=fill_col, outline=outline_col)

    # ── 1) GRID PAPER — checkered isometric floor ──
    grid_line = (210, 214, 222, 255)
    for gz in range(grid_l):
        for gx in range(grid_w):
            if (gx + gz) % 2 == 0:
                fill = (235, 237, 242, 255)
            else:
                fill = (228, 230, 236, 255)
            _draw_iso_tile(draw, gx, gz, fill, grid_line)

    # ── 2) BAY FLOOR HIGHLIGHT & WIREFRAME ENVELOPE ──
    bay_wireframe = (140, 160, 185, 180)
    for gi, ginfo in enumerate(groups_info):
        gox = ginfo.get("offset_x", 0) + grid_pad
        goz = ginfo.get("offset_z", 0) + grid_pad
        slot_map = _build_slot_map(ginfo)
        gw = ginfo.get("width", 1)
        gl = ginfo.get("length", 1)
        gh = ginfo.get("height", 1)

        # Draw floor slots (y = 0) with clear highlighted bay tile styling
        for (sx, sy, sz), _ in slot_map.items():
            if sy != 0:
                continue
            ax, az = sx + gox, sz + goz
            if (ax + az) % 2 == 0:
                fill = (218, 232, 244, 255)
            else:
                fill = (208, 224, 238, 255)
            _draw_iso_tile(draw, ax, az, fill, (160, 180, 205, 255))

        # Exact wireframe blueprint boundary cage for the bay volume
        p_b_back = (iso_x(gox, goz), iso_y(gox, goz, 0))
        p_b_right = (iso_x(gox + gw, goz), iso_y(gox + gw, goz, 0))
        p_b_front = (iso_x(gox + gw, goz + gl), iso_y(gox + gw, goz + gl, 0))
        p_b_left = (iso_x(gox, goz + gl), iso_y(gox, goz + gl, 0))

        p_t_back = (iso_x(gox, goz), iso_y(gox, goz, gh))
        p_t_right = (iso_x(gox + gw, goz), iso_y(gox + gw, goz, gh))
        p_t_front = (iso_x(gox + gw, goz + gl), iso_y(gox + gw, goz + gl, gh))
        p_t_left = (iso_x(gox, goz + gl), iso_y(gox, goz + gl, gh))

        # Top perimeter wireframe
        draw.line([p_t_back, p_t_right, p_t_front, p_t_left, p_t_back], fill=bay_wireframe, width=1)
        # Vertical corner pillars
        draw.line([p_b_back, p_t_back], fill=bay_wireframe, width=1)
        draw.line([p_b_right, p_t_right], fill=bay_wireframe, width=1)
        draw.line([p_b_front, p_t_front], fill=bay_wireframe, width=1)
        draw.line([p_b_left, p_t_left], fill=bay_wireframe, width=1)


    # ── 3) RENDER LOADED MULTI-SLOT CARGO BOXES & CONTAINERS — back to front ──
    # Renders real physical container sizes (16 SCU 2x2x4, 8 SCU 2x2x2, 4 SCU 1x2x2, 2 SCU 1x1x2, 1 SCU 1x1x1)
    all_boxes = []
    for gi, (ginfo, gassgn) in enumerate(zip(groups_info, assignments)):
        gox = ginfo.get("offset_x", 0) + grid_pad
        goz = ginfo.get("offset_z", 0) + grid_pad
        for block in gassgn:
            cat = block.get("category", "FREE")
            if cat == "FREE":
                continue
            slots = block.get("slots", [])
            if not slots:
                continue
            min_x = min(s[0] for s in slots)
            max_x = max(s[0] for s in slots)
            min_y = min(s[1] for s in slots)
            max_y = max(s[1] for s in slots)
            min_z = min(s[2] for s in slots)
            max_z = max(s[2] for s in slots)
            bw = max_x - min_x + 1
            bh = max_y - min_y + 1
            bl = max_z - min_z + 1
            scu = block.get("scu", len(slots))

            bx = min_x + gox
            by = min_y
            bz = min_z + goz

            # If contiguous rectangular box: render as unified multi-slot container
            if bw * bh * bl == len(slots):
                all_boxes.append((bx, by, bz, bw, bh, bl, cat, scu))
            else:
                # Discontiguous fallback: render individual unit cubes
                for sx, sy, sz in slots:
                    all_boxes.append((sx + gox, sy, sz + goz, 1, 1, 1, cat, 1))

    # Sort back-to-front by isometric depth: (bx + bw + bz + bl, bx - bz, by)
    all_boxes.sort(key=lambda b: (b[0] + b[3] + b[2] + b[5], b[0] - b[2], b[1]))

    for bx, by, bz, bw, bh, bl, cat, scu in all_boxes:
        c_top = _CUBE_COLORS.get(cat, _CUBE_COLORS["FREE"])["top"]
        c_right = _CUBE_COLORS.get(cat, _CUBE_COLORS["FREE"])["right"]
        c_front = _CUBE_COLORS.get(cat, _CUBE_COLORS["FREE"])["left"]
        _draw_iso_box_pil(draw, iso_x, iso_y, bx, by, bz, bw, bh, bl,
                          cell_px, cell_h_px, c_top, c_right, c_front, cat, scu)

    # ── 4) BAY LABELS ──
    try:
        font = ImageFont.truetype("arial.ttf", max(11, cell_px))
    except Exception:
        font = ImageFont.load_default()
    try:
        font_small = ImageFont.truetype("arial.ttf", max(9, cell_px - 2))
    except Exception:
        font_small = font

    num_groups = len(groups_info)
    for gi, ginfo in enumerate(groups_info):
        gox = ginfo.get("offset_x", 0) + grid_pad
        goz = ginfo.get("offset_z", 0) + grid_pad
        gl = ginfo["length"]
        gw_val = ginfo["width"]

        # Label at bottom-left of bay
        lx = iso_x(gox + gw_val // 2, goz + gl)
        ly = iso_y(gox + gw_val // 2, goz + gl) + 8
        bay_name = ginfo.get("name", f"Bay {gi + 1}" if num_groups > 1 else "Main Cargo Bay")
        # Ship name
        draw.text((lx - 30, ly), vessel_name, fill=(50, 60, 80, 255), font=font)
        # Bay name + capacity
        cap_text = f"({ginfo['slots']} SCU)"
        draw.text((lx - 30, ly + cell_px + 2), bay_name, fill=(90, 100, 120, 255), font=font_small)
        draw.text((lx - 30, ly + cell_px * 2), cap_text, fill=(130, 140, 155, 255), font=font_small)

    # ── Auto-crop whitespace tightly ──
    bbox = img.getbbox()
    if bbox:
        img = img.crop((max(0, bbox[0] - 12), max(0, bbox[1] - 12),
                         min(img_w, bbox[2] + 12), min(img_h, bbox[3] + 12)))

    # Composite onto solid white background
    final_img = Image.new("RGB", img.size, (255, 255, 255))
    final_img.paste(img, (0, 0), img)

    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    final_img.save(tmp.name, "PNG")
    tmp.close()
    return tmp.name


def _draw_iso_diamond(draw, cx, cy, cell_px, fill, outline):
    hw, hh = cell_px // 2, cell_px // 4
    draw.polygon([(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)], fill=fill, outline=outline)


# ── Cube colors matching sc-cargo.space ──
# ── Cube colors matching sc-cargo.space ──
_CUBE_COLORS = {
    "CMD":     {"top": (120, 200, 140), "left": (90, 175, 110), "right": (70, 155, 90)},
    "ORE":     {"top": (255, 195, 60),  "left": (225, 160, 30),  "right": (195, 130, 15)},
    "WPN":     {"top": (0, 210, 245),   "left": (0, 170, 215),   "right": (0, 140, 185)},
    "CMP":     {"top": (190, 80, 225),  "left": (155, 45, 190),  "right": (125, 25, 160)},
    "MSL":     {"top": (255, 145, 45),  "left": (230, 110, 20),  "right": (200, 85, 10)},
    "AMM":     {"top": (240, 85, 85),   "left": (210, 50, 50),   "right": (175, 30, 30)},
    "BOX_ARM": {"top": (190, 60, 70),   "left": (150, 40, 50),   "right": (120, 25, 35)},
    "BOX_CLO": {"top": (45, 110, 185),  "left": (30, 85, 150),   "right": (20, 65, 120)},
    "BOX_UTL": {"top": (240, 185, 30),  "left": (205, 150, 15),  "right": (170, 120, 5)},
    "BOX_MED": {"top": (0, 180, 140),   "left": (0, 145, 110),   "right": (0, 115, 85)},
    "BOX_REP": {"top": (220, 105, 40),  "left": (180, 80, 25),   "right": (145, 60, 15)},
    "SUP":     {"top": (100, 170, 220), "left": (70, 145, 195), "right": (50, 125, 175)},
    "ORD":     {"top": (255, 145, 45),  "left": (230, 110, 20),  "right": (200, 85, 10)},
    "FREE":    {"top": (230, 240, 250), "left": (220, 230, 242), "right": (210, 220, 235)},
}


def _draw_cube_pil(draw, iso_x_fn, iso_y_fn, wx, wy, wz, cell_px, cell_h_px, category):
    """Draw a single 1x1x1 SCU cube at world position (wx, wy, wz) with precise isometric geometry."""
    colors = _CUBE_COLORS.get(category, _CUBE_COLORS["FREE"])
    alpha = 255 if category != "FREE" else 28
    edge = (45, 50, 60, 255) if category != "FREE" else (160, 175, 195, 75)

    # Top face vertices (at height wy + 1)
    t_back = (iso_x_fn(wx, wz), iso_y_fn(wx, wz, wy + 1))
    t_right = (iso_x_fn(wx + 1, wz), iso_y_fn(wx + 1, wz, wy + 1))
    t_left = (iso_x_fn(wx, wz + 1), iso_y_fn(wx, wz + 1, wy + 1))
    t_front = (iso_x_fn(wx + 1, wz + 1), iso_y_fn(wx + 1, wz + 1, wy + 1))

    # Bottom face vertices (at height wy)
    b_left = (iso_x_fn(wx, wz + 1), iso_y_fn(wx, wz + 1, wy))
    b_front = (iso_x_fn(wx + 1, wz + 1), iso_y_fn(wx + 1, wz + 1, wy))
    b_right = (iso_x_fn(wx + 1, wz), iso_y_fn(wx + 1, wz, wy))

    # 1. Top face (brightest)
    draw.polygon([t_back, t_right, t_front, t_left], fill=(*colors["top"], alpha), outline=edge)

    # 2. Left face (front-left visible side)
    draw.polygon([t_left, t_front, b_front, b_left], fill=(*colors["left"], alpha), outline=edge)

    # 3. Right face (front-right visible side)
    draw.polygon([t_front, t_right, b_right, b_front], fill=(*colors["right"], alpha), outline=edge)


def _draw_iso_box_pil(draw, iso_x_fn, iso_y_fn, bx, by, bz, bw, bh, bl,
                       cell_px, cell_h_px, color_top, color_right, color_front,
                       category, scu):
    """Draw a clean, seamless multi-slot isometric 3D cargo container of dimensions (bw, bh, bl)."""
    alpha = 255 if category != "FREE" else 28
    edge = (45, 50, 60, 255) if category != "FREE" else (160, 175, 195, 75)

    # Top face vertices (at height by + bh)
    t_back = (iso_x_fn(bx, bz), iso_y_fn(bx, bz, by + bh))
    t_right = (iso_x_fn(bx + bw, bz), iso_y_fn(bx + bw, bz, by + bh))
    t_left = (iso_x_fn(bx, bz + bl), iso_y_fn(bx, bz + bl, by + bh))
    t_front = (iso_x_fn(bx + bw, bz + bl), iso_y_fn(bx + bw, bz + bl, by + bh))

    # Bottom face vertices (at height by)
    b_left = (iso_x_fn(bx, bz + bl), iso_y_fn(bx, bz + bl, by))
    b_front = (iso_x_fn(bx + bw, bz + bl), iso_y_fn(bx + bw, bz + bl, by))
    b_right = (iso_x_fn(bx + bw, bz), iso_y_fn(bx + bw, bz, by))

    if category == "FREE":
        free_fill = (240, 245, 252, 28)
        draw.polygon([t_back, t_right, t_front, t_left], fill=free_fill, outline=edge)
        draw.polygon([t_left, t_front, b_front, b_left], fill=free_fill, outline=edge)
        draw.polygon([t_front, t_right, b_right, b_front], fill=free_fill, outline=edge)
    else:
        # 1. Top face (brightest)
        draw.polygon([t_back, t_right, t_front, t_left], fill=(*color_top, alpha), outline=edge)

        # 2. Left face (front-left visible)
        draw.polygon([t_left, t_front, b_front, b_left], fill=(*color_front, alpha), outline=edge)

        # 3. Right face (front-right visible)
        draw.polygon([t_front, t_right, b_right, b_front], fill=(*color_right, alpha), outline=edge)

        # Monolithic solid container styling matching sc-cargo.space
        if bw > 1 or bl > 1 or bh > 1:
            # Outer bevel frame highlight on top face
            pass

            # 4. Centered SCU Badge on Top Face Diamond
            if scu >= 2:
                tcx = (t_back[0] + t_right[0] + t_front[0] + t_left[0]) // 4
                tcy = (t_back[1] + t_right[1] + t_front[1] + t_left[1]) // 4
                scu_str = f"{int(scu)}"
                try:
                    f_size = max(9, min(cell_px - 2, 14))
                    lbl_font = ImageFont.truetype("arial.ttf", f_size)
                except Exception:
                    lbl_font = ImageFont.load_default()
                # Subtle text shadow + crisp white text
                draw.text((tcx - 3, tcy - 5), scu_str, fill=(20, 25, 35, 200), font=lbl_font)
                draw.text((tcx - 4, tcy - 6), scu_str, fill=(255, 255, 255, 255), font=lbl_font)

            # High-visibility Ordnance / Weapon / Commodity / Stor-All badge for large containers (>= 4 SCU)
            if category in ("MSL", "AMM", "WPN", "CMP", "CMD", "ORE", "BOX_ARM", "BOX_CLO", "BOX_UTL", "BOX_MED", "BOX_REP"):
                fcx = (t_front[0] + b_front[0]) // 2
                fcy = (t_front[1] + b_front[1]) // 2
                s = max(4, min(cell_px // 2, 12))
                _draw_ordnance_symbol_pil(draw, fcx, fcy, s, scu, category=category)



def _draw_ordnance_symbol_pil(draw, cx, cy, s, scu, category="MSL"):
    """Draw bold, high-contrast silhouette for weapons, components, ores, commodities, missiles, ammo, and Stor-All categories."""
    dark_edge = (30, 30, 30, 255)

    if category == "CMD":
        # Commodity / RMC / Freight container symbol (industrial crate / canister)
        cmd_lime = (220, 255, 220, 255)
        w = max(3, s // 2)
        h = max(3, s // 2)
        draw.rectangle([cx - w, cy - h, cx + w, cy + h], fill=cmd_lime, outline=dark_edge)
        draw.line([(cx - w, cy), (cx + w, cy)], fill=dark_edge, width=1)
        draw.line([(cx, cy - h), (cx, cy + h)], fill=dark_edge, width=1)

    if category == "WPN":
        # Ship Weapon: dual laser cannon / repeater barrel silhouette
        wpn_cyan = (200, 245, 255, 255)
        wpn_glow = (0, 220, 255, 255)
        bw = max(2, s // 3)
        bh = max(4, s)
        draw.rectangle([cx - bw - 2, cy - bh, cx - bw, cy + bh // 2], fill=wpn_cyan, outline=dark_edge)
        draw.rectangle([cx + bw, cy - bh, cx + bw + 2, cy + bh // 2], fill=wpn_cyan, outline=dark_edge)
        draw.rectangle([cx - bw, cy - bh // 3, cx + bw, cy + bh // 2 + 2], fill=wpn_glow, outline=dark_edge)
        draw.polygon([(cx - bw - 1, cy - bh), (cx - bw - 2, cy - bh - 2), (cx - bw, cy - bh - 2)], fill=(255, 255, 255, 255))
        draw.polygon([(cx + bw + 1, cy - bh), (cx + bw, cy - bh - 2), (cx + bw + 2, cy - bh - 2)], fill=(255, 255, 255, 255))

    elif category == "CMP":
        # Ship Component / Fabricator: Diamond shield module & circuit core
        cmp_purple = (240, 190, 255, 255)
        cmp_core = (170, 50, 240, 255)
        bh = max(4, s)
        draw.polygon([(cx, cy - bh), (cx + bh, cy), (cx, cy + bh), (cx - bh, cy)], fill=cmp_purple, outline=dark_edge)
        cs = max(2, bh // 2)
        draw.rectangle([cx - cs, cy - cs, cx + cs, cy + cs], fill=cmp_core, outline=dark_edge)

    elif category == "ORE":
        # Raw / Refined Ore: Mineral crystal cluster
        gold_color = (255, 215, 50, 255)
        gem_light = (255, 245, 180, 255)
        bh = max(4, s)
        draw.polygon([(cx, cy - bh), (cx + bh // 2, cy + bh // 3), (cx, cy + bh), (cx - bh // 2, cy + bh // 3)], fill=gold_color, outline=dark_edge)
        draw.polygon([(cx, cy - bh), (cx - bh // 2, cy + bh // 3), (cx, cy)], fill=gem_light, outline=dark_edge)
        draw.polygon([(cx + bh // 2, cy - bh // 3), (cx + bh, cy + bh // 2), (cx + bh // 3, cy + bh // 2)], fill=gold_color, outline=dark_edge)

    elif category == "AMM":
        # Ammunition bullet cartridge symbol
        bullet_gold = (255, 220, 90, 255)
        w = max(2, s // 2)
        h = max(4, s)
        draw.rectangle([cx - w - 2, cy - h // 3, cx - w, cy + h // 2], fill=bullet_gold, outline=dark_edge)
        draw.rectangle([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2], fill=bullet_gold, outline=dark_edge)
        draw.polygon([(cx, cy - h), (cx - w // 2, cy - h // 2), (cx + w // 2, cy - h // 2)], fill=(255, 255, 255, 255), outline=dark_edge)
        draw.rectangle([cx + w, cy - h // 3, cx + w + 2, cy + h // 2], fill=bullet_gold, outline=dark_edge)

    elif category == "BOX_ARM":
        # Stor-All Armory: Handgun / small arm silhouette
        draw.rectangle([cx - s // 2, cy - s // 4, cx + s // 2, cy], fill=(255, 240, 240, 255), outline=dark_edge)
        draw.rectangle([cx + s // 6, cy, cx + s // 2, cy + s // 2], fill=(255, 200, 200, 255), outline=dark_edge)

    elif category == "BOX_CLO":
        # Stor-All Armor: Helmet visor silhouette
        draw.ellipse([cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2], fill=(220, 240, 255, 255), outline=dark_edge)
        draw.rectangle([cx - s // 3, cy - s // 6, cx + s // 3, cy + s // 6], fill=(40, 100, 180, 255))

    elif category == "BOX_UTL":
        # Stor-All Tools: Wrench / multi-tool
        draw.rectangle([cx - s // 6, cy - s // 2, cx + s // 6, cy + s // 2], fill=(255, 245, 180, 255), outline=dark_edge)
        draw.rectangle([cx - s // 3, cy - s // 2, cx + s // 3, cy - s // 4], fill=(255, 210, 40, 255), outline=dark_edge)

    elif category == "BOX_MED":
        # Stor-All Medical: Bold Red/White Cross
        w = max(2, s // 3)
        draw.rectangle([cx - w, cy - s // 2, cx + w, cy + s // 2], fill=(255, 255, 255, 255), outline=dark_edge)
        draw.rectangle([cx - s // 2, cy - w, cx + s // 2, cy + w], fill=(255, 255, 255, 255), outline=dark_edge)

    elif category == "BOX_REP":
        # Stor-All Repair Deck: Spanner & Gear
        draw.ellipse([cx - s // 3, cy - s // 3, cx + s // 3, cy + s // 3], fill=(255, 200, 160, 255), outline=dark_edge)
        draw.line([cx - s // 2, cy + s // 2, cx + s // 2, cy - s // 2], fill=(255, 140, 50, 255), width=2)

    else:
        # Missile / Rocket symbol (high-contrast white & gold sharp silhouette)
        msl_white = (255, 255, 255, 255)
        msl_gold = (255, 200, 50, 255)
        bw = max(2, s // 3)
        bh = max(4, s)
        draw.polygon([(cx, cy - bh), (cx - bw, cy - bh // 3), (cx + bw, cy - bh // 3)], fill=msl_gold, outline=dark_edge)
        draw.rectangle([cx - bw, cy - bh // 3, cx + bw, cy + bh // 2], fill=msl_white, outline=dark_edge)
        draw.polygon([(cx - bw, cy + bh // 6), (cx - bw * 2 - 2, cy + bh // 2 + 1), (cx - bw, cy + bh // 2)], fill=msl_gold, outline=dark_edge)
        draw.polygon([(cx + bw, cy + bh // 6), (cx + bw * 2 + 2, cy + bh // 2 + 1), (cx + bw, cy + bh // 2)], fill=msl_gold, outline=dark_edge)
        draw.line([cx - bw // 2, cy + bh // 2 + 1, cx + bw // 2, cy + bh // 2 + 1], fill=(255, 120, 0, 255), width=1)


# ── Ordnance icon cache ──
_ORD_ICON_CACHE = {}

def _load_ordnance_icon(scu, target_size):
    """Load and cache ordnance PNG icon, resized to target_size."""
    if scu >= 30:
        icon_name = "ordnance_bomb.png"
    elif scu >= 10:
        icon_name = "ordnance_torpedo.png"
    else:
        icon_name = "ordnance_missile.png"

    cache_key = f"{icon_name}_{target_size}"
    if cache_key in _ORD_ICON_CACHE:
        return _ORD_ICON_CACHE[cache_key]

    try:
        from PIL import Image
        icon_path = PATHS.resource(icon_name)
        if os.path.isfile(icon_path):
            icon = Image.open(icon_path).convert("RGBA")
            icon = icon.resize((target_size, target_size), Image.LANCZOS)
            _ORD_ICON_CACHE[cache_key] = icon
            return icon
    except Exception:
        pass

    _ORD_ICON_CACHE[cache_key] = None
    return None


def _overlay_ordnance_icon(img, cx, cy, cell_px, scu):
    """Paste ordnance PNG icon onto the cargo grid image at (cx, cy)."""
    icon_size = max(12, cell_px // 2)
    icon = _load_ordnance_icon(scu, icon_size)
    if icon is None:
        return

    try:
        paste_x = cx - icon_size // 2
        paste_y = cy - icon_size // 2
        if paste_x >= 0 and paste_y >= 0:
            img.paste(icon, (paste_x, paste_y), icon)
    except Exception:
        pass


def _draw_legend(pdf, breakdown, ship_grid, vessel_name, y_pos):
    """Draw stats line and color legend at bottom of grid page."""
    cap = ship_grid.get("capacity", "?") if ship_grid else "?"
    used = breakdown.get("total_vol", 0)
    free = cap - used if isinstance(cap, (int, float)) else "?"
    cmd = breakdown.get("commodity_vol", 0)
    ore = breakdown.get("ore_vol", 0)
    wpn = breakdown.get("ship_weapon_vol", 0)
    cmp = breakdown.get("ship_component_vol", 0)
    sup = breakdown.get("supply_vol", 0)
    ordn = breakdown.get("ordnance_vol", 0)
    groups = len(ship_grid.get("groups", [])) if ship_grid else 0

    y = min(y_pos, 186)  # Must fit on landscape page (210mm tall)

    # Overload / Cannot fit warning
    is_overloaded = isinstance(cap, (int, float)) and used > cap
    if is_overloaded:
        overflow_scu = used - cap
        pdf.set_fill_color(180, 20, 20)
        pdf.rect(14, y - 7, 268, 5.5, 'F')
        pdf.set_font("Roboto", "B", 7)
        pdf.set_text_color(255, 255, 255)
        pdf.text(16, y - 3.2, f"CRITICAL ALERT: CARGO EXCEEDS VESSEL CAPACITY BY +{overflow_scu:.0f} SCU (CANNOT FIT IN HOLD // OVERLOADED)")

    # Stats line
    pdf.set_font("Roboto", "", 6.5)
    if is_overloaded:
        pdf.set_text_color(180, 20, 20)
        stats = f"Vessel: {vessel_name}  |  Capacity: {cap} SCU  |  Sections: {groups}  |  STATUS: OVERLOADED"
        free_str = f"OVERFLOW (+{used - cap:.0f} SCU CANNOT FIT)"
    else:
        pdf.set_text_color(60, 70, 90)
        stats = f"Vessel: {vessel_name}  |  Capacity: {cap} SCU  |  Sections: {groups}"
        free_str = f"{free:.0f} SCU"

    pdf.text(14, y, stats)
    stats2 = f"Used: {used:.0f} SCU | Free: {free_str} | Cmd: {cmd:.0f} | Ore: {ore:.0f} | Wpn: {wpn:.0f} | Cmp: {cmp:.0f} | Msl/Ammo: {ordn:.0f} | Sup: {sup:.0f}"
    pdf.text(14, y + 4.5, stats2)

    # Row 1: Direct Grid Cargo Categories
    legend_y1 = y + 10
    row1_items = [
        ("CMD", "Commodities / RMC", COLORS["CMD"]),
        ("ORE", "Ores & Minerals", COLORS["ORE"]),
        ("WPN", "Ship Weapons", COLORS["WPN"]),
        ("CMP", "Components / Fab", COLORS["CMP"]),
        ("MSL", "Missiles / Torps", COLORS["MSL"]),
        ("AMM", "Ammunition", COLORS["AMM"]),
    ]
    x1 = 14
    for code, label, color in row1_items:
        pdf.set_fill_color(*color)
        pdf.set_draw_color(80, 80, 80)
        pdf.set_line_width(0.1)
        pdf.rect(x1, legend_y1 - 2.5, 3, 3, 'DF')
        pdf.set_font("Roboto", "", 5.0)
        pdf.set_text_color(60, 70, 90)
        pdf.text(x1 + 4, legend_y1, f"{code} — {label}")
        x1 += pdf.get_string_width(f"{code} — {label}") + 6

    # Row 2: Stor-All Categorized Boxes & Free Space
    legend_y2 = y + 15.5
    row2_items = [
        ("BOX-ARM", "Stor-All [Weapons]", COLORS["BOX_ARM"]),
        ("BOX-CLO", "Stor-All [Armor]", COLORS["BOX_CLO"]),
        ("BOX-UTL", "Stor-All [Tools]", COLORS["BOX_UTL"]),
        ("BOX-MED", "Stor-All [Medical]", COLORS["BOX_MED"]),
        ("BOX-REP", "Stor-All [Repair]", COLORS["BOX_REP"]),
        ("SUP", "Stor-All [Supply]", COLORS["SUP"]),
        ("FREE", "Free Space", COLORS["FREE"]),
    ]
    x2 = 14
    for code, label, color in row2_items:
        pdf.set_fill_color(*color)
        pdf.set_draw_color(80, 80, 80)
        pdf.set_line_width(0.1)
        pdf.rect(x2, legend_y2 - 2.5, 3, 3, 'DF')
        pdf.set_font("Roboto", "", 5.0)
        pdf.set_text_color(60, 70, 90)
        pdf.text(x2 + 4, legend_y2, f"{code} — {label}")
        x2 += pdf.get_string_width(f"{code} — {label}") + 5
