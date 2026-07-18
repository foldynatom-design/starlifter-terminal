# -*- coding: utf-8 -*-
"""Test all module imports (skipping PIL-dependent ones if Pillow not installed)."""
import sys
sys.path.insert(0, 'source')

results = []

def test(name, fn):
    try:
        fn()
        results.append((name, "OK"))
    except ModuleNotFoundError as e:
        if 'PIL' in str(e) or 'cv2' in str(e) or 'customtkinter' in str(e) or 'fpdf' in str(e) or 'main' in str(e):
            results.append((name, f"SKIP (missing: {e.name})"))
        else:
            results.append((name, f"FAIL: {e}"))
    except Exception as e:
        results.append((name, f"FAIL: {e}"))

test("path_config", lambda: __import__('path_config'))
test("lore_helper", lambda: __import__('lore_helper'))
test("slang_helper", lambda: __import__('slang_helper'))
test("storall_packer", lambda: __import__('storall_packer'))
test("fleet_helper", lambda: __import__('fleet_helper'))
test("cargo_grid_renderer", lambda: __import__('cargo_grid_renderer'))
test("uex_sync", lambda: __import__('uex_sync'))
test("rp_stories", lambda: __import__('rp_stories'))
test("signature_helper", lambda: __import__('signature_helper'))
test("pdf_engine", lambda: __import__('pdf_engine'))

# Test PATHS data loading
from path_config import PATHS
from storall_packer import load_volume_map
from fleet_helper import _load_uex_ships_db
from cargo_grid_renderer import _load_grid_db

vm = load_volume_map()
ships = _load_uex_ships_db()
grids = _load_grid_db()

print("=" * 60)
print("MODULE IMPORT RESULTS")
print("=" * 60)
for name, status in results:
    icon = "[OK]" if status == "OK" else "[SKIP]" if "SKIP" in status else "[FAIL]"
    print(f"  {icon} {name:25s} {status}")

print()
print("DATA LOADING RESULTS")
print("=" * 60)
print(f"  PATHS.app_root:     {PATHS.app_root}")
print(f"  PATHS.resources:    {PATHS.resources}")
print(f"  volume_map:         {len(vm)} items")
print(f"  ships_db:           {len(ships)} ships")
print(f"  grid_db:            {len(grids)} ships")

import os
paths_json = os.path.join(PATHS.app_root, "starlifter_paths.json")
print(f"  paths.json exists:  {os.path.exists(paths_json)}")
print(f"  temp_dir exists:    {os.path.isdir(PATHS.temp_dir)}")
ver_file = os.path.join(PATHS.temp_dir, ".version")
if os.path.exists(ver_file):
    print(f"  version marker:     {open(ver_file).read().strip()}")

ok = sum(1 for _, s in results if s == "OK")
skip = sum(1 for _, s in results if "SKIP" in s)
fail = sum(1 for _, s in results if "FAIL" in s)
print()
print(f"SUMMARY: {ok} OK, {skip} SKIP (missing deps), {fail} FAIL")
if fail == 0:
    print(">>> ALL CORE MODULES PASS!")
else:
    print(">>> SOME MODULES FAILED")
    sys.exit(1)
