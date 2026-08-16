# -*- coding: utf-8 -*-
"""
lore_helper.py - RP Lore System for Starlifter Terminal.

Ranks, SC dates, cargo context, crew text rephrasing, synonyms,
volume_map, ore_quality_map, story cache, and dynamic narrative generation.

Usage:
    from lore_helper import *
"""

import os
import random
import time
import re

# Import narrative lore templates
try:
    from rp_stories import stories
except ImportError:
    stories = ["Standard logistics dispatch for {ship}. {officer} confirms {cargo_type} staged. Captain {captain} approved."]

# Lore story cache for locking text during channel changes
LORE_STORY_CACHE = {
    "text": None,
    "danger_level": None,
    "vessel": None,
    "manifest_hash": None,
    "captain": None,
    "officer": None,
    "crew": None
}

# Isolated random instance for story generation — does NOT corrupt global random state
_story_rng = random.Random()
_SESSION_SEED = int(time.time() * 1000) & 0xFFFFFFFF

# Star Citizen RP year offset (real year + 930 = SC year)
SC_YEAR_OFFSET = 930

# 44th Battle Group rank system (Officers & Enlisted / Crew)
BG44_RANKS = {
    # Enlisted & NCO Ranks
    "smr": "Starman Recruit", "smr.": "Starman Recruit",
    "tpr": "Trooper Recruit", "tpr.": "Trooper Recruit",
    "rec": "Recruit", "rec.": "Recruit",
    "str": "Starman", "str.": "Starman", "starman": "Starman",
    "lstr": "Leading Starman", "lstr.": "Leading Starman",
    "t1c": "Trooper 1st Class", "t1c.": "Trooper 1st Class",
    "jpo": "Jr. Petty Officer", "jpo.": "Jr. Petty Officer",
    "lcpl": "Lance Corporal", "lcpl.": "Lance Corporal",
    "pvt": "Private", "pvt.": "Private",
    "cpl": "Corporal", "cpl.": "Corporal",
    "sgt": "Sergeant", "sgt.": "Sergeant",
    "po": "Petty Officer", "po.": "Petty Officer",
    "cpo": "Chief Petty Officer", "cpo.": "Chief Petty Officer",
    "ssgt": "Staff Sergeant", "ssgt.": "Staff Sergeant",
    "mcpo": "Master Chief Petty Officer", "mcpo.": "Master Chief Petty Officer",
    "msgt": "Master Sergeant", "msgt.": "Master Sergeant",
    "wo": "Warrant Officer", "wo.": "Warrant Officer",
    # Officer Ranks
    "ens": "Ensign", "ens.": "Ensign",
    "2lt": "2nd Lieutenant", "2lt.": "2nd Lieutenant",
    "ltjg": "Lieutenant Junior Grade", "ltjg.": "Lieutenant Junior Grade",
    "1lt": "1st Lieutenant", "1lt.": "1st Lieutenant",
    "lt": "Lieutenant", "lt.": "Lieutenant", "lieutenant": "Lieutenant",
    "cpt": "Captain", "cpt.": "Captain",
    "lcdr": "Lieutenant Commander", "lcdr.": "Lieutenant Commander",
    "maj": "Major", "maj.": "Major",
    "cdr": "Commander", "cdr.": "Commander", "cmdr": "Commander", "cmdr.": "Commander",
    "ltcol": "Lieutenant Colonel", "ltcol.": "Lieutenant Colonel",
    "capt": "Captain (Navy)", "capt.": "Captain (Navy)",
    "col": "Colonel", "col.": "Colonel",
    "cdre": "Commodore", "cdre.": "Commodore",
    "radm": "Rear Admiral", "radm.": "Rear Admiral",
    "adm": "Admiral", "adm.": "Admiral",
}

