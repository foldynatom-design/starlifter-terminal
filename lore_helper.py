# -*- coding: utf-8 -*-
"""
lore_helper.py - RP Lore System for Starlifter Terminal.

Ranks, SC dates, cargo context, crew text rephrasing, synonyms,
volume_map, ore_quality_map, story cache.

Usage:
    from lore_helper import *
"""

import random
import time

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

# Isolated random instance for story generation Ă˘â‚¬â€ť does NOT corrupt global random state
# Session seed ensures different stories across app launches, stable within session
_story_rng = random.Random()
_SESSION_SEED = int(time.time() * 1000) & 0xFFFFFFFF

# Star Citizen RP year offset (real year + 930 = SC year)
SC_YEAR_OFFSET = 930

# 44th Battle Group rank system
BG44_RANKS = {
    "ens": "Ensign", "ens.": "Ensign",
    "2lt": "2nd Lieutenant", "2lt.": "2nd Lieutenant",
    "ltjg": "Lieutenant Junior Grade", "ltjg.": "Lieutenant Junior Grade",
    "1lt": "1st Lieutenant", "1lt.": "1st Lieutenant",
    "lt": "Lieutenant", "lt.": "Lieutenant",
    "cpt": "Captain", "cpt.": "Captain",
    "lcdr": "Lieutenant Commander", "lcdr.": "Lieutenant Commander",
    "maj": "Major", "maj.": "Major",
    "cdr": "Commander", "cdr.": "Commander",
    "ltcol": "Lieutenant Colonel", "ltcol.": "Lieutenant Colonel",
    "capt": "Captain (Navy)", "capt.": "Captain (Navy)",
    "col": "Colonel", "col.": "Colonel",
    "cdre": "Commodore", "cdre.": "Commodore",
    "radm": "Rear Admiral", "radm.": "Rear Admiral",
}

# ── Refined Ore Quality Guide ──
# Quality 700+ = GOOD for captains. Used in PDF recommendations.
ore_quality_map = {
    "refined quantainium":  {"tier": "S", "min_good": 700, "value_mult": 15.0, "note": "Extremely volatile. Handle under inert atmo only."},
    "refined agricium":     {"tier": "A", "min_good": 700, "value_mult": 8.0,  "note": "High-value. Store in climate-controlled containers."},
    "refined laranite":     {"tier": "A", "min_good": 700, "value_mult": 6.5,  "note": "Premium alloy precursor. Fragile crystal matrix."},
    "refined bexlite":      {"tier": "A", "min_good": 700, "value_mult": 5.0,  "note": "Rare mineral. Secure in shielded containers."},
    "refined taranite":     {"tier": "A", "min_good": 700, "value_mult": 5.5,  "note": "Strategic reserve material. Transport under escort."},
    "refined gold":         {"tier": "B", "min_good": 650, "value_mult": 3.0,  "note": "Standard bullion. Stable at room temperature."},
    "refined titanium":     {"tier": "B", "min_good": 650, "value_mult": 2.5,  "note": "Structural alloy grade. Stack max 4 high."},
    "refined copper":       {"tier": "C", "min_good": 600, "value_mult": 1.5,  "note": "Industrial grade. Standard handling protocol."},
    "refined iron":         {"tier": "C", "min_good": 600, "value_mult": 1.0,  "note": "Bulk industrial. No special handling required."},
    "refined silicon":      {"tier": "C", "min_good": 600, "value_mult": 1.2,  "note": "Electronics grade. Keep dry and dust-free."},
}

def extract_rank(name):
    """Extract rank from name like 'Lt. Thomas Wolf' -> ('Lieutenant', 'Thomas Wolf')"""
    if not name:
        return "UEE Logistics Officer", name
    parts = name.strip().split(None, 1)
    if len(parts) >= 2:
        prefix = parts[0].lower().rstrip(".")
        # Check both with and without dot
        for key in [prefix, prefix + "."]:
            if key in BG44_RANKS:
                return BG44_RANKS[key], parts[1]
    return "UEE Logistics Officer", name


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

