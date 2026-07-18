# Quick test: C2 Hercules torpedo placement
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))
from cargo_grid_renderer import load_ship_grid, _compute_grid_dimensions, _assign_blocks_to_slots
from storall_packer import calculate_cargo_breakdown

items = [
    {"name": "Seeker IX Torpedo", "qty": 3},
    {"name": "Refined Gold", "qty": 10},
    {"name": "P8-SC SMG", "qty": 5},
]
bd = calculate_cargo_breakdown(items)
grid = load_ship_grid("C2 Hercules")
gi = _compute_grid_dimensions(grid)
a = _assign_blocks_to_slots(gi, bd)

print("C2 Hercules torpedo placement:")
for b in [b for g in a for b in g if b["category"] != "FREE"]:
    xs = [s[0] for s in b["slots"]]
    ys = [s[1] for s in b["slots"]]
    zs = [s[2] for s in b["slots"]]
    w = max(xs) - min(xs) + 1
    h = max(ys) - min(ys) + 1
    l = max(zs) - min(zs) + 1
    cat = b["category"]
    label = b["label"][:30]
    scu = b["scu"]
    print(f"  [{cat}] {label:<30} {scu:>5} SCU -> {w}x{h}x{l} at ({min(xs)},{min(ys)},{min(zs)})")
