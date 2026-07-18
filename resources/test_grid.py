# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from cargo_grid_renderer import load_ship_grid, render_cargo_directive, _compute_grid_dimensions

# Test 1: Load C2 Hercules
g = load_ship_grid('C2 Hercules')
assert g is not None, "C2 Hercules not found!"
cap = g.get('capacity', 0)
groups = len(g.get('groups', []))
print(f"C2 Hercules: cap={cap} SCU, groups={groups}")

# Test 2: Load Caterpillar
g2 = load_ship_grid('Drake Caterpillar')
assert g2 is not None, "Caterpillar not found!"
print(f"Caterpillar: cap={g2['capacity']} SCU, groups={len(g2['groups'])}")

# Test 3: Load by clean name
g3 = load_ship_grid('Idris')
if g3:
    print(f"Idris: cap={g3['capacity']} SCU, groups={len(g3['groups'])}")
else:
    print("Idris: not found (expected — might not be in DB)")

# Test 4: Render directive
d = render_cargo_directive(g, 'C2 Hercules', 'Port Olisar', 'EVA')
print(f"Directive: {d}")

# Test 5: Compute dimensions
dims = _compute_grid_dimensions(g)
for i, gd in enumerate(dims):
    print(f"  Group {i}: {gd['width']}x{gd['height']}x{gd['length']} = {gd['slots']} slots")

# Test 6: Fuzzy match
g4 = load_ship_grid('Freelancer')
assert g4 is not None
print(f"Freelancer: cap={g4['capacity']} SCU")

print("\n=== CARGO GRID RENDERER OK ===")
