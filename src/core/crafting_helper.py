# -*- coding: utf-8 -*-
"""
crafting_helper.py - Blueprint matching and raw material/ore requirement resolver.

Handles items that cannot be purchased at commercial shop terminals:
1. If a blueprint/recipe exists -> flags item as 'NEED TO BE CRAFTED',
   identifies the required Blueprint, and calculates the necessary ores and materials.
2. If no blueprint/recipe exists -> flags item as 'UNOBTAINABLE // NEEDS TO BE LOOTED'.
"""

import os
import json
import re
import path_config

_RECIPES_CACHE = None

def _load_recipes():
    global _RECIPES_CACHE
    if _RECIPES_CACHE is not None:
        return _RECIPES_CACHE

    recipes_path = os.path.join(path_config.PATHS.resources, "crafting_recipes.json")
    if not os.path.exists(recipes_path):
        # Fallback search in relative directory
        recipes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "crafting_recipes.json")

    if os.path.exists(recipes_path):
        try:
            with open(recipes_path, "r", encoding="utf-8") as f:
                _RECIPES_CACHE = json.load(f)
        except Exception as e:
            print(f"[CRAFTING_HELPER_ERROR] Failed to load crafting_recipes.json: {e}")
            _RECIPES_CACHE = {}
    else:
        _RECIPES_CACHE = {}
    return _RECIPES_CACHE


def clean_item_name(name):
    """Normalize item name: lowercased, stripped quotes, stripped size/skin tags."""
    if not name:
        return ""
    n = str(name).lower().strip()
    # Remove quotes
    n = n.replace('"', '').replace("'", "")
    # Remove parenthetical tags like (Size 4), (40 cap), (Desert Shadow), etc.
    n = re.sub(r'\s*\([^)]*\)', '', n).strip()
    # Remove special skin tags in quotes or brackets
    n = re.sub(r'\s*\[[^\]]*\]', '', n).strip()
    # Normalize multiple spaces
    n = ' '.join(n.split())
    return n


_PURE_LOOT_KEYWORDS = [
    "star kitten", "starkitten", "takahashi racing", "subscriber", "sub flair", "pledge",
    "afterlife", "stoneface", "executive", "citizencon", "best in show", "bis",
    "day of the vara", "vara", "luminalia", "foundation festival", "red festival", "coramor",
    "prototype", "alien", "xenotech", "banu", "vanduul",
    "golden ticket", "relic", "artifact", "trophy", "event exclusive",
    "unobtainable", "loot only", "field recovery", "wreckage", "derelict",
    "special edition", "custom prototype", "rare sub"
]

def is_pure_loot_item(item_name):
    """Checks if an item is a rare subscriber flair, event reward, alien artifact or loot-only drop."""
    if not item_name:
        return False
    n = str(item_name).lower()
    return any(k in n for k in _PURE_LOOT_KEYWORDS)


def get_crafting_recipe(item_name):
    """
    Search for a crafting recipe/blueprint for given item name.
    Returns dict with keys: 'blueprint', 'category', 'materials' (list of dicts),
    or None if item is not craftable.
    """
    if not item_name:
        return None

    # Subscriber flair, event rewards and pure loot items CANNOT be crafted
    if is_pure_loot_item(item_name):
        return None

    recipes_db = _load_recipes()
    if not recipes_db:
        return None

    raw_clean = clean_item_name(item_name)

    # 1. Direct and substring lookup in specific_items (from sc-craft.tools)
    specific_items = recipes_db.get("specific_items", {})
    if specific_items:
        # Pass 1: Exact match with normalized key
        for sk, sinfo in specific_items.items():
            if clean_item_name(sk) == raw_clean or sk.lower().strip() == raw_clean:
                return sinfo
        
        # Pass 2: Substring / key in name match (longest match wins)
        best_match = None
        best_len = 0
        for sk, sinfo in specific_items.items():
            sk_c = clean_item_name(sk)
            if sk_c == raw_clean:
                return sinfo
            if sk_c in raw_clean or raw_clean in sk_c:
                if len(sk_c) > best_len:
                    best_match = sinfo
                    best_len = len(sk_c)
        if best_match and best_len >= 5:
            return best_match

        # Pass 3: All words exact match
        raw_words = set(w for w in re.split(r'[\s\-_]+', raw_clean) if len(w) >= 2)
        best_word_match = None
        max_matched_words = 0
        for sk, sinfo in specific_items.items():
            sk_words = set(w for w in re.split(r'[\s\-_]+', clean_item_name(sk)) if len(w) >= 2)
            if sk_words and sk_words == raw_words:
                return sinfo


    # 2. Exact or key matching across all category tables
    for cat_name, cat_entries in recipes_db.items():
        if not isinstance(cat_entries, dict) or cat_name in ("specific_items", "categories"):
            continue
        # Direct key match
        if raw_clean in cat_entries:
            return cat_entries[raw_clean]

        # Key contained in item name or item name contained in key
        for key, info in cat_entries.items():
            if key == raw_clean or key in raw_clean:
                return info

    # 2. Token / word root matching (e.g. "p4-ar" in "P4-AR Nightstalker", "adp-mk4" in "ADP-mk4 Core Woodland")
    armor_keys = ["adp-mk4", "orc-mkx", "macflex", "morozov", "defiance", "truedef", "arden-cl", "aril", "clash", "tcs-4", "stoneskin", "second skin", "beacon", "csp-68h", "csp-68m"]
    for ak in armor_keys:
        if ak in raw_clean:
            cat_armor = recipes_db.get("armor", {})
            for k, info in cat_armor.items():
                if ak in k:
                    return info

    weapon_keys = ["p4-ar", "c54", "coda", "devastator", "fs-9", "gallant", "karna", "p8-sc", "s71", "arrowhead", "scalpel", "custodian", "demeco", "lh86", "arclight", "salvo", "gp-33", "animus", "scourge"]
    for wk in weapon_keys:
        if wk in raw_clean:
            cat_weapons = recipes_db.get("weapons", {})
            for k, info in cat_weapons.items():
                if wk in k:
                    return info

    # Tool & Attachment keys
    tool_keys = ["pyro multi-tool", "truhold", "cambio srt canister", "cambio srt battery", "cambio srt", "maxlift tractor beam battery", "maxlift", "paramed", "medpen", "oxypen"]
    for tk in tool_keys:
        if tk in raw_clean:
            cat_tools = recipes_db.get("tools", {})
            if tk in cat_tools:
                return cat_tools[tk]

    # Ship component generic roots
    if "shield generator" in raw_clean or "shield" in raw_clean:
        return recipes_db.get("ship_components", {}).get("shield generator")
    if "cooler" in raw_clean:
        return recipes_db.get("ship_components", {}).get("cooler")
    if "power plant" in raw_clean:
        return recipes_db.get("ship_components", {}).get("power plant")
    if "quantum drive" in raw_clean:
        return recipes_db.get("ship_components", {}).get("quantum drive")
    if "cannon" in raw_clean:
        return recipes_db.get("ship_components", {}).get("cannon")
    if "repeater" in raw_clean or "gatling" in raw_clean:
        return recipes_db.get("ship_components", {}).get("repeater")
    if "torpedo" in raw_clean:
        return recipes_db.get("ship_components", {}).get("torpedo")
    if "missile" in raw_clean:
        return recipes_db.get("ship_components", {}).get("missile")
    if "magazine" in raw_clean or "ammo" in raw_clean:
        for sk in ["size 1 ammunition", "size 2 ammunition", "size 3 ammunition", "size 4 ammunition", "size 5 ammunition"]:
            if sk in raw_clean:
                return recipes_db.get("ammunition", {}).get(sk)
        return recipes_db.get("ammunition", {}).get("magazine")
    if "decoy" in raw_clean:
        return recipes_db.get("ammunition", {}).get("decoy countermeasures")
    if "noise" in raw_clean:
        return recipes_db.get("ammunition", {}).get("noise countermeasures")

    return None