def get_cargo_context_sentence(items_list):
    has_fuels = False
    has_ordnance = False
    has_ores = False
    has_salvage = False
    has_equip = False
    for item in items_list:
        name_low = item["name"].lower()
        if any(x in name_low for x in ["quantainium", "hydrogen fuel", "quantum fuel"]):
            has_fuels = True
        elif any(x in name_low for x in ["missile", "torpedo", "bomb", "ammunition", "seeker", "colossus", "stormburst"]):
            has_ordnance = True
        elif any(x in name_low for x in ["silicon", "iron", "copper", "titanium", "gold", "laranite", "agricium", "bexlite", "taranite"]):
            has_ores = True
        elif any(x in name_low for x in ["recycled material composite", "rmc"]):
            has_salvage = True
        elif any(x in name_low for x in ["armor", "helmet", "rifle", "pistol", "magazine", "tractor beam", "cambio", "cruz", "tool", "battery"]):
            has_equip = True
            
    if has_fuels:
        return ", and high-pressure containers with volatile fuel were additionally stabilized to prevent static initiation during quantum jump"
    elif has_ordnance:
        return ", with transport of highly explosive ammunition and heavy torpedoes safely isolated and magnetically locked in forward launch shafts"
    elif has_ores:
        return ", and heavy pallets of refined metals and silicon were firmly anchored to the floor grid to prevent any shift in the ship center of gravity"
    elif has_salvage:
        return ", and containers of recycled composite material (RMC) were secured for immediate use in repairing damaged fleet hulls"
    elif has_equip:
        return ", and transport crates with personal equipment, logistics tools and CRUZ hydration packs were stored in auxiliary lockable boxes"
    else:
        return ", and the standard cargo layout was carefully checked against the maximum ship load capacity"

# RP Stories â€” imported from rp_stories.py (uses {cargo_type} placeholder)
from rp_stories import stories
_stories_loaded = True


