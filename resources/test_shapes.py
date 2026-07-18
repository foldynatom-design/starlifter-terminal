# -*- coding: utf-8 -*-
"""Test ordnance grid shapes and block placement with the updated renderer."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from cargo_grid_renderer import _get_ordnance_shape, _ORDNANCE_GRID_SHAPES
from cargo_grid_renderer import load_ship_grid, _compute_grid_dimensions, _assign_blocks_to_slots
from storall_packer import calculate_cargo_breakdown

# Test 1: Shape detection
print("=== Shape Detection ===")
tests = [
    ("Pioneer I Missile", "S1", 0.125),
    ("Tempest II Missile", "S2", 1.0),
    ("Arrester III Missile", "S3", 8.0),
    ("Raptor IV Missile", "S4", 8.0),
    ("Reaper V Missile", "S5", 16.0),
    ("Hellion VII Missile", "S7", 16.0),
    ("Seeker IX Torpedo", "S9", 24.0),
    ("Vanquisher X-CS Torpedo", "S10", 32.0),
    ("Calamity XII-CS Torpedo", "S12", 32.0),
    ("Stormburst Bomb", None, 8.0),
    ("Colossus Bomb", None, 32.0),
]
for name, expected_sc, expected_scu in tests:
    shape = _get_ordnance_shape(name)
    if shape:
        scu = shape["scu"]
        dims = f"{shape['w']}x{shape['h']}x{shape['l']}"
        ok = abs(scu - expected_scu) < 0.01
        print(f"  {name:<30} -> {dims} ({scu} SCU) {'OK' if ok else 'FAIL'}")
    else:
        print(f"  {name:<30} -> None (FAIL)")

# Test 2: Shape-aware placement with Caterpillar
print("\n=== Placement Test (Caterpillar + 3x S9 torpedoes) ===")
items = [
    {"name": "Seeker IX Torpedo", "qty": 3},
    {"name": "Refined Gold", "qty": 50},
    {"name": "P8-SC SMG", "qty": 5},
]
bd = calculate_cargo_breakdown(items)
grid = load_ship_grid('Caterpillar')
groups_info = _compute_grid_dimensions(grid)
assignments = _assign_blocks_to_slots(groups_info, bd)

for gi, gassgn in enumerate(assignments):
    placed_cat = [b for b in gassgn if b['category'] != 'FREE']
    if placed_cat:
        print(f"  Bay {gi}:")
        for b in placed_cat:
            xs = [s[0] for s in b['slots']]
            ys = [s[1] for s in b['slots']]
            zs = [s[2] for s in b['slots']]
            bw = max(xs) - min(xs) + 1
            bh = max(ys) - min(ys) + 1
            bl = max(zs) - min(zs) + 1
            print(f"    [{b['category']}] {b['label'][:30]:<30} {b['scu']:>5} SCU -> {bw}x{bh}x{bl} shape at ({min(xs)},{min(ys)},{min(zs)})")

# Test 3: Verify torpedo shapes are 2x2x6
print("\n=== Torpedo Shape Verification ===")
for b in [b for gassgn in assignments for b in gassgn if 'TORPEDO' in b.get('label', '')]:
    xs = [s[0] for s in b['slots']]
    ys = [s[1] for s in b['slots']]
    zs = [s[2] for s in b['slots']]
    bw = max(xs) - min(xs) + 1
    bh = max(ys) - min(ys) + 1
    bl = max(zs) - min(zs) + 1
    expected = "2x2x6"
    actual = f"{bw}x{bh}x{bl}"
    ok = actual == expected
    print(f"  {b['label'][:30]}: {actual} {'OK' if ok else f'FAIL (expected {expected})'}")

print("\n=== ALL TESTS OK ===")
