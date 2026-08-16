# -*- coding: utf-8 -*-
"""
generate_ship_dimensions.py — Generates resources/ship_dimensions.json
from uex_ships_db.json so that hangar fit checks and dimension lookups work 100%.
"""
import json, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

def generate_ship_dimensions():
    uex_p = os.path.join(RES_DIR, "uex_ships_db.json")
    if not os.path.isfile(uex_p):
        print("[ERR] uex_ships_db.json not found")
        return {}

    with open(uex_p, "r", encoding="utf-8") as f:
        ships_data = json.load(f)

    ship_list = ships_data if isinstance(ships_data, list) else list(ships_data.values())
    dims_map = {}

    for s in ship_list:
        if not isinstance(s, dict): continue
        s_name = s.get("name") or s.get("model", "")
        if not s_name: continue

        l = float(s.get("length", 0) or 0)
        w = float(s.get("beam", s.get("width", 0)) or 0)
        h = float(s.get("height", 0) or 0)

        if l > 0:
            dims = {
                "length": round(l, 1),
                "width": round(w, 1),
                "height": round(h, 1),
                "pad_size": s.get("pad_size", "L")
            }
            dims_map[s_name.lower().strip()] = dims
            if s.get("model"):
                dims_map[s["model"].lower().strip()] = dims

    out_p = os.path.join(RES_DIR, "ship_dimensions.json")
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(dims_map, f, indent=2, ensure_ascii=False)

    print(f"[OK] Generated resources/ship_dimensions.json with {len(dims_map)} ship dimension entries!")
    return dims_map

if __name__ == "__main__":
    generate_ship_dimensions()
