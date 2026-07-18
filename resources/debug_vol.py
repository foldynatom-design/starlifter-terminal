import sys, os, json
sys.path.insert(0, 'ai/test')
from path_config import PATHS

vf = PATHS.resource('item_volumes.json')
print(f"Path: {vf}")
print(f"Exists: {os.path.exists(vf)}")

d = json.load(open(vf, 'r', encoding='utf-8'))
print(f"Type: {type(d)}, Len: {len(d)}")
if isinstance(d, list):
    print(f"First item: {d[0]}")
elif isinstance(d, dict):
    print(f"Sample keys: {list(d.keys())[:5]}")

from storall_packer import load_volume_map
vm = load_volume_map()
print(f"\nload_volume_map() returned: type={type(vm)}, len={len(vm)}")
print(f"Sample: {list(vm.items())[:5]}")
