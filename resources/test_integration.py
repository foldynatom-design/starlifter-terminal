# -*- coding: utf-8 -*-
"""Integration test: storall_packer + cargo_grid_renderer together."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from storall_packer import calculate_cargo_breakdown
from cargo_grid_renderer import load_ship_grid, _compute_grid_dimensions, _assign_blocks_to_slots

# Simulate a real cargo manifest
items = [
    {"name": "Refined Quantainium", "qty": 8},
    {"name": "P8-SC SMG", "qty": 10},
    {"name": "Medpen", "qty": 20},
    {"name": "Burrito", "qty": 15},
    {"name": "Seeker IX Torpedo", "qty": 3},
    {"name": "MaxLift Tractor Beam", "qty": 5},
    {"name": "MaxLift Tractor Beam Battery", "qty": 5},
]

print("=== Cargo Breakdown ===")
bd = calculate_cargo_breakdown(items)
print(f"  Commodity: {bd['commodity_vol']} SCU")
print(f"  Supply:    {bd['supply_vol']} SCU")
print(f"  Ordnance:  {bd['ordnance_vol']} SCU")
print(f"  Total:     {bd['total_vol']} SCU")
print(f"  Stor-All boxes: {len(bd.get('stor_all_boxes', []))}")
for box in bd.get('stor_all_boxes', []):
    print(f"    {box.get('label', '?')}: {len(box.get('items', []))} items")
print(f"  Ordnance items: {len(bd.get('ordnance_items', []))}")
for oi in bd.get('ordnance_items', []):
    print(f"    {oi['name']} x{oi['qty']} = {oi['total_scu']} SCU")
print(f"  Commodity items: {len(bd.get('commodity_items', []))}")
for ci in bd.get('commodity_items', []):
    print(f"    {ci['name']} x{ci['qty']} = {ci['total_scu']} SCU")

# Load C2 grid and assign blocks
print("\n=== Block Assignment (C2 Hercules) ===")
grid = load_ship_grid('C2 Hercules')
groups_info = _compute_grid_dimensions(grid)
assignments = _assign_blocks_to_slots(groups_info, bd)

for gi, gassgn in enumerate(assignments):
    print(f"  Group {gi}: {len(gassgn)} blocks")
    for block in gassgn:
        print(f"    [{block['category']}] {block['label']} ({block['scu']} SCU) -> {len(block['slots'])} slots")

print("\n=== INTEGRATION TEST OK ===")
