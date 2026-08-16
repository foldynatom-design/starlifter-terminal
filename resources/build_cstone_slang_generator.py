# -*- coding: utf-8 -*-
"""
build_cstone_slang_generator.py — Comprehensive Star Citizen Slang & Acronyms Engine.
Combines:
1. Full CStone Table 0 canonical items (2,395+ items)
2. Reddit (r/starcitizen) community slang, ship nicknames, weapon codes, and abbreviations
3. Automatic word-reversal for color/variant specifications (e.g. 'yellow adiva jacket' -> 'Adiva Jacket Yellow')
4. Seamless integration with Ctrl+C / Ctrl+V clipboard importing
"""
import json, os, re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

# ── Reddit Community Slang, Ship Nicknames, and Common Acronyms ──
REDDIT_COMMUNITY_ALIASES = {
    # Ships & Vehicles
    "cutty": "Drake Cutlass Black",
    "cutty black": "Drake Cutlass Black",
    "cutty red": "Drake Cutlass Red",
    "cutty blue": "Drake Cutlass Blue",
    "cutty steel": "Drake Cutlass Steel",
    "cutlet": "Drake Cutter",
    "cutter": "Drake Cutter",
    "connie": "RSI Constellation Andromeda",
    "connie andromeda": "RSI Constellation Andromeda",
    "connie taurus": "RSI Constellation Taurus",
    "connie aquila": "RSI Constellation Aquila",
    "connie phoenix": "RSI Constellation Phoenix",
    "taurus": "RSI Constellation Taurus",
    "andromeda": "RSI Constellation Andromeda",
    "aquila": "RSI Constellation Aquila",
    "phoenix": "RSI Constellation Phoenix",
    "c2": "Crusader C2 Hercules",
    "m2": "Crusader M2 Hercules",
    "a2": "Crusader A2 Hercules",
    "hercules": "Crusader C2 Hercules",
    "cat": "Drake Caterpillar",
    "caterpillar": "Drake Caterpillar",
    "carrack": "Anvil Carrack",
    "msr": "Crusader Mercury Star Runner",
    "mercury": "Crusader Mercury Star Runner",
    "star runner": "Crusader Mercury Star Runner",
    "tali": "Aegis Retaliator",
    "retaliator": "Aegis Retaliator",
    "hh": "Aegis Hammerhead",
    "hammerhead": "Aegis Hammerhead",
    "890j": "Origin 890 Jump",
    "890 jump": "Origin 890 Jump",
    "890": "Origin 890 Jump",
    "bmm": "Banu Merchantman",
    "merchantman": "Banu Merchantman",
    "farer": "MISC Starfarer",
    "'farer": "MISC Starfarer",
    "starfarer": "MISC Starfarer",
    "starfarer gemini": "MISC Starfarer Gemini",
    "gemini": "MISC Starfarer Gemini",
    "penguin": "Aegis Avenger Titan",
    "titan": "Aegis Avenger Titan",
    "avenger titan": "Aegis Avenger Titan",
    "stalker": "Aegis Avenger Stalker",
    "warlock": "Aegis Avenger Warlock",
    "fatmax": "MISC Freelancer MAX",
    "fat max": "MISC Freelancer MAX",
    "freelancer max": "MISC Freelancer MAX",
    "freelancer dur": "MISC Freelancer DUR",
    "freelancer mis": "MISC Freelancer MIS",
    "dur": "MISC Freelancer DUR",
    "mis": "MISC Freelancer MIS",
    "c1": "Crusader C1 Spirit",
    "c1 spirit": "Crusader C1 Spirit",
    "spirit c1": "Crusader C1 Spirit",
    "a1": "Crusader A1 Spirit",
    "a1 spirit": "Crusader A1 Spirit",
    "e1": "Crusader E1 Spirit",
    "zeus cl": "RSI Zeus Mk II CL",
    "zeus es": "RSI Zeus Mk II ES",
    "zeus mr": "RSI Zeus Mk II MR",
    "corsair": "Drake Corsair",
    "vulture": "Drake Vulture",
    "prospector": "MISC Prospector",
    "mole": "Argo MOLE",
    "raft": "Argo RAFT",
    "srv": "Argo SRV",
    "mpuv": "Argo MPUV Cargo",
    "mpuv cargo": "Argo MPUV Cargo",
    "mpuv tractor": "Argo MPUV Tractor",
    "mpuv-1c": "Argo MPUV Cargo",
    "mpuv-1t": "Argo MPUV Tractor",
    "glad": "Anvil Gladius",
    "gladius": "Anvil Gladius",
    "sabre": "Aegis Sabre",
    "sabre raven": "Aegis Sabre Raven",
    "vanguard": "Aegis Vanguard Warden",
    "warden": "Aegis Vanguard Warden",
    "harbi": "Aegis Vanguard Harbinger",
    "harbinger": "Aegis Vanguard Harbinger",
    "senti": "Aegis Vanguard Sentinel",
    "sentinel": "Aegis Vanguard Sentinel",
    "hoplite": "Aegis Vanguard Hoplite",
    "eclipse": "Aegis Eclipse",
    "reclaimer": "Aegis Reclaimer",
    "redeemer": "Aegis Redeemer",
    "arrow": "Anvil Arrow",
    "nomad": "Consolidated Outland Nomad",
    "100i": "Origin 100i",
    "125a": "Origin 125a",
    "135c": "Origin 135c",
    "300i": "Origin 300i",
    "315p": "Origin 315p",
    "325a": "Origin 325a",
    "400i": "Origin 400i",
    "600i": "Origin 600i Explorer",
    "600i explorer": "Origin 600i Explorer",
    "600i touring": "Origin 600i Touring",
    "hull a": "MISC Hull A",
    "hull c": "MISC Hull C",
    "hull d": "MISC Hull D",
    "hull e": "MISC Hull E",
    "ironclad": "Drake Ironclad",
    "ironclad assault": "Drake Ironclad Assault",
    "idris": "Aegis Idris-M",
    "idris-m": "Aegis Idris-M",
    "idris-p": "Aegis Idris-P",
    "javelin": "Aegis Javelin",
    "kraken": "Drake Kraken",
    "polaris": "RSI Polaris",
    "galaxy": "RSI Galaxy",
    "arrastra": "RSI Arrastra",
    "perseus": "RSI Perseus",
    "scorpius": "RSI Scorpius",
    "scorpius antares": "RSI Scorpius Antares",
    "f7a": "Anvil F7A Hornet Mk II",
    "f7c": "Anvil F7C Hornet",
    "f8a": "Anvil F8A Lightning",
    "f8c": "Anvil F8C Lightning",

    # Ship Weapons & Ordnance
    "panther": "CF-337 Panther Laser Repeater",
    "cf337": "CF-337 Panther Laser Repeater",
    "cf-337": "CF-337 Panther Laser Repeater",
    "badger": "CF-227 Badger Laser Repeater",
    "cf227": "CF-227 Badger Laser Repeater",
    "cf-227": "CF-227 Badger Laser Repeater",
    "rhino": "CF-447 Rhino Laser Repeater",
    "cf447": "CF-447 Rhino Laser Repeater",
    "cf-447": "CF-447 Rhino Laser Repeater",
    "bulldog": "CF-117 Bulldog Laser Repeater",
    "cf117": "CF-117 Bulldog Laser Repeater",
    "cf-117": "CF-117 Bulldog Laser Repeater",
    "attrition 1": "Attrition-1 Laser Repeater",
    "attrition 2": "Attrition-2 Laser Repeater",
    "attrition 3": "Attrition-3 Laser Repeater",
    "attrition 4": "Attrition-4 Laser Repeater",
    "attrition 5": "Attrition-5 Laser Repeater",
    "attrition-1": "Attrition-1 Laser Repeater",
    "attrition-2": "Attrition-2 Laser Repeater",
    "attrition-3": "Attrition-3 Laser Repeater",
    "attrition-4": "Attrition-4 Laser Repeater",
    "attrition-5": "Attrition-5 Laser Repeater",
    "omnisky 3": "Omnisky III Laser Cannon",
    "omnisky iii": "Omnisky III Laser Cannon",
    "omnisky 6": "Omnisky VI Laser Cannon",
    "omnisky vi": "Omnisky VI Laser Cannon",
    "omnisky 9": "Omnisky IX Laser Cannon",
    "omnisky ix": "Omnisky IX Laser Cannon",
    "omnisky 12": "Omnisky XII Laser Cannon",
    "omnisky xii": "Omnisky XII Laser Cannon",
    "deadbolt 1": "Deadbolt I Ballistic Cannon",
    "deadbolt 2": "Deadbolt II Ballistic Cannon",
    "deadbolt 3": "Deadbolt III Ballistic Cannon",
    "deadbolt 4": "Deadbolt IV Ballistic Cannon",
    "deadbolt 5": "Deadbolt V Ballistic Cannon",
    "ad4b": "AD4B Ballistic Gatling",
    "ad5b": "AD5B Ballistic Gatling",
    "sledge 2": "Sledge II Mass Driver",
    "sledge 3": "Sledge III Mass Driver",
    "m3a": "M3A Laser Cannon",
    "m4a": "M4A Laser Cannon",
    "m5a": "M5A Laser Cannon",
    "m6a": "M6A Laser Cannon",
    "m7a": "M7A Laser Cannon",
    "s1 ammo": "Size 1 Ammunition",
    "s2 ammo": "Size 2 Ammunition",
    "s3 ammo": "Size 3 Ammunition",
    "s4 ammo": "Size 4 Ammunition",
    "s5 ammo": "Size 5 Ammunition",
    "s7 ammo": "Size 7 Ammunition",
    "seeker 9": "Seeker IX Torpedo",
    "argus 9": "Argos IX Torpedo",
    "argos 9": "Argos IX Torpedo",
    "typhoon 9": "Typhoon IX Torpedo",
    "decoys": "Decoy Countermeasures",
    "noise": "Noise Countermeasures",
    "chaff": "Decoy Countermeasures",
    "flares": "Decoy Countermeasures",

    # Ship Components (Shields, QD, Coolers, Power)
    "fr66": "FR-66 Shield Generator",
    "fr-66": "FR-66 Shield Generator",
    "fr76": "FR-76 Shield Generator",
    "fr-76": "FR-76 Shield Generator",
    "fr86": "FR-86 Shield Generator",
    "fr-86": "FR-86 Shield Generator",
    "palisade": "Palisade Shield Generator",
    "mirage": "Mirage Shield Generator",
    "siren": "Siren Shield Generator",
    "atlas": "Atlas Quantum Drive",
    "voyage": "Voyage Quantum Drive",
    "crossfield": "Crossfield Quantum Drive",
    "ts2": "TS-2 Quantum Drive",
    "ts-2": "TS-2 Quantum Drive",
    "pontes": "Pontes Quantum Drive",
    "xl1": "XL-1 Quantum Drive",
    "xl-1": "XL-1 Quantum Drive",
    "spectre": "Spectre Quantum Drive",
    "js300": "JS-300 Power Plant",
    "js-300": "JS-300 Power Plant",
    "js400": "JS-400 Power Plant",
    "js-400": "JS-400 Power Plant",
    "coolcore": "CoolCore Cooler",
    "ultra-flow": "Ultra-Flow Cooler",

    # FPS Weapons & Gear
    "p4": "P4-AR Rifle",
    "p4ar": "P4-AR Rifle",
    "p4-ar": "P4-AR Rifle",
    "p8": "P8-SC SMG",
    "p8sc": "P8-SC SMG",
    "p8-sc": "P8-SC SMG",
    "fs9": "FS-9 LMG",
    "fs-9": "FS-9 LMG",
    "c54": "C-54 Ballistic SMG",
    "c-54": "C-54 Ballistic SMG",
    "karna": "Karna Rifle",
    "demeco": "Demeco LMG",
    "gallant": "Gallant Energy Rifle",
    "s38": "S-38 Pistol",
    "s-38": "S-38 Pistol",
    "arclight": "Arclight Pistol",
    "lh86": "LH86 Pistol",
    "lh-86": "LH86 Pistol",
    "devastator": "Devastator Shotgun",
    "ravager": "Ravager-212 Twin Shotgun",
    "br2": "BR-2 Shotgun",
    "br-2": "BR-2 Shotgun",
    "arrowhead": "Arrowhead Sniper Rifle",
    "p6lr": "P6-LR Sniper Rifle",
    "p6-lr": "P6-LR Sniper Rifle",
    "atzkav": "Atzkav Sniper Rifle",
    "scourge": "Scourge Railgun",
    "animus": "Animus Missile Launcher",
    "medpen": "Hemozal MedPen",
    "hemozal": "Hemozal MedPen",
    "oxypen": "Oxypen",
    "resurgera": "Resurgera MedPen",
    "rosurge": "Resurgera MedPen",
    "sterogen": "Sterogen MedPen",
    "paramed": "ParaMed Medical Device",
    "maxlift": "MaxLift Tractor Beam",
    "tractor": "MaxLift Tractor Beam",
    "cambio": "Cambio SRT",
    "srt": "Cambio SRT",
    "pyro ryt": "Pyro RYT Multi-Tool",
    "multitool": "Pyro RYT Multi-Tool",
    "multi-tool": "Pyro RYT Multi-Tool",

    # Commodities & Mining
    "rmc": "Recycled Material Composite (RMC)",
    "cm": "Construction Materials (CM)",
    "laranite": "Laranite",
    "agricium": "Agricium",
    "titanium": "Titanium",
    "beryl": "Beryl",
    "quant": "Quantanium (Raw)",
    "quantanium": "Quantanium",
    "meds": "Medical Supplies",
    "med supplies": "Medical Supplies",
    "medical supplies": "Medical Supplies",
    "distilled": "Distilled Spirits",
    "stims": "Stims",
    "widow": "WiDoW",
    "slam": "Slam",
    "neon": "Neon",
    "altruciat": "Altruciat Toxin",
    "h2": "Hydrogen Fuel",
    "hydrogen": "Hydrogen Fuel",
    "hydrogen fuel": "Hydrogen Fuel",
    "q-fuel": "Quantum Fuel",
    "quantum fuel": "Quantum Fuel",
    "cruz": "CRUZ Lux",
    "cruz lux": "CRUZ Lux",
    "cruz flow": "CRUZ Flow",
    "cruz pulse": "CRUZ Pulse",
}

