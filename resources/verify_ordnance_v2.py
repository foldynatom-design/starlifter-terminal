# -*- coding: utf-8 -*-
"""
Verify ordnance SCU values against starcitizen.tools wiki — FIXED regex.
Now correctly parses "1/8 SCU box", "24 SCU box", etc.
"""
import json
import re
import urllib.request
import urllib.error
import time
import os

ORDNANCE_TO_CHECK = {
    # S1 missiles
    "Pioneer I Missile": "Pioneer_I_Missile",
    "Spark I Missile": "Spark_I_Missile",
    "Arrow I Missile": "Arrow_I_Missile",
    "Marksman I Missile": "Marksman_I_Missile",
    # S2 missiles
    "Tempest II Missile": "Tempest_II_Missile",
    "Ignite II Missile": "Ignite_II_Missile",
    "Dominator II Missile": "Dominator_II_Missile",
    "Rattler II Missile": "Rattler_II_Missile",
    "Bullet II Missile": "Bullet_II_Missile",
    # S3 missiles
    "Arrester III Missile": "Arrester_III_Missile",
    "Thunderbolt III Missile": "Thunderbolt_III_Missile",
    "Viper III Missile": "Viper_III_Missile",
    "Chaos III Missile": "Chaos_III_Missile",
    # S4 missiles
    "Raptor IV Missile": "Raptor_IV_Missile",
    "Pathfinder IV Missile": "Pathfinder_IV_Missile",
    "Dragon IV Missile": "Dragon_IV_Missile",
    "Assailant IV Missile": "Assailant_IV_Missile",
    # S5 missiles
    "Reaper V Missile": "Reaper_V_Missile",
    "Stalker V Missile": "Stalker_V_Missile",
    "Scimitar V Missile": "Scimitar_V_Missile",
    "Valkyrie V Missile": "Valkyrie_V_Missile",
    # S7 missiles
    "Hellion VII Missile": "Hellion_VII_Missile",
    # S9 torpedoes
    "Seeker IX Torpedo": "Seeker_IX_Torpedo",
    "Argos IX Torpedo": "Argos_IX_Torpedo",
    "Typhoon IX Torpedo": "Typhoon_IX_Torpedo",
    # S10 torpedoes
    "Vanquisher X-CS Torpedo": "Vanquisher_X-CS_Torpedo",
    "Vanquisher X-EM Torpedo": "Vanquisher_X-EM_Torpedo",
    "Vanquisher X-IR Torpedo": "Vanquisher_X-IR_Torpedo",
    # S12 torpedoes
    "Calamity XII-CS Torpedo": "Calamity_XII-CS_Torpedo",
    "Calamity XII-IR Torpedo": "Calamity_XII-IR_Torpedo",
    # Bombs
    "Stormburst Bomb": "Stormburst_Bomb",
    "Colossus Bomb": "Colossus_Bomb",
    "Thunderball Bomb": "Thunderball_Bomb",
}


def fetch_scu_from_wiki(page_name):
    """Fetch SCU box size from starcitizen.tools wiki page."""
    url = f"https://starcitizen.tools/{page_name}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return None, None, f"HTTP error: {e}"

    # FIXED: Parse "XX SCU box" including fractions like "1/8 SCU box"
    # Pattern: "1/8 SCU box · 0.5 m" or "24 SCU box · 7.5 m"
    fraction_match = re.search(r'(\d+)/(\d+)\s*SCU\s*box', html)
    if fraction_match:
        num = int(fraction_match.group(1))
        den = int(fraction_match.group(2))
        scu = num / den
        return scu, f"{num}/{den}", "fraction_box"

    # Whole number: "24 SCU box"
    whole_match = re.search(r'(?<!/)\b(\d+)\s*SCU\s*box', html)
    if whole_match:
        scu = int(whole_match.group(1))
        return float(scu), str(scu), "whole_box"

    # Also get physical dimensions for reference
    dim_match = re.search(r'Dimensions:\s*length\s*([\d.]+)\s*m,\s*width\s*([\d.]+)\s*m,\s*height\s*([\d.]+)\s*m', html)
    if dim_match:
        l, w, h = float(dim_match.group(1)), float(dim_match.group(2)), float(dim_match.group(3))
        return None, f"{l}x{w}x{h}", f"dims_only({l}x{w}x{h})"

    return None, None, "not_found"


def main():
    vol_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'item_volumes.json')
    with open(vol_path, 'r', encoding='utf-8') as f:
        volume_map = json.load(f)

    results = []
    errors = []

    for display_name, wiki_page in ORDNANCE_TO_CHECK.items():
        key = display_name.lower()
        current_val = volume_map.get(key, "NOT IN DB")

        wiki_scu, label, status = fetch_scu_from_wiki(wiki_page)
        time.sleep(0.3)

        if wiki_scu is not None:
            mismatch = ""
            if isinstance(current_val, (int, float)) and abs(wiki_scu - current_val) > 0.01:
                mismatch = f" *** MISMATCH (was {current_val})"
            results.append((display_name, current_val, wiki_scu, label, status, mismatch))
            print(f"  {display_name}: wiki={label} SCU box ({wiki_scu}), db={current_val}{mismatch}")
        else:
            errors.append((display_name, wiki_page, status))
            print(f"  {display_name}: FAILED ({status})")

    print(f"\n{'='*70}")
    print(f"Checked: {len(results)} items, Errors: {len(errors)}")

    mismatches = [r for r in results if r[5]]
    print(f"\nMISMATCHES ({len(mismatches)}):")
    for name, db_val, wiki_val, label, status, note in mismatches:
        print(f"  {name}: DB={db_val} -> WIKI={label} SCU ({wiki_val})")

    corrections = {}
    for name, db_val, wiki_val, label, status, note in results:
        if note:
            corrections[name.lower()] = wiki_val

    if corrections:
        print(f"\nCorrections JSON:")
        print(json.dumps(corrections, indent=2))

    out_path = os.path.join(os.path.dirname(__file__), 'ordnance_verification_v2.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            "results": [{"name": r[0], "db": r[1], "wiki_scu": r[2], "wiki_label": r[3], "status": r[4], "mismatch": bool(r[5])} for r in results],
            "errors": [{"name": e[0], "wiki_page": e[1], "error": e[2]} for e in errors],
            "corrections": corrections,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
