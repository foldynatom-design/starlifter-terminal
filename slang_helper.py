# -*- coding: utf-8 -*-
"""
slang_helper.py - Slang resolution for cargo item names.

Converts user slang/abbreviations to canonical item names.
E.g. "tractor" -> "MaxLift Tractor Beam", "kvanta" -> "Refined Quantainium"

Usage:
    from slang_helper import resolve_slang
"""

def resolve_slang(name_raw):
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


