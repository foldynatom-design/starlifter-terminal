# -*- coding: utf-8 -*-
"""
Comprehensive SCU verification: ores, gems, blueprints, commodities.
Scrapes starcitizen.tools for correct SCU box sizes.
"""
import json
import re
import urllib.request
import urllib.error
import time
import os


def fetch_scu_from_wiki(page_name):
    """Fetch SCU box size and cargo dimensions from starcitizen.tools."""
    url = f"https://starcitizen.tools/{page_name}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return None, None, f"HTTP error: {e}"

    # Parse SCU box - fractions first: "1/8 SCU box"
    fraction_match = re.search(r'(\d+)/(\d+)\s*SCU\s*box', html)
    if fraction_match:
        num, den = int(fraction_match.group(1)), int(fraction_match.group(2))
        return num / den, f"{num}/{den} SCU box", "ok"

    # Whole number: "24 SCU box" (but not "/24 SCU box")
    whole_match = re.search(r'(?<!/)\b(\d+)\s*SCU\s*box', html)
    if whole_match:
        scu = int(whole_match.group(1))
        return float(scu), f"{scu} SCU box", "ok"

    # Volume in microSCU
    vol_sr = re.search(r'volume\s+([\d,]+)\s*(?:&#181;|&mu;|\\u00b5|\xb5)SCU', html, re.IGNORECASE)
    if vol_sr:
        micro = int(vol_sr.group(1).replace(",", ""))
        scu = micro / 1_000_000
        return scu, f"{micro} uSCU", "from_volume"

    return None, None, "not_found"


# ── Items to check ──

ORES_AND_MINERALS = {
    # Raw ores
    "Quantainium": "Quantainium_(ore)",
    "Agricultural Supplies": "Agricultural_Supplies",
    "Agricium": "Agricium_(ore)",
    "Aluminum": "Aluminum_(ore)",
    "Beryl": "Beryl_(ore)",
    "Bexalite": "Bexalite_(ore)",
    "Borase": "Borase_(ore)",
    "Copper": "Copper_(ore)",
    "Corundum": "Corundum_(ore)",
    "Diamond": "Diamond_(ore)",
    "Gold": "Gold_(ore)",
    "Hephaestanite": "Hephaestanite_(ore)",
    "Iron": "Iron_(ore)",
    "Laranite": "Laranite_(ore)",
    "Quartz": "Quartz_(ore)",
    "Silicon": "Silicon_(ore)",
    "Taranite": "Taranite_(ore)",
    "Titanium": "Titanium_(ore)",
    "Tungsten": "Tungsten_(ore)",
    # Refined ores / commodities
    "Refined Quantainium": "Quantainium",
    "Refined Agricium": "Agricium",
    "Refined Aluminum": "Aluminum",
    "Refined Beryl": "Beryl",
    "Refined Bexalite": "Bexalite",
    "Refined Borase": "Borase",
    "Refined Copper": "Copper",
    "Refined Corundum": "Corundum",
    "Refined Diamond": "Diamond",
    "Refined Gold": "Gold",
    "Refined Hephaestanite": "Hephaestanite",
    "Refined Iron": "Iron",
    "Refined Laranite": "Laranite",
    "Refined Silicon": "Silicon",
    "Refined Taranite": "Taranite",
    "Refined Titanium": "Titanium",
    "Refined Tungsten": "Tungsten",
    # Gems
    "Aphorite": "Aphorite",
    "Dolivine": "Dolivine",
    "Hadanite": "Hadanite",
    "Janalite": "Janalite",
}

COMMODITIES = {
    "Hydrogen Fuel": "Hydrogen_Fuel",
    "Quantum Fuel": "Quantum_Fuel",
    "Recycled Material Composite": "Recycled_Material_Composite",
    "Construction Materials": "Construction_Materials",
    "Stims": "Stims",
    "Medical Supplies": "Medical_Supplies",
    "Scrap": "Scrap",
    "Waste": "Waste",
    "Distilled Spirits": "Distilled_Spirits",
    "Processed Food": "Processed_Food",
    "Astatine": "Astatine",
    "Chlorine": "Chlorine",
    "Fluorine": "Fluorine",
    "Iodine": "Iodine",
}

BLUEPRINTS = {
    "ADP-Mk4 Armor Blueprint": "ADP-Mk4_Armor_Blueprint",
    "ORC-Mkx Armor Blueprint": "ORC-Mkx_Armor_Blueprint",
    "MacFlex Armor Blueprint": "MacFlex_Armor_Blueprint",
    "P4-AR Rifle Blueprint": "P4-AR_Rifle_Blueprint",
    "Coda Pistol Blueprint": "Coda_Pistol_Blueprint",
    "C54 SMG Blueprint": "C54_SMG_Blueprint",
    "Devastator Shotgun Blueprint": "Devastator_Shotgun_Blueprint",
}


def check_category(name, items_dict, volume_map):
    """Check all items in a category dict."""
    results = []
    for display_name, wiki_page in items_dict.items():
        key = display_name.lower()
        current_val = volume_map.get(key, "NOT_IN_DB")

        wiki_scu, label, status = fetch_scu_from_wiki(wiki_page)
        time.sleep(0.25)

        if wiki_scu is not None:
            mismatch = ""
            if isinstance(current_val, (int, float)) and abs(wiki_scu - current_val) > 0.001:
                mismatch = " *** MISMATCH"
            elif current_val == "NOT_IN_DB":
                mismatch = " *** MISSING"
            results.append({
                "name": display_name,
                "key": key,
                "db": current_val,
                "wiki": wiki_scu,
                "label": label,
                "mismatch": bool(mismatch),
            })
            print(f"  {display_name}: wiki={label} ({wiki_scu:.4f}), db={current_val}{mismatch}")
        else:
            results.append({
                "name": display_name,
                "key": key,
                "db": current_val,
                "wiki": None,
                "label": status,
                "mismatch": False,
            })
            print(f"  {display_name}: FAILED ({status})")

    return results


def main():
    vol_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'item_volumes.json')
    with open(vol_path, 'r', encoding='utf-8') as f:
        volume_map = json.load(f)

    all_results = {}

    print("=== ORES & MINERALS ===")
    all_results["ores"] = check_category("ores", ORES_AND_MINERALS, volume_map)

    print("\n=== COMMODITIES ===")
    all_results["commodities"] = check_category("commodities", COMMODITIES, volume_map)

    print("\n=== BLUEPRINTS ===")
    all_results["blueprints"] = check_category("blueprints", BLUEPRINTS, volume_map)

    # Summary
    print(f"\n{'='*70}")
    total = sum(len(v) for v in all_results.values())
    mismatches = sum(1 for v in all_results.values() for r in v if r["mismatch"])
    missing = sum(1 for v in all_results.values() for r in v if r["db"] == "NOT_IN_DB")
    print(f"Total checked: {total}")
    print(f"Mismatches: {mismatches}")
    print(f"Missing from DB: {missing}")

    # Corrections
    corrections = {}
    for cat_results in all_results.values():
        for r in cat_results:
            if r["wiki"] is not None and (r["mismatch"] or r["db"] == "NOT_IN_DB"):
                corrections[r["key"]] = r["wiki"]

    if corrections:
        print(f"\nCorrections ({len(corrections)}):")
        for k, v in corrections.items():
            print(f"  {k}: {v}")

    out_path = os.path.join(os.path.dirname(__file__), 'commodity_verification.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"results": all_results, "corrections": corrections}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
