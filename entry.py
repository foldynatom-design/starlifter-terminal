# -*- coding: utf-8 -*-
import sys
import os
import re
import random
import threading
import urllib.request
import json
import math
import time
from tkinter import messagebox

# Explicitly import all packages used by the application to force PyInstaller's static analyzer to collect their C-extensions (.pyd files) and binary dependencies!
import cv2
import numpy
import fpdf
import PIL
import PIL.Image
import PIL.ImageTk
import customtkinter
import winsound
import main

# Determine base directory (next to EXE when frozen, next to script otherwise)
if getattr(sys, 'frozen', False):
    app_base = os.path.dirname(sys.executable)
else:
    app_base = os.path.dirname(os.path.abspath(__file__))

# Dynamically add _internal and _internal/numpy.libs to DLL search path
numpy_libs_path = os.path.join(app_base, '_internal', 'numpy.libs')
if os.path.exists(numpy_libs_path):
    try:
        os.add_dll_directory(numpy_libs_path)
    except Exception:
        pass

internal_path = os.path.join(app_base, '_internal')
if os.path.exists(internal_path):
    try:
        os.add_dll_directory(internal_path)
    except Exception:
        pass

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

# ── Monkey-patch resource_path to find files next to EXE ──
# main.pyc's resource_path tries sys._MEIPASS first, but fonts/, resources/,
# config.json, watermarks etc. live NEXT TO the EXE, not inside _MEIPASS.
_orig_resource_path = getattr(main, 'resource_path', None)

def _patched_resource_path(relative_path):
    """Check EXE directory first, then fall back to _MEIPASS."""
    exe_path = os.path.join(app_base, relative_path)
    if os.path.exists(exe_path):
        return exe_path
    if _orig_resource_path:
        return _orig_resource_path(relative_path)
    return exe_path

main.resource_path = _patched_resource_path

# Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ Sound effects utility Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
def _play_sound(sound_name):
    """Play a WAV from resources/sounds/ in background thread. Silently skips if missing."""
    import threading
    def _do_play():
        try:
            import winsound
            sounds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "sounds")
            if getattr(sys, 'frozen', False):
                sounds_dir = os.path.join(os.path.dirname(sys.executable), "resources", "sounds")
            wav_path = os.path.join(sounds_dir, sound_name)
            if os.path.exists(wav_path):
                # SND_FILENAME only (synchronous in thread) â€” SND_ASYNC breaks in daemon threads
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
        except Exception:
            pass
    threading.Thread(target=_do_play, daemon=True).start()

# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 2: Lore System
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

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
    # â”€â”€ Ammunition (1 SCU box each) â”€â”€
    "size 1 ammunition": 1.0, "size 2 ammunition": 1.0, "size 3 ammunition": 1.0,
    "size 4 ammunition": 1.0, "size 5 ammunition": 1.0, "size 6 ammunition": 1.0,
    "size 7 ammunition": 1.0,
    "decoy countermeasures": 1.0, "noise countermeasures": 1.0,
    # â”€â”€ Missiles (bounding box cage grid footprint, patch 4.9+) â”€â”€
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
    # â”€â”€ Materials & Commodities (SCU = 1.0, cSCU = 0.01) â”€â”€
    "quantum fuel": 1.0, "hydrogen fuel": 1.0,
    "recycled material composite (rmc)": 1.0,
    "construction materials": 0.01,
    "pancea medgel canister": 0.05,
    "stor-all 1 scu storage container": 1.0,
    "stor*all 2 scu self-storage container": 2.0,
    "stor*all 4 scu self-storage container": 4.0,
    "stor*all 8 scu self-storage container": 8.0,
    # â”€â”€ Refined Ores (cSCU = 0.01 SCU per unit) â”€â”€
    "refined silicon": 0.01, "refined iron": 0.01, "refined copper": 0.01,
    "refined titanium": 0.01, "refined gold": 0.01, "refined laranite": 0.01,
    "refined agricium": 0.01, "refined bexlite": 0.01, "refined taranite": 0.01,
    "refined quantainium": 0.01,
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

# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 3: Image Processing
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

def extract_signature_from_sheet(img):
    bbox = img.getbbox()
    if not bbox:
        return img
    ink_img = img.crop(bbox)
    w, h = ink_img.size
    col_ink = [0] * w
    for x in range(w):
        for y in range(h):
            pixel = ink_img.getpixel((x, y))
            if pixel[3] > 0:
                col_ink[x] += 1
    gaps = []
    in_gap = False
    gap_start = 0
    for x in range(w):
        is_empty = col_ink[x] <= 2
        if is_empty and not in_gap:
            in_gap = True
            gap_start = x
        elif not is_empty and in_gap:
            in_gap = False
            gaps.append((gap_start, x))
    if in_gap:
        gaps.append((gap_start, w))
    wide_gaps = [g for g in gaps if (g[1] - g[0]) >= 15]
    if wide_gaps:
        sub_images = []
        prev_end = 0
        for gap in wide_gaps:
            if gap[0] > prev_end:
                sub_images.append(ink_img.crop((prev_end, 0, gap[0], h)))
            prev_end = gap[1]
        if prev_end < w:
            sub_images.append(ink_img.crop((prev_end, 0, w, h)))
        sub_images = [sim for sim in sub_images if sim.getbbox()]
        if sub_images:
            return random.choice(sub_images)
    return ink_img

def get_signatures_dir():
    app_dir = getattr(main, 'APP_DIR', '.')
    p0 = os.path.join(app_dir, 'resources', 'Podpisy')
    if os.path.exists(p0):
        return p0
    p1 = os.path.join(app_dir, 'Podpisy')
    if os.path.exists(p1):
        return p1
    # Check user's Downloads folder (portable fallback)
    p2 = os.path.join(os.path.expanduser("~"), "Downloads", "Podpisy")
    if os.path.exists(p2):
        return p2
    p3 = os.path.join(os.getcwd(), 'Podpisy')
    if not os.path.exists(p3):
        os.makedirs(p3, exist_ok=True)
    return p3

# Cache processed images - pre-processed PNGs don't need runtime processing
_SIG_CACHE = {}

def get_processed_barcode_path(podpisy_dir):
    """Return path to a random barcode PNG. Pre-processed = instant."""
    if 'barcode_paths' in _SIG_CACHE:
        cached = _SIG_CACHE['barcode_paths']
        return random.choice(cached) if cached else None
    
    processed = []
    for barcode_num in range(1, 5):
        # Try pre-processed PNG first, then JPEG fallback
        for ext in ['.png', '.jpeg', '.jpg']:
            p = os.path.join(podpisy_dir, f"B{barcode_num}{ext}")
            if os.path.exists(p):
                if ext == '.png':
                    # Pre-processed, use directly
                    processed.append(p)
                else:
                    # Runtime processing needed (fallback for old installs)
                    try:
                        from PIL import Image
                        img = Image.open(p).convert("RGBA")
                        if img.width > 600:
                            ratio = 600 / img.width
                            img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
                        datas = list(img.getdata())
                        newData = [(255,255,255,0) if px[0]>210 and px[1]>210 and px[2]>210 else px for px in datas]
                        img.putdata(newData)
                        bbox = img.getbbox()
                        if bbox: img = img.crop(bbox)
                        tmp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", f"temp_barcode_{barcode_num}.png")
                        img.save(tmp, "PNG")
                        processed.append(tmp)
                    except Exception:
                        processed.append(p)
                break
    
    _SIG_CACHE['barcode_paths'] = processed
    return random.choice(processed) if processed else None

def process_signature(podpisy_dir, name_key, is_captain=False):
    """Return path to a random signature PNG. Pre-processed = instant."""
    possible_files = []
    if is_captain:
        for i in range(1, 9):
            possible_files.append(f"{i}")
    else:
        name_key_lower = name_key.lower()
        if "thomas wolf" in name_key_lower:
            possible_files = ["Lt. Thomas Wolf 1", "Signature_of_Lt._Thomas_Wolf_2", "Signature_of_Lt._Thomas_Wolf_3"]
        elif "rebot1401" in name_key_lower:
            possible_files = ["Signature_Lstr_Rebot1401_1", "Signature_Lstr_Rebot1401_2", "Signature_Lstr_Rebot1401_3"]
        elif "cinnebar" in name_key_lower:
            possible_files = ["Signature_of_Rstr._Cinnebar_1", "Signature_of_Rstr._Cinnebar_2", "Signature_of_Rstr._Cinnebar_3"]
        elif "odin borr" in name_key_lower:
            possible_files = ["Signature_Str._Odin_Borr_1", "Signature_Str._Odin_Borr_2", "Signature_Str._Odin_Borr_3"]
    if not possible_files:
        return None
    
    cache_key = f"sig_{name_key}_{is_captain}"
    if cache_key in _SIG_CACHE:
        cached = _SIG_CACHE[cache_key]
        return random.choice(cached) if cached else None
    
    processed = []
    for chosen_base in possible_files:
        sig_path = None
        # Try PNG first (pre-processed), then JPEG
        for ext in [".png", ".jpeg", ".jpg"]:
            p = os.path.join(podpisy_dir, chosen_base + ext)
            if os.path.exists(p):
                sig_path = p
                break
        if not sig_path:
            # Fuzzy search
            try:
                for f in os.listdir(podpisy_dir):
                    f_base = os.path.splitext(f)[0]
                    if f_base.lower().strip() == chosen_base.lower().strip():
                        sig_path = os.path.join(podpisy_dir, f)
                        break
            except Exception:
                pass
        if not sig_path or not os.path.exists(sig_path):
            continue
        
        # Flatten alpha onto page background (fpdf doesn't support PNG alpha)
        if sig_path.lower().endswith('.png'):
            try:
                from PIL import Image
                img = Image.open(sig_path).convert("RGBA")
                # Create background matching document page color
                bg = Image.new("RGBA", img.size, (245, 247, 250, 255))
                bg.paste(img, mask=img.split()[3])  # Composite using alpha
                flat_path = sig_path.replace(".png", "_flat.png")
                bg.convert("RGB").save(flat_path)
                processed.append(flat_path)
            except Exception:
                processed.append(sig_path)  # Fallback to original
        else:
            # Runtime processing fallback
            try:
                from PIL import Image
                img = Image.open(sig_path).convert("RGBA")
                if img.width > 800:
                    ratio = 800 / img.width
                    img = img.resize((800, int(img.height * ratio)), Image.LANCZOS)
                datas = list(img.getdata())
                newData = [(255,255,255,0) if px[0]>200 and px[1]>200 and px[2]>200 else px for px in datas]
                img.putdata(newData)
                img = extract_signature_from_sheet(img)
                bbox = img.getbbox()
                if bbox: img = img.crop(bbox)
                tmp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", f"temp_sig_{chosen_base.replace(' ', '_')}.png")
                img.save(tmp, "PNG")
                processed.append(tmp)
            except Exception:
                processed.append(sig_path)
    
    _SIG_CACHE[cache_key] = processed
    return random.choice(processed) if processed else None

def process_r1_stamp(podpisy_dir):
    r1_path = None
    extensions = [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"]
    for ext in extensions:
        p = os.path.join(podpisy_dir, "R1" + ext)
        if os.path.exists(p):
            r1_path = p
            break
    if not r1_path:
        try:
            for f in os.listdir(podpisy_dir):
                f_base, f_ext = os.path.splitext(f)
                if f_base.lower() == "r1":
                    r1_path = os.path.join(podpisy_dir, f)
                    break
        except Exception:
            pass
    if not r1_path:
        return None
    
    # Check cache
    if 'r1_stamp' in _SIG_CACHE:
        return _SIG_CACHE['r1_stamp']
    
    # If PNG (pre-processed with rotation+transparency), use directly
    if r1_path.lower().endswith('.png'):
        _SIG_CACHE['r1_stamp'] = r1_path
        return r1_path
    
    # Runtime processing fallback for JPEG
    try:
        from PIL import Image
        img = Image.open(r1_path).convert("RGBA")
        if img.width > 300:
            ratio = 300 / img.width
            img = img.resize((300, int(img.height * ratio)), Image.LANCZOS)
        datas = list(img.getdata())
        newData = [(255,255,255,0) if px[0]>210 and px[1]>210 and px[2]>210 else px for px in datas]
        img.putdata(newData)
        rotated_img = img.rotate(15, expand=True, resample=Image.BICUBIC)
        r_datas = list(rotated_img.getdata())
        r_newData = [(px[0], px[1], px[2], 100) if px[3] > 0 else px for px in r_datas]
        rotated_img.putdata(r_newData)
        bbox = rotated_img.getbbox()
        if bbox: rotated_img = rotated_img.crop(bbox)
        tmp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "temp_r1_stamp.png")
        rotated_img.save(tmp, "PNG")
        _SIG_CACHE['r1_stamp'] = tmp
        return tmp
    except Exception as e:
        print(f"Error processing R1 stamp: {e}")
        return r1_path

# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 4: PDF Helpers
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

def get_telemetry(text, danger_level, items_list=None):
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

def draw_report_paragraph(self, x, y, width, text, redacted_sentences_indices=None, fully_redacted=False):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    self.set_xy(x, y)
    self.set_font("Roboto", "", 8)
    line_height = 4.0
    space_w = self.get_string_width(' ')
    current_x = x
    current_y = y
    for idx, sentence in enumerate(sentences):
        is_redacted = fully_redacted or (redacted_sentences_indices and idx in redacted_sentences_indices)
        words = sentence.split(' ')
        for w_idx, word in enumerate(words):
            word_to_draw = word + (' ' if w_idx < len(words) - 1 else '')
            word_w = self.get_string_width(word_to_draw)
            if current_x + word_w > x + width:
                current_x = x
                current_y += line_height
                self.set_xy(current_x, current_y)
            if is_redacted:
                self.set_fill_color(0, 0, 0)
                self.rect(current_x, current_y + 0.5, word_w - 0.5, line_height - 1, 'F')
                current_x += word_w
            else:
                self.set_text_color(30, 40, 60)
                self.cell(word_w, line_height, word_to_draw, ln=0)
                current_x += word_w
        if idx < len(sentences) - 1:
            current_x += space_w
    return current_y

