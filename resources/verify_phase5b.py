# Phase 5 continued — functional unit tests (no GUI needed)
import sys, os, json
sys.path.insert(0, 'source')
sys.stdout.reconfigure(encoding='utf-8')

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        result = fn()
        if result is False:
            raise AssertionError("returned False")
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1

# ═══════════════════════════════════════════
print("=" * 60)
print("5.11 — Shuttle Recommendation")
print("=" * 60)

from fleet_helper import _recommend_shuttle, can_shuttle_fit

# Test with Idris (S-pad hangar, known Golem OX fits)
r = _recommend_shuttle("Idris", 50)
print(f"  Idris + 50 SCU → {r}")
test("Idris returns recommendation", lambda: r is not None)
test("Idris recommendation has 'recommended'", lambda: 'recommended' in r if r else False)
test("Idris recommended = Golem OX", lambda: 'golem' in r.get('recommended',{}).get('name','').lower() if r else False)

# Test with Carrack (XS hangar, Pisces fits)
r2 = _recommend_shuttle("Carrack", 10)
print(f"  Carrack + 10 SCU → {r2}")
test("Carrack returns recommendation", lambda: r2 is not None)

# Test can_shuttle_fit
test("can_shuttle_fit: Pisces in Carrack", lambda: can_shuttle_fit("Pisces", "Carrack"))
test("can_shuttle_fit: Caterpillar NOT in Carrack", lambda: not can_shuttle_fit("Caterpillar", "Carrack"))

# ═══════════════════════════════════════════
print()
print("=" * 60)
print("5.12 — Stor-All Boxing")
print("=" * 60)

from storall_packer import pack_items, calculate_cargo_breakdown, STOR_ALL_CATEGORIES, STOR_ALL_SIZES

# Test packing
items = [
    {"name": "P4-AR Rifle", "qty": 5, "price": 850},
    {"name": "Medpen", "qty": 20, "price": 150},
    {"name": "TowBar Tractor Beam", "qty": 2, "price": 5000},
]
result = pack_items(items)
num = result.get('num_boxes', 0) if isinstance(result, dict) else len(result)
print(f"  Packed {len(items)} item types → {num} boxes ({result.get('box_label', '?')})")
test("pack_items returns result", lambda: num > 0)
if isinstance(result, dict):
    print(f"    box_label: {result.get('box_label')}, total_loose_vol: {result.get('total_loose_vol', 0):.3f}")
    for i, bx in enumerate(result.get('boxes', [])[:3]):
        print(f"    Box {i+1}: {bx}")

# Test breakdown
breakdown = calculate_cargo_breakdown(items)
test("breakdown has total_vol", lambda: 'total_vol' in breakdown)
test("breakdown has stor_all_boxes", lambda: 'stor_all_boxes' in breakdown)
print(f"  Breakdown: total={breakdown.get('total_vol',0):.3f} SCU, "
      f"boxes={len(breakdown.get('stor_all_boxes', []))}")

# ═══════════════════════════════════════════
print()
print("=" * 60)
print("5.8 — Auto-battery (slang resolution)")
print("=" * 60)

from slang_helper import resolve_slang

# resolve_slang uses 'self' — it's a monkey-patched method, can't call standalone
# Verify it exists and source has slang entries
test("resolve_slang is callable", lambda: callable(resolve_slang))

# Check slang entries exist in source
content = open('source/slang_helper.py', 'r', encoding='utf-8').read()
slang_count = content.count("\":") 
print(f"  slang_helper.py: ~{slang_count} dict entries")
test("slang_helper has entries", lambda: slang_count > 30)
test("has TowBar slang", lambda: "towbar" in content.lower() or "tow bar" in content.lower())

# ═══════════════════════════════════════════
print()
print("=" * 60)
print("5.10 — Cargo Grid (unit tests)")
print("=" * 60)

from cargo_grid_renderer import load_ship_grid, _compute_grid_dimensions, _assign_blocks_to_slots

# Test load for known ships
for ship in ["Caterpillar", "C2 Hercules", "Hull C", "Carrack"]:
    grid = load_ship_grid(ship)
    if grid:
        cap = grid.get("capacity", "?")
        grps = len(grid.get("groups", []))
        test(f"load_ship_grid('{ship}'): {cap} SCU, {grps} bays", lambda: True)
    else:
        test(f"load_ship_grid('{ship}'): found", lambda: False)

# Test block assignment
cat_grid = load_ship_grid("Caterpillar")
if cat_grid:
    dims = _compute_grid_dimensions(cat_grid)
    breakdown_cat = {
        "ordnance_items": [{"name": "Pioneer I Missile", "qty": 4, "scu_per_unit": 1}],
        "commodity_items": [{"name": "Titanium", "qty": 10, "total_scu": 10}],
        "stor_all_boxes": [{"label": "STOR-ALL #1 [8 SCU] ARMOR", "scu": 8}],
    }
    assignments = _assign_blocks_to_slots(dims, breakdown_cat)
    total_assigned = sum(len(a) for a in assignments)
    test(f"Block assignment: {total_assigned} blocks placed", lambda: total_assigned > 0)
    for gi, ga in enumerate(assignments):
        for blk in ga:
            print(f"    Bay {gi+1}: {blk['label']} ({blk['category']}) → {len(blk['slots'])} slots")

# ═══════════════════════════════════════════
print()
print("=" * 60)
print("UI Panel integrity")
print("=" * 60)

# Check apply_all_patches exists
test("ui_panel.py has apply_all_patches", lambda: 'apply_all_patches' in open('source/ui_panel.py','r',encoding='utf-8').read())

# Check key functions exist in ui_panel
content = open('source/ui_panel.py', 'r', encoding='utf-8').read()
for fn in ['_patched_animate_generate', 'patched_init', 'resolve_slang', 
           'handle_global_paste', 'patched_create_left_panel', '_patched_show_main',
           '_patched_add_new_vessel', '_patched_sec_changed']:
    test(f"  ui_panel has {fn}", lambda f=fn: f'def {f}' in content)

# Check entry.py has apply_all_patches call
entry_content = open('source/entry.py', 'r', encoding='utf-8').read()
test("entry.py calls apply_all_patches", lambda: 'apply_all_patches(main)' in entry_content)
test("entry.py has __main__", lambda: "if __name__ == '__main__'" in entry_content)

# ═══════════════════════════════════════════
print()
print("=" * 60)
total = passed + failed
print(f"TOTAL: {passed}/{total} PASS ({failed} FAIL)")
print("=" * 60)
if failed == 0:
    print(">>> ALL FUNCTIONAL TESTS PASS!")