# ── Refined Ore Quality Guide ──
ore_quality_map = {
    "refined quantainium":  {"tier": "S", "min_good": 700, "value_mult": 15.0, "note": "Extremely volatile. Handle under inert atmo only."},
    "refined agricium":     {"tier": "A", "min_good": 700, "value_mult": 8.0,  "note": "High-value. Store in climate-controlled containers."},
    "refined laranite":     {"tier": "A", "min_good": 700, "value_mult": 6.5,  "note": "Premium alloy precursor. Fragile crystal matrix."},
    "refined bexalite":      {"tier": "A", "min_good": 700, "value_mult": 5.0,  "note": "Rare mineral. Secure in shielded containers."},
    "refined taranite":     {"tier": "A", "min_good": 700, "value_mult": 5.5,  "note": "Strategic reserve material. Transport under escort."},
    "refined gold":         {"tier": "B", "min_good": 650, "value_mult": 3.0,  "note": "Standard bullion. Stable at room temperature."},
    "refined titanium":     {"tier": "B", "min_good": 650, "value_mult": 2.5,  "note": "Structural alloy grade. Stack max 4 high."},
    "refined copper":       {"tier": "C", "min_good": 600, "value_mult": 1.5,  "note": "Industrial grade. Standard handling protocol."},
    "refined iron":         {"tier": "C", "min_good": 600, "value_mult": 1.0,  "note": "Bulk industrial. No special handling required."},
    "refined silicon":      {"tier": "C", "min_good": 600, "value_mult": 1.2,  "note": "Electronics grade. Keep dry and dust-free."},
}

def extract_rank(name):
    """Extract rank and clean name: 'Lt. Thomas Wolf' -> ('Lieutenant', 'Thomas Wolf') or 'Str. Cinner' -> ('Starman', 'Cinner')"""
    if not name or not str(name).strip():
        return "UEE Logistics Officer", ""
    cleaned = str(name).strip()
    parts = cleaned.split(None, 1)
    if len(parts) >= 2:
        prefix = parts[0].lower().rstrip(".")
        for key in [prefix, prefix + "."]:
            if key in BG44_RANKS:
                return BG44_RANKS[key], parts[1]
    return "UEE Logistics Officer", cleaned

def format_full_rank_name(name):
    """Expand abbreviated rank in name: 'Lt. Thomas Wolf' -> 'Lieutenant Thomas Wolf'"""
    if not name or not str(name).strip():
        return ""
    cleaned = str(name).strip()
    rank, clean_name = extract_rank(cleaned)
    if rank != "UEE Logistics Officer" and clean_name:
        return f"{rank} {clean_name}"
    return cleaned

def format_officer_address(name, style_idx=None, rng=None):
    """Dynamically formats officer mention with realistic military variation:
    - Style 0: 'Lieutenant Thomas Wolf' (Full rank & name)
    - Style 1: 'Lt. Wolf' or 'Lieutenant Wolf' (Rank + surname)
    - Style 2: 'the Loading Officer' or 'the Deck Lieutenant' (Role/rank only)
    - Style 3: 'Officer Wolf' (Officer + surname)
    - Style 4: 'Wolf' (Surname only)
    """
    if not name or not str(name).strip():
        return "the Loading Officer"
    
    local_rng = rng or _story_rng
    rank, clean_name = extract_rank(name)
    name_parts = clean_name.split() if clean_name else []
    surname = name_parts[-1] if name_parts else clean_name
    first_name = name_parts[0] if len(name_parts) > 1 else ""

    short_rank = name.split()[0] if name.split() else ""
    if not short_rank.endswith(".") and len(short_rank) <= 4:
        short_rank += "."

    options = []
    # 0. Full rank and full name
    if rank != "UEE Logistics Officer" and clean_name:
        options.append(f"{rank} {clean_name}")
    else:
        options.append(f"Logistics Officer {clean_name}")

    # 1. Rank + Surname
    if rank != "UEE Logistics Officer" and surname:
        options.append(f"{rank} {surname}")
        options.append(f"{short_rank} {surname}")
    elif surname:
        options.append(f"Officer {surname}")

    # 2. Role / Rank only
    if rank != "UEE Logistics Officer":
        options.append(f"the {rank}")
        options.append(f"the Deck {rank}")
    options.append("the Loading Officer")
    options.append("the Duty Officer")

    # 3. Officer + Surname
    if surname:
        options.append(f"Officer {surname}")
        options.append(f"Logistics Officer {surname}")

    # 4. Surname only
    if surname:
        options.append(surname)

    if style_idx is not None and 0 <= style_idx < len(options):
        return options[style_idx]
    return local_rng.choice(options)

