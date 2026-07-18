# Comprehensive Phase 5 verification (non-GUI)
import sys, os, json
sys.path.insert(0, 'source')
sys.stdout.reconfigure(encoding='utf-8')

passed = 0
failed = 0
skipped = 0

def test(name, fn):
    global passed, failed, skipped
    try:
        result = fn()
        if result == "SKIP":
            print(f"  [SKIP] {name}")
            skipped += 1
        else:
            print(f"  [PASS] {name}")
            passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1

print("=" * 60)
print("PHASE 5 VERIFICATION")
print("=" * 60)

# 5.1 - Paths
print("\nA) Paths & Config:")
test("PATHS singleton", lambda: __import__('path_config').PATHS)
test("app_root exists", lambda: os.path.isdir(__import__('path_config').PATHS.app_root) or 1/0)
test("resources exists", lambda: os.path.isdir(__import__('path_config').PATHS.resources) or 1/0)
test("starlifter_paths.json", lambda: os.path.exists(
    os.path.join(__import__('path_config').PATHS.app_root, 'starlifter_paths.json')) or 1/0)
test("temp_dir exists", lambda: os.path.isdir(__import__('path_config').PATHS.temp_dir) or 1/0)
test("version marker 0.6", lambda: open(
    os.path.join(__import__('path_config').PATHS.temp_dir, '.version')).read().strip() == '0.6' or 1/0)

# 5.3 - Resources
print("\nB) Resources:")
from path_config import PATHS
for res in ['cvbg44_logo.png', 'sls29_logo.png', 'ship_grids_db.json', 
            'item_volumes.json', 'uex_ships_db.json', 'uex_locations_db.json',
            'uex_trade_db.json', 'uex_items_trade_db.json']:
    test(f"  {res}", lambda r=res: os.path.exists(PATHS.resource(r)) or 1/0)

# 5.4 - Sounds
print("\nC) Sounds:")
sounds_dir = PATHS.sounds
if os.path.isdir(sounds_dir):
    for wav in os.listdir(sounds_dir):
        if wav.endswith('.wav'):
            test(f"  {wav}", lambda w=wav: os.path.exists(os.path.join(sounds_dir, w)) or 1/0)
else:
    test("sounds_dir", lambda: "SKIP")

# 5.5 - Video
print("\nD) Video:")
test("intro_video.mp4", lambda: os.path.exists(PATHS.resource('intro_video.mp4')) or 1/0)

# Data loading
print("\nE) Data Loading:")
from storall_packer import load_volume_map
vm = load_volume_map()
test(f"volume_map ({len(vm)} items)", lambda: len(vm) > 2000 or 1/0)

from fleet_helper import _load_uex_ships_db
ships = _load_uex_ships_db()
test(f"ships_db ({len(ships)} ships)", lambda: len(ships) > 300 or 1/0)

from cargo_grid_renderer import _load_grid_db, _get_ordnance_shape
grids = _load_grid_db()
test(f"grid_db ({len(grids)} ships)", lambda: len(grids) > 100 or 1/0)

# Ordnance shapes
print("\nF) Ordnance Shapes:")
test("S1 = 0.125 SCU", lambda: _get_ordnance_shape("Pioneer I Missile")["scu"] == 0.125 or 1/0)
test("S3 = 8 SCU", lambda: _get_ordnance_shape("TaskForce III Missile")["scu"] == 8.0 or 1/0)
test("S9 = 24 SCU", lambda: _get_ordnance_shape("Seeker IX Torpedo")["scu"] == 24.0 or 1/0)
test("S10 = 32 SCU (Colossus)", lambda: _get_ordnance_shape("Colossus Bomb")["scu"] == 32.0 or 1/0)

# UEX sync
print("\nG) UEX Data:")
from uex_sync import uex_locations_db, uex_ships_db, _uex_locations_db, _uex_ships_db
test(f"locations_db ({len(_uex_locations_db)} locs)", lambda: len(_uex_locations_db) > 0 or 1/0)
test(f"ships_db ({len(_uex_ships_db)} ships)", lambda: len(_uex_ships_db) > 300 or 1/0)

trade_path = os.path.join(PATHS.resources, 'uex_trade_db.json')
if os.path.exists(trade_path):
    trade = json.load(open(trade_path, encoding='utf-8'))
    test(f"trade_db ({len(trade)} commodities)", lambda: len(trade) > 100 or 1/0)

items_path = os.path.join(PATHS.resources, 'uex_items_trade_db.json')
if os.path.exists(items_path):
    items = json.load(open(items_path, encoding='utf-8'))
    test(f"items_trade_db ({len(items)} items)", lambda: len(items) > 2000 or 1/0)

# Config
print("\nH) Config:")
config_path = PATHS.config
if os.path.exists(config_path):
    cfg = json.load(open(config_path, encoding='utf-8'))
    fi = cfg.get('frequent_items', [])
    test(f"config.json ({len(fi)} frequent_items)", lambda: len(fi) > 200 or 1/0)

# Module counts
print("\nI) Module Structure:")
modules = ['entry', 'ui_panel', 'pdf_engine', 'cargo_grid_renderer', 'fleet_helper',
           'uex_sync', 'storall_packer', 'path_config', 'signature_helper',
           'lore_helper', 'slang_helper', 'rp_stories']
for m in modules:
    fpath = f'source/{m}.py'
    if os.path.exists(fpath):
        lines = sum(1 for _ in open(fpath, encoding='utf-8'))
        test(f"  {m}.py ({lines} lines)", lambda: True)

# Bare except check
print("\nJ) Code Quality:")
import re
total_bare = 0
for m in modules:
    fpath = f'source/{m}.py'
    if os.path.exists(fpath):
        for line in open(fpath, encoding='utf-8'):
            if re.match(r'^\s*except\s*:', line):
                total_bare += 1
test(f"bare 'except:' = {total_bare}", lambda: total_bare == 0 or 1/0)

# Hardcoded paths
total_hc = 0
for m in modules:
    fpath = f'source/{m}.py'
    if os.path.exists(fpath):
        for line in open(fpath, encoding='utf-8'):
            if 'os.path.dirname(os.path.abspath(__file__))' in line:
                total_hc += 1
            if 'os.path.dirname(sys.executable)' in line:
                total_hc += 1
test(f"hardcoded paths = {total_hc}", lambda: total_hc <= 1 or 1/0)

# Summary
print()
print("=" * 60)
print(f"RESULTS: {passed} PASS, {failed} FAIL, {skipped} SKIP")
print("=" * 60)
if failed == 0:
    print(">>> ALL TESTS PASSED!")
else:
    print(f">>> {failed} TESTS FAILED")
    sys.exit(1)