# Loose item volume definitions (in SCU)
volume_map = {
    "adp-core": 0.015,
    "adp armor": 0.015,
    "adp helmet": 0.015,
    "adp arms": 0.015,
    "adp legs": 0.015,
    "adp-core helmet": 0.015,
    "adp-mk4 helmet woodland": 0.015,
    "adp-mk4 core woodland": 0.015,
    "adp-mk4 arms woodland": 0.010,
    "adp-mk4 legs woodland": 0.010,
    "orc-mkx helmet woodland": 0.010,
    "orc-mkx core woodland": 0.012,
    "orc-mkx arms woodland": 0.008,
    "orc-mkx legs woodland": 0.008,
    "field recon suit helmet": 0.008,
    "field recon suit core": 0.010,
    "field recon suit arms": 0.006,
    "field recon suit legs": 0.006,
    "tailwind flight suit": 0.012,
    "tailwind helmet": 0.010,
    "omni-afs sapphire slate": 0.012,
    "omni-afs sapphire slate helmet": 0.010,
    "aril helmet": 0.010,
    "aril core": 0.012,
    "aril arms": 0.008,
    "aril legs": 0.008,
    "aril backpack": 0.040,
    "csp-68h backpack": 0.050,
    "csp-68m backpack": 0.040,
    "csp-68l backpack": 0.030,
    "cruz lux": 0.0005,
    "cruz": 0.0005,
    "maxlift tractor beam": 0.008,
    "maxlift tractor beam battery": 0.002,
    "cambio srt": 0.008,
    "cambio multi-tool battery": 0.002,
    "cambio srt canister": 0.004,
    "behring laser repair tool": 0.008,
    "laser repair battery": 0.002,
    "p4-ar rifle": 0.025,
    "p4-ar magazine": 0.001,
    "coda pistol": 0.010,
    "coda magazine": 0.0005,
    "gallant rifle": 0.025,
    "gallant magazine": 0.001,
    "c54 smg": 0.015,
    "c54 magazine": 0.0008,
    "lumin v smg": 0.018,
    "lumin v magazine": 0.0008,
    "scalpel sniper rifle": 0.035,
    "scalpel magazine": 0.0012,
    "custodian smg": 0.014,
    "custodian magazine": 0.0008,
    "devastator shotgun": 0.028,
    "devastator magazine": 0.0012,
    "fs-9 lmg": 0.030,
    "fs-9 magazine": 0.0015,
    "deo black shirt": 0.002,
    "prim black shoes": 0.002,
    "ventra gloves black": 0.001,
    "quantainium water bottle": 0.0005,
    "scorch plasma grenade": 0.001,
    "behring \"cq7\" bullpup rifle": 0.025,
    "cq7": 0.025,
    "waveshift mining gadget": 0.030,
    "sabir mining gadget": 0.030,
    # â”€â”€ Weapons (missing) â”€â”€
    "p4-ar \"nightstalker\" rifle": 0.025,
    "s-38 pistol": 0.010,
    "s-38 magazine": 0.0005,
    "p8-sc smg": 0.015,
    "p8-sc magazine": 0.001,
    "p6-lr sniper rifle": 0.035,
    "p6-lr magazine": 0.001,
    "p8-ar rifle": 0.025,
    "p8-ar magazine": 0.001,
    "behring \"cq7\" magazine": 0.001,
    "mk-4 frag grenade": 0.001,
    "pink quikflare": 0.0005,
    # — Materials & Commodities (SCU = 1.0 grid slot minimum) —
    "quantum fuel": 1.0, "hydrogen fuel": 1.0,
    "recycled material composite (rmc)": 1.0,
    "construction materials": 1.0,
    "pancea medgel canister": 0.05,
    "stor-all 1 scu storage container": 1.0,
    "stor*all 2 scu self-storage container": 2.0,
    "stor*all 4 scu self-storage container": 4.0,
    "stor*all 8 scu self-storage container": 8.0,
    # — Refined Ores (1 SCU grid slot minimum per unit) —
    "refined silicon": 1.0, "refined iron": 1.0, "refined copper": 1.0,
    "refined titanium": 1.0, "refined gold": 1.0, "refined laranite": 1.0,
    "refined agricium": 1.0, "refined bexlite": 1.0, "refined taranite": 1.0,
    "refined quantainium": 1.0,
    # — Ammunition (1 SCU box each) —
    "size 1 ammunition": 1.0, "size 2 ammunition": 1.0, "size 3 ammunition": 1.0,
    "size 4 ammunition": 1.0, "size 5 ammunition": 1.0, "size 6 ammunition": 1.0,
    "size 7 ammunition": 1.0,
    "decoy countermeasures": 1.0, "noise countermeasures": 1.0,
    # — Missiles (bounding box cage grid footprint, patch 4.9+) —
    # S1-S2: snap to 1 SCU grid slot with cage frame
    "pioneer i missile": 1.0, "viper i missile": 1.0, "spark i missile": 1.0,
    "marksman ii missile": 1.0, "tempest ii missile": 1.0,
    "strikeforce ii missile": 1.0, "ignite ii missile": 1.0, "dominator ii missile": 1.0,
    # S3: 2 SCU bounding box cage (elongated, snaps 2x1)
    "arrester iii missile": 2.0, "thunderbolt iii missile": 2.0,
    # S4: 2 SCU cage (wider body)
    "raptor iv missile": 2.0, "stalker iv missile": 2.0,
    # S5: 4 SCU cage (~4 grid slots length)
    "reaper v missile": 4.0,
    # â”€â”€ Torpedoes (S9) & Bombs (S10) â”€â”€ large ordnance on grid â”€â”€
    # S9 torpedo: ~6-8 SCU bounding box cage on grid
    "seeker ix torpedo": 8.0, "argus ix torpedo": 8.0, "typhoon ix torpedo": 8.0,
    # S10 bomb: massive ~16 SCU cage footprint
    "stormburst bomb": 16.0, "colossus bomb": 16.0,
    # â”€â”€ Food & Drinks (tiny) â”€â”€
    "buster's chocolate bar": 0.0005, "fizzz peach": 0.0005,
    "karoby energy bar": 0.0005, "onemeal nutrition bar": 0.0005,
    "pips energy t17": 0.0005, "readymeal": 0.0005,
    "snaggle stick": 0.0005, "veggie dog": 0.0005,
    "mug": 0.0005,
    # â”€â”€ Uniforms (missing variants) â”€â”€
    "tcs-4 undersuit": 0.005, "tcs-4 undersuit black/grey": 0.005,
    "tcs-4 undersuit black": 0.005,
    "odyssey undersuit": 0.005, "beacon undersuit": 0.005,
    "orc-mkx helmet twilight": 0.010, "orc-mkx core twilight": 0.012,
    "orc-mkx arms twilight": 0.008, "orc-mkx legs twilight": 0.008,
    "adp-mk4 helmet (slate)": 0.015, "adp-mk4 core (slate)": 0.015,
    "adp-mk4 arms (slate)": 0.010, "adp-mk4 legs (slate)": 0.010,
    "macflex helmet": 0.010, "macflex core": 0.012,
    "macflex arms": 0.008, "macflex legs": 0.008,
    "omni-afs saphire slate": 0.012,
    "adiva jacket imperial": 0.006, "adiva jacket white": 0.006,
    "adiva jacket blue": 0.006, "adiva jacket yellow": 0.006,
    "adiva jacket dark green": 0.006, "adiva jacket red": 0.006,
    "lemarque pants": 0.002, "deo shirt black": 0.002, "prim shoes black": 0.002,
    # â”€â”€ Utility & Medical (missing) â”€â”€
    "paramed medical device": 0.008, "paramed refill": 0.002,
    "hemozal medpen": 0.001, "adrenapen": 0.001, "corticopen": 0.001,
    "deconpen": 0.001, "detoxpen": 0.001, "opiopen": 0.001,
    "cambio-lite srt attachment": 0.005,
    "lifeguard medical attachment": 0.005,
    "truhold tractor beam attachment": 0.005,
    "item fabricator": 0.050,
    "apx fire extinguisher": 0.010,
}

