# -*- coding: utf-8 -*-
"""
Verify ordnance SCU values against starcitizen.tools wiki.
Scrapes the Dimensions/Cargo section for each item to get the correct SCU box size.
"""
import json
import re
import urllib.request
import urllib.error
import time
import os

# Items to verify — all ordnance from item_volumes.json
ORDNANCE_TO_CHECK = {
    # S1 missiles
    "Pioneer I Missile": "Pioneer_I_Missile",
    "Viper I Missile": "Viper_I_Missile",  
    "Spark I Missile": "Spark_I_Missile",
    "Arrow I Missile": "Arrow_I_Missile",
    "Taskforce I Missile": "Taskforce_I_Missile",
    "Marksman I Missile": "Marksman_I_Missile",
    # S2 missiles
    "Marksman II Missile": "Marksman_II_Missile",
    "Tempest II Missile": "Tempest_II_Missile",
    "Strikeforce II Missile": "Strikeforce_II_Missile",
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
    "Stalker IV Missile": "Stalker_IV_Missile",  # Might be Stalker V
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
    "Argos IX Torpedo": "Argos_IX_Torpedo",  # might be Argus
    "Typhoon IX Torpedo": "Typhoon_IX_Torpedo",
    # S10 torpedoes
    "Vanquisher X-CS Torpedo": "Vanquisher_X-CS_Torpedo",
    "Vanquisher X-EM Torpedo": "Vanquisher_X-EM_Torpedo",
    "Vanquisher X-IR Torpedo": "Vanquisher_X-IR_Torpedo",
    "EX-T10-CS Executor Torpedo": "EX-T10-CS_%22Executor%22_Torpedo",
    "EX-T10-EM Executor Torpedo": "EX-T10-EM_%22Executor%22_Torpedo",
    "EX-T10-IR Executor Torpedo": "EX-T10-IR_%22Executor%22_Torpedo",
    "VT-T10 Veritas Torpedo": "VT-T10_%22Veritas%22_Torpedo",
    # S12 torpedoes
    "Calamity XII-CS Torpedo": "Calamity_XII-CS_Torpedo",
    "Calamity XII-IR Torpedo": "Calamity_XII-IR_Torpedo",
    "EX-T12-CS Executor Torpedo": "EX-T12-CS_%22Executor%22_Torpedo",
    "EX-T12-EM Executor Torpedo": "EX-T12-EM_%22Executor%22_Torpedo",
    "EX-T12-IR Executor Torpedo": "EX-T12-IR_%22Executor%22_Torpedo",
    # Bombs
    "Stormburst Bomb": "Stormburst_Bomb",
    "Colossus Bomb": "Colossus_Bomb",
    "Thunderball Bomb": "Thunderball_Bomb",
    # Ammunition
    "Size 1 Ammunition": None,  # skip - not on wiki individually
    "Size 2 Ammunition": None,
    "Size 3 Ammunition": None,
    "Size 4 Ammunition": None,
    "Size 5 Ammunition": None,
    "Size 6 Ammunition": None,
    "Size 7 Ammunition": None,
}


def fetch_scu_from_wiki(page_name):
    """Fetch SCU box size from starcitizen.tools wiki page."""
    url = f"https://starcitizen.tools/{page_name}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return None, f"HTTP error: {e}"

    # Look for SCU box pattern: "XX SCU box" in the dimensions section
    # Pattern examples: "24 SCU box", "1 SCU box", "2 SCU box"
    scu_match = re.search(r'(\d+)\s*SCU\s*box', html)
    if scu_match:
        return int(scu_match.group(1)), "found"

    # Alternative: look for Volume in microSCU
    vol_match = re.search(r'Volume\s*[\s:]*?([\d,]+)\s*(?:&mu;|\\u00b5|micro|u)SCU', html, re.IGNORECASE)
    if vol_match:
        micro_scu = int(vol_match.group(1).replace(",", ""))
        # Convert microSCU to SCU (1 SCU = 1,000,000 microSCU)
        scu = micro_scu / 1_000_000
        return scu, "from_volume"

    # Try parsing for "XX SCU" near cargo/dimensions
    cargo_match = re.search(r'Cargo.*?(\d+)\s*SCU', html, re.IGNORECASE | re.DOTALL)
    if cargo_match:
        return int(cargo_match.group(1)), "cargo_section"

    return None, "not_found"


def main():
    # Load current item_volumes.json
    vol_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'item_volumes.json')
    with open(vol_path, 'r', encoding='utf-8') as f:
        volume_map = json.load(f)

    results = []
    errors = []

    for display_name, wiki_page in ORDNANCE_TO_CHECK.items():
        if wiki_page is None:
            continue

        key = display_name.lower()
        current_val = volume_map.get(key, "NOT IN DB")

        wiki_scu, status = fetch_scu_from_wiki(wiki_page)
        time.sleep(0.3)  # Be polite to the wiki

        if wiki_scu is not None:
            mismatch = ""
            if isinstance(current_val, (int, float)) and abs(wiki_scu - current_val) > 0.01:
                mismatch = f" *** MISMATCH (was {current_val})"
            results.append((display_name, current_val, wiki_scu, status, mismatch))
            print(f"  {display_name}: wiki={wiki_scu} SCU, db={current_val}{mismatch}")
        else:
            errors.append((display_name, wiki_page, status))
            print(f"  {display_name}: FAILED ({status})")

    # Summary
    print(f"\n{'='*60}")
    print(f"Checked: {len(results)} items")
    print(f"Errors:  {len(errors)} items")

    mismatches = [r for r in results if r[4]]
    print(f"\nMISMATCHES ({len(mismatches)}):")
    for name, db_val, wiki_val, status, note in mismatches:
        print(f"  {name}: DB={db_val} -> WIKI={wiki_val}")

    # Output corrections as JSON
    corrections = {}
    for name, db_val, wiki_val, status, note in results:
        if note:  # mismatch
            corrections[name.lower()] = wiki_val

    if corrections:
        print(f"\nCorrections to apply:")
        print(json.dumps(corrections, indent=2))

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), 'ordnance_verification.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            "results": [{"name": r[0], "db": r[1], "wiki": r[2], "status": r[3], "mismatch": bool(r[4])} for r in results],
            "errors": [{"name": e[0], "wiki_page": e[1], "error": e[2]} for e in errors],
            "corrections": corrections,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