def format_ore_volume(qty_units):
    """Formats raw ore / material quantity in cSCU and SCU (1 cSCU = 0.01 SCU)."""
    cscu = int(qty_units)
    scu = cscu / 100.0
    return f"{cscu} cSCU ({scu:.2f} SCU)"


def resolve_unbuyable_item(item_name, qty=1):
    """
    Resolve item that has no commercial buy location:
    Returns dict:
    {
        'status': 'NEED_TO_BE_CRAFTED' | 'UNOBTAINABLE_LOOT',
        'can_craft': bool,
        'blueprint': str or None,
        'category': str,
        'materials': list of {'name': str, 'qty': int, 'unit_qty': int, 'cscu': int, 'scu': float, 'vol_str': str},
        'display_directive': str,
        'directive_type': 'CRAFTING' | 'LOOT'
    }
    """
    qty = max(1, int(qty or 1))
    recipe = get_crafting_recipe(item_name)

    if recipe:
        bp_name = recipe.get("blueprint", f"{item_name} Blueprint")
        cat_name = recipe.get("category", "Fabrication")
        raw_mats = recipe.get("materials", [])
        agg_mats = {}
        for m in raw_mats:
            m_name = m.get("name", "Composite")
            m_unit_qty = m.get("qty_per_unit", 1)
            agg_mats[m_name] = agg_mats.get(m_name, 0) + m_unit_qty

        total_mats = []
        mat_desc_parts = []
        for m_name, m_unit_qty in agg_mats.items():
            total_m_qty = m_unit_qty * qty
            vol_str = format_ore_volume(total_m_qty)
            total_mats.append({
                "name": m_name,
                "qty": total_m_qty,
                "unit_qty": m_unit_qty,
                "cscu": total_m_qty,
                "scu": total_m_qty / 100.0,
                "vol_str": vol_str
            })
            mat_desc_parts.append(f"{vol_str} {m_name}")

        mat_str = ", ".join(mat_desc_parts) if mat_desc_parts else "Refined Ores / Minerals"
        directive = f"NEED TO BE CRAFTED (Blueprint: {bp_name} | Mining Required: {mat_str} - TO BE MINED)"

        return {
            "status": "NEED_TO_BE_CRAFTED",
            "can_craft": True,
            "blueprint": bp_name,
            "category": cat_name,
            "materials": total_mats,
            "display_directive": directive,
            "directive_type": "CRAFTING"
        }
    else:
        directive = "UNOBTAINABLE // NEEDS TO BE LOOTED (No vendor terminal & no blueprint available)"
        return {
            "status": "UNOBTAINABLE_LOOT",
            "can_craft": False,
            "blueprint": None,
            "category": "Unmapped / Field Recovery",
            "materials": [],
            "display_directive": directive,
            "directive_type": "LOOT"
        }


def aggregate_required_materials(crafted_items):
    """
    Given a list of crafted item resolutions or dicts with 'materials',
    aggregates and returns consolidated list of required ores/materials with cSCU and SCU.
    """
    consolidated = {}
    for it in crafted_items:
        mats = it.get("materials", [])
        for m in mats:
            m_name = m["name"]
            consolidated[m_name] = consolidated.get(m_name, 0) + m["qty"]

    result = []
    for name, total_qty in sorted(consolidated.items(), key=lambda x: -x[1]):
        result.append({
            "name": name,
            "qty": total_qty,
            "cscu": total_qty,
            "scu": total_qty / 100.0,
            "vol_str": format_ore_volume(total_qty)
        })
    return result