# â”€â”€ Refined Ore Quality Guide â”€â”€
# Quality 700+ = GOOD for captains. Used in PDF recommendations.
ore_quality_map = {
    "refined quantainium":  {"tier": "S", "min_good": 700, "value_mult": 15.0, "note": "Extremely volatile. Handle under inert atmo only."},
    "refined agricium":     {"tier": "A", "min_good": 700, "value_mult": 8.0,  "note": "High-value. Store in climate-controlled containers."},
    "refined laranite":     {"tier": "A", "min_good": 700, "value_mult": 6.5,  "note": "Premium alloy precursor. Fragile crystal matrix."},
    "refined bexlite":      {"tier": "A", "min_good": 700, "value_mult": 5.0,  "note": "Rare mineral. Secure in shielded containers."},
    "refined taranite":     {"tier": "A", "min_good": 700, "value_mult": 5.5,  "note": "Strategic reserve material. Transport under escort."},
    "refined gold":         {"tier": "B", "min_good": 650, "value_mult": 3.0,  "note": "Standard bullion. Stable at room temperature."},
    "refined titanium":     {"tier": "B", "min_good": 650, "value_mult": 2.5,  "note": "Structural alloy grade. Stack max 4 high."},
    "refined copper":       {"tier": "C", "min_good": 600, "value_mult": 1.5,  "note": "Industrial grade. Standard handling protocol."},
    "refined iron":         {"tier": "C", "min_good": 600, "value_mult": 1.0,  "note": "Bulk industrial. No special handling required."},
    "refined silicon":      {"tier": "C", "min_good": 600, "value_mult": 1.2,  "note": "Electronics grade. Keep dry and dust-free."},
}