def draw_signatures(self):
    current_y = self.get_y()
    if current_y > (self.h - 85):
        self.add_page()
        current_y = self.get_y()
    box_y = current_y + 4
    box_height = 276 - box_y
    if box_height < 75:
        self.add_page()
        box_y = 20
        box_height = 256
    self.set_line_width(0.3)
    self.set_draw_color(100, 116, 139)
    # White background with subtle border for manifest
    self.set_fill_color(245, 247, 250)
    self.rect(12, box_y, 186, box_height, 'DF')
    # Navy header bar for section title
    self.set_fill_color(15, 30, 60)
    self.rect(12, box_y, 186, 6, 'F')
    self.set_text_color(220, 220, 220)
    self.set_font("Roboto", "B", 8)
    self.text(14, box_y + 4.2, "LOGISTICS DIRECTIVE & FIELD REPORT")
    severity_level = self.severity.upper()
    danger_level = "LOW"
    if "MINOR" in severity_level:
        danger_level = "LOW"
    elif "SEVERE" in severity_level:
        danger_level = "MEDIUM"
    elif "CATASTROPHIC" in severity_level:
        danger_level = "HIGH"
        
    items_list = getattr(self, "manifest_items", [])
    current_manifest_hash = str([(item["name"], item["qty"]) for item in items_list])
    current_captain = self.captain if self.captain else ""
    current_officer = self.loading_officer if self.loading_officer else ""
    current_crew = self.loading_crew if self.loading_crew else ""
    current_vessel = self.vessel if self.vessel else ""
    
    global LORE_STORY_CACHE
    cache_invalid = (
        LORE_STORY_CACHE.get("text") is None or
        LORE_STORY_CACHE.get("danger_level") != danger_level or
        LORE_STORY_CACHE.get("vessel") != current_vessel or
        LORE_STORY_CACHE.get("manifest_hash") != current_manifest_hash or
        LORE_STORY_CACHE.get("captain") != current_captain or
        LORE_STORY_CACHE.get("officer") != current_officer or
        LORE_STORY_CACHE.get("crew") != current_crew
    )
    
    if cache_invalid:
        # Seed from session + vessel + cargo + danger for per-launch + per-config variation
        combined_seed = hash((_SESSION_SEED, current_vessel, current_manifest_hash, danger_level))
        _story_rng.seed(combined_seed)
        if danger_level == "LOW":
            story_idx = _story_rng.randint(0, 9)
        elif danger_level == "MEDIUM":
            story_idx = _story_rng.randint(10, 19)
        else:
            story_idx = _story_rng.randint(20, 29)
        story_template = stories[story_idx]
        
        cargo_sentence = get_cargo_context_sentence(items_list)
        story_template = story_template.replace("{ship}", "{ship}" + cargo_sentence)
        # Build cargo_type from actual items
        if items_list:
            top_items = sorted(items_list, key=lambda x: int(x.get('qty', 1)) if str(x.get('qty', 1)).isdigit() else 1, reverse=True)[:2]
            cargo_desc_parts = [ti['name'].split(' (')[0][:20] for ti in top_items]
            cargo_type = " and ".join(cargo_desc_parts) if cargo_desc_parts else "supply"
        else:
            cargo_type = "supply"
        
        crew_val = self.loading_crew
        is_crew_empty = not crew_val or crew_val.strip().upper() in ["NONE", "PENDING", "PENDING APPROVED", ""]
        if is_crew_empty:
            formatted_story = rephrase_crew_text(story_template, self.loading_officer)
            formatted_story = formatted_story.format(
                captain=self.captain,
                officer=self.loading_officer,
                ship=self.vessel,
                location=self.location,
                cargo_type=cargo_type
            )
        else:
            formatted_story = story_template.format(
                captain=self.captain,
                officer=self.loading_officer,
                crew=crew_val,
                ship=self.vessel,
                location=self.location,
                cargo_type=cargo_type
            )
        formatted_story = apply_synonyms(formatted_story)
        LORE_STORY_CACHE["text"] = formatted_story
        LORE_STORY_CACHE["danger_level"] = danger_level
        LORE_STORY_CACHE["vessel"] = current_vessel
        LORE_STORY_CACHE["manifest_hash"] = current_manifest_hash
        LORE_STORY_CACHE["captain"] = current_captain
        LORE_STORY_CACHE["officer"] = current_officer
        LORE_STORY_CACHE["crew"] = current_crew
        
    formatted_story = LORE_STORY_CACHE["text"]
    self.set_line_width(0.2)
    self.set_draw_color(180, 190, 200)
    self.line(140, box_y + 8, 140, box_y + box_height - 24)
    sec = self.security_level.upper()
    fully_redacted = False
    redacted_sentences_indices = []
    # CLASSIFIED (OFFICERS) = NO redaction at all
    # SECURED/RESTRICTED = redact every other sentence
    if "RESTRICTED" in sec or ("SECURED" in sec and "OFFICERS" not in sec and "ENCRYPTED" not in sec):
        sentences_count = len(re.split(r'(?<=[.!?])\s+', formatted_story))
        redacted_sentences_indices = [i for i in range(sentences_count) if i % 2 == 1]
    # PUBLIC = fully redacted
    elif "PUBLIC" in sec or "OPEN" in sec:
        fully_redacted = True
    # OFFICERS/ENCRYPTED/CLASSIFIED = no redaction
        
    paragraph_end_y = self.draw_report_paragraph(14, box_y + 10, 122, formatted_story, redacted_sentences_indices, fully_redacted)
    
    loose_items = []
    total_loose_vol = 0.0
    items_list = getattr(self, "manifest_items", [])
    
    # Whitelist: ONLY these categories go into Stor-All boxes
    STOR_ALL_CATEGORIES = [
        "pistol", "rifle", "shotgun", "smg", "lmg", "sniper", "knife", "weapon",
        "grenade", "multitool", "tractor",
        "food", "burrito", "sandwich", "noodle", "drink", "bottle", "bar ", "ration",
        "medpen", "medkit", "oxypen", "adrenapen",
        "mining gadget", "mining attachment", "mining head", "mining module",
        "armor", "helmet", "undersuit", "backpack", "chest", "legs", "arms",
        "flightsuit", "jacket", "vest",
    ]

    for item in items_list:
        name_low = item["name"].lower()
        qty = int(item["qty"]) if isinstance(item["qty"], (int, float)) or (isinstance(item["qty"], str) and item["qty"].isdigit()) else 1
        
        # Only whitelist items need Stor-All
        is_stor_all = any(cat in name_low for cat in STOR_ALL_CATEGORIES)
        if not is_stor_all:
            continue
        
        # Skip items already in SCU boxes
        box = item["box_size"].lower()
        if any(s in box for s in ["1 scu", "2 scu", "4 scu", "8 scu"]):
            continue
        
        unit_vol = 0.0
        for k, vol in volume_map.items():
            if k in name_low:
                unit_vol = vol
                break
        if unit_vol == 0.0:
            unit_vol = 0.005
        
        item_vol = qty * unit_vol
        total_loose_vol += item_vol
        loose_items.append({
            "name": item["name"],
            "qty": qty,
            "unit_vol": unit_vol,
            "total_vol": item_vol
        })
            
    # Available Stor-All sizes: usable capacity per box
    STOR_ALL_SIZES = [
        (0.125, "1/8 SCU", 0.10),
        (1.0,   "1 SCU",   0.85),
        (2.0,   "2 SCU",   1.70),
        (4.0,   "4 SCU",   3.40),
        (8.0,   "8 SCU",   6.80),
    ]
    
    def _pick_box_size(vol):
        """Pick the smallest Stor-All that fits ALL loose items in one box if possible."""
        for scu, label, cap in STOR_ALL_SIZES:
            if vol <= cap:
                return scu, label, cap
        return 8.0, "8 SCU", 6.80
    
    if total_loose_vol > 0:
        box_scu, box_label, max_capacity = _pick_box_size(total_loose_vol)
        num_boxes = math.ceil(total_loose_vol / max_capacity)
        # Cap at reasonable number
        num_boxes = min(num_boxes, 3)
    else:
        num_boxes = 0
        max_capacity = 0.85
        box_label = "1 SCU"
    
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
                "vol": fit_vol
            })
            box_vols[curr_box_idx] += fit_vol
            qty_remaining -= fit_qty
            
            if box_vols[curr_box_idx] >= max_capacity:
                curr_box_idx += 1
                
    if num_boxes > 0 and ("VERIFIED" not in sec and "PUBLIC" not in sec):
        self.set_font("Roboto", "B", 7)
        self.set_text_color(140, 100, 30)
        self.text(14, paragraph_end_y + 6, "LOGISTICS AUTO-BOXING PACKING MANIFEST:")
        self.set_font("Roboto", "", 6)
        self.set_text_color(40, 50, 70)
        for idx, box in enumerate(boxes):
            items_str = ", ".join(f"{entry['qty']}x {entry['name']}" for entry in box)
            if len(items_str) > 75:
                items_str = items_str[:72] + "..."
            self.text(14, paragraph_end_y + 9.5 + idx * 3.2, f"STOR-ALL #{idx+1} [{box_label}] [Used: {box_vols[idx]:.2f}/{max_capacity:.2f} SCU]: {items_str}")

    telemetry = get_telemetry(formatted_story, danger_level, items_list)
    self.set_font("Roboto", "B", 7.5)
    self.set_text_color(140, 100, 30)
    self.text(142, box_y + 11, "HOLD TELEMETRY SENSORS:")
    self.set_font("Roboto", "", 6.5)
    self.set_text_color(60, 70, 90)
    self.text(142, box_y + 16, "GRAVITY FIELD:")
    self.set_font("Roboto", "B", 6.5)
    if "ACTIVE" in telemetry["gravity"]:
        self.set_text_color(46, 204, 113)
    elif "WARNING" in telemetry["gravity"]:
        self.set_text_color(241, 196, 15)
    else:
        self.set_text_color(231, 76, 60)
    self.text(142, box_y + 19, telemetry["gravity"])
    self.set_font("Roboto", "", 6.5)
    self.set_text_color(60, 70, 90)
    self.text(142, box_y + 24, "ATM SEAL INTEGRITY:")
    self.set_font("Roboto", "B", 6.5)
    if "NOMINAL" in telemetry["atmosphere"]:
        self.set_text_color(46, 204, 113)
    elif "PRESSURE" in telemetry["atmosphere"] or "WARNING" in telemetry["atmosphere"]:
        self.set_text_color(241, 196, 15)
    else:
        self.set_text_color(231, 76, 60)
    self.text(142, box_y + 27, telemetry["atmosphere"])
    self.set_font("Roboto", "", 6.5)
    self.set_text_color(60, 70, 90)
    self.text(142, box_y + 32, "TRACTOR CLAMPS:")
    self.set_font("Roboto", "B", 6.5)
    if "LOCKED" in telemetry["clamps"]:
        self.set_text_color(46, 204, 113)
    elif "UNSTABLE" in telemetry["clamps"]:
        self.set_text_color(241, 196, 15)
    else:
        self.set_text_color(231, 76, 60)
    self.text(142, box_y + 35, telemetry["clamps"])
    self.set_font("Roboto", "", 6.5)
    self.set_text_color(60, 70, 90)
    self.text(142, box_y + 40, "HAZMAT / RADIATION:")
    self.set_font("Roboto", "B", 6.5)
    if "CLEAR" in telemetry["hazmat"]:
        self.set_text_color(46, 204, 113)
    elif "MONITORING" in telemetry["hazmat"]:
        self.set_text_color(241, 196, 15)
    else:
        self.set_text_color(231, 76, 60)
    self.text(142, box_y + 43, telemetry["hazmat"])
    
    # RENDER CARGO GRID SCHEMATIC
    grid_db_path = getattr(main, 'resource_path', lambda p: p)(os.path.join('resources', 'ship_grids_db.json'))
    vessel_clean = self.vessel
    for prefix in ["Aegis", "Anvil", "Drake", "RSI", "Crusader", "MISC", "Origin", "Consolidated Outland", "Argo", "Mirai", "Gatac", "Esperia"]:
        if vessel_clean.lower().startswith(prefix.lower()):
            vessel_clean = vessel_clean[len(prefix):].strip()
            break
            
    ship_grid = None
    if os.path.exists(grid_db_path):
        try:
            with open(grid_db_path, "r", encoding="utf-8") as gf:
                db_data = json.load(gf)
            vessel_low = self.vessel.lower().strip()
            vessel_clean_low = vessel_clean.lower().strip()
            # Strategy 1: Exact match on full name or cleaned name
            for key, val in db_data.items():
                kl = key.lower()
                if kl == vessel_low or kl == vessel_clean_low:
                    ship_grid = val
                    break
            # Strategy 2: Partial match — vessel name in DB key or DB key in vessel
            if not ship_grid:
                for key, val in db_data.items():
                    kl = key.lower()
                    if vessel_clean_low in kl or kl in vessel_clean_low or vessel_low in kl or kl in vessel_low:
                        ship_grid = val
                        break
            # Strategy 3: Word-based match — any significant word matches
            if not ship_grid:
                vessel_words = [w for w in vessel_low.split() if len(w) > 2]
                for key, val in db_data.items():
                    kl = key.lower()
                    if any(w in kl for w in vessel_words):
                        ship_grid = val
                        break
        except Exception:
            pass

    grid_area_x = 142
    grid_area_y = box_y + 10
    grid_area_w = 52
    grid_area_h = box_height - 35

    # No grid on page 1 — full grid is on page 3
    self.set_line_width(0.15)
    self.set_draw_color(180, 190, 200)
    self.set_fill_color(235, 238, 242)
    self.rect(grid_area_x, grid_area_y, grid_area_w, grid_area_h, 'DF')

    if "PUBLIC" in sec or "OPEN" in sec:
        self.set_font("Roboto", "B", 6)
        self.set_text_color(140, 100, 30)
        self.text(grid_area_x + 2, grid_area_y + 4, "CARGO [REDACTED]")
    elif ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", "?")
        grps = len(ship_grid.get("groups", []))
        self.set_font("Roboto", "B", 6)
        self.set_text_color(140, 100, 30)
        self.text(grid_area_x + 2, grid_area_y + 4, "CARGO GRID")
        self.set_font("Roboto", "", 5.5)
        self.set_text_color(60, 70, 90)
        sfx = "s" if grps > 1 else ""
        self.text(grid_area_x + 4, grid_area_y + 10, f"{cap} SCU / {grps} section{sfx}")
        self.set_font("Roboto", "I", 5)
        self.set_text_color(100, 110, 140)
        self.text(grid_area_x + 4, grid_area_y + 16, "SEE PAGE 3")
        self.text(grid_area_x + 4, grid_area_y + 20, "FULL SCHEMATIC")
    else:
        self.set_font("Roboto", "I", 6.5)
        self.set_text_color(80, 90, 110)
        self.text(grid_area_x + 4, grid_area_y + 12, "NO GRID DATA")

    
    # Render Cargo Grid Placement Directive
    # ── DYNAMIC CARGO DIRECTIVE (works for ALL ships) ──
    vessel_upper = self.vessel.upper()
    load_loc = getattr(self, 'location', '') or ''
    load_type = ''
    try:
        if hasattr(self, '_loading_type_var'):
            load_type = self._loading_type_var.get()
        elif hasattr(self, 'loading_type_var'):
            load_type = self.loading_type_var.get()
    except: pass
    loc_sfx = f" Staging: {load_loc}." if load_loc else ""
    type_sfx = f" Method: {load_type}." if load_type else ""
    if ship_grid and "groups" in ship_grid:
        cap = ship_grid.get("capacity", 0)
        grp_count = len(ship_grid.get("groups", []))
        max_height = 1
        max_width = 1
        for g in ship_grid.get("groups", []):
            for gr in g.get("grids", []):
                max_height = max(max_height, gr.get("height", 1))
                max_width = max(max_width, gr.get("width", 1))
        max_crate = min(32, max_width * max_width)
        holds = f"{grp_count} hold section{'s' if grp_count > 1 else ''}"
        grid_directive = f"CARGO DIRECTIVE: {holds} ({cap} SCU). Stack: {max_height}h, {max_crate} SCU max.{loc_sfx}{type_sfx} Clamps locked."
    else:
        grid_directive = f"CARGO DIRECTIVE: Standard bay. Grid-lock all.{loc_sfx}{type_sfx} Verify clamp power."

    self.set_font("Roboto", "I", 5.5)
    self.set_text_color(60, 70, 90)
    self.set_xy(14, box_y + box_height - 29)
    # Cargo directive — redact for PUBLIC
    if "PUBLIC" in sec or "OPEN" in sec:
        self.cell(118, 4, "CARGO DIRECTIVE: [REDACTED // PUBLIC CHANNEL]", ln=0)
    else:
        self.cell(118, 4, grid_directive[:140], ln=0)

    # RECOMMENDED LOGISTICS SHUTTLE — redact for PUBLIC
    if "PUBLIC" not in sec and "OPEN" not in sec:
        try:
            total_cargo_scu = sum(
                int(float(i.get("qty", 1))) * (
                    8 if "8 scu" in i.get("box_size", "").lower()
                    else 4 if "4 scu" in i.get("box_size", "").lower()
                    else 1 if "1 scu" in i.get("box_size", "").lower()
                    else 0.05
                )
                for i in items_list
            ) + num_boxes
            shuttle_rec = _recommend_shuttle(self.vessel, total_cargo_scu)
            if shuttle_rec and shuttle_rec.get("shuttle"):
                self.set_font("Roboto", "B", 5)
                self.set_text_color(180, 140, 30)
                self.text(14, box_y + box_height - 25.5,
                    f"RECOMMENDED LOGISTICS VEHICLE: {shuttle_rec['shuttle'].upper()} // {shuttle_rec.get('method', 'EVA')}")
        except Exception:
            pass

    sig_section_y = box_y + box_height - 24
    self.set_line_width(0.2)
    self.set_draw_color(15, 30, 60)
    self.line(12, sig_section_y, 198, sig_section_y)
    self.set_text_color(15, 30, 60)
    self.set_font("Roboto", "B", 7)
    self.text(15, sig_section_y + 4, "LOADING OFFICER SIGNATURE")
    self.text(108, sig_section_y + 4, "SHIP CAPTAIN SIGNATURE")
    officer_name = self.loading_officer if self.loading_officer else "Authorized Logistics Officer"
    self.set_text_color(40, 50, 70)
    self.set_font("Roboto", "", 6)
    if ("VERIFIED" in sec or "PUBLIC" in sec) and self.loading_officer:
        self.set_fill_color(0, 0, 0)
        self.rect(15, sig_section_y + 6, 80, 10, 'F')
        self.rect(108, sig_section_y + 6, 80, 10, 'F')
        self.text(15, sig_section_y + 9, "REDACTED // SECURED CHANNEL")
        self.text(108, sig_section_y + 9, "REDACTED // SECURED CHANNEL")
    else:
        self.text(15, sig_section_y + 9, f"Name: {officer_name}")
        captain_name = self.captain if self.captain else "Authorized Ship Captain"
        self.text(108, sig_section_y + 9, f"Name: {captain_name}")
        # Extract ranks from names (e.g. "Lt. Wolf" -> "Lieutenant")
        officer_rank, _ = extract_rank(officer_name)
        captain_rank, _ = extract_rank(captain_name)
        self.text(15, sig_section_y + 12, f"Rank: {officer_rank}")
        self.text(108, sig_section_y + 12, f"Rank: {captain_rank}")
        
        podpisy_dir = get_signatures_dir()
        officer_sig_img = process_signature(podpisy_dir, officer_name, is_captain=False)
        captain_sig_img = process_signature(podpisy_dir, captain_name, is_captain=True)
        r1_stamp_img = process_r1_stamp(podpisy_dir)
        
        if officer_sig_img and os.path.exists(officer_sig_img):
            self.image(officer_sig_img, x=45, y=sig_section_y + 5, w=35, h=8)
        else:
            self.set_font("Courier", "I", 7)
            self.set_text_color(150, 150, 150)
            self.text(50, sig_section_y + 9, f"~ {officer_name} ~")
            self.set_font("Roboto", "", 6)
            
        if captain_sig_img and os.path.exists(captain_sig_img):
            self.image(captain_sig_img, x=138, y=sig_section_y + 5, w=35, h=8)
        else:
            self.set_font("Courier", "I", 7)
            self.set_text_color(150, 150, 150)
            self.text(143, sig_section_y + 9, f"~ {captain_name} ~")
            self.set_font("Roboto", "", 6)
            
        if r1_stamp_img and os.path.exists(r1_stamp_img):
            self.image(r1_stamp_img, x=51, y=sig_section_y - 2, w=22, h=18)

    self.set_font("Roboto", "B", 6)
    self.set_text_color(80, 90, 110)
    self.text(15, sig_section_y + 15.5, "VERIFIED SECURITY SIGNATURE SEAL - 44TH BATTLE GROUP LOGISTICS")

    # ══════ PAGE 3: FULL-SIZE CARGO GRID ══════
    if ship_grid and "groups" in ship_grid and "PUBLIC" not in sec and "OPEN" not in sec:
        self.add_page()
        self.set_fill_color(245, 247, 250)
        self.rect(0, 0, 210, 297, 'F')
        self.set_draw_color(15, 30, 60)
        self.set_line_width(1.0)
        self.rect(8, 8, 194, 281)
        self.set_line_width(0.3)
        self.rect(10, 10, 190, 277)

        # Title bar
        self.set_fill_color(15, 30, 60)
        self.rect(10, 10, 190, 10, 'F')
        self.set_text_color(200, 168, 78)
        self.set_font("Roboto", "B", 10)
        self.text(14, 17, f"CARGO GRID SCHEMATIC // {self.vessel.upper()}")
        self.set_font("Roboto", "", 7)
        self.set_text_color(180, 190, 210)
        self.text(150, 17, f"REQ: {getattr(self, 'req_id', 'N/A')}")

        # Grid area
        lg_x, lg_y, lg_w, lg_h = 15, 28, 180, 210
        self.set_line_width(0.2)
        self.set_draw_color(180, 190, 200)
        self.set_fill_color(235, 238, 242)
        self.rect(lg_x, lg_y, lg_w, lg_h, 'DF')

        self.set_font("Roboto", "B", 8)
        self.set_text_color(140, 100, 30)
        self.text(lg_x + 3, lg_y + 6, f"HOLD CARGO ALLOCATION — {ship_grid.get('capacity', '?')} SCU")
        self.set_font("Roboto", "I", 5)
        self.set_text_color(100, 110, 130)
        self.text(lg_x + lg_w - 20, lg_y + lg_h - 3, u"BOW \u2192")

        groups = ship_grid["groups"]
        cells = []
        min_x = min_z = float('inf')
        max_x = max_z = float('-inf')
        for g in groups:
            gx, gz = g.get("x", 0), g.get("z", 0)
            for gr in g.get("grids", []):
                w, h = gr.get("width", 4), gr.get("height", 1)
                for cx in range(w):
                    for cz in range(h):
                        px, pz = gx + cx, gz + cz
                        cells.append((px, pz))
                        min_x, max_x = min(min_x, px), max(max_x, px)
                        min_z, max_z = min(min_z, pz), max(max_z, pz)

        if cells:
            grid_w = max_x - min_x + 1
            grid_h = max_z - min_z + 1

            # Cell size to fill grid area
            cell_w = min((lg_w - 20) / max(grid_w, 1), 16)
            cell_h = min((lg_h - 30) / max(grid_h, 1), 16)
            cell_sz = min(cell_w, cell_h)
            depth = cell_sz * 0.35  # 3D depth offset

            total_w = grid_w * cell_sz + depth
            total_h = grid_h * cell_sz + depth
            base_x = lg_x + (lg_w - total_w) / 2
            base_y = lg_y + (lg_h - total_h) / 2 + 5

            # Cargo volumes
            items_list = getattr(self, "manifest_items", [])
            commodity_vol = supply_vol = ordnance_vol = 0
            for item in items_list:
                nm = item["name"].lower()
                try: q = int(float(item.get("qty", 1)))
                except: q = 1
                vol = q * volume_map.get(nm, 0.01)
                if any(x in nm for x in ["missile", "torpedo", "bomb"]): ordnance_vol += vol
                elif any(x in nm for x in ["rmc", "silicon", "quantanium", "ore", "scrap"]): commodity_vol += vol
                else: supply_vol += vol
            total_vol = commodity_vol + supply_vol + ordnance_vol
            capacity = ship_grid.get("capacity", max(len(cells), 1))

            # Sort for back-to-front rendering
            for cell_x, cell_z in sorted(cells, key=lambda c: (c[1], c[0])):
                rx = cell_x - min_x
                rz = cell_z - min_z
                cx = base_x + rx * cell_sz
                cy = base_y + rz * cell_sz

                idx = rx * grid_h + rz
                frac = idx / max(len(cells), 1)
                if frac < (commodity_vol / max(total_vol, 0.01)):
                    top_c, side_c, lbl = (120,200,120), (80,160,80), "CMD"
                elif frac < ((commodity_vol + supply_vol) / max(total_vol, 0.01)):
                    top_c, side_c, lbl = (120,170,220), (80,130,180), "SUP"
                elif frac < ((commodity_vol + supply_vol + ordnance_vol) / max(total_vol, 0.01)):
                    top_c, side_c, lbl = (220,120,120), (180,80,80), "ORD"
                else:
                    top_c, side_c, lbl = (50,55,65), (30,35,40), ""

                s = cell_sz * 0.9
                d = depth * 0.8

                # Side face (right)
                self.set_fill_color(*side_c)
                self.set_draw_color(160, 165, 175)
                self.set_line_width(0.1)
                self.rect(cx + s, cy - d, d, s, 'DF')

                # Side face (bottom)
                r2, g2, b2 = side_c
                self.set_fill_color(max(0,r2-20), max(0,g2-20), max(0,b2-20))
                self.rect(cx, cy + s - d, s, d, 'DF')

                # Top face
                self.set_fill_color(*top_c)
                self.rect(cx, cy - d, s, s, 'DF')

                # Label
                if lbl:
                    self.set_font("Roboto", "B", max(3.5, min(5.5, cell_sz * 0.35)))
                    self.set_text_color(255, 255, 255)
                    self.text(cx + s * 0.2, cy - d + s * 0.55, lbl)

        # Legend
        legend_y = lg_y + lg_h + 5
        self.set_font("Roboto", "B", 7)
        self.set_text_color(40, 40, 50)
        self.text(lg_x, legend_y, "LEGEND:")
        for i, (clr, nm) in enumerate([((120,200,120),"Commodity"), ((120,170,220),"Supply"),
                                        ((220,120,120),"Ordnance"), ((50,55,65),"Free")]):
            lx = lg_x + 22 + i * 35
            self.set_fill_color(*clr)
            self.rect(lx, legend_y - 3, 5, 4, 'F')
            self.set_font("Roboto", "", 6)
            self.set_text_color(60, 60, 70)
            self.text(lx + 6, legend_y, nm)

        # Ship info
        self.set_font("Roboto", "", 6)
        self.set_text_color(80, 90, 110)
        iy = legend_y + 8
        cap = ship_grid.get("capacity", "?")
        self.text(lg_x, iy, f"Vessel: {self.vessel} | Capacity: {cap} SCU | Sections: {len(groups)} | Cells: {len(cells)}")
        self.text(lg_x, iy + 5, f"Commodity: {commodity_vol:.0f} SCU | Supply: {supply_vol:.0f} SCU | Ordnance: {ordnance_vol:.0f} SCU | Free: {max(0, capacity - total_vol):.0f} SCU")
        self.text(lg_x, iy + 10, "CLASSIFICATION: " + sec)

# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 5: Resource Path + Font Cache
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

def resource_path_patched(relative_path):
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    
    p = os.path.join(base, 'resources', relative_path)
    if os.path.exists(p):
        return p
    p2 = os.path.join(base, relative_path)
    if os.path.exists(p2):
        return p2
        
    if getattr(sys, 'frozen', False):
        base_temp = sys._MEIPASS
        p3 = os.path.join(base_temp, 'resources', relative_path)
        if os.path.exists(p3):
            return p3
        p4 = os.path.join(base_temp, relative_path)
        if os.path.exists(p4):
            return p4
            
    return os.path.join(base, relative_path)

main.resource_path = resource_path_patched

# Apply logo search paths
local_logo = getattr(main, 'resource_path', lambda p: p)("logo.png")
local_logo_uee = getattr(main, 'resource_path', lambda p: p)("logo_uee44.png")
if os.path.exists(local_logo): main.LOGO_FILE = local_logo
if os.path.exists(local_logo_uee): main.LOGO_UEE_FILE = local_logo_uee

# Subclass FPDF templates to implement v0.6 features
OriginalMilitaryPDF = main.MilitaryPDF

# Pre-cache Roboto font data at module level (parse TTF once, reuse everywhere)
_FONT_CACHE = {}
def _precache_fonts():
    """Parse Roboto TTF files once and store font definitions for reuse.
    
    IMPORTANT: fpdf 1.7.2 generates .pkl cache files next to the .ttf files.
    These .pkl files contain the ABSOLUTE PATH from the machine where they were
    generated. If the installer ships pre-generated .pkl files from a different
    machine (e.g. C:\\Users\\tomas.foldyna\\...), they will cause a
    'No such file or directory' error on any other PC.
    
    Fix: Always delete stale .pkl files before calling add_font so that fpdf
    regenerates them with the correct local paths for the current machine.
    """
    import fpdf
    fonts_dir = getattr(main, 'resource_path', lambda p: p)('fonts')
    if not os.path.exists(fonts_dir):
        fonts_dir = getattr(main, 'resource_path', lambda p: p)('resources/fonts')
    reg_font = os.path.join(fonts_dir, "Roboto-Regular.ttf")
    bold_font = os.path.join(fonts_dir, "Roboto-Bold.ttf")

    # --- Delete stale .pkl files from any previous machine ---
    # This guarantees fpdf always regenerates them with the correct local paths.
    for pkl_name in ("Roboto-Regular.pkl", "Roboto-Regular.cw127.pkl",
                     "Roboto-Bold.pkl", "Roboto-Bold.cw127.pkl"):
        pkl_path = os.path.join(fonts_dir, pkl_name)
        try:
            if os.path.exists(pkl_path):
                os.remove(pkl_path)
        except Exception:
            pass  # Read-only filesystem edge case — silently ignore
    # ---------------------------------------------------------

    # Create a temporary PDF just to parse fonts once
    tmp = fpdf.FPDF()
    try:
        if os.path.exists(reg_font):
            tmp.add_font("Roboto", "", reg_font, uni=True)
            tmp.add_font("Roboto", "I", reg_font, uni=True)
        if os.path.exists(bold_font):
            tmp.add_font("Roboto", "B", bold_font, uni=True)
        # Store parsed font definitions
        for key, val in tmp.fonts.items():
            _FONT_CACHE[key] = val
    except Exception as e:
        print(f"[WARNING] Font pre-cache failed: {e}")