def format_captain_address(name, style_idx=None, rng=None):
    """Dynamically formats captain mention with realistic military variation:
    - Style 0: 'Captain Vance' / 'Leading Starman Rebot1401'
    - Style 1: 'Capt. Vance' / 'LSTR. Rebot1401'
    - Style 2: 'Captain' / 'Commander' / 'Skipper'
    - Style 3: 'Vance' / 'Rebot1401'
    """
    if not name or not str(name).strip():
        return "Captain"
    
    local_rng = rng or _story_rng
    rank, clean_name = extract_rank(name)
    name_parts = clean_name.split() if clean_name else []
    surname = name_parts[-1] if name_parts else clean_name

    options = []
    if rank != "UEE Logistics Officer" and clean_name:
        options.append(f"{rank} {clean_name}")
        options.append(f"{rank} {surname}")
        options.append(f"Captain {surname}")
    elif "captain" in name.lower() or "cmdr" in name.lower() or "cdr" in name.lower():
        options.append(name)
        options.append(f"Captain {surname}")
    else:
        options.append(f"Captain {clean_name}")
        options.append(f"Captain {surname}")

    options.append("Captain")
    options.append("Commander")
    options.append("Skipper")
    if surname:
        options.append(surname)

    if style_idx is not None and 0 <= style_idx < len(options):
        return options[style_idx]
    return local_rng.choice(options)

def sc_date_now():
    """Return current date/time in Star Citizen format: '2956-07-17 01:30 SET'"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    sc_year = now.year + SC_YEAR_OFFSET
    return f"{sc_year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d} SET"

def sc_date_only():
    """Return current date in SC format: '2956-07-17'"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    sc_year = now.year + SC_YEAR_OFFSET
    return f"{sc_year}-{now.month:02d}-{now.day:02d}"

def build_dynamic_cargo_phrase(items_list, rng=None, danger_level="LOW"):
    """Synthesizes rich, natural military phrasing summarized by broad categories and SCU volumes.
    Single specific item names are ONLY highlighted during incident/damage scenarios.
    """
    if not items_list:
        return "standardized military supply containers"

    local_rng = rng or _story_rng
    from collections import defaultdict

    cat_scu = defaultdict(float)
    cat_items = defaultdict(list)

    for it in items_list:
        raw_name = it.get("name", "")
        clean_nm = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
        qty = int(it.get("qty", 1)) if str(it.get("qty", "1")).isdigit() else 1
        box = str(it.get("box_size", "1 SCU")).lower()
        nm_low = clean_nm.lower()

        if "8 scu" in box: scu_val = qty * 8.0
        elif "4 scu" in box: scu_val = qty * 4.0
        elif "2 scu" in box: scu_val = qty * 2.0
        elif "1 scu" in box or "scu" in box: scu_val = qty * 1.0
        else: scu_val = qty * 0.05

        if any(k in nm_low for k in ["quantainium", "hydrogen fuel", "quantum fuel", "fuel"]):
            cat_scu["fuel"] += scu_val
            cat_items["fuel"].append(clean_nm)
        elif any(k in nm_low for k in ["missile", "torpedo", "bomb", "ammunition", "cannon", "repeater", "weapon", "rifle", "pistol", "smg", "lmg", "sniper", "shotgun", "magazine"]):
            cat_scu["ordnance_weapons"] += scu_val
            cat_items["ordnance_weapons"].append(clean_nm)
        elif any(k in nm_low for k in ["silicon", "iron", "copper", "titanium", "gold", "laranite", "agricium", "bexalite", "taranite", "ore"]):
            cat_scu["ores"] += scu_val
            cat_items["ores"].append(clean_nm)
        elif any(k in nm_low for k in ["recycled material", "rmc", "scrap", "composite"]):
            cat_scu["salvage"] += scu_val
            cat_items["salvage"].append(clean_nm)
        elif any(k in nm_low for k in ["armor", "helmet", "undersuit", "backpack", "core", "arms", "legs", "suit", "jacket", "shirt", "pants", "shoes", "gloves"]):
            cat_scu["armor"] += scu_val
            cat_items["armor"].append(clean_nm)
        elif any(k in nm_low for k in ["tractor", "cambio", "multitool", "battery", "canister", "srt"]):
            cat_scu["utility"] += scu_val
            cat_items["utility"].append(clean_nm)
        elif any(k in nm_low for k in ["cruz", "lux", "drink", "food", "ration", "medpen", "paramed", "lifeguard"]):
            cat_scu["medical_food"] += scu_val
            cat_items["medical_food"].append(clean_nm)
        else:
            cat_scu["general"] += scu_val
            cat_items["general"].append(clean_nm)

    phrases = []
    if cat_scu["salvage"] >= 0.5:
        phrases.append(f"{cat_scu['salvage']:.0f} SCU of composite salvage materials (RMC)")
    if cat_scu["ordnance_weapons"] >= 0.5:
        phrases.append(f"{cat_scu['ordnance_weapons']:.0f} SCU of naval ammunition & tactical ordnance")
    if cat_scu["ores"] >= 0.5:
        phrases.append(f"{cat_scu['ores']:.0f} SCU of refined industrial metals")
    if cat_scu["fuel"] >= 0.5:
        phrases.append(f"{cat_scu['fuel']:.0f} SCU of high-pressure fuel containment cells")
    if cat_scu["armor"] >= 0.05:
        phrases.append(f"{max(1.0, cat_scu['armor']):.0f} SCU of combat armor & EVA tactical gear")
    if cat_scu["utility"] >= 0.05:
        phrases.append(f"{max(1.0, cat_scu['utility']):.0f} SCU of logistics tools & engineering equipment")
    if cat_scu["medical_food"] >= 0.05:
        phrases.append(f"{max(1.0, cat_scu['medical_food']):.0f} SCU of medical supplies & field rations")
    if cat_scu["general"] >= 0.5 and not phrases:
        phrases.append(f"{cat_scu['general']:.0f} SCU of general military freight")

    if not phrases:
        top_items = sorted(items_list, key=lambda x: int(x.get('qty', 1)) if str(x.get('qty', 1)).isdigit() else 1, reverse=True)[:2]
        phrases = [f"containerized {ti.get('name', 'supplies')}" for ti in top_items]

    if len(phrases) == 1:
        return phrases[0]
    elif len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    else:
        return f"{phrases[0]}, {phrases[1]}, and {phrases[2]}"