def rephrase_crew_text(text, officer_name):
    # Apply direct overrides for specific sentences
    text = text.replace("The hangar crew led by {crew} has cleared the pad and returned all terminal lifters to their charging stations.",
                        "The hangar pad has been fully cleared and all terminal lifters returned to their charging stations under the direct supervision of Loading Officer {officer}.")
    text = text.replace("Loading crew {crew} reports a textbook grid alignment",
                        "Loading Officer {officer} reports a textbook grid alignment")
    text = text.replace("The loading team {crew} worked efficiently to ensure",
                        "The loading operations supervised by {officer} were completed efficiently to ensure")
    text = text.replace("Loading crew {crew} has already vacated the primary cargo elevator and cleared the deck floor.",
                        "The primary cargo elevator has already been vacated and the deck floor cleared under the supervision of {officer}.")
    text = text.replace("The loading crew {crew} did an excellent job of organizing the freight to allow easy access",
                        "Loading Officer {officer} did an excellent job of organizing the freight to allow easy access")
    text = text.replace("Loading crew {crew} worked diligently to complete the staging process fifteen minutes ahead of schedule.",
                        "The staging process was completed diligently fifteen minutes ahead of schedule under the supervision of {officer}.")
    text = text.replace("The loading team under the command of {crew} has completed their final sweep and exited the hangar.",
                        "The final deck sweep has been completed and the hangar cleared under the command of {officer}.")
    text = text.replace("The loading crew {crew} was highly professional and handled the fragile cargo crates with extreme care.",
                        "The cargo loading operations were highly professional and all fragile cargo crates were handled with extreme care under the supervision of {officer}.")
    text = text.replace("The cargo was staged by {crew} and officially approved for transport by Loading Officer {officer}.",
                        "The cargo was staged and officially approved for transport by Loading Officer {officer}.")
    text = text.replace("The loading crew {crew} has packed up their equipment and cleared the hangar bay floor.",
                        "All equipment has been packed up and the hangar bay floor cleared under the supervision of {officer}.")
    text = text.replace("The loading crew {crew} worked under elevated security protocols to get your ship loaded as quickly as possible.",
                        "Loading operations were completed under elevated security protocols supervised by {officer} to get your ship loaded as quickly as possible.")
    text = text.replace("While loading crew {crew} was moving the last 40-ton container, they noticed a minor hydraulic fluid leak",
                        "While moving the last 40-ton container under the supervision of {officer}, a minor hydraulic fluid leak was noticed")
    text = text.replace("The loading crew {crew} had to rush the final mag-lock checks to prevent a total airspace fine.",
                        "The final mag-lock checks had to be rushed under the supervision of {officer} to prevent a total airspace fine.")
    text = text.replace("Loading crew {crew} tried to scrub it off using standard industrial solvents",
                        "Attempts were made to scrub it off under the supervision of {officer} using standard industrial solvents")
    text = text.replace("The crew led by {crew} checked the physical fuses, and they are intact",
                        "The physical fuses were checked and confirmed intact under the supervision of {officer}")
    text = text.replace("The loading crew {crew} had to reset the external data port three times just to complete the handshake.",
                        "The external data port had to be reset three times under the supervision of {officer} just to complete the handshake.")
    text = text.replace("The loading crew {crew} had to secure extra physical straps over the 40-ton containers to prevent any micro-vibrations",
                        "Extra physical straps had to be secured over the 40-ton containers under the supervision of {officer} to prevent any micro-vibrations")
    text = text.replace("Loading crew {crew} ran an ultrasonic stress test and discovered a hairline fracture",
                        "An ultrasonic stress test run under the supervision of {officer} discovered a hairline fracture")
    text = text.replace("Loading crew {crew} had to close the hangar doors early to prevent anyone from wandering",
                        "The hangar doors had to be closed early under the supervision of {officer} to prevent anyone from wandering")
    text = text.replace("The crew led by {crew} didn't have a spare filter in stock, so you'll have to rely on the auxiliary system",
                        "No spare filter was in stock, so you'll have to rely on the auxiliary system under the supervision of {officer}")
    text = text.replace("two members of loading crew {crew} sustained severe flash burns and were rushed to the local medical clinic.",
                        "two members of the deck team sustained severe flash burns under the supervision of {officer} and were evacuated.")
    text = text.replace("Loading crew {crew} worked in absolute terror as explosions shook the hangar walls around them.",
                        "Loading operations supervised by {officer} were completed in absolute terror as explosions shook the hangar walls.")
    text = text.replace("Loading crew {crew} had to put on emergency hazmat gear, vent the entire cargo bay into space, and seal the leaking 40-ton crate.",
                        "Emergency hazmat gear had to be put on and the cargo bay vented into space under the supervision of {officer}.")
    text = text.replace("Loading crew {crew} is severely understaffed now, and they had to rush to throw the remaining military crates onto your ship.",
                        "Loading operations are severely understaffed now, and remaining crates were rushed onto the grid under the supervision of {officer}.")
    text = text.replace("Loading crew {crew} had to panic-load your ship to meet the emergency evacuation deadline",
                        "The cargo was panic-loaded under the supervision of {officer} to meet the emergency evacuation deadline")
    text = text.replace("Loading crew {crew} had to use primitive steel cables to hold the damaged crates in place.",
                        "Primitive steel cables had to be used under the supervision of {officer} to hold the damaged crates in place.")
    text = text.replace("Loading crew led by {crew} sustained casualties, and the remaining workers are fleeing the deck.",
                        "The deck team sustained casualties, and remaining operations were aborted under the supervision of {officer}.")
    text = text.replace("Loading crew {crew} had to use manual winches to drag the cargo onto your grid",
                        "Manual winches had to be used under the supervision of {officer} to drag the cargo onto your grid")
    text = text.replace("temporary structural braces were quickly installed by the remaining members of {crew}",
                        "temporary structural braces were quickly installed under the supervision of {officer}")
    text = text.replace("Loading crew {crew} abandoned the remaining cargo on the lift",
                        "The remaining cargo was abandoned on the lift under the supervision of {officer}")
    
    # Standard fallback replacements
    text = text.replace("loading crew {crew}", officer_name)
    text = text.replace("Loading crew {crew}", officer_name)
    text = text.replace("crew led by {crew}", f"operations led by {officer_name}")
    text = text.replace("{crew}", officer_name)
    return text