_precache_fonts()

# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 6: PatchedMilitaryPDF Class
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

class PatchedMilitaryPDF(OriginalMilitaryPDF):
    def add_font(self, family, style='', fname='', uni=False):
        # Use pre-cached font data if available to avoid slow TTF parsing
        cache_key = family.lower()
        if style: cache_key += style.lower()
        if cache_key in _FONT_CACHE:
            self.fonts[cache_key] = _FONT_CACHE[cache_key]
            return
        # Force uni=True for .ttf files to avoid cp1250 pickle.load crash on Windows
        if fname and fname.lower().endswith('.ttf'):
            uni = True
        super().add_font(family, style, fname, uni=uni)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "font_family_name"):
            self.font_family_name = "Arial"
        self.original_rows = []
        if not hasattr(self, 'security_level'):
            self.security_level = 'ALL'
        # Inject pre-cached fonts
        if _FONT_CACHE:
            self.fonts.update(_FONT_CACHE)

    def draw_table_row(self, pdf_row_index, name, box_size, qty, price, is_courtesy, total, unit, total_volume):
        # Force numeric types to avoid '>' str vs int errors in main.pyc
        try: qty = int(float(qty)) if not isinstance(qty, (int, float)) else qty
        except: qty = 1
        try: price = float(price) if not isinstance(price, (int, float)) else price
        except: price = 0.0
        try: total = float(total) if not isinstance(total, (int, float)) else total
        except: total = 0.0
        try: total_volume = float(total_volume) if not isinstance(total_volume, (int, float)) else total_volume
        except: total_volume = 0.0
        self.original_rows.append({
            'pdf_row_index': pdf_row_index,
            'name': str(name),
            'box_size': str(box_size),
            'qty': int(qty),
            'price': float(price),
            'is_courtesy': bool(is_courtesy),
            'unit': str(unit),
            'total_volume': float(total_volume)
        })

    def draw_table_footer(self, grand_total):
        official_uniforms = [
            "tcs-4 undersuit", "tcs-4 undersuit black", "tcs-4 undersuit black/grey",
            "tailwind flight suit", "tailwind helmet",
            "omni-afs sapphire slate", "omni-afs sapphire slate helmet",
            "adp-mk4 helmet woodland", "adp-mk4 core woodland", "adp-mk4 arms woodland", "adp-mk4 legs woodland", "csp-68h backpack",
            "orc-mkx helmet woodland", "orc-mkx core woodland", "orc-mkx arms woodland", "orc-mkx legs woodland", "csp-68m backpack",
            "field recon suit helmet", "field recon suit core", "field recon suit arms", "field recon suit legs", "csp-68l backpack",
            "aril helmet", "aril core", "aril arms", "aril legs", "aril backpack",
            "adiva jacket blue", "adiva jacket dark green", "adiva jacket imperial", "adiva jacket red", "adiva jacket white", "adiva jacket yellow",
            "lemarque pants", "deo black shirt", "prim black shoes", "ventra gloves black"
        ]
        official_weapons = [
            "fs-9 lmg", "fs-9 magazine",
            "p4-ar \"nightstalker\" rifle", "p4-ar rifle", "p4-ar magazine",
            "f55 lmg", "f55 lmg magazine",
            "p8-ar rifle", "p8-ar magazine",
            "p6-lr sniper rifle", "p6-lr magazine",
            "br2 shotgun", "br2 magazine",
            "p8-sc smg", "p8-sc magazine",
            "s-38 pistol", "s-38 magazine"
        ]
        
        for r in self.original_rows:
            name_low = r['name'].lower().strip()
            is_uniform = any(w in name_low for w in ["suit", "helmet", "core", "arms", "legs", "backpack", "jacket", "pants", "shirt", "shoes", "gloves"])
            is_weapon = any(w in name_low for w in ["rifle", "pistol", "smg", "lmg", "shotgun", "sniper", "magazine", "cq7", "coda"])
            
            if is_uniform:
                if name_low not in official_uniforms:
                    r['name'] = r['name'] + " [UNOFFICIAL EQ]"
            elif is_weapon:
                clean_name = name_low.replace('"', '').strip()
                clean_official = [w.replace('"', '').strip() for w in official_weapons]
                if clean_name not in clean_official:
                    r['name'] = r['name'] + " [UNOFFICIAL EQ]"

        total_loose_vol = 0.0
        for r in self.original_rows:
            name_low = r['name'].lower()
            qty = int(r['qty']) if isinstance(r['qty'], (int, float)) or (isinstance(r['qty'], str) and r['qty'].isdigit()) else 1
            
            unit_vol = 0.0
            is_loose = False
            for k, vol in volume_map.items():
                if k in name_low:
                    unit_vol = vol
                    is_loose = True
                    break
                    
            if is_loose or "unit" in r['box_size'].lower():
                if any(x in name_low for x in ["missile", "torpedo", "bomb", "seeker", "colossus", "stormburst"]):
                    continue
                if unit_vol == 0.0:
                    unit_vol = 0.005
                total_loose_vol += qty * unit_vol
                
        remaining = total_loose_vol
        boxes_to_add = []
        # Stor-All prices (approximate in-game prices)
        STOR_PRICES = {"1 SCU": 1500, "2 SCU": 2800, "4 SCU": 5200, "8 SCU": 9500}
        # Use fewest boxes possible: try one big box first
        if remaining <= 1.0:
            boxes_to_add.append(("Stor-All 1 SCU Storage Container", "1 SCU", 1.0))
        elif remaining <= 2.0:
            boxes_to_add.append(("Stor*All 2 SCU Self-Storage Container", "2 SCU", 2.0))
        elif remaining <= 4.0:
            boxes_to_add.append(("Stor*All 4 SCU Self-Storage Container", "4 SCU", 4.0))
        elif remaining <= 8.0:
            boxes_to_add.append(("Stor*All 8 SCU Self-Storage Container", "8 SCU", 8.0))
        else:
            # Multiple boxes needed — use 8 SCU + remainder
            full_8 = int(remaining // 8)
            for _ in range(min(full_8, 2)):
                boxes_to_add.append(("Stor*All 8 SCU Self-Storage Container", "8 SCU", 8.0))
            leftover = remaining - full_8 * 8
            if leftover > 4.0:
                boxes_to_add.append(("Stor*All 8 SCU Self-Storage Container", "8 SCU", 8.0))
            elif leftover > 2.0:
                boxes_to_add.append(("Stor*All 4 SCU Self-Storage Container", "4 SCU", 4.0))
            elif leftover > 1.0:
                boxes_to_add.append(("Stor*All 2 SCU Self-Storage Container", "2 SCU", 2.0))
            elif leftover > 0.01:
                boxes_to_add.append(("Stor-All 1 SCU Storage Container", "1 SCU", 1.0))

        # Save for supply route STOP 0
        self._stor_all_boxes = boxes_to_add
        for name, box_size, total_vol in boxes_to_add:
            box_price = STOR_PRICES.get(box_size, 1500)
            self.original_rows.append({
                'pdf_row_index': len(self.original_rows) + 1,
                'name': name,
                'box_size': box_size,
                'qty': "1",
                'price': box_price,
                'is_courtesy': False,
                'unit': "SCU",
                'total_volume': total_vol
            })
            
        self.manifest_items = []
        for idx, r in enumerate(self.original_rows):
            self.manifest_items.append({
                'name': r['name'],
                'qty': r['qty'],
                'box_size': r['box_size'],
                'total_volume': r['total_volume']
            })
            row_total = float(r['price']) * (int(r['qty']) if str(r['qty']).isdigit() else 1)
            super().draw_table_row(
                idx + 1,
                str(r['name']),
                str(r['box_size']),
                int(r['qty']),
                float(r['price']),
                bool(r['is_courtesy']),
                float(row_total),
                str(r['unit']),
                float(r['total_volume'])
            )
            
        super().draw_table_footer(grand_total)

    def cell(self, w, h, txt='', border=0, ln=0, align='', fill=False, link=''):
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ''
        redacted = False
        txt_clean = txt.strip().upper() if txt else ''
        
        # ALL / CLASSIFIED = NO redaction â€” everything visible
        if 'ALL' in sec or 'CLASSIFIED' in sec or 'OFFICERS' in sec or 'ENCRYPTED' in sec:
            pass  # No redaction
        
        
        # PUBLIC: redact ~90% (names, all prices, totals, locations)
        elif 'PUBLIC' in sec or 'OPEN' in sec:
            # Names
            if self.captain and self.captain.strip() and self.captain.upper() in txt_clean: redacted = True
            elif self.loading_officer and self.loading_officer.strip() and self.loading_officer.upper() in txt_clean: redacted = True
            elif self.loading_crew and self.loading_crew.strip() and self.loading_crew.upper() in txt_clean: redacted = True
            # All price columns
            if w == 26 and h == 7 and txt_clean and txt_clean != "UNIT AUEC": redacted = True
            if w == 30 and h == 7 and txt_clean and txt_clean != "TOTAL AUEC  ": redacted = True
            # Any aUEC value
            if 'AUEC' in txt_clean or 'TOTAL' in txt_clean:
                if 'UNIT' not in txt_clean and 'MANIFEST' not in txt_clean and 'CLASSIFICATION' not in txt_clean:
                    redacted = True
        
        # SECURED/RESTRICTED: redact names only
        elif 'RESTRICTED' in sec or 'SECURED' in sec:
            if self.captain and self.captain.strip() and self.captain.upper() in txt_clean: redacted = True
            elif self.loading_officer and self.loading_officer.strip() and self.loading_officer.upper() in txt_clean: redacted = True
            elif self.loading_crew and self.loading_crew.strip() and self.loading_crew.upper() in txt_clean: redacted = True
        
        if redacted:
            x = self.get_x()
            y = self.get_y()
            self.set_fill_color(0, 0, 0)
            rect_w = w if w > 0 else self.get_string_width(txt)
            self.rect(x, y + 1, rect_w, h - 2, 'F')
            return super().cell(w, h, '', border, ln, align, False, link)
        else:
            return super().cell(w, h, txt, border, ln, align, fill, link)

    def text(self, x, y, txt=''):
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ''
        redacted = False
        txt_clean = txt.strip().upper() if txt else ''
        
        # ALL / CLASSIFIED (OFFICERS) = NO redaction
        if 'ALL' in sec or 'CLASSIFIED' in sec or 'OFFICERS' in sec or 'ENCRYPTED' in sec:
            pass
        
        # PUBLIC: redact names + prices
        elif 'PUBLIC' in sec or 'OPEN' in sec or 'RESTRICTED' in sec or 'SECURED' in sec:
            if self.captain and self.captain.strip() and self.captain.upper() in txt_clean: redacted = True
            elif self.loading_officer and self.loading_officer.strip() and self.loading_officer.upper() in txt_clean: redacted = True
            elif self.loading_crew and self.loading_crew.strip() and self.loading_crew.upper() in txt_clean: redacted = True
        
        if redacted:
            w = self.get_string_width(txt)
            self.set_fill_color(0, 0, 0)
            self.rect(x, y - 3, w, 4, 'F')
        else:
            super().text(x, y, txt)

    def draw_redacted_text(self, text, start_x, start_y, width, height, line_height):
        pass

    draw_signatures = draw_signatures
    draw_report_paragraph = draw_report_paragraph

    def header(self):
        # WHITE background + navy header bar
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, 210, 297, 'F')
        self.set_fill_color(15, 30, 60)
        self.rect(8, 6, 194, 22, 'F')
        self.set_draw_color(180, 150, 60)
        self.set_line_width(0.5)
        self.line(8, 28, 202, 28)
        base = os.path.dirname(os.path.abspath(__file__))
        bg44_logo = os.path.join(base, "resources", "cvbg44_logo_dark.png")
        if not os.path.exists(bg44_logo):
            bg44_logo = os.path.join(base, "resources", "cvbg44_logo.png")
        if not os.path.exists(bg44_logo):
            bg44_logo = os.path.join(base, "cvbg44_logo.png")
        if os.path.exists(bg44_logo):
            try: self.image(bg44_logo, x=11, y=7, w=18, h=18)
            except: pass
        # SLS29 (Starlifter) logo on right side
        sls29_logo = os.path.join(base, "resources", "sls29_logo.png")
        if os.path.exists(sls29_logo):
            try: self.image(sls29_logo, x=183, y=7, w=18, h=18)
            except: pass
        try: self.set_font("Roboto", "B", 12)
        except: self.set_font("Helvetica", "B", 12)
        self.set_text_color(255, 255, 255)
        super().text(32, 16, "44th BATTLEGROUP // CARGO MANIFEST")
        try: self.set_font("Roboto", "", 7)
        except: self.set_font("Helvetica", "", 7)
        self.set_text_color(180, 190, 210)
        super().text(32, 22, "UEE FLEET LOGISTICS COMMAND // REQUISITION DOCUMENT")
        podpisy_dir = get_signatures_dir()
        barcode_file = get_processed_barcode_path(podpisy_dir)
        if barcode_file and os.path.exists(barcode_file):
            self.image(barcode_file, x=145, y=29, w=45, h=8)
        _header_rng = random.Random(getattr(self, 'incident_seed', 42))
        hid = f"{_header_rng.choice(['REQ','SEC','LOG','TAC','NAV'])}-{_header_rng.choice(['44BG','UEE-9N','FLEET-44'])}-{_header_rng.randint(10000,99999)}-{_header_rng.choice(['ALPHA','BRAVO','X-RAY','OMEGA'])}"
        try: self.set_font("Roboto", "B", 5)
        except: self.set_font("Helvetica", "B", 5)
        self.set_text_color(100, 116, 139)
        super().text(10, 36, f"LEDGER HASH: {hid}")

        # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ Classification Badge (colored pill) Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
        sec = self.security_level.upper() if hasattr(self, 'security_level') else ""
        # Map exact classification to badge
        badge_text = sec.replace("_", " ") if sec else "CLASSIFIED"
        badge_r, badge_g, badge_b = 180, 30, 30  # Red default
        if not sec or sec == "ALL":
            badge_text = "INACTIVE CHANNEL"
            badge_r, badge_g, badge_b = 30, 30, 30  # Black
        elif "OFFICERS" in sec or "ENCRYPTED" in sec:
            badge_text = "OFFICERS ONLY"
            badge_r, badge_g, badge_b = 180, 30, 30  # Red
        elif "PUBLIC" in sec or "OPEN" in sec:
            badge_text = "OPEN TO PUBLIC"
            badge_r, badge_g, badge_b = 40, 140, 60  # Green
        elif "RESTRICTED" in sec or "SECURED" in sec:
            badge_text = "SECURED MEMBERS"
            badge_r, badge_g, badge_b = 200, 150, 30  # Amber
        
        badge_w = self.get_string_width(badge_text) + 8
        self.set_fill_color(badge_r, badge_g, badge_b)
        self.rect(10, 30, badge_w, 5, 'F')
        self.set_text_color(255, 255, 255)
        try: self.set_font("Roboto", "B", 6)
        except: self.set_font("Helvetica", "B", 6)
        super().text(14, 33.5, badge_text)
        # PNG watermark overlay — each classification has its own image
        watermark_map = {
            "OPEN_PUBLIC": "watermark_public.png",
            "OPEN PUBLIC": "watermark_public.png",
            "PUBLIC": "watermark_public.png",
            "RESTRICTED": "watermark_secured.png",
            "SECURED": "watermark_secured.png",
            "OFFICERS_ONLY_ENCRYPTED": "watermark_classified.png",
            "CLASSIFIED": "watermark_classified.png",
        }
        wm_file = None
        for key, fname in watermark_map.items():
            if key in sec:
                wm_file = fname
                break
        if wm_file:
            wm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), wm_file)
            if os.path.exists(wm_path):
                try:
                    # Overlay watermark across page (centered, semi-transparent via alpha in PNG)
                    page_w = self.w
                    page_h = self.h
                    # Place watermark centered on page
                    wm_w = page_w * 0.7
                    wm_x = (page_w - wm_w) / 2
                    wm_y = page_h * 0.25
                    self.image(wm_path, x=wm_x, y=wm_y, w=wm_w)
                except Exception as e:
                    print(f"[Watermark] {e}")
        # Reset
        self.set_text_color(0, 0, 0)

main.MilitaryPDF = PatchedMilitaryPDF

# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 7: Direct Supply Route PDF Generator
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

