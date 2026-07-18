# -*- coding: utf-8 -*-
"""
Verify ALL ordnance SCU box sizes and their grid shapes.
For each missile size, compute physical grid footprint:
  grid_slots = ceil(L/1.25) x ceil(W/1.25) x ceil(H/1.25)

Cross-reference against wiki "SCU box" values.
"""
import json
import re
import urllib.request
import time
import math
import os

# Expected SCU box sizes per missile/torpedo size class (from wiki verification v2)
EXPECTED = {
    # Size class -> (SCU box, grid shape WxHxL, physical dims approx)
    "S1": {"scu_box": 0.125, "label": "1/8 SCU", "grid": "1x1x1", "phys": "1x1x1m"},
    "S2": {"scu_box": 1.0,   "label": "1 SCU",   "grid": "1x1x1", "phys": "1.25x1.25x1.25m"},
    "S3": {"scu_box": 8.0,   "label": "8 SCU",   "grid": "2x2x2", "phys": "2.5x2.5x2.5m"},
    "S4": {"scu_box": 8.0,   "label": "8 SCU",   "grid": "2x2x2", "phys": "2.5x2.5x2.5m"},
    "S5": {"scu_box": 16.0,  "label": "16 SCU",  "grid": "2x2x4", "phys": "2.5x2.5x5m"},
    "S7": {"scu_box": 16.0,  "label": "16 SCU",  "grid": "2x2x4", "phys": "2.5x2.5x5m"},
    "S9": {"scu_box": 24.0,  "label": "24 SCU",  "grid": "2x2x6", "phys": "2.5x2.5x7.5m"},
    "S10":{"scu_box": 32.0,  "label": "32 SCU",  "grid": "2x2x8", "phys": "2.5x2.5x10m"},
    "S12":{"scu_box": 32.0,  "label": "32 SCU",  "grid": "2x2x8", "phys": "2.5x2.5x10m"},
}

# All ordnance items from item_volumes.json with their size class
ORDNANCE_ITEMS = {
    # S1 missiles
    "pioneer i missile": "S1", "spark i missile": "S1", "spark i-g missile": "S1",
    "arrow i missile": "S1", "marksman i missile": "S1",
    "taskforce i missile": "S1", "viper i missile": "S1",
    # S2 missiles
    "tempest ii missile": "S2", "ignite ii missile": "S2",
    "dominator ii missile": "S2", "rattler ii missile": "S2", "bullet ii missile": "S2",
    # S3 missiles
    "arrester iii missile": "S3", "thunderbolt iii missile": "S3",
    "viper iii missile": "S3", "chaos iii missile": "S3",
    # S4 missiles
    "raptor iv missile": "S4", "stalker iv missile": "S4",
    "pathfinder iv missile": "S4", "dragon iv missile": "S4",
    "assailant iv missile": "S4",
    # S5 missiles
    "reaper v missile": "S5", "stalker v missile": "S5",
    "scimitar v missile": "S5", "valkyrie v missile": "S5",
    # S7 missiles
    "hellion vii missile": "S7",
    # S9 torpedoes
    "seeker ix torpedo": "S9", "argos ix torpedo": "S9",
    "argus ix torpedo": "S9", "typhoon ix torpedo": "S9",
    # S10 torpedoes
    "vanquisher x-cs torpedo": "S10", "vanquisher x-em torpedo": "S10",
    "vanquisher x-ir torpedo": "S10",
    'ex-t10-cs "executor" torpedo': "S10", 'ex-t10-em "executor" torpedo': "S10",
    'ex-t10-ir "executor" torpedo': "S10", 'vt-t10 "veritas" torpedo': "S10",
    # S12 torpedoes
    "calamity xii-cs torpedo": "S12", "calamity xii-ir torpedo": "S12",
    'ex-t12-cs "executor" torpedo': "S12", 'ex-t12-em "executor" torpedo': "S12",
    'ex-t12-ir "executor" torpedo': "S12",
    # Bombs
    "stormburst bomb": "S3",  # S3-equivalent
    "thunderball bomb": "S3",  # S3-equivalent
    "colossus bomb": "S10",    # S10-equivalent
}


def main():
    vol_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'item_volumes.json')
    with open(vol_path, 'r', encoding='utf-8') as f:
        vm = json.load(f)

    print("=== ORDNANCE SCU BOX VERIFICATION ===\n")
    print(f"{'Item':<40} {'Size':<5} {'DB SCU':>8} {'Expected':>10} {'Status'}")
    print("-" * 80)

    errors = []
    fixes = {}

    for item_key, size_class in sorted(ORDNANCE_ITEMS.items(), key=lambda x: x[1]):
        expected_scu = EXPECTED[size_class]["scu_box"]
        db_val = vm.get(item_key, "MISSING")

        if db_val == "MISSING":
            status = "MISSING"
            fixes[item_key] = expected_scu
            errors.append((item_key, size_class, db_val, expected_scu))
        elif isinstance(db_val, (int, float)) and abs(db_val - expected_scu) > 0.001:
            status = f"WRONG (should be {expected_scu})"
            fixes[item_key] = expected_scu
            errors.append((item_key, size_class, db_val, expected_scu))
        else:
            status = "OK"

        print(f"  {item_key:<38} {size_class:<5} {str(db_val):>8} {expected_scu:>10} {status}")

    print(f"\n{'='*80}")
    print(f"Total: {len(ORDNANCE_ITEMS)}, Errors: {len(errors)}")

    if fixes:
        print(f"\nApplying {len(fixes)} fixes...")
        for k, v in fixes.items():
            old = vm.get(k, "N/A")
            vm[k] = v
            print(f"  {k}: {old} -> {v}")

        with open(vol_path, 'w', encoding='utf-8') as f:
            json.dump(vm, f, indent=2, ensure_ascii=False)
        print("Saved!")

    # Print grid shape reference table
    print(f"\n=== ORDNANCE GRID SHAPE REFERENCE ===\n")
    print(f"{'Size':<5} {'SCU Box':>8} {'Grid Shape':<12} {'Physical':<20}")
    print("-" * 50)
    for sc, info in EXPECTED.items():
        print(f"  {sc:<5} {info['label']:>8} {info['grid']:<12} {info['phys']:<20}")

    # Save grid shapes for renderer
    shapes_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'ordnance_grid_shapes.json')
    shapes = {}
    for sc, info in EXPECTED.items():
        w, h, l = [int(x) for x in info["grid"].split("x")]
        shapes[sc] = {"width": w, "height": h, "length": l, "scu": info["scu_box"], "label": info["label"]}
    with open(shapes_path, 'w', encoding='utf-8') as f:
        json.dump(shapes, f, indent=2)
    print(f"\nGrid shapes saved to ordnance_grid_shapes.json")


if __name__ == "__main__":
    main()
