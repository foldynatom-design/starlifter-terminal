# -*- coding: utf-8 -*-
import json

with open('resources/ship_grids_db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

# Show 3 example ships with groups/grids
examples = ['C2 Hercules', 'Caterpillar', 'Freelancer']
for name in examples:
    # Find by partial match
    for k, v in db.items():
        if name.lower() in k.lower():
            cap = v.get('capacity', '?')
            groups = v.get('groups', [])
            src = v.get('_source', 'unknown')
            print(f"=== {k} (cap={cap} SCU, groups={len(groups)}, source={src}) ===")
            for gi, g in enumerate(groups):
                gx, gz = g.get('x', 0), g.get('z', 0)
                grids = g.get('grids', [])
                print(f"  Group {gi} (offset x={gx}, z={gz}):")
                for gri, gr in enumerate(grids):
                    w = gr.get('width', 0)
                    h = gr.get('height', 0)
                    l = gr.get('length', 0)
                    x, y, z = gr.get('x', 0), gr.get('y', 0), gr.get('z', 0)
                    print(f"    Grid {gri}: {w}x{h}x{l} (pos: x={x}, y={y}, z={z}) = {w*h*l} slots")
            total = sum(
                gr.get('width',0) * gr.get('height',0) * gr.get('length',0)
                for g in groups for gr in g.get('grids', [])
            )
            print(f"  Total computed: {total} slots (declared: {cap})")
            print()
            break

print(f"\nTotal ships in DB: {len(db)}")
concept = sum(1 for v in db.values() if v.get('_source') == 'concept_only')
print(f"Concept ships: {concept}")
sc_cargo = sum(1 for v in db.values() if v.get('_source') == 'sc-cargo.space')
print(f"SC-Cargo sourced: {sc_cargo}")