def get_cargo_context_sentence(items_list):
    """Returns an additional context clause tailored to the manifest."""
    has_fuels = False
    has_ordnance = False
    has_ores = False
    has_salvage = False
    has_equip = False
    for item in items_list:
        name_low = item.get("name", "").lower()
        if any(x in name_low for x in ["quantainium", "hydrogen fuel", "quantum fuel"]):
            has_fuels = True
        elif any(x in name_low for x in ["missile", "torpedo", "bomb", "ammunition", "seeker", "colossus", "stormburst", "repeater", "cannon"]):
            has_ordnance = True
        elif any(x in name_low for x in ["silicon", "iron", "copper", "titanium", "gold", "laranite", "agricium", "bexalite", "taranite"]):
            has_ores = True
        elif any(x in name_low for x in ["recycled material composite", "rmc"]):
            has_salvage = True
        elif any(x in name_low for x in ["armor", "helmet", "rifle", "pistol", "magazine", "tractor beam", "cambio", "cruz", "tool", "battery"]):
            has_equip = True
            
    if has_fuels:
        return ", with high-pressure fuel containment cells monitored for static discharge prior to quantum jump"
    elif has_ordnance:
        return ", with explosive ammunition and ordnance isolated and magnetically anchored in designated weapon racks"
    elif has_ores:
        return ", with high-density refined metal pallets securely anchored to the floor grid to maintain center of gravity"
    elif has_salvage:
        return ", with containerized composite materials (RMC) locked down for direct fleet hull repair logistics"
    elif has_equip:
        return ", with personal equipment, weapons, and logistics tools safely packed inside standardized Stor-All containers"
    else:
        return ", with the cargo layout balanced and verified against the naval ship load capacity envelope"

