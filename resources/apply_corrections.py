# -*- coding: utf-8 -*-
"""Apply verified SCU corrections from starcitizen.tools wiki to item_volumes.json."""
import json
import os

vol_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'item_volumes.json')

with open(vol_path, 'r', encoding='utf-8') as f:
    vm = json.load(f)

# Corrections from wiki verification (SCU box sizes)
corrections = {
    # S1 missiles -> 8 SCU box
    "pioneer i missile": 8,
    "spark i missile": 8,
    "spark i-g missile": 8,
    "arrow i missile": 8,
    "marksman i missile": 8,
    "taskforce i missile": 8,
    "viper i missile": 8,  # was missing from wiki but same size class
    # S2 missiles -> 1 SCU (ALREADY CORRECT)
    # S3 missiles -> 8 SCU box
    "arrester iii missile": 8,
    "thunderbolt iii missile": 8,
    "viper iii missile": 8,
    "chaos iii missile": 8,
    # S4 missiles -> 8 SCU box
    "raptor iv missile": 8,
    "stalker iv missile": 8,
    "pathfinder iv missile": 8,
    "dragon iv missile": 8,
    "assailant iv missile": 8,
    # S5 missiles -> 16 SCU box
    "reaper v missile": 16,
    "stalker v missile": 16,
    "scimitar v missile": 16,
    "valkyrie v missile": 16,
    # S7 missiles -> 16 SCU box
    "hellion vii missile": 16,
    # S9 torpedoes -> 24 SCU box
    "seeker ix torpedo": 24,
    "argos ix torpedo": 24,
    "argus ix torpedo": 24,  # alternate spelling
    "typhoon ix torpedo": 24,
    # S10 torpedoes -> 32 SCU box
    "vanquisher x-cs torpedo": 32,
    "vanquisher x-em torpedo": 32,
    "vanquisher x-ir torpedo": 32,
    "ex-t10-cs \"executor\" torpedo": 32,
    "ex-t10-em \"executor\" torpedo": 32,
    "ex-t10-ir \"executor\" torpedo": 32,
    "vt-t10 \"veritas\" torpedo": 32,
    # S12 torpedoes -> 32 SCU box (already correct)
    # Bombs
    "stormburst bomb": 8,
    "colossus bomb": 32,
    "thunderball bomb": 8,
}

applied = 0
added = 0
for key, new_val in corrections.items():
    old_val = vm.get(key)
    if old_val is not None:
        if old_val != new_val:
            print(f"  FIX: {key}: {old_val} -> {new_val}")
            vm[key] = new_val
            applied += 1
        else:
            print(f"  OK:  {key}: {old_val} (already correct)")
    else:
        print(f"  ADD: {key}: {new_val}")
        vm[key] = new_val
        added += 1

with open(vol_path, 'w', encoding='utf-8') as f:
    json.dump(vm, f, indent=2, ensure_ascii=False)

print(f"\nApplied {applied} corrections, added {added} new entries")
print(f"Total entries: {len(vm)}")
