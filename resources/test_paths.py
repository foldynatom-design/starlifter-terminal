import sys, os
sys.path.insert(0, 'source')
from path_config import PATHS

# Test cleanup_temp
PATHS.cleanup_temp('0.6')

vf = os.path.join(PATHS.temp_dir, '.version')
print(f"Temp dir exists: {os.path.isdir(PATHS.temp_dir)}")
if os.path.exists(vf):
    print(f"Version marker: {open(vf).read().strip()}")
else:
    print("Version marker: MISSING")

# Test temp_file
tf = PATHS.temp_file("test_sig_flat.png")
print(f"Temp file path: {tf}")

# Test resource()
logo = PATHS.resource("logo.png")
print(f"Logo: {logo} (exists: {os.path.exists(logo)})")
cfg = PATHS.resource("config.json")
print(f"Config: {cfg} (exists: {os.path.exists(cfg)})")
grids = PATHS.resource("ship_grids_db.json")
print(f"Grids: {grids} (exists: {os.path.exists(grids)})")

print("\nAll OK!")
