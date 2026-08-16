# -*- coding: utf-8 -*-
"""
slang_helper.py - Slang resolution for cargo item names.

Converts user slang/abbreviations to canonical item names.
E.g. "tractor" -> "MaxLift Tractor Beam", "kvanta" -> "Refined Quantainium"

Usage:
    from slang_helper import resolve_slang
"""
import os


import re

def resolve_slang(name_raw, config_data=None):
    if not name_raw or not isinstance(name_raw, str):
        return name_raw
    name_raw_low = name_raw.lower().strip()

    # Strip quantity multipliers like '10x', 'x10', '5x', 'x2'
    name_raw_clean = re.sub(r'\b(?:\d+x|x\d+)\b', '', name_raw_low).strip()
    if name_raw_clean:
        name_raw_low = name_raw_clean

    # 1. Custom user slang_aliases from config.json or config_data
    custom_aliases = {}
    if config_data and isinstance(config_data, dict) and "slang_aliases" in config_data:
        custom_aliases = config_data.get("slang_aliases", {})
    else:
        try:
            from path_config import PATHS
            import json as _json
            if hasattr(PATHS, "config") and os.path.isfile(PATHS.config):
                with open(PATHS.config, "r", encoding="utf-8") as _f:
                    _cfg = _json.load(_f)
                    custom_aliases = _cfg.get("slang_aliases", {})
        except Exception:
            pass

    if custom_aliases and isinstance(custom_aliases, dict):
        for alias_k, canonical_v in custom_aliases.items():
            if alias_k.lower().strip() == name_raw_low:
                return canonical_v

    # 1b. Check auto-generated Table 0 Cornerstone aliases
    try:
        from path_config import PATHS
        import json as _json
        gen_path = PATHS.resource("cstone_generated_slang.json")
        if os.path.isfile(gen_path):
            with open(gen_path, "r", encoding="utf-8") as _gf:
                gen_aliases = _json.load(_gf)
                if name_raw_low in gen_aliases:
                    return gen_aliases[name_raw_low]
    except Exception:
        pass

    slang_map = {
        # ── Mining Gadgets & Modules ──
        "waweshift": "Waveshift",
        "waveshift": "Waveshift",
        "waveshift mining gadget": "Waveshift",
        "sabir": "Sabir",
        "sabir mining gadget": "Sabir",
        "boremax": "BoreMax",
        "boremax mining gadget": "BoreMax",
        "optimax": "OptiMax",
        "optimax mining gadget": "OptiMax",
        "stampede": "Stampede",
        "stampede mining gadget": "Stampede",
        "focus": "Focus Mining Module",
        "torrent": "Torrent Mining Module",
        "rime": "Rime Mining Module",
        "fltr": "FLTR Mining Module",
        "quantainium water bottle": "CRUZ Lux",
        "water bottle": "CRUZ Lux",
        "omni-afs saphire slate": "Tailwind Flight Suit",
        "omni-afs sapphire slate": "Tailwind Flight Suit",
        "adiva imperial jacket": "Adiva Jacket Imperial",
        "adiva yellow jacket": "Adiva Jacket Yellow",
        "adiva jacket yellow": "Adiva Jacket Yellow",
        "adiva jacket imperial": "Adiva Jacket Imperial",
        "adiva blue jacket": "Adiva Jacket Blue",
        "adiva jacket blue": "Adiva Jacket Blue",
        "adiva red jacket": "Adiva Jacket Red",
        "adiva jacket red": "Adiva Jacket Red",
        "adiva white jacket": "Adiva Jacket White",
        "adiva jacket white": "Adiva Jacket White",
        "adiva dark green jacket": "Adiva Jacket Dark Green",
        "adiva jacket dark green": "Adiva Jacket Dark Green",
        "adiva green jacket": "Adiva Jacket Green",
        "adiva jacket green": "Adiva Jacket Green",
        "adiva black jacket": "Adiva Jacket Black",
        "adiva jacket black": "Adiva Jacket Black",
        "deo black shirt": "Deo Shirt Black",
        "deo shirt black": "Deo Shirt Black",
        "prim black shoes": "Prim Shoes Black",
        "prim shoes black": "Prim Shoes Black",
        "ventra black gloves": "Ventra Gloves Black",
        "ventra gloves black": "Ventra Gloves Black",
        "lemarque pants": "Lemarque Pants",

        # ── Weapons ──
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
        # ── Ammo & Magazines ──
        "p4 mag": "P4-AR Magazine",
        "p4 mags": "P4-AR Magazine",
        "p4 ammo": "P4-AR Magazine",
        "p4 magazine": "P4-AR Magazine",
        "p4ar mag": "P4-AR Magazine",
        "p4ar mags": "P4-AR Magazine",
        "p4ar ammo": "P4-AR Magazine",
        "p8 mag": "P8-SC Magazine",
        "p8 mags": "P8-SC Magazine",
        "p8 ammo": "P8-SC Magazine",
        "p8 magazine": "P8-SC Magazine",
        "p6 mag": "P6-LR Magazine",
        "p6 mags": "P6-LR Magazine",
        "p6 ammo": "P6-LR Magazine",
        "p6 magazine": "P6-LR Magazine",
        "fs9 mag": "FS-9 Magazine",
        "fs9 mags": "FS-9 Magazine",
        "fs9 ammo": "FS-9 Magazine",
        "fs-9 mag": "FS-9 Magazine",
        "fs-9 mags": "FS-9 Magazine",
        "fs-9 ammo": "FS-9 Magazine",
        "gallant mag": "Gallant Magazine",
        "gallant mags": "Gallant Magazine",
        "c54 mag": "C54 Magazine",
        "c54 mags": "C54 Magazine",
        "lumin mag": "Lumin V Magazine",
        "lumin mags": "Lumin V Magazine",
        "custodian mag": "Custodian Magazine",
        "custodian mags": "Custodian Magazine",
        "mag": "P4-AR Magazine",
        "mags": "P4-AR Magazine",
        "ammo": "P4-AR Magazine",
        "cambio multi-tool battery": "Cambio Multi-tool Battery",
        "cambio srt battery": "Cambio Multi-tool Battery",
        "cambio battery": "Cambio Multi-tool Battery",
        "battery": "Maxlift Tractor Beam Battery",
        "baterka": "Maxlift Tractor Beam Battery",
        "p4 star kitten": 'P4-AR "Star Kitten" Rifle',
        "p4-ar star kitten": 'P4-AR "Star Kitten" Rifle',
        "p4 starkitten": 'P4-AR "Star Kitten" Rifle',
        "p4-ar starkitten": 'P4-AR "Star Kitten" Rifle',
        "star kitten p4": 'P4-AR "Star Kitten" Rifle',
        "star kitten p4-ar": 'P4-AR "Star Kitten" Rifle',

        # ── Ship Quantum Drives ──
        "ts-2": "TS-2 Quantum Drive", "ts2": "TS-2 Quantum Drive", "ts 2": "TS-2 Quantum Drive",
        "vk-00": "VK-00 Quantum Drive", "vk00": "VK-00 Quantum Drive", "vk 00": "VK-00 Quantum Drive", "vk": "VK-00 Quantum Drive",
        "crossfield": "Crossfield Quantum Drive",
        "atlas": "Atlas Quantum Drive",
        "vfx": "VFX Size 1 Quantum Drive",

        # ── Ship Shield Generators ──
        "fr-86": "FR-86 Shield Generator (Size 3)", "fr86": "FR-86 Shield Generator (Size 3)", "fr 86": "FR-86 Shield Generator (Size 3)",
        "fr-76": "FR-76 Shield Generator (Size 2)", "fr76": "FR-76 Shield Generator (Size 2)", "fr 76": "FR-76 Shield Generator (Size 2)",
        "fr-66": "FR-66 Shield Generator (Size 1)", "fr66": "FR-66 Shield Generator (Size 1)", "fr 66": "FR-66 Shield Generator (Size 1)",

        # ── Ship Power Plants ──
        "js-500": "JS-500 Power Plant (Size 3)", "js500": "JS-500 Power Plant (Size 3)",
        "js-400": "JS-400 Power Plant (Size 2)", "js400": "JS-400 Power Plant (Size 2)",
        "js-300": "JS-300 Power Plant (Size 1)", "js300": "JS-300 Power Plant (Size 1)",

        # ── Ship Coolers ──
        "coolcore": "CoolCore Industrial Cooler (Size 3)",
        "eridani": "Eridani Cooler (Size 2)",
        "ultra-flow": "Ultra-Flow Cooler (Size 1)", "ultraflow": "Ultra-Flow Cooler (Size 1)",

        # ── Ship Cannons & Repeaters ──
        "m7a": "M7A Laser Cannon (Size 5)",
        "m6a": "M6A Laser Cannon (Size 4)",
        "m5a": "M5A Laser Cannon (Size 3)",
        "m4a": "M4A Laser Cannon (Size 2)",
        "cf-557": "CF-557 Giga-Panther Repeater (Size 5)", "cf557": "CF-557 Giga-Panther Repeater (Size 5)", "giga-panther": "CF-557 Giga-Panther Repeater (Size 5)",
        "cf-447": "CF-447 Rhino Laser Repeater (Size 4)", "cf447": "CF-447 Rhino Laser Repeater (Size 4)", "rhino": "CF-447 Rhino Laser Repeater (Size 4)",
        "cf-337": "CF-337 Panther Laser Repeater (Size 3)", "cf337": "CF-337 Panther Laser Repeater (Size 3)", "panther": "CF-337 Panther Laser Repeater (Size 3)",
        "cf-227": "CF-227 Badger Laser Repeater (Size 2)", "cf227": "CF-227 Badger Laser Repeater (Size 2)", "badger": "CF-227 Badger Laser Repeater (Size 2)",
        "cf-117": "CF-117 Bulldog Laser Repeater (Size 1)", "cf117": "CF-117 Bulldog Laser Repeater (Size 1)", "bulldog": "CF-117 Bulldog Laser Repeater (Size 1)",
        "tarantula": "Tarantula GT-870 Ballistic Cannon (Size 3)", "gt-870": "Tarantula GT-870 Ballistic Cannon (Size 3)",
        "deadbolt 4": "Deadbolt IV Ballistic Cannon (Size 4)", "deadbolt iv": "Deadbolt IV Ballistic Cannon (Size 4)",
        "deadbolt 5": "Deadbolt V Ballistic Cannon (Size 5)", "deadbolt v": "Deadbolt V Ballistic Cannon (Size 5)",

        # ── Mining & Salvage Heads, Tools, Modules ──
        "hofstede": "Hofstede S1 Mining Head",
        "klein": "Klein S1 Mining Head",
        "helix": "Helix S1 Mining Head",
        "lancet": "Lancet MH1 Mining Head",
        "arbor": "Arbor MH1 Mining Head",
        "impact": "Impact I Mining Head",
        "truhold": "TruHold Salvage Head",
        "cinch": "Cinch Salvage Module",
        "abrade": "Abrade Salvage Module",
        "trawler": "Trawler Salvage Module",
        "cinematic": "Cinematic Salvage Module",
        "fltr-xl": "FLTR-XL Passive Mining Module", "fltr": "FLTR-XL Passive Mining Module",
        "surge": "Surge Active Mining Module",
        "brand": "Brand Passive Mining Module",
        "lifesaver": "Lifesaver Passive Mining Module",
        "mole pod": "Argo Ore Pod", "argo ore pod": "Argo Ore Pod", "argo pod": "Argo Ore Pod", "mole ore pod": "Argo Ore Pod", "argo mole ore pod": "Argo Ore Pod",
        "misc ore pod": "MISC Ore Pod", "misc pod": "MISC Ore Pod", "prospector pod": "MISC Ore Pod", "prospector mining bag": "MISC Ore Pod",
        "drake mining pod": "Drake Ore Pod", "drake pod": "Drake Ore Pod", "drake ore pod": "Drake Ore Pod",
        "greycat roc ore pod": "Greycat ROC Ore Pod", "roc ore pod": "Greycat ROC Ore Pod", "roc pod": "Greycat ROC Ore Pod",
        "geo resource pod": "GEO Resource Pod", "geo pod": "GEO Resource Pod", "resource pod": "GEO Resource Pod",
        # ── Fuel Pods (from starcitizen.tools/Fuel_pod) ──
        "bonito": "Bonito Fuel Pod", "bonito fuel pod": "Bonito Fuel Pod",
        "cr-60": "CR-60 Fuel Pod", "cr60": "CR-60 Fuel Pod", "cr 60": "CR-60 Fuel Pod",
        "gargant": "Gargant Fuel Pod", "gargant fuel pod": "Gargant Fuel Pod",
        "gsx-ex": "GSX-EX Fuel Pod", "gsxex": "GSX-EX Fuel Pod",
        "gsx-hp": "GSX-HP Fuel Pod", "gsxhp": "GSX-HP Fuel Pod",
        "gsx-rf": "GSX-RF Fuel Pod", "gsxrf": "GSX-RF Fuel Pod",
        "nemec": "Nemec Fuel Pod", "nemec fuel pod": "Nemec Fuel Pod",
        "rumford": "Rumford Fuel Pod", "rumford fuel pod": "Rumford Fuel Pod",

        # ── Fuel Nozzles (from starcitizen.tools/Fuel_nozzle) ──
        "bendix": "Bendix Fuel Nozzle", "bendix nozzle": "Bendix Fuel Nozzle",
        "ezra": "Ezra Fuel Nozzle", "ezra nozzle": "Ezra Fuel Nozzle",
        "lindstrom": "Lindstrom Fuel Nozzle", "lindstrom nozzle": "Lindstrom Fuel Nozzle",
        "marlin": "Marlin Fuel Nozzle", "marlin nozzle": "Marlin Fuel Nozzle",
        "torrez": "Torrez Fuel Nozzle", "torrez nozzle": "Torrez Fuel Nozzle",

        # ── Ammunition by Size ──
        "5size ammo": "Size 5 Ammunition", "5 size ammo": "Size 5 Ammunition", "size 5 ammo": "Size 5 Ammunition", "size 5": "Size 5 Ammunition", "5size": "Size 5 Ammunition", "5 size": "Size 5 Ammunition",
        "4size ammo": "Size 4 Ammunition", "4 size ammo": "Size 4 Ammunition", "size 4 ammo": "Size 4 Ammunition", "size 4": "Size 4 Ammunition", "4size": "Size 4 Ammunition", "4 size": "Size 4 Ammunition",
        "3size ammo": "Size 3 Ammunition", "3 size ammo": "Size 3 Ammunition", "size 3 ammo": "Size 3 Ammunition", "size 3": "Size 3 Ammunition", "3size": "Size 3 Ammunition", "3 size": "Size 3 Ammunition",
        "2size ammo": "Size 2 Ammunition", "2 size ammo": "Size 2 Ammunition", "size 2 ammo": "Size 2 Ammunition", "size 2": "Size 2 Ammunition", "2size": "Size 2 Ammunition", "2 size": "Size 2 Ammunition",
        "1size ammo": "Size 1 Ammunition", "1 size ammo": "Size 1 Ammunition", "size 1 ammo": "Size 1 Ammunition", "size 1": "Size 1 Ammunition", "1size": "Size 1 Ammunition", "1 size": "Size 1 Ammunition",
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
        # ── Grenades & Explosives ──
        "scorch": "Scorch Plasma Grenade",
        "grenade": "Scorch Plasma Grenade",
        "nade": "Scorch Plasma Grenade",
        "frag": "MK-4 Frag Grenade",
        # ── Missiles & Torpedoes ──
        "torp": "Seeker IX Torpedo",
        "torpedo": "Seeker IX Torpedo",
        "torps": "Seeker IX Torpedo",
        "seeker": "Seeker IX Torpedo",
        "seeker 9": "Seeker IX Torpedo",
        "seeker ix": "Seeker IX Torpedo",
        "seeker ix torpedo": "Seeker IX Torpedo",
        "argus": "Argus IX Torpedo",
        "argus 9": "Argus IX Torpedo",
        "argus ix": "Argus IX Torpedo",
        "argus ix torpedo": "Argus IX Torpedo",
        "argos": "Argos IX Torpedo",
        "argos 9": "Argos IX Torpedo",
        "argos ix": "Argos IX Torpedo",
        "argos ix torpedo": "Argos IX Torpedo",
        "typhoon": "Typhoon IX Torpedo",
        "typhoon 9": "Typhoon IX Torpedo",
        "typhoon ix": "Typhoon IX Torpedo",
        "typhoon ix torpedo": "Typhoon IX Torpedo",
        "raptor": "Raptor IV Missile",
        "raptor 4": "Raptor IV Missile",
        "raptor iv": "Raptor IV Missile",
        "thunderbolt": "Thunderbolt III Missile",
        "thunderbolt 3": "Thunderbolt III Missile",
        "thunderbolt iii": "Thunderbolt III Missile",
        "dominator": "Dominator II Missile",
        "dominator 2": "Dominator II Missile",
        "dominator ii": "Dominator II Missile",
        "arrester 3": "Arrester III Missile",
        "arrester iii": "Arrester III Missile",
        "tempest": "Tempest II Missile",
        "tempest 2": "Tempest II Missile",
        "tempest ii": "Tempest II Missile",
        "rattler": "Rattler II Missile",
        "rattler 2": "Rattler II Missile",
        "rattler ii": "Rattler II Missile",
        "stalker": "Stalker V Missile",
        "stalker 5": "Stalker V Missile",
        "stalker v": "Stalker V Missile",
        "marksman": "Marksman I Missile",
        "marksman 1": "Marksman I Missile",
        "marksman i": "Marksman I Missile",
        "strikeforce": "StrikeForce II Missile",
        "strikeforce 2": "StrikeForce II Missile",
        "strikeforce ii": "StrikeForce II Missile",
        "taskforce": "Taskforce II Missile",
        "taskforce 2": "Taskforce II Missile",
        "taskforce ii": "Taskforce II Missile",
        "missile": "Raptor IV Missile",
        "missiles": "Raptor IV Missile",
        "bomb": "Stormburst Bomb",
        "bombs": "Stormburst Bomb",
        "stormburst": "Stormburst Bomb",
        "colossus": "Colossus Bomb",
        # ── Armor (common shorthand) ──
        "aril": "Aril Core",
        "aril helmet": "Aril Helmet",
        "aril core": "Aril Core",
        "aril arms": "Aril Arms",
        "aril legs": "Aril Legs",
        "aril backpack": "Aril Backpack",
        "orc": "ORC-mkX Core Woodland",
        "orc helmet": "ORC-mkX Helmet Woodland",
        "orc core": "ORC-mkX Core Woodland",
        "orc arms": "ORC-mkX Arms Woodland",
        "orc legs": "ORC-mkX Legs Woodland",
        "adp": "ADP-mk4 Core Woodland",
        "adp helmet": "ADP-mk4 Helmet Woodland",
        "adp core": "ADP-mk4 Core Woodland",
        "adp arms": "ADP-mk4 Arms Woodland",
        "adp legs": "ADP-mk4 Legs Woodland",
        "macflex": "MacFlex Core",
        "field recon": "Field Recon Suit Core",
        "recon suit": "Field Recon Suit Core",
        "tailwind": "Tailwind Flight Suit",
        "undersuit": "TCS-4 Undersuit",
        "tcs4": "TCS-4 Undersuit",
        "tcs-4": "TCS-4 Undersuit",
        "backpack": "CSP-68H Backpack",
        "rucksack": "CSP-68H Backpack",
        # ── Medical ──
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
        # ── Food & Drinks ──
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
        # ── Tools & Components ──
        "cambio srt canister": "Cambio SRT Canister",
        "cambio srt cannister": "Cambio SRT Canister",
        "cambio canister": "Cambio SRT Canister",
        "cambio cannister": "Cambio SRT Canister",
        "srt canister": "Cambio SRT Canister",
        "srt cannister": "Cambio SRT Canister",
        "canister": "Cambio SRT Canister",
        "cannister": "Cambio SRT Canister",
        "cambio srt": "Cambio SRT",
        "maxlift tractor beam": "MaxLift Tractor Beam",
        "tractor beam": "MaxLift Tractor Beam",
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
        "bexalite": "Refined Bexalite",
        "bexlite": "Refined Bexalite",
        "taranite": "Refined Taranite",
        "qt": "Refined Quantainium",
        "quantanium": "Refined Quantainium",
        "quant": "Refined Quantainium",
        "kvanta": "Refined Quantainium",
        "kvantainium": "Refined Quantainium",
        "rmc": "Recycled Material Composite (RMC)",
        "construction": "Construction Materials",
        # ── Containers ──
        "box": "Stor-All 1 SCU Storage Container",
        "crate": "Stor-All 1 SCU Storage Container",
        "1scu": "Stor-All 1 SCU Storage Container",
        "2scu": "Stor*All 2 SCU Self-Storage Container",
        "4scu": "Stor*All 4 SCU Self-Storage Container",
        "8scu": "Stor*All 8 SCU Self-Storage Container",
        # ── Fuel ──
        "qfuel": "Quantum Fuel",
        "quantum fuel": "Quantum Fuel",
        "hydro": "Hydrogen Fuel",
        "hydrogen": "Hydrogen Fuel",
        "h2": "Hydrogen Fuel",
        # ── Quantum Drives (Canonical with Size) ──
        "xl-1": "XL-1 Quantum Drive (Size 2)",
        "xl1": "XL-1 Quantum Drive (Size 2)",
        "xl 1": "XL-1 Quantum Drive (Size 2)",
        "xl-1 quantum drive": "XL-1 Quantum Drive (Size 2)",
        "xl1 quantum drive": "XL-1 Quantum Drive (Size 2)",
        "crossfield": "Crossfield Quantum Drive (Size 2)",
        "crossfield quantum drive": "Crossfield Quantum Drive (Size 2)",
        "vk-00": "VK-00 Quantum Drive (Size 1)",
        "vk00": "VK-00 Quantum Drive (Size 1)",
        "vk 00": "VK-00 Quantum Drive (Size 1)",
        "vk-00 quantum drive": "VK-00 Quantum Drive (Size 1)",
        "atlas": "Atlas Quantum Drive (Size 1)",
        "atlas quantum drive": "Atlas Quantum Drive (Size 1)",
        "ts-2": "TS-2 Quantum Drive (Size 3)",
        "ts2": "TS-2 Quantum Drive (Size 3)",
        "ts 2": "TS-2 Quantum Drive (Size 3)",
        "ts-": "TS-2 Quantum Drive (Size 3)",
        "ts": "TS-2 Quantum Drive (Size 3)",
        "ts-2 quantum drive": "TS-2 Quantum Drive (Size 3)",
        "pontes": "Pontes Quantum Drive (Size 3)",
        "pontes quantum drive": "Pontes Quantum Drive (Size 3)",
        "beacon": "Beacon Quantum Drive (Size 1)",
        "voyager": "Voyager Quantum Drive (Size 1)",
        "siren": "Siren Quantum Drive (Size 2)",
        "agate": "Agate Quantum Drive (Size 3)",
        "colossus quantum drive": "Colossus Quantum Drive (Size 4)",

        # ── Shield Generators (Canonical with Size) ──
        "fr-66": "FR-66 Shield Generator (Size 1)",
        "fr66": "FR-66 Shield Generator (Size 1)",
        "fr 66": "FR-66 Shield Generator (Size 1)",
        "fr-66 shield generator": "FR-66 Shield Generator (Size 1)",
        "fr-76": "FR-76 Shield Generator (Size 2)",
        "fr76": "FR-76 Shield Generator (Size 2)",
        "fr 76": "FR-76 Shield Generator (Size 2)",
        "fr-76 shield generator": "FR-76 Shield Generator (Size 2)",
        "fr-86": "FR-86 Shield Generator (Size 3)",
        "fr86": "FR-86 Shield Generator (Size 3)",
        "fr 86": "FR-86 Shield Generator (Size 3)",
        "fr-86 shield generator": "FR-86 Shield Generator (Size 3)",
        "palisade": "Palisade Shield Generator (Size 1)",
        "palisade shield generator": "Palisade Shield Generator (Size 1)",
        "rampart": "Rampart Shield Generator (Size 2)",
        "rampart shield generator": "Rampart Shield Generator (Size 2)",
        "umbra": "Umbra Shield Generator (Size 2)",
        "umbra shield generator": "Umbra Shield Generator (Size 2)",
        "aspis": "Aspis Shield Generator (Size 1)",
        "aspis shield generator": "Aspis Shield Generator (Size 1)",
        "allstop": "AllStop Shield Generator (Size 1)",
        "fullstop": "FullStop Shield Generator (Size 2)",
        "fortress": "Fortress Shield Generator (Size 3)",
        "bulwark": "Bulwark Shield Generator (Size 3)",

        # ── Power Plants (Canonical with Size) ──
        "js-300": "JS-300 Power Plant (Size 1)",
        "js300": "JS-300 Power Plant (Size 1)",
        "js 300": "JS-300 Power Plant (Size 1)",
        "js-300 power plant": "JS-300 Power Plant (Size 1)",
        "js-400": "JS-400 Power Plant (Size 2)",
        "js400": "JS-400 Power Plant (Size 2)",
        "js 400": "JS-400 Power Plant (Size 2)",
        "js-400 power plant": "JS-400 Power Plant (Size 2)",
        "js-500": "JS-500 Power Plant (Size 3)",
        "js500": "JS-500 Power Plant (Size 3)",
        "js 500": "JS-500 Power Plant (Size 3)",
        "js-500 power plant": "JS-500 Power Plant (Size 3)",
        "maelstrom": "Maelstrom Power Plant (Size 1)",
        "quadracell": "Quadracell Power Plant (Size 2)",
        "overdrive": "Overdrive Power Plant (Size 2)",
        "genesis": "Genesis Power Plant (Size 3)",

        # ── Coolers (Canonical with Size) ──
        "ultra-flow": "Ultra-Flow Cooler (Size 1)",
        "ultraflow": "Ultra-Flow Cooler (Size 1)",
        "ultra-flow cooler": "Ultra-Flow Cooler (Size 1)",
        "eridani": "Eridani Cooler (Size 2)",
        "eridani cooler": "Eridani Cooler (Size 2)",
        "coolcore": "CoolCore Industrial Cooler (Size 3)",
        "coolcore cooler": "CoolCore Industrial Cooler (Size 3)",
        "glacier": "Glacier Cooler (Size 2)",
        "icebox": "IceBox Cooler (Size 2)",
        "chill-out": "Chill-Out Cooler (Size 1)",
        "snowpack": "Snowpack Cooler (Size 3)",

        # ── Ship Weapons (Canonical with Size) ──
        "m4a": "M4A Laser Cannon (Size 2)",
        "m5a": "M5A Laser Cannon (Size 3)",
        "m6a": "M6A Laser Cannon (Size 4)",
        "m7a": "M7A Laser Cannon (Size 5)",
        "cf-117": "CF-117 Bulldog Laser Repeater (Size 1)",
        "cf117": "CF-117 Bulldog Laser Repeater (Size 1)",
        "bulldog": "CF-117 Bulldog Laser Repeater (Size 1)",
        "cf-227": "CF-227 Badger Laser Repeater (Size 2)",
        "cf227": "CF-227 Badger Laser Repeater (Size 2)",
        "badger": "CF-227 Badger Laser Repeater (Size 2)",
        "cf-337": "CF-337 Panther Laser Repeater (Size 3)",
        "cf337": "CF-337 Panther Laser Repeater (Size 3)",
        "panther": "CF-337 Panther Laser Repeater (Size 3)",
        "cf-447": "CF-447 Rhino Laser Repeater (Size 4)",
        "cf447": "CF-447 Rhino Laser Repeater (Size 4)",
        "rhino": "CF-447 Rhino Laser Repeater (Size 4)",
        "cf-557": "CF-557 Giga-Panther Repeater (Size 5)",
        "cf557": "CF-557 Giga-Panther Repeater (Size 5)",
        "giga-panther": "CF-557 Giga-Panther Repeater (Size 5)",
        "gigapanther": "CF-557 Giga-Panther Repeater (Size 5)",
        "deadbolt 4": "Deadbolt IV Ballistic Cannon (Size 4)",
        "deadbolt 5": "Deadbolt V Ballistic Cannon (Size 5)",
        "omnisky ix": "Omnisky IX Laser Cannon (Size 3)",
        "omnisky xii": "Omnisky XII Laser Cannon (Size 4)",

        # ── Ships (for shuttle context) ──
        "pisces": "C8X Pisces",
        "mpuv": "Argo MPUV-C",
        "ox": "Golem Ox",
        "golem": "Golem Ox",
        "cutter": "Drake Cutter",
    }
    # Exact match first
    if name_raw_low in slang_map:
        return slang_map[name_raw_low]
    # Check if input is already a canonical or specific variant name (contains variant keywords or multi-word item name)
    _canonical_low = {v.lower() for v in slang_map.values()}
    if name_raw_low in _canonical_low:
        for v in slang_map.values():
            if v.lower() == name_raw_low:
                return v
        return name_raw

    # If name_raw already specifies a variant color/type or specific item component,
    # DO NOT override it with short slang keys!
    _variant_keywords = {"twilight", "woodland", "slate", "sapphire", "nightstalker", "boneyard", "desert", "arctic", "black", "gold", "white", "harvester", "hazard", "quicksilver", "red alert", "scorched", "aqua", "imperial"}
    _component_words = {
        "helmet", "core", "arms", "legs", "backpack", "undersuit", "rifle", "smg", "pistol", "lmg", "sniper", "shotgun", "magazine", "mag", "canister", "attachment", "device", "gadget", "battery",
        "quantum", "drive", "shield", "generator", "power", "plant", "cooler", "repeater", "cannon", "gatling", "torpedo", "missile", "laser", "ballistic", "distortion"
    }
    if any(vk in name_raw_low for vk in _variant_keywords) or (len(name_raw_low.split()) >= 2 and any(w in name_raw_low for w in _component_words)):
        return name_raw.title() if name_raw.islower() else name_raw

    # Partial match (only for standalone short/slang inputs, not embedded inside full canonical names)
    for slang, official in sorted(slang_map.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r'(?:^|[\s\-_])' + re.escape(slang) + r'(?:$|[\s\-_])'
        if re.search(pattern, name_raw_low):
            return official
    # Match against config items (if config_data provided by caller)
    if config_data is not None:
        fi_data = config_data.get("frequent_items", {})
        flat_items = []
        if isinstance(fi_data, dict):
            for cat, cat_items in fi_data.items():
                if isinstance(cat_items, list):
                    flat_items.extend(cat_items)
        elif isinstance(fi_data, list):
            flat_items = fi_data
    return name_raw.title()


def register_vessel_slang_alias(custom_name, base_model="", config_data=None):
    """Auto-generate bot slang aliases when a custom vessel is registered (STROM 7).

    E.g. custom_name="UEE Barnabas", base_model="Aegis Reclaimer" ->
    full_name: "UEE Barnabas (Aegis Reclaimer)"
    aliases: "UEE Barnabas", "uee barnabas", "barnabas"
    """
    if not custom_name:
        return
    c_name = str(custom_name).strip()
    full_vessel = f"{c_name} ({base_model})" if base_model and base_model not in c_name else c_name

    aliases = {
        c_name.lower(),
        re.sub(r'^(uee|rsi|drake|aegis|anvil)\s+', '', c_name.lower()).strip(),
    }

    try:
        from path_config import PATHS
        import json as _json
        cfg_path = PATHS.config if hasattr(PATHS, "config") else "config.json"
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = _json.load(f)
            slang_aliases = cfg.setdefault("slang_aliases", {})
            for a in aliases:
                if a and len(a) >= 3:
                    slang_aliases[a] = full_vessel
            with open(cfg_path, "w", encoding="utf-8") as f:
                _json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[SLANG_HELPER_WARN] Failed to auto-register slang alias: {e}")


def resolve_vessel_slang(input_str, config_data=None):
    """Resolve vessel name input to canonical custom vessel name with slang support."""
    if not input_str:
        return input_str
    inp_low = str(input_str).lower().strip()
    canonical = resolve_slang(inp_low, config_data)
    return canonical