def generate_pdf_direct(self, save_path=None):
    """Generate Supply Route PDF directly using fpdf. Instant, no main.pyc."""
    import fpdf
    from tkinter import filedialog
    
    _ensure_trade_dbs()  # Lazy-load trade databases
    
    # Collect items from cargo table
    items = []
    for row in self.cargo_rows:
        name = row['name_var'].get().strip()
        qty_str = row['qty_var'].get().strip()
        unit = row.get('unit', 'unit')
        box_size = row['box_size_var'].get().strip() if 'box_size_var' in row else '1 SCU'
        price_str = row.get('price_var', None)
        if price_str and hasattr(price_str, 'get'):
            price_str = price_str.get().strip()
        else:
            price_str = '0'
        courtesy = row.get('courtesy_var', None)
        is_courtesy = False
        if courtesy and hasattr(courtesy, 'get'):
            is_courtesy = bool(courtesy.get())
        
        if not name or not qty_str or qty_str == '?':
            continue
        try:
            qty = int(float(qty_str))
            if qty <= 0: continue
        except ValueError:
            continue
        try:
            price = float(price_str.replace(',', '').replace(' ', '')) if price_str else 0
        except:
            price = 0
        
        items.append({
            'name': name, 'qty': qty, 'unit': unit,
            'box_size': box_size, 'price': price, 'is_courtesy': is_courtesy
        })
    
    if not items:
        messagebox.showerror("Error", "Cargo table is empty!")
        return
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ Auto-boxing: calculate Stor-All boxes for loose items Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    total_loose_vol = 0.0
    for item in items:
        name_low = item['name'].lower()
        unit_vol = 0.0
        is_loose = False
        for k, vol in volume_map.items():
            if k in name_low:
                unit_vol = vol
                is_loose = True
                break
        if is_loose or 'unit' in item['box_size'].lower():
            if any(x in name_low for x in ["missile", "torpedo", "bomb", "seeker", "colossus", "stormburst"]):
                continue
            if unit_vol == 0.0:
                unit_vol = 0.005
            total_loose_vol += item['qty'] * unit_vol
    
    boxes_to_add = []
    remaining = total_loose_vol
    while remaining > 0.0001:
        if remaining > 4.0:
            boxes_to_add.append(("Stor*All 8 SCU Self-Storage Container", "8 SCU"))
            remaining -= 8.0
        elif remaining > 2.0:
            boxes_to_add.append(("Stor*All 4 SCU Self-Storage Container", "4 SCU"))
            remaining -= 4.0
        elif remaining > 1.0:
            boxes_to_add.append(("Stor*All 2 SCU Self-Storage Container", "2 SCU"))
            remaining -= 2.0
        else:
            boxes_to_add.append(("Stor-All 1 SCU Storage Container", "1 SCU"))
            remaining -= 1.0
    
    for box_name, box_size in boxes_to_add:
        items.append({
            'name': box_name, 'qty': 1, 'unit': 'SCU',
            'box_size': box_size, 'price': 0, 'is_courtesy': True
        })
    
    # Get classification for filename
    classification_pre = self._classify_var.get() if hasattr(self, '_classify_var') else 'ALL'
    req_id_pre = self.req_id_var.get() if hasattr(self, 'req_id_var') else 'SR'
    safe_req = req_id_pre.replace(' ', '_').replace('/', '-')[:30]
    default_fn = f"{safe_req}_supply_route.pdf"
    
    if not save_path:
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_fn,
            title="Save Supply Route PDF"
        )
    if not save_path:
        return
    
    # Gather metadata
    req_id = self.req_id_var.get() if hasattr(self, 'req_id_var') else 'N/A'
    vessel = self.ship_selector.get() if hasattr(self, 'ship_selector') else ''
    officer = self.loading_officer_var.get() if hasattr(self, 'loading_officer_var') else ''
    captain = self.captain_var.get() if hasattr(self, 'captain_var') else ''
    crew = self.loading_crew_var.get() if hasattr(self, 'loading_crew_var') else ''
    location = self.location_var.get() if hasattr(self, 'location_var') else ''
    classification = self._classify_var.get() if hasattr(self, '_classify_var') else 'ALL'
    severity = self.severity_var.get() if hasattr(self, 'severity_var') else 'NOMINAL'
    delivery = self.delivery_date_var.get() if hasattr(self, 'delivery_date_var') else ''
    mission = self.mission_var.get() if hasattr(self, 'mission_var') else ''
    
    # Build PDF
    pdf = fpdf.FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(auto=False)
    
    # Inject pre-cached fonts
    if _FONT_CACHE:
        pdf.fonts.update(_FONT_CACHE)
    
    pdf.add_page()
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ PAGE BACKGROUND Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    pdf.set_fill_color(245, 238, 220)  # Parchment/industrial yellow
    pdf.rect(0, 0, 210, 297, 'F')
    
    # Gold border
    pdf.set_draw_color(180, 150, 60)
    pdf.set_line_width(1.5)
    pdf.rect(5, 5, 200, 287)
    pdf.set_line_width(0.3)
    pdf.rect(7, 7, 196, 283)
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ HEADER Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    pdf.set_fill_color(25, 32, 45)
    pdf.rect(10, 10, 190, 28, 'F')
    
    # SLS29 (Starlifter) logo (left)
    res_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
    sls29_logo = os.path.join(res_dir, "sls29_logo.png")
    if not os.path.exists(sls29_logo):
        sls29_logo = os.path.join(res_dir, "logo_dark.png")
    if not os.path.exists(sls29_logo):
        sls29_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
    if os.path.exists(sls29_logo):
        try: pdf.image(sls29_logo, x=12, y=12, w=20, h=20)
        except: pass
    
    # Title (shifted right for logo)
    pdf.set_text_color(200, 168, 78)
    try: pdf.set_font("Roboto", "B", 14)
    except: pdf.set_font("Helvetica", "B", 14)
    pdf.text(35, 22, "29th STARLIFTERS SQUADRON")
    
    try: pdf.set_font("Roboto", "", 8)
    except: pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(150, 160, 170)
    pdf.text(35, 28, "UEE LOGISTICS CENTER // SUPPLY ROUTE MANIFEST")
    
    # Classification badge
    badge_map = {
        'PUBLIC': ('OPEN TO PUBLIC', (34, 139, 34)),
        'SECURED': ('SECURED MEMBERS', (200, 150, 30)),
        'CLASSIFIED': ('OFFICERS ONLY', (180, 30, 30)),
        'ALL': ('INACTIVE CHANNEL', (60, 60, 60)),
    }
    badge_text, bc = badge_map.get(classification, ('INACTIVE CHANNEL', (60, 60, 60)))
    pdf.set_fill_color(*bc)
    badge_w = pdf.get_string_width(badge_text) + 8
    pdf.rect(195 - badge_w, 12, badge_w, 6, 'F')
    pdf.set_text_color(255, 255, 255)
    try: pdf.set_font("Roboto", "B", 6)
    except: pdf.set_font("Helvetica", "B", 6)
    pdf.text(195 - badge_w + 4, 16.5, badge_text)
    
    # Req ID right side
    pdf.set_text_color(120, 130, 140)
    try: pdf.set_font("Roboto", "", 7)
    except: pdf.set_font("Helvetica", "", 7)
    pdf.text(155, 28, f"REQ: {req_id}")
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ METADATA BLOCK Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    y = 42
    pdf.set_text_color(80, 70, 50)
    try: pdf.set_font("Roboto", "B", 7)
    except: pdf.set_font("Helvetica", "B", 7)
    
    meta_left = [
        ("Vessel:", vessel), ("Loading Officer:", officer),
        ("Ship Captain:", captain), ("Loading Crew:", crew if crew else "N/A")
    ]
    meta_right = [
        ("Location:", location),
        ("Delivery:", delivery if delivery else "N/A"), ("Mission:", mission if mission else "N/A")
    ]
    
    for i, (label, val) in enumerate(meta_left):
        try: pdf.set_font("Roboto", "B", 6.5)
        except: pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(120, 100, 50)
        pdf.text(12, y + i * 5, label)
        try: pdf.set_font("Roboto", "", 6.5)
        except: pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(50, 45, 35)
        pdf.text(42, y + i * 5, val)
    
    for i, (label, val) in enumerate(meta_right):
        try: pdf.set_font("Roboto", "B", 6.5)
        except: pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(120, 100, 50)
        pdf.text(110, y + i * 5, label)
        try: pdf.set_font("Roboto", "", 6.5)
        except: pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(50, 45, 35)
        pdf.text(138, y + i * 5, val)
    
    # ── PROCUREMENT ROUTE (rendered before cargo table) ──
    table_y = y + 24
    
    # Build procurement data: find where to buy each item
    # Determine loading location's system + planet for proximity sorting
    loading_planet = ""
    loading_system = "stanton"
    loading_loc = location.lower().strip()
    for cat_locs in _uex_locations_db.values():
        if isinstance(cat_locs, dict):
            for loc_name, loc_info in cat_locs.items():
                if loc_name.lower() in loading_loc or loading_loc in loc_name.lower():
                    loading_planet = (loc_info.get("planet") or "").lower()
                    loading_system = (loc_info.get("system") or "stanton").lower()
                    break
        if loading_planet:
            break
    
    # Realistic QT distances in minutes between planets/moons within Stanton
    # Same planet = 0, nearby = actual QT time in minutes
    _STANTON_QT_MINS = {
        ("hurston", "arccorp"): 6,
        ("hurston", "crusader"): 8,
        ("hurston", "microtech"): 14,
        ("arccorp", "crusader"): 5,
        ("arccorp", "microtech"): 11,
        ("crusader", "microtech"): 9,
    }
    # Pyro internal distances (all roughly 5-10 min)
    # Cross-system penalty: Stanton↔Pyro = 50 min (wormhole), Stanton↔Nyx = 80 min, Pyro↔Nyx = 40 min
    _SYSTEM_JUMP_PENALTY = {
        ("stanton", "pyro"): 50,
        ("stanton", "nyx"): 80,
        ("pyro", "nyx"): 40,
    }
    
    def _get_terminal_info(terminal_name):
        """Get (system, planet) for a terminal name from locations DB."""
        tn = terminal_name.lower()
        for cat_locs in _uex_locations_db.values():
            if isinstance(cat_locs, dict):
                for loc_name, loc_info in cat_locs.items():
                    if loc_name.lower() in tn or tn in loc_name.lower():
                        sys = (loc_info.get("system") or "stanton").lower()
                        pla = (loc_info.get("planet") or "").lower()
                        return sys, pla
        # Guess from name prefixes
        if "arc-l" in tn or "area 18" in tn or "area18" in tn: return "stanton", "arccorp"
        if "cru-l" in tn or "orison" in tn or "port olisar" in tn: return "stanton", "crusader"
        if "hur-l" in tn or "lorville" in tn or "everus" in tn: return "stanton", "hurston"
        if "mic-l" in tn or "new babbage" in tn or "port tressler" in tn: return "stanton", "microtech"
        if "levski" in tn: return "nyx", "delamar"
        if "ruin" in tn or "checkmate" in tn or "pyro" in tn: return "pyro", ""
        return "stanton", ""
    
    def _qt_distance(terminal_name):
        """Estimated QT travel time in minutes from loading location. Lower = closer."""
        t_sys, t_pla = _get_terminal_info(terminal_name)
        
        # Cross-system jump penalty
        if t_sys != loading_system:
            pair = tuple(sorted([loading_system, t_sys]))
            penalty = _SYSTEM_JUMP_PENALTY.get(pair, 100)
            return penalty  # wormhole jump + internal travel
        
        # Same system
        if not t_pla or not loading_planet:
            return 15  # unknown planet within same system
        if t_pla == loading_planet:
            return 0  # same planet / orbital station
        
        # Known intra-system distances
        pair = tuple(sorted([loading_planet, t_pla]))
        return _STANTON_QT_MINS.get(pair, 12)  # default ~12 min if unknown
    
    def _enrich_location(terminal_name):
        """Format location as 'System > Planet > Location'."""
        tn = terminal_name.lower()
        for cat_locs in _uex_locations_db.values():
            if isinstance(cat_locs, dict):
                for loc_name, loc_info in cat_locs.items():
                    if loc_name.lower() == tn or tn in loc_name.lower() or loc_name.lower() in tn:
                        system = loc_info.get("system", "Stanton")
                        planet = loc_info.get("planet", "")
                        if planet:
                            return f"{system} > {planet} > {loc_name}"
                        return f"{system} > {loc_name}"
        # Fallback: guess from name
        if "arc-l" in tn or "area" in tn: return f"Stanton > ArcCorp > {terminal_name}"
        if "cru-l" in tn or "orison" in tn: return f"Stanton > Crusader > {terminal_name}"
        if "hur-l" in tn or "lorville" in tn: return f"Stanton > Hurston > {terminal_name}"
        if "mic-l" in tn or "babbage" in tn: return f"Stanton > MicroTech > {terminal_name}"
        if "levski" in tn: return f"Nyx > Delamar > {terminal_name}"
        return terminal_name
    
    procurement = []
    has_loose_items = total_loose_vol > 0.0001 if 'total_loose_vol' in dir() else False
    
    for item in items:
        iname = item['name']
        iname_low = iname.lower().strip()
        best_loc = None
        best_price = None
        
        # Skip Stor-All boxes (auto-added)
        if 'stor' in iname_low and ('all' in iname_low or 'storage' in iname_low):
            has_loose_items = True
            continue
        
        # 1) Commodity trade DB — prefer nearby locations
        candidates = []
        for db_name, entries in _uex_trade_db.items():
            if db_name.lower() == iname_low or iname_low in db_name.lower() or db_name.lower() in iname_low:
                for e in entries:
                    if e.get('b', 0) > 0:
                        dist = _qt_distance(e['t'])
                        candidates.append((dist, e['b'], e['t']))
                break
        
        # 2) Items trade DB
        if not candidates and _uex_items_trade_db:
            for db_name, entries in _uex_items_trade_db.items():
                if db_name.lower() == iname_low or iname_low in db_name.lower() or db_name.lower() in iname_low:
                    for e in entries:
                        if e.get('b', 0) > 0:
                            dist = _qt_distance(e['t'])
                            candidates.append((dist, e['b'], e['t']))
                    break
        
        if candidates:
            # Sort by distance first, then price
            candidates.sort(key=lambda x: (x[0], x[1]))
            # Prefer same-system: if any candidate < 50 min, filter out wormhole ones
            same_sys = [c for c in candidates if c[0] < 50]
            if same_sys:
                candidates = same_sys
            best_loc = candidates[0][2]
            best_price = candidates[0][1]
        
        procurement.append({
            'name': iname, 'qty': item['qty'],
            'loc': _enrich_location(best_loc) if best_loc else 'CHECK LOCAL TERMINAL',
            'price': best_price,
            'raw_loc': best_loc or '',
            'qt_min': _qt_distance(best_loc) if best_loc else 99,
        })
    
    if procurement:
        proc_y = table_y
        if proc_y > 230:
            pdf.add_page()
            pdf.set_fill_color(245, 238, 220)
            pdf.rect(0, 0, 210, 297, 'F')
            pdf.set_draw_color(180, 150, 60)
            pdf.set_line_width(1.5)
            pdf.rect(5, 5, 200, 287)
            pdf.set_line_width(0.3)
            pdf.rect(7, 7, 196, 283)
            proc_y = 15
        
        # Header
        pdf.set_fill_color(25, 32, 45)
        pdf.rect(10, proc_y, 190, 7, 'F')
        pdf.set_text_color(200, 168, 78)
        try: pdf.set_font("Roboto", "B", 7)
        except: pdf.set_font("Helvetica", "B", 7)
        origin = location if location else "ORIGIN"
        pdf.text(12, proc_y + 5, f"PROCUREMENT ROUTE // FROM {origin[:30].upper()} (UEX PROXIMITY DATA)")
        
        try: pdf.set_font("Roboto", "", 5.5)
        except: pdf.set_font("Helvetica", "", 5.5)
        
        py = proc_y + 9
        
        # Per-item procurement list
        for i, p in enumerate(procurement):
            if py > 250:
                pdf.add_page()
                pdf.set_fill_color(245, 238, 220)
                pdf.rect(0, 0, 210, 297, 'F')
                pdf.set_draw_color(180, 150, 60)
                pdf.set_line_width(1.5)
                pdf.rect(5, 5, 200, 287)
                pdf.set_line_width(0.3)
                pdf.rect(7, 7, 196, 283)
                py = 15
            
            if i % 2 == 0:
                pdf.set_fill_color(235, 228, 210)
            else:
                pdf.set_fill_color(245, 238, 220)
            pdf.rect(10, py - 1, 190, 4.5, 'F')
            
            pdf.set_text_color(40, 35, 25)
            pdf.text(12, py + 2, f"{p['qty']}x {p['name'][:35]}")
            
            if p['price']:
                pdf.set_text_color(34, 120, 34)
                try: pdf.set_font("Roboto", "", 4.5)
                except: pdf.set_font("Helvetica", "", 4.5)
                qt = p.get('qt_min', 99)
                qt_str = f" (~{qt} min QT)" if qt > 0 else " (local)"
                if qt >= 50:
                    pdf.set_text_color(180, 50, 30)  # Red for wormhole
                    qt_str = f" (⚠ WORMHOLE ~{qt} min)"
                # Show terminal name + enriched location
                raw = p.get('raw_loc', '')
                if raw and raw.lower() not in p['loc'].lower():
                    loc_display = f"@ {raw[:25]} // {p['loc'][:30]}{qt_str}"
                else:
                    loc_display = f"@ {p['loc'][:50]}{qt_str}"
                pdf.text(68, py + 2, loc_display)
                pdf.set_text_color(120, 100, 50)
                pdf.text(178, py + 2, f"{p['price']:,.0f}/u")
                try: pdf.set_font("Roboto", "", 5.5)
                except: pdf.set_font("Helvetica", "", 5.5)
            else:
                pdf.set_text_color(180, 80, 30)
                pdf.text(68, py + 2, p['loc'][:65])
            
            py += 4.5
        
        # Route summary grouped by location
        py += 3
        loc_items = {}
        for p in procurement:
            loc_items.setdefault(p['loc'], []).append(p)
        
        # Sort locations by planet distance (use raw_loc for accurate distance)
        def _loc_sort_key(loc_items_pair):
            loc, litems = loc_items_pair
            raw = litems[0].get('raw_loc', loc) if litems else loc
            return (_qt_distance(raw), -len(litems))
        sorted_locs = sorted(loc_items.items(), key=_loc_sort_key)
        
        if py < 245 and len(sorted_locs) >= 1:
            # Add Stor-All purchase as first stop if needed
            stor_all_stop = None
            if has_loose_items:
                # Find nearest Stor-All vendor
                stor_loc = "LOCAL TERMINAL"
                if _uex_items_trade_db:
                    stor_candidates = []
                    for db_name, entries in _uex_items_trade_db.items():
                        if "stor" in db_name.lower() and "scu" in db_name.lower() and "self-storage" in db_name.lower():
                            for e in entries:
                                if e.get('b', 0) > 0:
                                    dist = _qt_distance(e['t'])
                                    stor_candidates.append((dist, e['b'], e['t']))
                    if stor_candidates:
                        stor_candidates.sort(key=lambda x: (x[0], x[1]))
                        stor_loc = stor_candidates[0][2]
                # Build exact container list from Stor-All items in cargo
                box_counts = {}
                for item in items:
                    ilow = item['name'].lower()
                    if 'stor' in ilow and ('all' in ilow or 'storage' in ilow):
                        box_counts[item['name']] = box_counts.get(item['name'], 0) + int(item['qty'])
                if box_counts:
                    box_list = ", ".join(f"{v}x {k[:25]}" for k, v in box_counts.items())
                else:
                    box_list = "Stor-All containers"
                stor_all_stop = f"STOP 0: {_enrich_location(stor_loc)} -> Buy {box_list}"
            
            num_stops = min(len(sorted_locs), 5) + (1 if stor_all_stop else 0)
            summary_h = num_stops * 4 + 6
            pdf.set_fill_color(35, 42, 55)
            pdf.rect(10, py - 1, 190, summary_h, 'F')
            pdf.set_text_color(200, 168, 78)
            try: pdf.set_font("Roboto", "B", 6)
            except: pdf.set_font("Helvetica", "B", 6)
            pdf.text(12, py + 3, f"OPTIMIZED ROUTE ({origin[:20].upper()}):")
            
            try: pdf.set_font("Roboto", "", 5.5)
            except: pdf.set_font("Helvetica", "", 5.5)
            pdf.set_text_color(200, 210, 220)
            
            stop_idx = 0
            stop_y = py + 7
            
            if stor_all_stop:
                pdf.set_text_color(120, 200, 80)
                pdf.text(14, stop_y, stor_all_stop)
                pdf.set_text_color(200, 210, 220)
                stop_y += 4
                stop_idx = 1
            
            for j, (loc, litems) in enumerate(sorted_locs[:5]):
                item_names = ", ".join(f"{p['qty']}x {p['name'][:15]}" for p in litems[:3])
                if len(litems) > 3:
                    item_names += f" +{len(litems)-3} more"
                # Show terminal/shop name from raw_loc
                raw = litems[0].get('raw_loc', '') if litems else ''
                if raw and raw.lower() not in loc.lower():
                    stop_label = f"{loc[:30]} ({raw[:20]})"
                else:
                    stop_label = loc[:50]
                pdf.text(14, stop_y, f"STOP {stop_idx + j + 1}: {stop_label} -> {item_names[:65]}")
                stop_y += 4
            
            py += summary_h + 2
        
        table_y = py + 8
    
    # ⚓⚓ CARGO TABLE ⚓⚓
    # Header
    pdf.set_fill_color(25, 32, 45)
    pdf.rect(10, table_y, 190, 7, 'F')
    pdf.set_text_color(200, 168, 78)
    try: pdf.set_font("Roboto", "B", 6.5)
    except: pdf.set_font("Helvetica", "B", 6.5)
    
    cols = [("Item / Description", 12), ("Box Size", 82), ("Qty", 105),
            ("Unit Price", 118), ("Total", 148), ("Courtesy", 172)]
    for label, x in cols:
        pdf.text(x, table_y + 5, label)
    
    # Rows
    row_y = table_y + 8
    grand_total = 0
    try: pdf.set_font("Roboto", "", 6.5)
    except: pdf.set_font("Helvetica", "", 6.5)
    
    for i, item in enumerate(items):
        if row_y > 240:
            # Need new page
            pdf.add_page()
            pdf.set_fill_color(245, 238, 220)
            pdf.rect(0, 0, 210, 297, 'F')
            pdf.set_draw_color(180, 150, 60)
            pdf.set_line_width(1.5)
            pdf.rect(5, 5, 200, 287)
            pdf.set_line_width(0.3)
            pdf.rect(7, 7, 196, 283)
            row_y = 15
        
        # Alternating row colors
        if i % 2 == 0:
            pdf.set_fill_color(235, 228, 210)
        else:
            pdf.set_fill_color(245, 238, 220)
        pdf.rect(10, row_y - 1, 190, 6, 'F')
        
        # Row line
        pdf.set_draw_color(200, 185, 140)
        pdf.set_line_width(0.1)
        pdf.line(10, row_y + 5, 200, row_y + 5)
        
        try:
            total = int(float(item['qty'])) * float(item['price'])
        except (ValueError, TypeError):
            total = 0
        if item['is_courtesy']:
            total = 0
        grand_total += total
        
        pdf.set_text_color(40, 35, 25)
        pdf.text(12, row_y + 3.5, item['name'][:40])
        pdf.text(82, row_y + 3.5, str(item['box_size']))
        pdf.text(105, row_y + 3.5, str(item['qty']))
        
        pdf.text(118, row_y + 3.5, f"{item['price']:,.0f} aUEC")
        pdf.text(148, row_y + 3.5, f"{total:,.0f}")
        
        if item['is_courtesy']:
            pdf.set_text_color(34, 139, 34)
            pdf.text(175, row_y + 3.5, "YES")
            pdf.set_text_color(40, 35, 25)
        
        row_y += 6
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ FOOTER / TOTALS Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    pdf.set_draw_color(180, 150, 60)
    pdf.set_line_width(0.5)
    pdf.line(10, row_y, 200, row_y)
    
    try: pdf.set_font("Roboto", "B", 7)
    except: pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(120, 100, 50)
    pdf.text(12, row_y + 5, f"TOTAL ITEMS: {len(items)}")
    
    pdf.text(148, row_y + 5, f"TOTAL: {grand_total:,.0f} aUEC")
    
    # â”€â”€ ORE QUALITY + ORDNANCE ADVISORIES â”€â”€
    advisory_y = row_y + 8
    has_ores = False
    has_ordnance = False
    ore_notes = []
    for item in items:
        name_low = item["name"].lower()
        # Check for refined ores
        if name_low in ore_quality_map:
            oq = ore_quality_map[name_low]
            ore_notes.append(f"  {item['name']}: Tier {oq['tier']} (Q{oq['min_good']}+ recommended) - {oq['note']}")
            has_ores = True
        # Check for ordnance (missiles/torpedoes/bombs)
        if any(x in name_low for x in ["missile", "torpedo", "bomb", "ammunition", "countermeasure"]):
            has_ordnance = True
    
    if has_ores or has_ordnance:
        try: pdf.set_font("Roboto", "B", 5.5)
        except: pdf.set_font("Helvetica", "B", 5.5)
        
        if has_ordnance:
            pdf.set_fill_color(45, 35, 25)
            pdf.rect(10, advisory_y - 1.5, 190, 5, 'F')
            pdf.set_text_color(230, 180, 60)
            pdf.text(14, advisory_y + 1.5, "ORDNANCE NOTICE // All missiles, torpedoes and bombs require bounding box cage placement on cargo grid (patch 4.9+). SCU = grid footprint with cage.")
            advisory_y += 6
        
        if has_ores and ore_notes:
            pdf.set_fill_color(35, 40, 30)
            note_h = min(len(ore_notes), 4) * 4 + 5
            pdf.rect(10, advisory_y - 1.5, 190, note_h, 'F')
            pdf.set_text_color(120, 200, 80)
            pdf.text(14, advisory_y + 1.5, "MATERIAL QUALITY ADVISORY // Recommended refinery quality grade 700+ for all Tier A/B ores:")
            try: pdf.set_font("Roboto", "", 5)
            except: pdf.set_font("Helvetica", "", 5)
            pdf.set_text_color(160, 190, 140)
            for i, note in enumerate(ore_notes[:4]):
                pdf.text(16, advisory_y + 5 + i * 3.5, note[:130])
            advisory_y += note_h + 1
        
        row_y = advisory_y - 6
    
    # SHUTTLE RECOMMENDATION
    total_scu = 0
    for item in items:
        name_low = item.get("name", "").lower().strip()
        box_sz = item.get("box_size", "1 unit").lower()
        try:
            qty = int(float(item.get("qty", 1)))
        except (ValueError, TypeError):
            qty = 1
        # Use volume_map first (most accurate, includes bounding box cage for ordnance)
        if name_low in volume_map:
            total_scu += qty * volume_map[name_low]
        # Fallback: parse box_size string for SCU multiplier
        elif "8 scu" in box_sz: total_scu += qty * 8
        elif "4 scu" in box_sz: total_scu += qty * 4
        elif "2 scu" in box_sz: total_scu += qty * 2
        elif "1 scu" in box_sz or "scu" in box_sz: total_scu += qty * 1
        elif "cscu" in box_sz: total_scu += qty * 0.01
        elif any(x in box_sz for x in ["missile", "torpedo", "bomb"]): total_scu += qty * 2
        elif any(x in box_sz for x in ["rifle", "smg", "pistol", "grenade"]): total_scu += qty * 0.02
        elif any(x in box_sz for x in ["helmet", "core", "arms", "legs"]): total_scu += qty * 0.01
        else: total_scu += qty * 0.01  # minimal default
    
    # Only show shuttle rec for EVA loading (not hangar)
    loading_type = ""
    try:
        if hasattr(self, 'loading_type_var'):
            loading_type = self.loading_type_var.get().lower()
        elif hasattr(self, '_loading_type'):
            loading_type = str(self._loading_type).lower()
    except: pass
    
    is_eva = "eva" in loading_type or "space" in loading_type
    
    try:
        if is_eva:
            shuttle_rec = _recommend_shuttle(vessel, total_scu)
            if shuttle_rec and shuttle_rec.get("note"):
                try: pdf.set_font("Roboto", "I", 6)
                except: pdf.set_font("Helvetica", "I", 6)
                pdf.set_text_color(120, 100, 50)
                pdf.text(12, row_y + 10, shuttle_rec["note"][:130])
                row_y += 6
    except Exception:
        pass
    
    # CAPACITY / CONCEPT WARNING
    ship_cap = 0
    is_concept = False
    vessel_low = vessel.lower().strip()
    for k, v in _uex_ships_db.items():
        sname = v.get("name", k).lower()
        if vessel_low == k.lower() or vessel_low == sname or vessel_low in sname:
            ship_cap = v.get("scu", 0)
            is_concept = v.get("is_concept", False) or k.lower() in _CONCEPT_SHIPS
            break
    
    warn_msgs = []
    if is_concept:
        warn_msgs.append("ADVISORY // VESSEL CLASSIFIED AS CONCEPT-STAGE -- CARGO GRID DATA MAY BE APPROXIMATE")
    if ship_cap > 0 and total_scu > ship_cap:
        ovr = int((total_scu / ship_cap - 1) * 100)
        warn_msgs.append(f"WARNING // CARGO EXCEEDS VESSEL CAPACITY: {total_scu:.0f} SCU vs {ship_cap} SCU MAX (+{ovr}%) -- REDISTRIBUTE IMMEDIATELY")
    
    if warn_msgs:
        for wmsg in warn_msgs:
            row_y += 2
            wy = row_y + 8
            try: pdf.set_font("Roboto", "B", 5.5)
            except: pdf.set_font("Helvetica", "B", 5.5)
            is_warn = "WARNING" in wmsg
            if is_warn:
                pdf.set_fill_color(255, 235, 235)
            else:
                pdf.set_fill_color(255, 248, 220)
            pdf.rect(10, wy - 2, 190, 6, 'F')
            if is_warn:
                pdf.set_draw_color(200, 40, 30)
            else:
                pdf.set_draw_color(180, 150, 50)
            pdf.set_line_width(0.3)
            pdf.rect(10, wy - 2, 190, 6, 'D')
            if is_warn:
                pdf.set_text_color(180, 30, 20)
            else:
                pdf.set_text_color(150, 120, 30)
            pdf.text(14, wy + 1.8, wmsg[:145])
            row_y += 7
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ SIGNATURE Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    sig_y = row_y + 12
    if sig_y > 250:
        pdf.add_page()
        pdf.set_fill_color(245, 238, 220)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_draw_color(180, 150, 60)
        pdf.set_line_width(1.5)
        pdf.rect(5, 5, 200, 287)
        pdf.set_line_width(0.3)
        pdf.rect(7, 7, 196, 283)
        sig_y = 20
    
    pdf.set_text_color(200, 168, 78)
    try: pdf.set_font("Roboto", "B", 8)
    except: pdf.set_font("Helvetica", "B", 8)
    pdf.text(12, sig_y, "LOADING OFFICER AUTHORIZATION")
    pdf.set_draw_color(200, 168, 78)
    pdf.set_line_width(0.2)
    pdf.line(12, sig_y + 1.5, 120, sig_y + 1.5)
    
    try: pdf.set_font("Roboto", "", 6.5)
    except: pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(80, 70, 50)
    pdf.text(12, sig_y + 7, f"Name: {officer}")
    pdf.text(12, sig_y + 11, "Rank: UEE Logistics Officer")
    
    # Officer signature line + PNG
    pdf.set_draw_color(150, 140, 110)
    pdf.set_line_width(0.1)
    pdf.line(40, sig_y + 20, 110, sig_y + 20)
    
    podpisy_dir = get_signatures_dir()
    sig_file = process_signature(podpisy_dir, officer)
    if sig_file and os.path.exists(sig_file):
        pdf.image(sig_file, x=42, y=sig_y + 8, w=55, h=13)
    
    # R1 Stamp (right)
    stamp_file = process_r1_stamp(podpisy_dir)
    if stamp_file and os.path.exists(stamp_file):
        pdf.image(stamp_file, x=155, y=sig_y, w=22, h=22)
    
    # â”€â”€ SYSTEM NOTICE (text only, no black header) â”€â”€
    notice_y = sig_y + 24
    pdf.set_draw_color(200, 168, 78)
    pdf.set_line_width(0.2)
    pdf.line(10, notice_y, 200, notice_y)
    try: pdf.set_font("Roboto", "I", 4.5)
    except: pdf.set_font("Helvetica", "I", 4.5)
    pdf.set_text_color(140, 130, 110)
    pdf.text(12, notice_y + 3.5, "Document generated by 29th Starlifters Squadron // Requisition Terminal v0.5 // Verify all quantities before loading.")
    
    # Barcode
    barcode_file = get_processed_barcode_path(podpisy_dir)
    if barcode_file and os.path.exists(barcode_file):
        pdf.image(barcode_file, x=70, y=sig_y + 26, w=55, h=10)
    
    # Ledger hash
    seed = hash(req_id + vessel + officer)
    random.seed(seed)
    prefixes = ["REQ", "SEC", "LOG", "TAC", "NAV"]
    divisions = ["44BG", "UEE-9N", "FLEET-44", "TAC-DIV"]
    suffixes = ["ALPHA", "BRAVO", "X-RAY", "OMEGA", "DELTA-6"]
    hash_id = f"{random.choice(prefixes)}-{random.choice(divisions)}-{random.randint(10000, 99999)}-{random.choice(suffixes)}"
    try: pdf.set_font("Roboto", "B", 4.5)
    except: pdf.set_font("Helvetica", "B", 4.5)
    pdf.set_text_color(120, 110, 90)
    pdf.text(82, sig_y + 38, f"LEDGER HASH: {hash_id}")
    
    # Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬ SAVE Ă˘â€ťâ‚¬Ă˘â€ťâ‚¬
    try:
        pdf.output(save_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate PDF: {e}")
        return
    
    # Only show success for single generation (not batch)
    if not hasattr(self, '_gen3_running') or not self._gen3_running:
        messagebox.showinfo("Success", f"Supply Route PDF saved to:\n{save_path}")

def _patched_generate_supply_route_pdf(self):
    """Direct PDF generation Ă˘â‚¬â€ť no main.pyc, instant."""
    generate_pdf_direct(self)

def _patched_animate_generate(self):
    """Animate TRANSMITTING UPLINK on button, then generate PDF in thread."""
    import threading, time
    btn = getattr(self, '_sr_btn', None)
    
    def _run():
        _play_sound("pdf_generated.wav")  # Sound on click
        # Flash animation
        frames = [">> TRANSMITTING UPLINK...", ">> TRANSMITTING UPLINK.. ", ">> TRANSMITTING UPLINK.  ",
                  "   TRANSMITTING UPLINK...", ">> UPLINK ACTIVE <<<", ">> TRANSMITTING UPLINK..."]
        if btn:
            try:
                btn.configure(state="disabled", fg_color="#1a3a2a", text_color="#00ff88")
            except: pass
        for i in range(6):
            if btn:
                try: btn.configure(text=frames[i % len(frames)])
                except: pass
            time.sleep(0.3)
        
        # Generate
        try:
            generate_pdf_direct(self)
        except Exception as e:
            try: messagebox.showerror("Error", f"Failed to generate PDF: {e}")
            except: pass
        
        # Restore button
        if btn:
            try:
                btn.configure(text="Generate Supply Route PDF", state="normal",
                              fg_color="#2a3a1a", text_color="#c8a84e")
            except: pass
    
    threading.Thread(target=_run, daemon=True).start()
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 8: Shuttle Recommendation Engine
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

# Which pad sizes fit in each mother ship's hangar (verified in-game data)
# NOTE: Some ships in UEX are concept-only and may not be flyable yet
_HANGAR_FIT_MAP = {
    "idris":        {
        "max_pad": "S",
        "name": "Idris",
        "note": "Internal hangar (24x55m). Fits S-pad ships: Gladius, Sabre, Arrow, Terrapin, Freelancer (tight). Cutlass/Constellation do NOT fit.",
        "known_fits": ["golem ox", "golem", "gladius", "sabre", "arrow", "hornet", "terrapin", "freelancer", "freelancer mis",
                       "pisces", "mpuv", "85x", "mustang", "aurora", "avenger", "prospector", "100i", "135c", "300i",
                       "ares", "scorpius", "buccaneer", "talon", "nox", "hoverquad", "ptv", "mule", "atls", "cutter"],
        "known_no_fit": ["cutlass", "constellation", "railen", "raft", "hull a", "starlancer", "vanguard", "c1 spirit",
                         "caterpillar", "mercury", "corsair", "retaliator", "starfarer", "valkyrie"],
    },
    "kraken":       {
        "max_pad": "M",
        "name": "Kraken",
        "note": "Landing pads (4x M-pad on deck). Open-air pads, not enclosed hangar. M-pad ships land on deck.",
        "known_fits": [],
        "known_no_fit": [],
    },
    "polaris":      {
        "max_pad": "XS",
        "name": "Polaris",
        "note": "Internal hangar (24x32x12m XS metric). Fits fighters: Gladius, Sabre, Arrow, Hornet, Scorpius. Freelancer fits tight with gear retracted.",
        "known_fits": ["golem ox", "golem", "gladius", "sabre", "arrow", "hornet", "f8c", "buccaneer", "talon", "scorpius",
                       "pisces", "mpuv", "85x", "mustang", "aurora", "100i", "prospector", "terrapin",
                       "vulture", "nox", "hoverquad", "ptv", "mule", "cutter"],
        "known_no_fit": ["cutlass", "constellation", "railen", "raft", "hull a", "freelancer max",
                         "starlancer", "vanguard", "mercury", "caterpillar"],
    },
    "carrack":      {
        "max_pad": "XS",
        "name": "Carrack",
        "note": "Internal hangar (XS snub bay). Designed for Pisces C8X. Very limited cargo shuttle options.",
        "known_fits": ["golem ox", "golem", "pisces", "c8x", "85x", "mpuv", "razor", "m50", "merlin", "archimedes",
                       "nox", "hoverquad", "ptv", "mule", "135c", "csv", "cutter"],
        "known_no_fit": ["gladius", "arrow", "aurora", "mustang", "avenger"],
    },
    "890 jump":     {
        "max_pad": "XS",
        "name": "890 Jump",
        "note": "Internal hangar (XS snub bay). Designed for 85X. Similar to Carrack bay.",
        "known_fits": ["golem ox", "golem", "85x", "pisces", "mpuv", "merlin", "archimedes", "nox", "hoverquad", "razor", "m50", "135c", "cutter"],
        "known_no_fit": ["gladius", "arrow", "aurora", "mustang", "avenger"],
    },
    "odyssey":      {
        "max_pad": "S",
        "name": "Odyssey",
        "note": "Internal hangar (S-pad). Concept ship \u2013 hangar size not final. Expected to fit S-pad fighters.",
        "concept_only": True,
        "known_fits": [],
        "known_no_fit": [],
    },
    "merchantman":  {
        "max_pad": "S",
        "name": "Merchantman",
        "note": "Internal hangar (S-pad). Concept ship \u2013 hangar specs subject to change.",
        "concept_only": True,
        "known_fits": [],
        "known_no_fit": [],
    },
    "galaxy":       {
        "max_pad": "XS",
        "name": "Galaxy",
        "note": "Internal hangar (XS snub). Concept ship \u2013 limited hangar bay.",
        "concept_only": True,
        "known_fits": [],
        "known_no_fit": [],
    },
    "javelin":      {
        "max_pad": "S",
        "name": "Javelin",
        "note": "Internal hangar. Large capital ship \u2013 S-pad ships expected to fit.",
        "concept_only": True,
        "known_fits": [],
        "known_no_fit": [],
    },
    "ironclad":     {
        "max_pad": "XS",
        "name": "Ironclad",
        "note": "Vehicle bay, not a standard hangar. Primarily for ground vehicles and cargo.",
        "known_fits": ["mule", "ptv", "cyclone", "ursa", "hoverquad", "nox"],
        "known_no_fit": [],
    },
}

_PAD_ORDER = {"XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5}

# Ships that are concept-only (not yet flyable) \u2013 flag in recommendations
_CONCEPT_SHIPS = {"railen", "hull b", "hull d", "hull e", "endeavor", "orion", "pioneer",
                  "merchantman", "genesis starliner", "crucible", "odyssey", "odin",
                  "ironclad assault", "hermes", "salvation", "moth", "tyilui", "paladin",
                  "shiv"}

# Priority cargo shuttles \u2013 these are the GO-TO ships for internal hangar loading
# Golem OX (64 SCU, ~15.5x10x4.5m) fits in most hangars and is the best dedicated shuttle
# MPUV Cargo (2 SCU) is tiny but always fits everywhere
# Cutter (4 SCU) small but reliable
_PRIORITY_SHUTTLES = {"golem ox": 100, "mpuv cargo": 90, "cutter": 80, "mpuv tractor": 70,
                      "csv-sm": 60, "135c": 50, "pisces": 40, "c8x pisces expedition": 40}

def _recommend_shuttle(vessel_name, total_scu):
    """Recommend best cargo shuttle + loading method for mother ship + cargo.
    
    Returns dict with:
        hangar_shuttles: list of ships that fit in hangar
        pad_shuttles: list of larger ships for landing pad
        recommended: best option
        loading_method: 'hangar' / 'landing_pad' / 'eva'
        note: human-readable note for PDF (English only)
    """
    if not vessel_name or total_scu <= 0:
        return None
    
    vn_low = vessel_name.lower()
    
    # Find mother ship hangar info
    hangar_info = None
    for key, val in _HANGAR_FIT_MAP.items():
        if key in vn_low:
            hangar_info = val
            break
    
    if not hangar_info:
        # Not a carrier \u2013 no recommendation needed
        return None
    
    max_pad_order = _PAD_ORDER.get(hangar_info["max_pad"], 0)
    known_fits = hangar_info.get("known_fits", [])
    known_no_fit = hangar_info.get("known_no_fit", [])
    is_concept_mother = hangar_info.get("concept_only", False)
    
    # Find ships that fit IN the hangar (by pad size AND not in known_no_fit)
    # Also include priority shuttles (like Golem OX) even if they have no pad_type
    hangar_ships = []
    for k, v in _uex_ships_db.items():
        pad = v.get("pad_type", "")
        scu = v.get("scu", 0)
        ship_name_low = k.lower()
        
        if scu <= 0:
            continue
        
        # HARD RULE: concept-only ships are NEVER recommended
        if ship_name_low in _CONCEPT_SHIPS:
            continue
        # Also check by display name
        display_name = v.get("name", "").lower()
        if any(cs in display_name for cs in _CONCEPT_SHIPS):
            continue
        
        # Priority shuttles (Golem OX, MPUV, Cutter) \u2013 always include if not in known_no_fit
        priority_score = 0
        is_priority = False
        for pk, pv in _PRIORITY_SHUTTLES.items():
            if pk in ship_name_low or ship_name_low in pk:
                priority_score = pv
                is_priority = True
                break
        
        if not is_priority:
            # Regular ship \u2013 must have pad and fit within max_pad
            if not pad or _PAD_ORDER.get(pad, 99) > max_pad_order:
                continue
        
        # Check known_no_fit \u2013 skip ships explicitly known to NOT fit
        if any(nf in ship_name_low or ship_name_low in nf for nf in known_no_fit):
            continue
        
        # If ship has NO pad_type and is NOT a priority shuttle, skip it
        # (unknown vehicles should not be recommended)
        if not pad and not is_priority:
            continue
        
        trips = max(1, -(-total_scu // scu))  # ceil division
        
        # Bonus priority if ship is in known_fits list
        is_known = any(kf in ship_name_low or ship_name_low in kf for kf in known_fits)
        
        hangar_ships.append({
            "name": v.get("name", v.get("short_name", "?")),
            "scu": scu,
            "trips": trips,
            "is_cargo": v.get("is_cargo", 0),
            "pad": pad if pad else "GV",
            "is_known_fit": is_known,
            "priority": priority_score,
        })
    
    # Sort: priority shuttles first, then known fits, then cargo, then fewest trips
    hangar_ships.sort(key=lambda x: (-x["priority"], -x["is_known_fit"], -x["is_cargo"], x["trips"], -x["scu"]))
    
    # Find ships for LANDING PAD / EVA (won't fit in hangar but can carry the cargo)
    pad_ships = []
    for k, v in _uex_ships_db.items():
        pad = v.get("pad_type", "")
        scu = v.get("scu", 0)
        if not pad or scu < total_scu:
            continue
        if _PAD_ORDER.get(pad, 99) <= max_pad_order:
            continue
        if k.lower() in _CONCEPT_SHIPS:
            continue
        pad_ships.append({
            "name": v.get("name", v.get("short_name", "?")),
            "scu": scu,
            "trips": 1,
            "is_cargo": v.get("is_cargo", 0),
            "pad": pad,
        })
    pad_ships.sort(key=lambda x: (-x["is_cargo"], x["scu"]))
    
    # Determine best recommendation
    best_hangar = hangar_ships[0] if hangar_ships else None
    best_pad = pad_ships[0] if pad_ships else None
    
    # Concept mother ship disclaimer
    concept_note = " (NOTE: This vessel is concept-only, hangar specs subject to change.)" if is_concept_mother else ""
    
    # Build recommendation â€” ideal 1 trip, max 2, >2 = warning
    if best_hangar and best_hangar["trips"] <= 2:
        loading_method = "hangar"
        recommended = best_hangar
        if best_hangar["trips"] == 1:
            note = (
                f"SHUTTLE RECOMMENDATION: Use {best_hangar['name']} ({best_hangar['scu']} SCU, pad {best_hangar['pad']}). "
                f"Single trip \u2013 load directly in {hangar_info['name']} internal hangar.{concept_note}"
            )
        else:
            note = (
                f"SHUTTLE RECOMMENDATION: Use {best_hangar['name']} ({best_hangar['scu']} SCU, pad {best_hangar['pad']}). "
                f"2 trips required via {hangar_info['name']} internal hangar. This is acceptable.{concept_note}"
            )
    elif best_hangar and best_hangar["trips"] > 2:
        loading_method = "landing_pad"
        recommended = best_pad if best_pad else best_hangar
        pad_option = f"Recommended: {best_pad['name']} ({best_pad['scu']} SCU, pad {best_pad['pad']}) on Landing Pad. " if best_pad else ""
        note = (
            f"\u26a0 WARNING: CARGO VOLUME EXCEEDS EFFICIENT HANGAR LOADING ({best_hangar['trips']} trips via {best_hangar['name']}). "
            f"This vessel REQUIRES a Landing Pad or EVA (free float) loading. "
            f"{pad_option}{concept_note}"
        )
    elif best_pad:
        loading_method = "landing_pad"
        recommended = best_pad
        note = (
            f"NO CARGO SHUTTLE FITS IN {hangar_info['name'].upper()} INTERNAL HANGAR for {total_scu} SCU. "
            f"Loading MUST be done via Landing Pad or EVA (free float). "
            f"Recommended: {best_pad['name']} ({best_pad['scu']} SCU, pad {best_pad['pad']}) on Landing Pad.{concept_note}"
        )
    else:
        loading_method = "eva"
        recommended = None
        note = (
            f"NO SUITABLE CARGO SHUTTLE AVAILABLE for {total_scu} SCU in {hangar_info['name']}. "
            f"Loading MUST be performed via EVA (free float) with manual cargo transfer.{concept_note}"
        )
    
    hangar_note = hangar_info.get("note", "")
    if hangar_note:
        note += f" [{hangar_note}]"
    
    return {
        "hangar_shuttles": hangar_ships[:5],
        "pad_shuttles": pad_ships[:3],
        "recommended": recommended,
        "loading_method": loading_method,
        "note": note,
        "mother_ship": hangar_info["name"],
        "total_scu": total_scu,
    }


# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 9: App Init + Slang + Clipboard
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

def run_sync_patched(self, *args, **kwargs):
    import time
    time.sleep(1)

# RequisitionApp init monkeypatch
original_init = main.RequisitionApp.__init__

def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    
    # Override window size to fit screen better
    try:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1050, screen_w - 100)
        win_h = min(700, screen_h - 100)
        x = (screen_w - win_w) // 2
        y = max(20, (screen_h - win_h) // 2 - 30)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(950, 600)
        self.maxsize(1100, 750)
        self.resizable(False, False)
    except Exception:
        pass
    
    grid_db_path = getattr(main, 'resource_path', lambda p: p)(os.path.join('resources', 'ship_grids_db.json'))
    self.ship_grids_db = {}
    if os.path.exists(grid_db_path):
        try:
            with open(grid_db_path, "r", encoding="utf-8") as gf:
                self.ship_grids_db = json.load(gf)
        except Exception:
            pass

    # Set window icon if available
    icon_path = getattr(main, 'resource_path', lambda p: p)("app_icon.ico")
    if os.path.exists(icon_path):
        try:
            self.iconbitmap(icon_path)
        except Exception:
            pass

    if hasattr(self, "title"):
        self.title("29th Starlifters - Requisition Terminal v0.6")
        
    def update_header_version(widget):
        if hasattr(widget, "cget") and hasattr(widget, "configure"):
            try:
                txt = widget.cget("text")
                if txt and "REQUISITION TERMINAL v0.5" in txt:
                    widget.configure(text=txt.replace("v0.5", "v0.6"))
            except Exception:
                pass
        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                update_header_version(child)
    update_header_version(self)
            
    self.bind_all("<Control-v>", self.handle_global_paste)
    self.bind_all("<Control-V>", self.handle_global_paste)
    
    original_add_cargo_row = self.add_cargo_row_to_ui
    
    def patched_add_cargo_row(name, qty, box_size, price, courtesy=False, unit='SCU', *args, **kwargs):
        vessel_name = self.vessel_var.get() if hasattr(self, "vessel_var") else ""
        
        vessel_clean = vessel_name
        for prefix in ["Aegis", "Anvil", "Drake", "RSI", "Crusader", "MISC", "Origin", "Consolidated Outland", "Argo", "Mirai", "Gatac", "Esperia"]:
            if vessel_clean.lower().startswith(prefix.lower()):
                vessel_clean = vessel_clean[len(prefix):].strip()
                break
                
        name_low = name.lower()
        is_snub = any(x in name_low for x in ["golem ox", "mpuv", "pisces"])
        
        loading_loc = self._loading_type_var.get() if hasattr(self, "_loading_type_var") else "In Hangar"
        if is_snub and loading_loc != "In Hangar":
            can_hold_snub = any(x in vessel_name.upper() for x in ["IDRIS", "POLARIS", "890 JUMP", "CARRACK", "IRONCLAD"])
            if not can_hold_snub and vessel_name != "":
                messagebox.showwarning(
                    "\u26a0\ufe0f Dimensional Fit Warning",
                    f"Selected cargo shuttle ({name}) is too large for the {vessel_name}'s hangar / cargo bay doors!\n"
                    "Please deploy a carrier class mother-ship (Idris, Polaris, Carrack, Ironclad) for snub operations."
                )
        
        # Auto-fill price from config if missing (vessel loadouts often have no price)
        if (price == 0 or price == '' or price is None) and not courtesy:
            fi_data = self.config_data.get("frequent_items", {})
            flat_items = []
            if isinstance(fi_data, dict):
                for cat, cat_items in fi_data.items():
                    if isinstance(cat_items, list):
                        flat_items.extend(cat_items)
            elif isinstance(fi_data, list):
                flat_items = fi_data
            for fi in flat_items:
                if isinstance(fi, dict) and fi.get("name", "").lower() == name_low:
                    price = fi.get("price", 0)
                    if not box_size or box_size == "unit":
                        box_size = fi.get("box_size", fi.get("unit", box_size))
                    break
        
        res = original_add_cargo_row(name, qty, box_size, price, courtesy, unit, *args, **kwargs)
        
        if not getattr(self, '_auto_adding_battery', False):
            self._auto_adding_battery = True
            try:
                # Build flat items for battery price lookup
                fi_data = self.config_data.get("frequent_items", {})
                flat_cfg = []
                if isinstance(fi_data, dict):
                    for cat, cat_items in fi_data.items():
                        if isinstance(cat_items, list):
                            flat_cfg.extend(cat_items)
                elif isinstance(fi_data, list):
                    flat_cfg = fi_data
                
                if "maxlift tractor beam" in name_low and not any(w in name_low for w in ["battery", "attachment"]):
                    has_battery = any("maxlift tractor beam battery" in r['name_var'].get().lower() for r in self.cargo_rows)
                    if not has_battery:
                        batt_price = 175
                        for item in flat_cfg:
                            if isinstance(item, dict) and "maxlift tractor beam battery" in item.get("name","").lower():
                                batt_price = item["price"]
                                break
                        self.add_cargo_row_to_ui("Maxlift Tractor Beam Battery", qty, "unit", batt_price, courtesy, "unit")
                elif "cambio srt" in name_low and not any(w in name_low for w in ["battery", "canister", "attachment"]):
                    has_battery = any("cambio multi-tool battery" in r['name_var'].get().lower() for r in self.cargo_rows)
                    if not has_battery:
                        batt_price = 63
                        for item in flat_cfg:
                            if isinstance(item, dict) and "cambio multi-tool battery" in item.get("name","").lower():
                                batt_price = item["price"]
                                break
                        self.add_cargo_row_to_ui("Cambio Multi-tool Battery", qty, "unit", batt_price, courtesy, "unit")
            finally:
                self._auto_adding_battery = False
        return res
        
    self.add_cargo_row_to_ui = patched_add_cargo_row

    video_names = ["intro_video.mp4", "m\u00e1_to_b\u00fdt_animace_p\u0159i_spou\u0161te.mp4"]
    found_path = None
    for name in video_names:
        p0 = os.path.join(main.APP_DIR, 'resources', name)
        if os.path.exists(p0):
            found_path = p0
            break
        p1 = os.path.join(main.APP_DIR, name)
        if os.path.exists(p1):
            found_path = p1
            break
        p2 = getattr(main, 'resource_path', lambda p: p)(name)
        if os.path.exists(p2):
            found_path = p2
            break
    if found_path:
        self.video_path = found_path
        self.cap = cv2.VideoCapture(self.video_path)
        self.use_video = True if self.cap.isOpened() else False


def resolve_slang(self, name_raw):
    name_raw_low = name_raw.lower().strip()
    slang_map = {
        # \u2500\u2500 Weapons \u2500\u2500
        "tractor": "MaxLift Tractor Beam",
        "beam": "MaxLift Tractor Beam",
        "tractora": "MaxLift Tractor Beam",
        "maxlift": "MaxLift Tractor Beam",
        "multi": "Cambio SRT",
        "cambio": "Cambio SRT",
        "multitool": "Cambio SRT",
        "tool": "Cambio SRT",
        "p4": "P4-AR Rifle",
        "p4ar": "P4-AR Rifle",
        "p4-ar": "P4-AR Rifle",
        "nightstalker": 'P4-AR "Nightstalker" Rifle',
        "cq7": 'Behring "CQ7" Bullpup Rifle',
        "bullpup": 'Behring "CQ7" Bullpup Rifle',
        "coda": "Coda Pistol",
        "gallant": "Gallant Rifle",
        "c54": "C54 SMG",
        "lumin": "Lumin V SMG",
        "lumin v": "Lumin V SMG",
        "scalpel": "Scalpel Sniper Rifle",
        "sniper": "Scalpel Sniper Rifle",
        "custodian": "Custodian SMG",
        "devastator": "Devastator Shotgun",
        "shotgun": "Devastator Shotgun",
        "fs9": "FS-9 LMG",
        "fs-9": "FS-9 LMG",
        "lmg": "FS-9 LMG",
        "smg": "P8-SC SMG",
        "p8": "P8-SC SMG",
        "s38": "S-38 Pistol",
        "s-38": "S-38 Pistol",
        "pistol": "S-38 Pistol",
        "p6": "P6-LR Sniper Rifle",
        "p6lr": "P6-LR Sniper Rifle",
        "p6-lr": "P6-LR Sniper Rifle",
        # \u2500\u2500 Ammo & Magazines \u2500\u2500
        "mag": "P4-AR Magazine",
        "mags": "P4-AR Magazine",
        "ammo": "P4-AR Magazine",
        "battery": "Maxlift Tractor Beam Battery",
        "baterka": "Maxlift Tractor Beam Battery",
        "s1 ammo": "Size 1 Ammunition",
        "s2 ammo": "Size 2 Ammunition",
        "s3 ammo": "Size 3 Ammunition",
        "s4 ammo": "Size 4 Ammunition",
        "s5 ammo": "Size 5 Ammunition",
        "s6 ammo": "Size 6 Ammunition",
        "s7 ammo": "Size 7 Ammunition",
        "countermeasures": "Decoy Countermeasures",
        "decoys": "Decoy Countermeasures",
        "chaff": "Decoy Countermeasures",
        "noise": "Noise Countermeasures",
        "flare": "Pink QuikFlare",
        "flares": "Pink QuikFlare",
        # \u2500\u2500 Grenades & Explosives \u2500\u2500
        "scorch": "Scorch Plasma Grenade",
        "grenade": "Scorch Plasma Grenade",
        "nade": "Scorch Plasma Grenade",
        "frag": "MK-4 Frag Grenade",
        # \u2500\u2500 Missiles & Torpedoes \u2500\u2500
        "torp": "Seeker IX Torpedo",
        "torpedo": "Seeker IX Torpedo",
        "torps": "Seeker IX Torpedo",
        "seeker": "Seeker IX Torpedo",
        "argus": "Argus IX Torpedo",
        "typhoon": "Typhoon IX Torpedo",
        "raptor": "Raptor IV Missile",
        "thunderbolt": "Thunderbolt III Missile",
        "dominator": "Dominator II Missile",
        "ignite": "Ignite II Missile",
        "reaper": "Reaper V Missile",
        "missile": "Raptor IV Missile",
        "missiles": "Raptor IV Missile",
        "bomb": "Stormburst Bomb",
        "bombs": "Stormburst Bomb",
        "stormburst": "Stormburst Bomb",
        "colossus": "Colossus Bomb",
        # \u2500\u2500 Armor (common shorthand) \u2500\u2500
        "aril": "Aril Core",
        "orc": "ORC-mkX Core Woodland",
        "adp": "ADP-mk4 Core Woodland",
        "macflex": "MacFlex Core",
        "field recon": "Field Recon Suit Core",
        "recon suit": "Field Recon Suit Core",
        "tailwind": "Tailwind Flight Suit",
        "undersuit": "TCS-4 Undersuit",
        "tcs4": "TCS-4 Undersuit",
        "tcs-4": "TCS-4 Undersuit",
        "backpack": "CSP-68H Backpack",
        "rucksack": "CSP-68H Backpack",
        # \u2500\u2500 Medical \u2500\u2500
        "medgel": "Pancea MedGel Canister",
        "panacea": "Pancea MedGel Canister",
        "medpen": "Hemozal MedPen",
        "hemozal": "Hemozal MedPen",
        "adrenaline": "AdrenaPen",
        "adrena": "AdrenaPen",
        "cortico": "CorticoPen",
        "decon": "DeconPen",
        "detox": "DetoxPen",
        "opio": "OpioPen",
        "paramedic": "ParaMed Medical Device",
        "paramed": "ParaMed Medical Device",
        "medkit": "ParaMed Medical Device",
        "fire extinguisher": "APX Fire Extinguisher",
        "extinguisher": "APX Fire Extinguisher",
        # \u2500\u2500 Food & Drinks \u2500\u2500
        "cruz": "CRUZ Lux",
        "lux": "CRUZ Lux",
        "piticko": "CRUZ Lux",
        "drink": "CRUZ Lux",
        "water": "Quantainium Water Bottle",
        "bottle": "Quantainium Water Bottle",
        "chocolate": "Buster's Chocolate Bar",
        "energy bar": "Karoby Energy Bar",
        "food": "ReadyMeal",
        "meal": "ReadyMeal",
        "readymeal": "ReadyMeal",
        "snack": "Snaggle Stick",
        "hotdog": "Veggie Dog",
        # \u2500\u2500 Tools & Components \u2500\u2500
        "canister": "Cambio SRT Canister",
        "lifeguard": "LifeGuard Medical Attachment",
        "truhold": "TruHold Tractor Beam Attachment",
        "fab": "Item Fabricator",
        "fabricator": "Item Fabricator",
        "silicon": "Refined Silicon",
        "iron": "Refined Iron",
        "copper": "Refined Copper",
        "titanium": "Refined Titanium",
        "gold": "Refined Gold",
        "laranite": "Refined Laranite",
        "agricium": "Refined Agricium",
        "bexlite": "Refined Bexlite",
        "taranite": "Refined Taranite",
        "qt": "Refined Quantainium",
        "quantanium": "Refined Quantainium",
        "quant": "Refined Quantainium",
        "rmc": "Recycled Material Composite (RMC)",
        "construction": "Construction Materials",
        # \u2500\u2500 Containers \u2500\u2500
        "box": "Stor-All 1 SCU Storage Container",
        "crate": "Stor-All 1 SCU Storage Container",
        "1scu": "Stor-All 1 SCU Storage Container",
        "2scu": "Stor*All 2 SCU Self-Storage Container",
        "4scu": "Stor*All 4 SCU Self-Storage Container",
        "8scu": "Stor*All 8 SCU Self-Storage Container",
        # \u2500\u2500 Fuel \u2500\u2500
        "qfuel": "Quantum Fuel",
        "quantum fuel": "Quantum Fuel",
        "hydro": "Hydrogen Fuel",
        "hydrogen": "Hydrogen Fuel",
        "h2": "Hydrogen Fuel",
        # \u2500\u2500 Ships (for shuttle context) \u2500\u2500
        "pisces": "C8X Pisces",
        "mpuv": "Argo MPUV-C",
        "ox": "Golem Ox",
        "golem": "Golem Ox",
        "cutter": "Drake Cutter",
    }
    # Exact match first
    if name_raw_low in slang_map:
        return slang_map[name_raw_low]
    # Partial match
    for slang, official in slang_map.items():
        if slang in name_raw_low:
            return official
    # Match against config items
    fi_data = self.config_data.get("frequent_items", {})
    flat_items = []
    if isinstance(fi_data, dict):
        for cat, cat_items in fi_data.items():
            if isinstance(cat_items, list):
                flat_items.extend(cat_items)
    elif isinstance(fi_data, list):
        flat_items = fi_data
    for fi in flat_items:
        if isinstance(fi, dict) and fi.get("name"):
            fi_name_low = fi["name"].lower()
            if name_raw_low == fi_name_low or name_raw_low in fi_name_low or fi_name_low in name_raw_low:
                return fi["name"]
    return name_raw.title()


def handle_global_paste(self, event=None):
    try:
        clipboard = self.clipboard_get()
    except Exception:
        return
    
    # â”€â”€ PHASE 1: Detect structured Discord bot format â”€â”€
    # Format: SHIP: <name>\nCAPTAIN: <name>\nLOCATION: <loc>\nMISSION: <desc>\n---\n<cargo lines>
    metadata_keys = {
        "ship": "ship_selector", "vessel": "ship_selector",
        "captain": "captain_var", "cap": "captain_var",
        "location": "location_var", "loc": "location_var",
        "mission": "mission_var",
        "officer": "loading_officer_var",
        "delivery": "delivery_date_var", "date": "delivery_date_var",
        "time": "delivery_date_var",  # TIME: appends to date
        "classification": "_classify_var", "class": "_classify_var",
        "risk": "danger_level_var", "danger": "danger_level_var",
    }
    
    lines = clipboard.split("\n")
    metadata_found = {}
    cargo_lines = []
    separator_found = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Check for separator (--- or ===)
        if stripped.startswith("---") or stripped.startswith("==="):
            separator_found = True
            continue
        # Check for metadata key:value pattern
        if ":" in stripped and not separator_found:
            key_part, _, val_part = stripped.partition(":")
            key_clean = key_part.strip().lower().replace("*", "").replace("_", "")
            val_clean = val_part.strip()
            if key_clean in metadata_keys and val_clean:
                metadata_found[metadata_keys[key_clean]] = val_clean
                continue
        # Everything else or after separator = cargo
        cargo_lines.append(stripped)
    
    # Apply metadata to UI fields
    meta_applied = 0
    for field_attr, value in metadata_found.items():
        if field_attr == "ship_selector" and hasattr(self, "ship_selector"):
            # Fuzzy match ship name against DB
            val_low = value.lower()
            if hasattr(self, "_all_ship_names"):
                matches = [n for n in self._all_ship_names if val_low in n.lower()]
                if matches:
                    value = matches[0]  # Best match
            self.ship_selector.set(value)
            meta_applied += 1
        elif hasattr(self, field_attr):
            var = getattr(self, field_attr)
            if hasattr(var, "set"):
                var.set(value)
                meta_applied += 1
    
    # â”€â”€ PHASE 2: Parse cargo items (same as before, but from filtered lines) â”€â”€
    raw_text = "\n".join(cargo_lines) if cargo_lines else clipboard
    raw_parts = []
    for line in raw_text.split("\n"):
        for part in re.split(r'[,;]', line):
            part = part.strip()
            if part:
                raw_parts.append(part)
    parsed_items = []
    for part in raw_parts:
        # Match patterns: "5x traktor", "10 p4", "20 scorch", "traktor 5", "traktor"
        match = re.match(r'^(?:(\d+)\s*[xX]?\s+)?(.*?)(?:\s+[xX]?(\d+))?$', part)
        if match:
            qty_str = match.group(1) or match.group(3) or "1"
            item_name = (match.group(2) or "").strip()
            if not item_name or item_name.isdigit():
                continue
            try:
                qty = int(qty_str)
            except Exception:
                qty = 1
            if item_name:
                parsed_items.append((item_name, qty))
    if parsed_items:
        added_count = 0
        # Build flat item list from config (handles both dict and list structure)
        flat_items = []
        fi_data = self.config_data.get("frequent_items", [])
        if isinstance(fi_data, dict):
            for cat, cat_items in fi_data.items():
                if isinstance(cat_items, list):
                    flat_items.extend(cat_items)
        elif isinstance(fi_data, list):
            flat_items = fi_data
        
        for raw_name, qty in parsed_items:
            name_clean = self.resolve_slang(raw_name)
            price = 0
            box_size = "unit"
            for fi in flat_items:
                if isinstance(fi, dict) and fi.get("name", "").lower() == name_clean.lower():
                    price = fi.get("price", 0)
                    box_size = fi.get("box_size", fi.get("unit", "unit"))
                    break
            self.add_cargo_row_to_ui(name_clean, str(qty), box_size, price, False, "unit")
            added_count += 1
        if added_count > 0:
            _play_sound("clipboard_import.wav")
            meta_msg = f"\n\nMetadata applied: {meta_applied} fields" if meta_applied > 0 else ""
            meta_detail = ""
            if metadata_found:
                meta_detail = "\n" + "\n".join(f"  {k}: {v}" for k, v in metadata_found.items())
            messagebox.showinfo("Logistics Import", f"Successfully imported {added_count} items from clipboard!\nAll slang names have been resolved to UEE database standards.{meta_msg}{meta_detail}")
    elif not metadata_found:
        # Nothing parsed at all
        messagebox.showerror("Error", "Could not find any items to parse!")

main.RequisitionApp.__init__ = patched_init
main.RequisitionApp.run_sync = run_sync_patched
main.RequisitionApp.resolve_slang = resolve_slang
main.RequisitionApp.handle_global_paste = handle_global_paste


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# Loading Location System - UEX-powered autocomplete + Loading Type dropdown

# Load UEX location database
import json as _json
_uex_locations_db = {}
_uex_ships_db = {}

# Ensure resources directory exists
_res_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
if getattr(sys, 'frozen', False):
    _res_dir = os.path.join(os.path.dirname(sys.executable), "resources")

_loc_db_path = os.path.join(_res_dir, "uex_locations_db.json")
if os.path.exists(_loc_db_path):
    try:
        with open(_loc_db_path, "r", encoding="utf-8") as _f:
            _uex_locations_db = _json.load(_f)
    except: pass
else:
    print("[WARNING] uex_locations_db.json not found - location autocomplete disabled")

_ships_db_path = os.path.join(_res_dir, "uex_ships_db.json")
if os.path.exists(_ships_db_path):
    try:
        with open(_ships_db_path, "r", encoding="utf-8") as _f:
            _uex_ships_db = _json.load(_f)
    except: pass
else:
    print("[WARNING] uex_ships_db.json not found - shuttle recommendations disabled")

# Trade DBs - lazy loaded on first PDF generation to speed up boot
_uex_trade_db = None  # Loaded lazily
_uex_items_trade_db = None  # Loaded lazily

def _ensure_trade_dbs():
    """Lazy-load trade databases on first use."""
    global _uex_trade_db, _uex_items_trade_db
    if _uex_trade_db is None:
        _uex_trade_db = {}
        _trade_db_path = os.path.join(_res_dir, "uex_trade_db.json")
        if os.path.exists(_trade_db_path):
            try:
                with open(_trade_db_path, "r", encoding="utf-8") as _f:
                    _uex_trade_db = _json.load(_f)
            except: pass
    if _uex_items_trade_db is None:
        _uex_items_trade_db = {}
        _items_trade_path = os.path.join(_res_dir, "uex_items_trade_db.json")
        if os.path.exists(_items_trade_path):
            try:
                with open(_items_trade_path, "r", encoding="utf-8") as _f:
                    _uex_items_trade_db = _json.load(_f)
            except: pass

def _verify_and_update_uex_data(status_callback=None):
    """Comprehensive verify: Wiki API + UEX API for ships, cargo grids, name linking.
    
    Returns dict with: added, updated, errors, total_api, total_local,
                       grids_added, grids_linked, warnings
    """
    import urllib.request
    global _uex_ships_db
    
    _SIZE_TO_PAD = {0: "GV", 1: "XS", 2: "S", 3: "M", 4: "L", 5: "XL"}
    result = {
        "added": [], "updated": [], "total_api": 0, "total_local": len(_uex_ships_db),
        "errors": [], "grids_added": [], "grids_linked": [], "warnings": [],
        "uex_total": 0, "wiki_total": 0,
    }
    
    def _normalize(name):
        return name.lower().replace("-", " ").replace("_", " ").strip()
    
    # 1) Fetch from Star Citizen Wiki API
    wiki_vehicles = []
    if status_callback:
        status_callback("Connecting to Star Citizen Wiki API...")
    try:
        url = "https://api.star-citizen.wiki/api/v2/vehicles?limit=500"
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        api_data = _json.loads(raw)
        wiki_vehicles = api_data.get("data", []) if isinstance(api_data, dict) else api_data
        result["wiki_total"] = len(wiki_vehicles)
    except Exception as e:
        result["warnings"].append(f"Wiki API: {e}")
    
    # 2) Fetch from UEX API
    uex_vehicles = []
    if status_callback:
        status_callback("Connecting to UEX API...")
    try:
        url2 = "https://uexcorp.space/api/2.0/vehicles"
        req2 = urllib.request.Request(url2, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
        with urllib.request.urlopen(req2, timeout=20) as resp2:
            raw2 = resp2.read().decode("utf-8")
        uex_data = _json.loads(raw2)
        uex_vehicles = uex_data.get("data", []) if isinstance(uex_data, dict) else uex_data
        result["uex_total"] = len(uex_vehicles)
    except Exception as e:
        result["warnings"].append(f"UEX API: {e}")
    
    if not wiki_vehicles and not uex_vehicles:
        result["errors"].append("Both APIs unreachable")
        return result
    
    result["total_api"] = max(result["wiki_total"], result["uex_total"])
    
    # 3) Process Wiki vehicles
    if status_callback:
        status_callback(f"Processing {len(wiki_vehicles)} Wiki + {len(uex_vehicles)} UEX vehicles...")
    
    for v in wiki_vehicles:
        name = v.get("name", "")
        if not name:
            continue
        key = _normalize(name)
        sizes = v.get("sizes", {}) or {}
        dim = v.get("dimension", {}) or {}
        sc = v.get("size_class", 0) or 0
        new_entry = {
            "name": v.get("game_name", name) or name,
            "short_name": name,
            "scu": v.get("cargo_capacity", 0) or 0,
            "length": sizes.get("length", dim.get("length", 0)) or 0,
            "width": sizes.get("beam", dim.get("width", 0)) or 0,
            "height": sizes.get("height", dim.get("height", 0)) or 0,
            "is_spaceship": 1 if v.get("is_spaceship") else 0,
            "is_ground_vehicle": 1 if v.get("is_vehicle") else 0,
            "size_class": sc,
        }
        if sc in _SIZE_TO_PAD:
            new_entry["pad_type"] = _SIZE_TO_PAD[sc]
        prod = v.get("production_status", {})
        if isinstance(prod, dict):
            new_entry["production_status"] = prod.get("en_EN", "")
        prod_str = str(new_entry.get("production_status", "")).lower()
        new_entry["is_concept"] = ("concept" in prod_str or "in development" in prod_str 
                                   or key in _CONCEPT_SHIPS)
        if key in _uex_ships_db:
            old = _uex_ships_db[key]
            changes = []
            for field in ["length", "width", "height"]:
                if (old.get(field, 0) or 0) == 0 and (new_entry.get(field, 0) or 0) > 0:
                    old[field] = new_entry[field]
                    changes.append(field)
            if not old.get("pad_type") and new_entry.get("pad_type"):
                old["pad_type"] = new_entry["pad_type"]
                changes.append("pad")
            if (old.get("scu", 0) or 0) == 0 and new_entry["scu"] > 0:
                old["scu"] = new_entry["scu"]
                changes.append("scu")
            for f in ["is_spaceship", "is_ground_vehicle", "size_class", "production_status", "is_concept"]:
                if f not in old or f == "is_concept":
                    old[f] = new_entry.get(f, 0)
            if changes:
                result["updated"].append(f"{name} ({', '.join(changes)})")
        else:
            _uex_ships_db[key] = new_entry
            result["added"].append(name)
    
    # 4) Process UEX vehicles (fill gaps)
    for v in uex_vehicles:
        name = v.get("name", "") or v.get("vehicle_name", "")
        if not name:
            continue
        key = _normalize(name)
        scu = v.get("scu", v.get("cargo", 0)) or 0
        pad = v.get("pad_type", v.get("size", "")) or ""
        
        if key in _uex_ships_db:
            old = _uex_ships_db[key]
            changes = []
            if (old.get("scu", 0) or 0) == 0 and scu > 0:
                old["scu"] = scu
                changes.append("scu")
            if not old.get("pad_type") and pad:
                old["pad_type"] = str(pad).upper()
                changes.append("pad")
            if changes and name not in str(result["updated"]):
                result["updated"].append(f"{name} (UEX: {', '.join(changes)})")
        else:
            new_entry = {
                "name": name, "short_name": name, "scu": scu,
                "is_spaceship": 1, "is_ground_vehicle": 0,
            }
            if pad:
                new_entry["pad_type"] = str(pad).upper()
            _uex_ships_db[key] = new_entry
            if name not in result["added"]:
                result["added"].append(f"{name} (UEX)")
    
    # 5) Cross-validate cargo grids
    if status_callback:
        status_callback("Cross-validating cargo grids...")
    
    grids_db = {}
    grids_path = os.path.join(_res_dir, "ship_grids_db.json")
    try:
        if os.path.exists(grids_path):
            with open(grids_path, "r", encoding="utf-8") as gf:
                grids_db = _json.load(gf)
    except:
        pass
    
    grids_keys_lower = {k.lower(): k for k in grids_db}
    grids_modified = False
    
    for key, ship in _uex_ships_db.items():
        scu = ship.get("scu", 0) or 0
        if scu <= 0:
            continue
        if ship.get("is_ground_vehicle", 0):
            continue
        
        ship_name = ship.get("name", ship.get("short_name", key))
        
        # Try to find in grids
        grid_match = None
        for gk_lower, gk_orig in grids_keys_lower.items():
            if key == gk_lower or _normalize(ship_name) == gk_lower:
                grid_match = gk_orig
                break
        
        if not grid_match and scu >= 1 and scu <= 2000:
            # Auto-create stub grid
            w = max(1, int(scu ** 0.5))
            l = max(1, int(scu / w))
            auto_grid = {
                "manufacturer": ship.get("manufacturer", "Unknown"),
                "name": ship_name,
                "capacity": scu,
                "groups": [{"x": 0, "z": 0, "grids": [{"x": 0, "y": 0, "z": 0, "width": w, "height": 1, "length": l}]}],
                "_auto_generated": True
            }
            grids_db[ship_name] = auto_grid
            grids_keys_lower[_normalize(ship_name)] = ship_name
            result["grids_added"].append(f"{ship_name} ({scu} SCU)")
            grids_modified = True
        elif grid_match:
            result["grids_linked"].append(ship_name)
    
    if grids_modified:
        try:
            with open(grids_path, "w", encoding="utf-8") as gf:
                _json.dump(grids_db, gf, indent=2, ensure_ascii=False)
        except Exception as e:
            result["warnings"].append(f"Grid save: {e}")
    
    # 6) Save updated ship DB
    if result["added"] or result["updated"]:
        db_path = os.path.join(_res_dir, "uex_ships_db.json")
        try:
            with open(db_path, "w", encoding="utf-8") as f:
                _json.dump(_uex_ships_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            result["warnings"].append(f"Ship DB save: {e}")
    
    # 7) Ship names for autocomplete
    result["all_ship_names"] = sorted(set(
        v.get("name", v.get("short_name", k)) for k, v in _uex_ships_db.items()
        if v.get("is_spaceship", 1) and v.get("scu", 0) > 0
    ))
    
    if status_callback:
        status_callback(f"Done! Wiki:{result['wiki_total']} UEX:{result['uex_total']} "
                       f"+{len(result['added'])} ~{len(result['updated'])} grids:+{len(result['grids_added'])}")
    
    return result


# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 10: Left Panel Override
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

# Monkey-patch create_left_panel
original_create_left_panel = main.RequisitionApp.create_left_panel

def patched_create_left_panel(self, *args, **kwargs):
    res = original_create_left_panel(self, *args, **kwargs)
    import customtkinter as ctk
    import tkinter as tk

    # HIERARCHY:
    # left_frame = CTkFrame (grid, rows 0-8 = metadata)
    # scroll_frame = left_frame.master = CTkScrollableFrame (pack, sections)
    #   [0] VIEW LOGISTICAL DIRECTIVE button
    #   [1] LOGISTICS MANUAL button
    #   [2] REQUISITION METADATA label
    #   [3] left_frame (metadata)
    #   [4-8] QUICK-ADD section (keep)
    #   [9-12] CLIPBOARD section (keep)
    #   [13] DOCUMENT GENERATION label (replace)
    #   [14] Generate Supply Route PDF button (replace)
    #   [15] SYSTEM UTILITIES label (replace)
    #   [16] Save as Ship Template button (replace)
    #   [17] Update Supply Intel Database button (replace)

    left_frame = None
    for attr in ['location_entry', 'captain_entry', 'loading_crew_entry', 'req_id_entry']:
        if hasattr(self, attr):
            left_frame = getattr(self, attr).master
            break
    if not left_frame:
        return res

    scroll_frame = left_frame.master  # CTkScrollableFrame

    # \u2500\u2500 1) In left_frame: hide row 5 (Loading Location) \u2500\u2500
    for child in left_frame.winfo_children():
        try:
            info = child.grid_info()
            if info and int(info.get('row', -1)) == 5:
                child.grid_remove()
        except:
            pass

    # Row 9: Loading Type (after Severity at row 8)
    self._loading_type_var = tk.StringVar(value="In Hangar")
    ctk.CTkLabel(master=left_frame, text="Loading Type:",
        font=ctk.CTkFont(size=12), text_color="#aabbcc"
    ).grid(row=9, column=0, padx=(10, 5), pady=(5, 5), sticky="w")
    self._loading_type_combo = ctk.CTkComboBox(master=left_frame,
        values=["In Hangar", "Landing Pad", "Planetary", "EVA (Free Float)"],
        variable=self._loading_type_var, state="readonly", width=200,
        fg_color="#1a1a2e", button_color="#2a3a4a",
        dropdown_fg_color="#1a1a2e", dropdown_text_color="#dddddd", text_color="#dddddd")
    self._loading_type_combo.grid(row=9, column=1, padx=(0, 10), pady=(5, 5), sticky="ew")

    # Row 10: Station / Location (right after Loading Type)
    ctk.CTkLabel(master=left_frame, text="Station / Location:",
        font=ctk.CTkFont(size=12), text_color="#aabbcc"
    ).grid(row=10, column=0, padx=(10, 5), pady=(5, 2), sticky="w")
    self._location_ac_var = tk.StringVar()
    self._location_ac_entry = ctk.CTkEntry(master=left_frame, textvariable=self._location_ac_var,
        placeholder_text="Type to search...", width=200,
        fg_color="#1a1a2e", text_color="#dddddd", border_color="#2a3a4a")
    self._location_ac_entry.grid(row=10, column=1, padx=(0, 10), pady=(5, 2), sticky="ew")

    # Row 10: autocomplete listbox (hidden initially)
    self._ac_listbox = tk.Listbox(left_frame, height=5, bg="#1a1a2e", fg="#dddddd",
        selectbackground="#2a3a4a", selectforeground="#ffffff",
        font=("Segoe UI", 9), borderwidth=1, relief="solid")

    # Load location DB
    _all_locs = []
    try:
        _lp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "uex_locations_db.json")
        if getattr(sys, 'frozen', False):
            _lp = os.path.join(os.path.dirname(sys.executable), "resources", "uex_locations_db.json")
        if os.path.exists(_lp):
            with open(_lp, "r", encoding="utf-8") as lf:
                locs = json.load(lf)
            if isinstance(locs, dict):
                _tl = {"cities": "City", "space_stations": "Station", "outposts": "Outpost",
                        "planets": "Planet", "moons": "Moon"}
                for ck, cd in locs.items():
                    if isinstance(cd, dict):
                        t = _tl.get(ck, ck)
                        for ln, ld in cd.items():
                            p = ld.get('planet', '') if isinstance(ld, dict) else ''
                            s = ld.get('system', '') if isinstance(ld, dict) else ''
                            parts = [f"[{t}]", ln]
                            if p: parts.append(f"({p})")
                            elif s: parts.append(f"({s})")
                            _all_locs.append((" ".join(parts), ck, ln))
    except: pass

    def _filt():
        lt = self._loading_type_var.get()
        if lt == "Landing Pad": return [l for l in _all_locs if l[1] == "space_stations"]
        elif lt == "In Hangar": return [l for l in _all_locs if l[1] in ("cities", "space_stations")]
        elif lt == "Planetary": return [l for l in _all_locs if l[1] == "outposts"]
        else:
            r = [l for l in _all_locs if l[1] in ("planets", "moons")]
            r.insert(0, ("[Deep Space] Open Orbit", "deep_space", "Deep Space"))
            return r

    def _on_key(event):
        typed = self._location_ac_var.get().lower()
        if len(typed) < 2: self._ac_listbox.grid_remove(); return
        ms = [l[0] for l in _filt() if typed in l[0].lower()][:8]
        if ms:
            self._ac_listbox.delete(0, tk.END)
            for m in ms: self._ac_listbox.insert(tk.END, m)
            self._ac_listbox.grid(row=11, column=0, columnspan=2, padx=10, sticky="ew")
        else: self._ac_listbox.grid_remove()

    def _on_sel(event):
        sel = self._ac_listbox.curselection()
        if sel: self._location_ac_var.set(self._ac_listbox.get(sel[0])); self._ac_listbox.grid_remove()

    self._location_ac_entry.bind("<KeyRelease>", _on_key)
    self._ac_listbox.bind("<<ListboxSelect>>", _on_sel)
    def _lt_chg(*a): self._location_ac_var.set(""); self._ac_listbox.grid_remove()
    self._loading_type_var.trace_add("write", _lt_chg)

    def _clean(raw):
        n = raw
        if n.startswith("["):
            idx = n.find("] ")
            if idx > 0: n = n[idx + 2:]
        if " (" in n: n = n[:n.rfind(" (")]
        return n.strip()

    # Wire to PDF
    if hasattr(self, 'location_entry'):
        def _lg():
            lt, loc = self._loading_type_var.get(), self._location_ac_var.get()
            return f"{_clean(loc)} ({lt})" if loc else lt
        self.location_entry.get = _lg
    if hasattr(self, 'location_var'):
        def _lvg():
            lt, loc = self._loading_type_var.get(), self._location_ac_var.get()
            return f"{_clean(loc)} ({lt})" if loc else lt
        self.location_var.get = _lvg

    # Shuttle status (inside left_frame grid row 11)
    self._shuttle_status = ctk.CTkLabel(master=left_frame, text="", font=ctk.CTkFont(size=9),
        text_color="#556677", anchor="w")
    self._shuttle_status.grid(row=12, column=0, columnspan=2, padx=10, pady=(0, 0), sticky="w")
    def _upd_sh(*a):
        v = self.ship_selector.get().upper() if hasattr(self, 'ship_selector') else ""
        lt = self._loading_type_var.get()
        cap = any(k in v for k in ["IDRIS", "JAVELIN", "POLARIS", "KRAKEN", "BENGAL", "890"])
        if lt == "EVA (Free Float)" and cap:
            self._shuttle_status.configure(text="\u26a0 EVA FREE-FLOAT: No docking", text_color="#cc4444")
        elif lt == "EVA (Free Float)":
            self._shuttle_status.configure(text="\u26a0 EVA: Manual transfer", text_color="#cc8844")
        elif lt == "In Hangar" and cap:
            self._shuttle_status.configure(text="\u2713 Hangar loading", text_color="#66cc77")
        elif lt == "Landing Pad" and cap:
            self._shuttle_status.configure(text="\u2713 Landing pad ops", text_color="#ccaa33")
        else: self._shuttle_status.configure(text="")
    self._loading_type_var.trace_add("write", _upd_sh)

    # \u2500\u2500 2) In scroll_frame: Replace DOCUMENT GENERATION [13-14] + SYSTEM UTILITIES [15-17] \u2500\u2500
    # Hide old sections by text matching in scroll_frame children
    _hide_texts = ['document generation', 'system utilities',
                   'generate supply route', 'save as ship template', 'update supply intel']
    for child in scroll_frame.winfo_children():
        try:
            if not hasattr(child, 'cget'): continue
            try: txt = str(child.cget('text')).lower()
            except: continue
            for ht in _hide_texts:
                if ht in txt:
                    child.pack_forget()
                    break
        except: pass

    # Add new unified section to scroll_frame (packed at bottom)
    sec_label = ctk.CTkLabel(master=scroll_frame, text="[ DOCUMENT GENERATION & UTILITIES ]",
        font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#c8a84e")
    sec_label.pack(padx=10, pady=(10, 2), anchor="w")

    # Classification row
    cls_frame = ctk.CTkFrame(master=scroll_frame, fg_color="transparent")
    cls_frame.pack(padx=10, pady=(2, 5), fill="x")
    ctk.CTkLabel(master=cls_frame, text="Classification:", font=ctk.CTkFont(size=11),
        text_color="#8899aa").pack(side="left", padx=(0, 5))

    self._classify_var = tk.StringVar(value="ALL")
    def _on_cls(val):
        cs = {"ALL": ("#1a2a3a", "#888888"), "PUBLIC": ("#1a3a1a", "#66cc77"),
              "SECURED": ("#3a3a1a", "#ccaa33"), "CLASSIFIED": ("#3a1a1a", "#cc4444")}
        c = cs.get(val, cs["ALL"])
        self._classify_combo.configure(fg_color=c[0], text_color=c[1])
        # Map classification to security level
        m = {"ALL": "ALL", "PUBLIC": "OPEN_PUBLIC", "SECURED": "RESTRICTED",
             "CLASSIFIED": "OFFICERS_ONLY_ENCRYPTED"}
        sec_val = m.get(val, "ALL")
        if hasattr(self, 'security_level_var'):
            self.security_level_var.set(sec_val)
        if hasattr(self, 'on_security_level_changed'):
            self.on_security_level_changed(sec_val)
        if val == "ALL":
            # ALL = only Gen All active, disable single manifest + supply route
            self._gen3_btn.configure(state="normal", fg_color="#3a2a10", hover_color="#5a4a20", text_color="#c8a84e")
            self._sr_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
            # Disable golden manifest button
            if hasattr(self, 'generate_btn'):
                self.generate_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
        else:
            # Specific classification: enable single manifest + supply route, disable Gen All
            self._gen3_btn.configure(state="disabled", fg_color="#2a2a2a", hover_color="#2a2a2a", text_color="#555555")
            self._sr_btn.configure(state="normal", fg_color="#2a3a1a", text_color="#c8a84e")
            if hasattr(self, 'generate_btn'):
                self.generate_btn.configure(state="normal", fg_color="#c8a84e", text_color="#1a1a1a")

    self._classify_combo = ctk.CTkComboBox(master=cls_frame,
        values=["ALL", "PUBLIC", "SECURED", "CLASSIFIED"],
        variable=self._classify_var, state="readonly", width=160, command=_on_cls,
        fg_color="#1a2a3a", text_color="#c8a84e", button_color="#2a3a4a",
        dropdown_fg_color="#1a2a3a", dropdown_text_color="#aabbcc", dropdown_hover_color="#2a3a4a")
    self._classify_combo.pack(side="left", fill="x", expand=True)

    # Generate Supply Route PDF (single) - keep original functionality
    self._sr_btn = ctk.CTkButton(master=scroll_frame, text="Generate Supply Route PDF",
        command=lambda: self.animate_generate_supply_route_pdf(),
        font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
        fg_color="#2a3a1a", hover_color="#3a4a2a", text_color="#c8a84e",
        height=30, corner_radius=6)
    self._sr_btn.pack(padx=10, pady=(2, 2), fill="x")

    # Generate All 3 PDFs (3 manifests: PUBLIC, SECURED, CLASSIFIED)
    def _gen3():
        if not self.cargo_rows:
            messagebox.showerror("Error", "Cargo table is empty!")
            return
        # Ask for save folder ONCE
        from tkinter import filedialog as fd
        save_dir = fd.askdirectory(title="Select folder to save all 3 PDFs")
        if not save_dir:
            return
        
        self._gen3_btn.configure(text="\u27f3 Generating...", state="disabled")
        self.update_idletasks()
        
        # Collect items from cargo table
        items = []
        for row in self.cargo_rows:
            name = row['name_var'].get().strip()
            qty_str = row['qty_var'].get().strip()
            unit = row['unit']
            box_size = row['box_size_var'].get().strip() if 'box_size_var' in row else '1 SCU'
            if not qty_str or qty_str == '?':
                continue
            try:
                qty = int(float(qty_str))
                if qty <= 0: continue
            except ValueError:
                continue
            items.append({'name': name, 'qty': qty, 'unit': unit, 'box_size': box_size})
        
        if not items:
            messagebox.showerror("Error", "No items with valid quantities!")
            self._gen3_btn.configure(text="Generate All 3 PDFs", state="normal",
                fg_color="#3a2a10", text_color="#c8a84e")
            return
        
        warehouse = ""
        if hasattr(self, 'location_var'):
            warehouse = self.location_var.get().strip()
        if not warehouse:
            warehouse = "Port Tressler"
        
        lvls = [
            ("OPEN_PUBLIC", "PUBLIC"),
            ("RESTRICTED", "SECURED_MEMBERS"),
            ("OFFICERS_ONLY_ENCRYPTED", "CLASSIFIED")
        ]
        generated = 0
        orig_sec = self.security_level_var.get() if hasattr(self, 'security_level_var') else "ALL"
        
        self._gen3_running = True  # Suppress per-PDF popups
        # Suppress ALL messagebox popups during batch generation
        import tkinter.messagebox as _mb
        _orig_showinfo = _mb.showinfo
        _orig_showwarning = _mb.showwarning
        _mb.showinfo = lambda *a, **kw: None
        _mb.showwarning = lambda *a, **kw: None
        
        # 1) Generate Supply Route PDF
        try:
            req_id_batch = self.req_id_var.get().replace(' ', '_').replace('/', '-')[:30] if hasattr(self, 'req_id_var') else 'SR'
            sr_path = os.path.join(save_dir, f"{req_id_batch}_supply_route.pdf")
            generate_pdf_direct(self, save_path=sr_path)
            generated += 1
        except Exception as e:
            print(f"[Gen3] Error generating supply route: {e}")
        
        # 2) Generate 3 Manifest PDFs via main.pyc
        from tkinter import filedialog as _fd
        _orig_asksave = _fd.asksaveasfilename  # Save original
        
        for sec_val, label in lvls:
            try:
                # Set security level for header/badge
                if hasattr(self, 'security_level_var'):
                    self.security_level_var.set(sec_val)
                if hasattr(self, 'on_security_level_changed'):
                    self.on_security_level_changed(sec_val)
                
                # Set classification for redaction logic
                cls_map = {"OPEN_PUBLIC": "PUBLIC", "RESTRICTED": "SECURED",
                           "OFFICERS_ONLY_ENCRYPTED": "CLASSIFIED"}
                cls_val = cls_map.get(sec_val, "ALL")
                if hasattr(self, '_classify_var'):
                    self._classify_var.set(cls_val)
                # Force invalidate lore story cache for correct redaction
                global LORE_STORY_CACHE
                LORE_STORY_CACHE["text"] = None
                self.update_idletasks()
                import time; time.sleep(0.1)
                
                # Monkey-patch filedialog to return batch path
                target_path = os.path.join(save_dir, f"{req_id_batch}_{label}.pdf")
                _fd.asksaveasfilename = lambda _tp=target_path, **kw: _tp
                
                # Generate manifest via main.pyc
                _orig_gen_req(self)
                generated += 1
            except Exception as e:
                print(f"[Gen3] Error generating {label}: {e}")
        
        # Restore filedialog
        _fd.asksaveasfilename = _orig_asksave
        
        # Restore original classification
        self._gen3_running = False
        # Restore messagebox
        _mb.showinfo = _orig_showinfo
        _mb.showwarning = _orig_showwarning
        if hasattr(self, 'security_level_var'):
            self.security_level_var.set(orig_sec)
        if hasattr(self, 'on_security_level_changed'):
            self.on_security_level_changed(orig_sec)
        self._gen3_btn.configure(text="Generate All PDFs", state="normal",
            fg_color="#3a2a10", text_color="#c8a84e")
        if generated > 0:
            _play_sound("pdf_generated.wav")
            messagebox.showinfo("Batch Complete",
                f"All {generated} PDFs saved in:\n{save_dir}")

    self._gen3_btn = ctk.CTkButton(master=scroll_frame, text="Generate All PDFs", command=_gen3,
        font=ctk.CTkFont(size=11, weight="bold"), fg_color="#3a2a10", hover_color="#5a4a20",
        text_color="#c8a84e", height=30, corner_radius=6)
    self._gen3_btn.pack(padx=10, pady=(2, 2), fill="x")

    # Find the golden "GENERATE MANIFEST PDF" button from main.pyc and store reference
    def _find_generate_btn(parent):
        """Recursively find the golden manifest button in the widget tree."""
        for child in parent.winfo_children():
            try:
                txt = str(child.cget('text')).upper()
                if 'GENERATE' in txt and 'MANIFEST' in txt:
                    return child
            except: pass
            try:
                found = _find_generate_btn(child)
                if found: return found
            except: pass
        return None
    self.generate_btn = _find_generate_btn(self)
    
    # Initial state: ALL selected = disable manifest + SR, enable Gen All
    self._sr_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
    def _force_disable_golden():
        try:
            if self.generate_btn and self._classify_var.get().upper() == "ALL":
                self.generate_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
        except: pass
    if self.generate_btn:
        self.generate_btn.configure(state="disabled", fg_color="#2a2a2a", text_color="#555555")
    self.after(300, _force_disable_golden)
    self.after(1000, _force_disable_golden)
    self.after(2500, _force_disable_golden)

    # Update Trade Routes
    def _update_trade_routes():
        import threading
        self._trade_btn.configure(text="\u27f3 Updating...", state="disabled")
        self.update_idletasks()
        def _run():
            import urllib.request
            result = {"updated": 0, "errors": [], "items": []}
            try:
                # Fetch commodities from UEX API
                url = "https://uexcorp.space/api/2.0/commodities"
                req = urllib.request.Request(url, headers={"User-Agent": "StarlifterRequisitionTerminal/0.6"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = resp.read().decode("utf-8")
                api_data = _json.loads(raw)
                commodities = api_data.get("data", []) if isinstance(api_data, dict) else api_data
                
                # Build lookup by name (lowercase)
                api_lookup = {}
                for c in commodities:
                    cname = (c.get("name", "") or c.get("commodity_name", "")).lower().strip()
                    if cname:
                        api_lookup[cname] = c
                
                # Match against config items
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
                if getattr(sys, 'frozen', False):
                    config_path = os.path.join(os.path.dirname(sys.executable), "config.json")
                
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as cf:
                        config = _json.load(cf)
                    
                    items = config.get("frequent_items", [])
                    for item in items:
                        iname = item.get("name", "").lower().strip()
                        match = api_lookup.get(iname)
                        if not match:
                            for k, v in api_lookup.items():
                                if iname in k or k in iname:
                                    match = v
                                    break
                        if match:
                            new_price = match.get("price_buy", match.get("price", 0)) or 0
                            if new_price > 0 and new_price != item.get("price", 0):
                                old_price = item.get("price", 0)
                                item["price"] = new_price
                                result["items"].append(f"{item['name']}: {old_price} \u2192 {new_price} aUEC")
                                result["updated"] += 1
                    
                    if result["updated"] > 0:
                        with open(config_path, "w", encoding="utf-8") as cf:
                            _json.dump(config, cf, indent=2, ensure_ascii=False)
                        if hasattr(self, 'config_data'):
                            self.config_data = config
                
                result["total_commodities"] = len(commodities)
                result["matched"] = sum(1 for item in items if any(
                    item.get("name","").lower().strip() in k or k in item.get("name","").lower().strip()
                    for k in api_lookup))
                
            except Exception as e:
                result["errors"].append(str(e))
            
            self.after(0, lambda: _trade_done(result))
        
        def _trade_done(r):
            self._trade_btn.configure(text="\u27f3 Update Trade Routes", state="normal")
            if r["errors"]:
                messagebox.showerror("Trade Routes", f"Error: {r['errors'][0]}")
            else:
                msg = f"UEX Commodities: {r.get('total_commodities', 0)}\n"
                msg += f"Matched items: {r.get('matched', 0)}\n"
                msg += f"Price updates: {r['updated']}\n\n"
                if r["items"]:
                    msg += "Changes:\n" + "\n".join(f"  {s}" for s in r["items"][:15])
                else:
                    msg += "All prices up to date!"
                _play_sound("verify_sync.wav")
                messagebox.showinfo("Trade Routes", msg)
        
        threading.Thread(target=_run, daemon=True).start()

    self._trade_btn = ctk.CTkButton(master=scroll_frame, text="\u27f3 Update Trade Routes",
        command=_update_trade_routes,
        font=ctk.CTkFont(size=10), fg_color="#1a2a3a", hover_color="#2a3a4a",
        text_color="#6699bb", height=26, corner_radius=6)
    self._trade_btn.pack(padx=10, pady=(5, 2), fill="x")

    # Verify All Data (grey)
    import threading
    _sp = ["\u27f3", "\u25d0", "\u25d3", "\u25d1", "\u25d2"]; _si = [0]; _sa = [False]
    def _anim():
        if _sa[0]:
            _si[0] = (_si[0] + 1) % len(_sp)
            self._verify_btn.configure(text=f"{_sp[_si[0]]} Syncing...")
            self.after(200, _anim)
    def _on_verify():
        self._verify_btn.configure(state="disabled"); _sa[0] = True; _anim()
        def _run():
            result = _verify_and_update_uex_data()
            self.after(0, lambda: _done(result))
        def _done(r):
            _sa[0] = False
            self._verify_btn.configure(text="\u27f3 Verify All Data", state="normal")
            if r["errors"]:
                messagebox.showerror("Verify", f"Error: {r['errors'][0]}")
            else:
                a, u = len(r["added"]), len(r["updated"])
                ga = len(r.get("grids_added", []))
                gl = len(r.get("grids_linked", []))
                wn = r.get("warnings", [])
                msg = f"Wiki API: {r.get('wiki_total', 0)} vehicles\n"
                msg += f"UEX API: {r.get('uex_total', 0)} vehicles\n"
                msg += f"Local DB: {len(_uex_ships_db)} ships\n"
                msg += f"Cargo grids: {gl} linked, {ga} auto-created\n\n"
                if a:
                    msg += f"\u2795 {a} NEW ships:\n" + "".join(f"  + {s}\n" for s in r["added"][:12])
                if u:
                    msg += f"\n\u27f3 {u} UPDATED:\n" + "".join(f"  ~ {s}\n" for s in r["updated"][:12])
                if ga:
                    msg += f"\n\U0001f4e6 {ga} new cargo grids:\n" + "".join(f"  \u25a3 {s}\n" for s in r["grids_added"][:8])
                if wn:
                    msg += f"\n\u26a0 Warnings:\n" + "".join(f"  ! {w}\n" for w in wn[:5])
                if not a and not u and not ga:
                    msg += "\u2713 All databases up to date!"
                # Update ship selector if new ships available
                if r.get("all_ship_names") and hasattr(self, 'ship_selector'):
                    try:
                        self.ship_selector.configure(values=r["all_ship_names"])
                    except: pass
                _play_sound("verify_sync.wav")
                messagebox.showinfo("Verify All Data", msg)
        threading.Thread(target=_run, daemon=True).start()

    self._verify_btn = ctk.CTkButton(master=scroll_frame, text="\u27f3 Verify All Data", command=_on_verify,
        font=ctk.CTkFont(size=10), fg_color="#2a2a2a", hover_color="#3a3a3a",
        text_color="#888888", height=26, corner_radius=6)
    self._verify_btn.pack(padx=10, pady=(5, 10), fill="x")

    # Patch clipboard exports to not show messagebox
    _orig_export = main.RequisitionApp.export_to_clipboard
    _orig_export_blank = main.RequisitionApp.export_blank_template_to_clipboard
    def _silent_export(s, *a, **kw):
        _orig_showinfo = messagebox.showinfo
        messagebox.showinfo = lambda *a, **kw: None
        try: _orig_export(s, *a, **kw)
        finally: messagebox.showinfo = _orig_showinfo
    def _silent_export_blank(s, *a, **kw):
        _orig_showinfo = messagebox.showinfo
        messagebox.showinfo = lambda *a, **kw: None
        try: _orig_export_blank(s, *a, **kw)
        finally: messagebox.showinfo = _orig_showinfo
    main.RequisitionApp.export_to_clipboard = _silent_export
    main.RequisitionApp.export_blank_template_to_clipboard = _silent_export_blank

    return res

main.RequisitionApp.create_left_panel = patched_create_left_panel


# â”€â”€ Monkey-patch add_new_vessel: custom autocomplete dialog â”€â”€
_orig_add_new_vessel = main.RequisitionApp.add_new_vessel
def _patched_add_new_vessel(self):
    """Custom 'Add New Vessel' dialog with autocomplete from ship DB."""
    import tkinter as tk
    
    all_ships = getattr(self, '_all_ship_names', [])
    if not all_ships and _uex_ships_db:
        all_ships = sorted(set(
            v.get("name", v.get("short_name", k))
            for k, v in _uex_ships_db.items()
            if v.get("scu", 0) > 0 and v.get("is_spaceship", 1)
        ))
    
    result = [None]
    
    dlg = tk.Toplevel(self)
    dlg.title("Add New Vessel")
    dlg.geometry("380x340")
    dlg.configure(bg="#1a1a2e")
    dlg.transient(self)
    dlg.grab_set()
    
    tk.Label(dlg, text="Enter new vessel/ship name:", fg="#cccccc", bg="#1a1a2e",
             font=("Segoe UI", 10)).pack(padx=15, pady=(15, 5), anchor="w")
    
    entry_var = tk.StringVar()
    entry = tk.Entry(dlg, textvariable=entry_var, font=("Segoe UI", 11),
                     bg="#0d1117", fg="#ffffff", insertbackground="#ffffff",
                     relief="solid", bd=1)
    entry.pack(padx=15, pady=(0, 5), fill="x")
    entry.focus_set()
    
    tk.Label(dlg, text="Suggestions from database:", fg="#888888", bg="#1a1a2e",
             font=("Segoe UI", 8)).pack(padx=15, pady=(5, 2), anchor="w")
    
    listbox = tk.Listbox(dlg, height=10, bg="#0d1117", fg="#dddddd",
                         selectbackground="#2a3a4a", selectforeground="#ffffff",
                         font=("Segoe UI", 9), relief="solid", bd=1)
    listbox.pack(padx=15, pady=(0, 10), fill="both", expand=True)
    
    def _filter(*args):
        typed = entry_var.get().lower().strip()
        listbox.delete(0, tk.END)
        if len(typed) < 2:
            for s in all_ships[:30]:
                listbox.insert(tk.END, s)
            return
        words = typed.split()
        matches = [s for s in all_ships if all(w in s.lower() for w in words)]
        if not matches:
            matches = [s for s in all_ships if typed in s.lower()]
        for s in matches[:30]:
            listbox.insert(tk.END, s)
    
    entry_var.trace_add("write", _filter)
    _filter()
    
    def _on_select(event):
        sel = listbox.curselection()
        if sel:
            entry_var.set(listbox.get(sel[0]))
    
    def _on_dblclick(event):
        sel = listbox.curselection()
        if sel:
            entry_var.set(listbox.get(sel[0]))
            _ok()
    
    listbox.bind("<<ListboxSelect>>", _on_select)
    listbox.bind("<Double-1>", _on_dblclick)
    
    btn_frame = tk.Frame(dlg, bg="#1a1a2e")
    btn_frame.pack(padx=15, pady=(0, 15), fill="x")
    
    def _ok():
        name = entry_var.get().strip()
        if name:
            result[0] = name
        dlg.destroy()
    
    def _cancel():
        dlg.destroy()
    
    tk.Button(btn_frame, text="OK", command=_ok, width=12,
              bg="#2a3a4a", fg="#ffffff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
    tk.Button(btn_frame, text="Cancel", command=_cancel, width=12,
              bg="#333333", fg="#cccccc", font=("Segoe UI", 9)).pack(side="left")
    
    entry.bind("<Return>", lambda e: _ok())
    entry.bind("<Escape>", lambda e: _cancel())
    
    dlg.wait_window()
    
    new_name = result[0]
    if not new_name:
        return
    
    # Check duplicate
    existing = list(self.config_data.get("vessels", {}).keys())
    if new_name in existing:
        messagebox.showerror("Error", f"Vessel '{new_name}' already exists!")
        return
    
    # Add to config
    self.config_data.setdefault("vessels", {})[new_name] = {}
    self.save_config_file()
    vessel_options = list(self.config_data.get("vessels", {}).keys())
    self.ship_selector.configure(values=sorted(vessel_options))
    self.ship_selector.set(new_name)
    self.on_vessel_changed()
    _play_sound("cargo_add.wav")

main.RequisitionApp.add_new_vessel = _patched_add_new_vessel

# Disable Communication Channel dropdown (visual only, controlled by Classification)
_orig_show_main = main.RequisitionApp.show_main_app_layout
def _patched_show_main(self, *a, **kw):
    r = _orig_show_main(self, *a, **kw)
    try:
        if hasattr(self, 'sec_selector'):
            self.sec_selector.configure(state="disabled")
            # Find "Communication Channel:" header label in parent
            self._com_header = None
            parent = self.sec_selector.master
            for child in parent.winfo_children():
                if hasattr(child, 'cget'):
                    try:
                        txt = child.cget("text")
                        if txt and "channel" in str(txt).lower():
                            self._com_header = child
                            child.configure(text_color="#778899")  # Neutral blue-gray
                            break
                    except: pass
            
            def _style_com(text, txt_color, fg_color, btn_color):
                """Set text + colors on CTkComboBox and force redraw."""
                self.sec_selector.set(text)
                self.sec_selector.configure(
                    text_color=txt_color,
                    fg_color=fg_color,
                    button_color=btn_color,
                    button_hover_color=btn_color
                )
                try: self.sec_selector._draw()
                except: pass
            
            def _patched_sec_changed(sec_val):
                try:
                    sv = sec_val.upper() if sec_val else "ALL"
                    if sv == "ALL" or not sv:
                        _style_com("// INACTIVE CHANNEL //",
                            "#888888", "#2a2a2a", "#333333")
                    elif "PUBLIC" in sv or "OPEN" in sv:
                        _style_com("\u25C9  OPEN TO PUBLIC",
                            "#ccffdd", "#1a4a1a", "#2a5a2a")
                    elif "RESTRICTED" in sv or "SECURED" in sv:
                        _style_com("\u25C9  44th BATTLEGROUP RESTRICTED",
                            "#ffeeaa", "#3a3a0a", "#4a4a1a")
                    elif "OFFICERS" in sv or "ENCRYPTED" in sv:
                        _style_com("\u26A0  OFFICERS OF 44th BG ONLY",
                            "#ffcccc", "#3a0a0a", "#4a1a1a")
                    else:
                        self.sec_selector.set(sec_val)
                except Exception as e:
                    print(f"[SecChanged] {e}")
            self.on_security_level_changed = _patched_sec_changed
            _patched_sec_changed("ALL")
    except: pass
    
    # â”€â”€ Ship Selector: loadout vessels only â”€â”€
    try:
        if hasattr(self, 'ship_selector'):
            loadout_vessels = sorted(self.config_data.get("vessels", {}).keys())
            all_db_names = sorted(set(
                v.get("name", v.get("short_name", k))
                for k, v in _uex_ships_db.items()
                if v.get("scu", 0) > 0 and v.get("is_spaceship", 1)
            )) if _uex_ships_db else []
            self._loadout_ship_names = loadout_vessels
            self._all_ship_names = all_db_names
            self.ship_selector.configure(values=loadout_vessels)
            self.ship_selector.set("")  # Empty â€” user must select
            # Clear default loadout cargo that main.pyc loaded
            if hasattr(self, 'cargo_rows') and self.cargo_rows:
                for row in list(self.cargo_rows):
                    try:
                        if 'frame' in row:
                            row['frame'].destroy()
                    except: pass
                self.cargo_rows.clear()
            # Delayed clear: main.pyc may re-set default ship after our patch
            def _force_empty_ship():
                try:
                    self.ship_selector.set("")
                    if hasattr(self, 'cargo_rows') and self.cargo_rows:
                        for row in list(self.cargo_rows):
                            try:
                                if 'frame' in row: row['frame'].destroy()
                            except: pass
                        self.cargo_rows.clear()
                except: pass
            self.after(500, _force_empty_ship)
            self.after(1500, _force_empty_ship)
            self.after(3000, _force_empty_ship)
            self.after(5000, _force_empty_ship)
            self.after(8000, _force_empty_ship)
            # Set delivery date to SC format (year + 930)
            if hasattr(self, 'delivery_date_var'):
                self.delivery_date_var.set(sc_date_only())
            # Regenerate req_id when ship changes
            def _on_ship_selected(event=None):
                if hasattr(self, 'req_id_var'):
                    import time
                    ship = self.ship_selector.get().strip()
                    if ship and len(ship) > 3:
                        seed = hash(ship + str(int(time.time())))
                        rng = random.Random(seed)
                        suffixes = ["X41", "X86", "S26", "A17", "B03", "C55", "D12"]
                        new_id = f"UEE-LOG-{rng.randint(10,99)}-{rng.randint(1000,9999)}-{rng.choice(suffixes)}"
                        self.req_id_var.set(new_id)
                        _play_sound("cargo_add.wav")
            
            self.ship_selector.bind('<<ComboboxSelected>>', _on_ship_selected)
    except Exception as e:
        print(f"[Ship selector] {e}")
    
    # â”€â”€ Item Combo: add search/filter autocomplete â”€â”€
    try:
        if hasattr(self, 'item_combo') or hasattr(self, 'item_dropdown'):
            combo = getattr(self, 'item_combo', None) or getattr(self, 'item_dropdown', None)
            if combo:
                fi_data = self.config_data.get("frequent_items", {})
                all_item_names = []
                if isinstance(fi_data, dict):
                    for cat, cat_items in fi_data.items():
                        if isinstance(cat_items, list):
                            for item in cat_items:
                                if isinstance(item, dict) and item.get("name"):
                                    all_item_names.append(item["name"])
                elif isinstance(fi_data, list):
                    for item in fi_data:
                        if isinstance(item, dict) and item.get("name"):
                            all_item_names.append(item["name"])
                self._all_item_names = sorted(set(all_item_names))
                
                def _on_item_key(event=None):
                    typed = combo.get().lower().strip()
                    if not typed or len(typed) < 2:
                        combo.configure(values=self._all_item_names)
                        return
                    words = typed.split()
                    filtered = [n for n in self._all_item_names if all(w in n.lower() for w in words)]
                    if not filtered:
                        filtered = [n for n in self._all_item_names if typed in n.lower()]
                    if filtered:
                        combo.configure(values=filtered)
                        try: combo._open_dropdown_menu()
                        except: pass
                
                combo.bind('<KeyRelease>', _on_item_key)
    except Exception as e:
        print(f"[Item autocomplete] {e}")
    
    return r
main.RequisitionApp.show_main_app_layout = _patched_show_main


# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â
# SECTION 11: Final Wiring + Entry Point
# Ă˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘ÂĂ˘â€˘Â

# Wire PDF generation
main.RequisitionApp.generate_supply_route_pdf = _patched_generate_supply_route_pdf
main.RequisitionApp.animate_generate_supply_route_pdf = _patched_animate_generate
main.RequisitionApp.run_supply_route_generation = lambda self, items=None, warehouse='': generate_pdf_direct(self)

# â”€â”€ Monkey-patch manifest generation: sync classification + sound â”€â”€
_orig_gen_req = main.RequisitionApp.generate_requisition_pdf
def _patched_generate_requisition_pdf(self):
    """Sync _classify_var â†’ security_level_var before manifest generation."""
    # Guard: ALL = disabled, must select specific classification
    cls_val = self._classify_var.get().upper() if hasattr(self, '_classify_var') else "ALL"
    if cls_val == "ALL":
        from tkinter import messagebox
        messagebox.showwarning("Classification Required",
            "Select a specific classification (PUBLIC / SECURED / CLASSIFIED) before generating.")
        return
    cls_to_sec = {
        "CLASSIFIED": "OFFICERS_ONLY_ENCRYPTED",
        "SECURED": "RESTRICTED",
        "PUBLIC": "OPEN_PUBLIC",
    }
    sec_val = cls_to_sec.get(cls_val, "OFFICERS_ONLY_ENCRYPTED")
    if hasattr(self, 'security_level_var'):
        self.security_level_var.set(sec_val)
    _play_sound("pdf_generated.wav")
    return _orig_gen_req(self)

main.RequisitionApp.generate_requisition_pdf = _patched_generate_requisition_pdf

if __name__ == '__main__':
    try:
        import customtkinter
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")
        app = main.RequisitionApp()
        app.mainloop()
    except Exception as e:
        import traceback
        import sys
        import os
        import tkinter as tk
        from tkinter import messagebox
        
        # Determine base path for the log
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        crash_log = os.path.join(base_dir, 'crash_log.txt')
        
        try:
            with open(crash_log, 'w', encoding='utf-8') as f:
                f.write("A critical error occurred while starting the application:\n\n")
                traceback.print_exc(file=f)
                f.write("\n\nPlease send this crash_log.txt to the developer.")
        except:
            pass # Fail silently if we can't write the log
            
        # Try to show a popup error
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", f"Application crashed on startup.\nSee {crash_log} for details.\n\nError: {str(e)}")
            root.destroy()
        except:
            pass