def generate_slang_from_cstone():
    master_path = os.path.join(RES_DIR, "cstone_master_db.json")
    master_db = {}
    if os.path.isfile(master_path):
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                master_db = json.load(f)
        except Exception:
            pass

    slang_aliases = {}

    # 1. First add all Reddit community aliases
    for k, v in REDDIT_COMMUNITY_ALIASES.items():
        slang_aliases[k.lower().strip()] = v

    # 2. Add all Table 0 canonical items and generate permutations
    for item_name, details in master_db.items():
        if not isinstance(details, dict): continue
        canonical = details.get("name") or item_name
        canon_clean = canonical.strip()
        canon_low = canon_clean.lower()

        # Direct lowercase
        slang_aliases[canon_low] = canon_clean

        # Shorthand variants (no punctuation, hyphens)
        no_punct = re.sub(r'[\'\"()\-]', ' ', canon_low)
        no_punct_single = re.sub(r'\s+', ' ', no_punct).strip()
        slang_aliases[no_punct_single] = canon_clean

        # Reversed color / word order for clothing and armors:
        # e.g. "Adiva Jacket Yellow" -> "yellow adiva jacket", "yellow adiva", "adiva yellow"
        words = canon_low.split()
        if len(words) >= 3:
            last_word = words[-1]
            if last_word in ["yellow", "woodland", "twilight", "imperial", "blue", "red", "white", "black", "green", "hazard", "quicksilver", "tactical", "desert", "arctic"]:
                reversed_phrase = f"{last_word} {' '.join(words[:-1])}"
                slang_aliases[reversed_phrase] = canon_clean
                slang_aliases[f"{words[0]} {last_word}"] = canon_clean

        # Ship weapons shorthand:
        # e.g. "CF-337 Panther Laser Repeater" -> "panther", "panther repeater", "cf337", "cf-337"
        if any(w in canon_low for w in ["repeater", "cannon", "gatling", "shield", "generator", "drive", "cooler"]):
            for w in words:
                if len(w) >= 4 and w not in ["laser", "repeater", "cannon", "ballistic", "shield", "generator", "quantum", "drive", "cooler"]:
                    slang_aliases[w] = canon_clean
                    slang_aliases[f"{w} {words[-1]}"] = canon_clean

    print(f"[SLANG_GEN] Generated {len(slang_aliases)} aliases from Reddit slang & Table 0 canonical items!")
    
    out_path = os.path.join(RES_DIR, "cstone_generated_slang.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(slang_aliases, f, indent=2, ensure_ascii=False)
    
    return slang_aliases

if __name__ == "__main__":
    generate_slang_from_cstone()