def apply_synonyms(text):
    synonyms = {
        "catastrophe": ["disaster", "calamity", "cataclysm"],
        "nightmare": ["calamity", "ordeal", "crisis"],
        "accident": ["mishap", "incident", "occurrence"],
        "unstable": ["volatile", "fluctuating", "shaky"],
        "danger": ["risk", "hazard", "threat"],
        "completed": ["finalized", "concluded", "finished"],
        "nominal": ["stable", "optimal", "baseline"],
        "failed": ["malfunctioned", "errored", "faulted"],
        "damaged": ["compromised", "ruptured", "impaired"],
        "secured": ["locked down", "safeguarded", "firmly fixed"],
        "catastrophic": ["disastrous", "devastating", "ruinous"]
    }
    words = text.split(" ")
    punctuation_chars = ',.!:;()[]"\\' + "'"
    for idx, w in enumerate(words):
        clean_w = w.lower().strip(punctuation_chars)
        if clean_w in synonyms:
            if _story_rng.random() < 0.35:
                replacement = _story_rng.choice(synonyms[clean_w])
                if w[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                left_punct = w[:len(w) - len(w.lstrip(punctuation_chars))]
                right_punct = w[len(w.rstrip(punctuation_chars)):]
                words[idx] = left_punct + replacement + right_punct
    return " ".join(words)


# ── Telemetry sensor data (gravity, atmo, clamps, hazmat) ────────────

def get_telemetry(text, danger_level, items_list=None):
    """Generate RP telemetry readout based on cargo context and danger level.

    Returns dict with keys: gravity, atmosphere, clamps, hazmat.
    Values change dynamically based on:
      - danger_level: 'low' / 'medium' / 'high'
      - Story text keywords (acid, fire, damage, failed)
      - Cargo types (ordnance, fuel, ores, salvage)
    """
    text_lower = text.lower()
    danger_lower = danger_level.lower()
    is_acid = any(w in text_lower for w in ["acid", "toxic", "chemical", "gas"])
    is_fire = any(w in text_lower for w in ["fire", "flames", "explosive", "explosion"])
    is_damage = any(w in text_lower for w in ["damage", "ruptured", "bent", "broken"])
    is_failed = any(w in text_lower for w in ["failed", "failing", "sparks", "power grid"])

    # Detect actual cargo types
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
            if any(x in nl for x in ["missile", "torpedo", "bomb", "ammunition", "seeker", "colossus", "stormburst"]):
                has_ordnance = True
            elif any(x in nl for x in ["quantainium", "hydrogen fuel", "quantum fuel"]):
                has_fuel = True
            elif any(x in nl for x in ["silicon", "iron", "copper", "titanium", "gold", "laranite", "agricium", "ore"]):
                has_ores = True
            elif any(x in nl for x in ["recycled material", "rmc"]):
                has_salvage = True

    # Base values
    gravity = "ACTIVE (1.0G - STABLE)"
    atmosphere = "NOMINAL (101.3 kPa)"
    clamps = "LOCKED (Power Draw: 42 kW)"
    hazmat = "CLEAR / SECURE"

    # Danger level adjustments
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

    # Cargo-specific overrides
    if has_ordnance:
        hazmat = "ALERT // EXPLOSIVE ORDNANCE IN HOLD"
        if danger_lower == "low":
            atmosphere = "SEALED (O2 Suppressed - Ordnance Protocol)"
    if has_fuel:
        hazmat = "WARNING // VOLATILE FUEL (Quantainium)"
        atmosphere = "VENTING STANDBY (Low O2 - Fuel Safety)"
        if danger_lower != "low":
            gravity = "DAMPENED (Anti-ignition field active)"
    if has_ores and total_scu > 50:
        clamps = f"HEAVY LOAD ({total_scu} SCU - Reinforced)"
        if danger_lower == "low":
            gravity = f"COMPENSATING (Mass: {total_scu} SCU)"
    if has_salvage:
        hazmat = "MONITORING (RMC Composite - Low particulate)"

    # Story-text overrides (highest priority)
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