def rephrase_crew_text(text, officer_name):
    """Rephrases crew mentions if loading crew is empty."""
    text = text.replace("The hangar crew led by {crew} has cleared the pad and returned all terminal lifters to their charging stations.",
                        "The hangar pad has been fully cleared and all terminal lifters returned to their charging stations under the direct supervision of {officer}.")
    text = text.replace("Loading crew {crew} reports a textbook grid alignment",
                        "{officer} reports a textbook grid alignment")
    text = text.replace("loading crew {crew}", officer_name)
    text = text.replace("Loading crew {crew}", officer_name)
    text = text.replace("crew led by {crew}", f"operations led by {officer_name}")
    text = text.replace("{crew}", officer_name)
    return text

def get_telemetry(text, danger_level, items_list=None):
    """Generate RP telemetry readout based on cargo context and danger level."""
    text_lower = text.lower()
    danger_lower = danger_level.lower()
    is_acid = any(w in text_lower for w in ["acid", "toxic", "chemical", "gas"])
    is_fire = any(w in text_lower for w in ["fire", "flames", "explosive", "explosion"])
    is_damage = any(w in text_lower for w in ["damage", "ruptured", "bent", "broken"])
    is_failed = any(w in text_lower for w in ["failed", "failing", "sparks", "power grid"])

    has_ordnance = False
    has_fuel = False
    has_ores = False
    has_salvage = False
    total_scu = 0
    if items_list:
        for item in items_list:
            nl = item.get("name", "").lower()
            qty = int(item.get("qty", 1)) if str(item.get("qty", "1")).isdigit() else 1
            total_scu += qty
            if any(x in nl for x in ["missile", "torpedo", "bomb", "ammunition", "seeker", "repeater", "cannon"]):
                has_ordnance = True
            elif any(x in nl for x in ["quantainium", "hydrogen fuel", "quantum fuel"]):
                has_fuel = True
            elif any(x in nl for x in ["silicon", "iron", "copper", "titanium", "gold", "laranite", "agricium", "ore"]):
                has_ores = True
            elif any(x in nl for x in ["recycled material", "rmc"]):
                has_salvage = True

    gravity = "ACTIVE (1.0G - STABLE)"
    atmosphere = "NOMINAL (101.3 kPa)"
    clamps = "LOCKED (Power Draw: 42 kW)"
    hazmat = "CLEAR / SECURE"

    if danger_lower == "medium":
        gravity = "WARNING (Fluctuations: 0.9G - 1.1G)"
        atmosphere = "PRESSURE FLUX (96.8 kPa)"
        clamps = "UNSTABLE (Power Draw: 58 kW)"
        hazmat = "MONITORING ANOMALIES (Low risk)"
    elif danger_lower == "high":
        gravity = "CRITICAL FAULT (0.2G - 2.1G)"
        atmosphere = "COMPROMISED (Drop: 55.4 kPa)"
        clamps = "FAILING (Auxiliary power)"
        hazmat = "ALERT - VOLATILE HOLD CONTEXT"

    if has_ordnance:
        hazmat = "ALERT // EXPLOSIVE ORDNANCE IN HOLD"
        if danger_lower == "low":
            atmosphere = "SEALED (O2 Suppressed - Ordnance Protocol)"
    if has_fuel:
        hazmat = "WARNING // VOLATILE FUEL"
        atmosphere = "VENTING STANDBY (Low O2 - Fuel Safety)"
        if danger_lower != "low":
            gravity = "DAMPENED (Anti-ignition field active)"
    if has_ores and total_scu > 50:
        clamps = f"HEAVY LOAD ({total_scu} SCU - Reinforced)"
    if has_salvage:
        hazmat = "MONITORING (RMC Composite - Low particulate)"

    if is_acid:
        hazmat = "CRITICAL (Corrosive Outbreak)"
    if is_fire:
        hazmat = "ALERT (Thermal Hazard Active)"
        atmosphere = "VENTING ACTIVE (Low Oxygen)"
    if is_damage:
        gravity = "SHIELD PRESSURE COLLAPSE"
        atmosphere = "DECOMPRESSION RISK (72.1 kPa)"
    if is_failed:
        clamps = "EMERGENCY POWER CLAMP ENGAGED"
        gravity = "STABILIZATION ERROR"

    return {"gravity": gravity, "atmosphere": atmosphere, "clamps": clamps, "hazmat": hazmat}

