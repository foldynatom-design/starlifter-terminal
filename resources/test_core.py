# -*- coding: utf-8 -*-
"""Quick test of modules that don't need PIL/cv2/tkinter."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

print("--- Testing storall_packer ---")
from storall_packer import pack_items, calculate_cargo_breakdown, load_volume_map, STOR_ALL_CATEGORIES, STOR_ALL_SIZES, _pick_box_size

vm = load_volume_map()
print(f"  volume_map: {len(vm)} entries")

bd = calculate_cargo_breakdown([{"name": "Refined Gold", "qty": 5}, {"name": "P8-SC Pistol", "qty": 10}])
print(f"  breakdown: commodity={bd['commodity_vol']}, supply={bd['supply_vol']}, ordnance={bd['ordnance_vol']}")
print(f"  stor_all_boxes: {len(bd.get('stor_all_boxes', []))} boxes")

print("\n--- Testing fleet_helper ---")
from fleet_helper import _recommend_shuttle, can_shuttle_fit

r = can_shuttle_fit('MPUV Cargo', 'C2 Hercules')
fit = 'YES' if r and r.get('fits') else 'NO'
print(f"  can_shuttle_fit: MPUV in C2 = {fit}")

print("\n--- Testing lore_helper ---")
from lore_helper import get_telemetry

tel = get_telemetry('Ship under heavy fire', 'high', [{"name": "Seeker IX Torpedo", "qty": 2}])
print(f"  get_telemetry: gravity={tel['gravity'][:30]}...")

print("\n=== ALL CORE IMPORTS OK ===")