def apply_synonyms(text, rng=None):
    """Applies contextual synonyms to avoid repetitive phrasing."""
    local_rng = rng or _story_rng
    synonyms = {
        "catastrophe": ["disaster", "calamity", "cataclysm"],
        "nightmare": ["calamity", "ordeal", "crisis"],
        "accident": ["mishap", "incident", "occurrence"],
        "unstable": ["volatile", "fluctuating", "shaky"],
        "danger": ["risk", "hazard", "threat"],
        "completed": ["finalized", "concluded", "finished", "executed"],
        "nominal": ["stable", "optimal", "baseline", "green"],
        "failed": ["malfunctioned", "errored", "faulted"],
        "damaged": ["compromised", "ruptured", "impaired"],
        "secured": ["locked down", "safeguarded", "firmly fixed", "latched"],
        "catastrophic": ["disastrous", "devastating", "ruinous"]
    }
    words = text.split(" ")
    punctuation_chars = ',.!:;()[]"\\' + "'"
    for idx, w in enumerate(words):
        clean_w = w.lower().strip(punctuation_chars)
        if clean_w in synonyms:
            if local_rng.random() < 0.40:
                replacement = local_rng.choice(synonyms[clean_w])
                if w[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                left_punct = w[:len(w) - len(w.lstrip(punctuation_chars))]
                right_punct = w[len(w.rstrip(punctuation_chars)):]
                words[idx] = left_punct + replacement + right_punct
    return " ".join(words)

def generate_dynamic_lore_story(items_list, vessel, location, captain, loading_officer, loading_crew, danger_level="LOW", seed_entropy=None):
    """Master narrative generator. Generates a completely customized, high-variety,
    context-aware military logistics dispatch note.
    """
    local_rng = random.Random()
    if seed_entropy is not None:
        local_rng.seed(seed_entropy)
    else:
        local_rng.seed(int(time.time() * 1000000) & 0xFFFFFFFF)

    # 1. Filter templates by danger level
    total_templates = len(stories)
    low_templates = stories[0:20]
    med_templates = stories[20:35]
    high_templates = stories[35:total_templates]

    d_upper = str(danger_level).upper()
    if "HIGH" in d_upper or "CATASTROPHIC" in d_upper:
        pool = high_templates
    elif "MEDIUM" in d_upper or "SEVERE" in d_upper:
        pool = med_templates
    else:
        pool = low_templates

    template = local_rng.choice(pool)

    # 2. Build cargo phrase categorized by SCU volume
    cargo_phrase = build_dynamic_cargo_phrase(items_list, rng=local_rng, danger_level=danger_level)

    # 3. Format officer & captain with realistic variation
    officer_str = format_officer_address(loading_officer, rng=local_rng)
    captain_str = format_captain_address(captain, rng=local_rng)

    # 4. Format crew safely (never leave empty holes)
    crew_val = str(loading_crew or "").strip()
    if not crew_val or crew_val.upper() in ["NONE", "PENDING", "PENDING APPROVED", ""]:
        crew_str = local_rng.choice([
            "the station deck team", "the terminal logistics detail",
            "the naval stevedores", "the primary cargo detail"
        ])
    else:
        crew_str = local_rng.choice([
            f"the logistics detachment from {crew_val}",
            f"the loading team {crew_val}",
            f"the deck crew of {crew_val}",
            crew_val
        ])

    # 5. Format location safely (never leave empty holes)
    loc_val = str(location or "").strip()
    if not loc_val or loc_val.upper() in ["NONE", "PENDING", ""]:
        loc_str = "the primary staging hangar"
    else:
        loc_str = loc_val

    # 6. Format vessel safely
    v_val = str(vessel or "").strip()
    if not v_val or v_val.upper() in ["NONE", "PENDING", ""]:
        ship_str = "the primary transport vessel"
    else:
        ship_str = v_val

    # 7. Substitute placeholders cleanly
    story = template.format(
        cargo_type=cargo_phrase,
        ship=ship_str,
        captain=captain_str,
        officer=officer_str,
        crew=crew_str,
        location=loc_str
    )

    # 8. Clean up double spaces or awkward punctuation
    story = re.sub(r'\s+', ' ', story).strip()

    # 9. Apply contextual synonyms
    story = apply_synonyms(story, rng=local_rng)
    return story
