# -*- coding: utf-8 -*-
"""
sc_cargo_ships_scraper.py — Scraper and sync engine for sc-cargo.space
Extracts 100% of all Star Citizen ships, official & unofficial cargo capacities (SCU),
and 3D cargo grid layouts (dimensions, bay sections, coordinates).
"""
import urllib.request, re, json, os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

def fetch_sccargo_bundle():
    main_url = "https://sc-cargo.space/"
    req = urllib.request.Request(main_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        scripts = re.findall(r'<script\b[^>]*src=["\']([^"\']+)["\']', html)
        bundle_path = None
        for s in scripts:
            if "index-" in s and s.endswith(".js"):
                bundle_path = s
                break
        if not bundle_path:
            bundle_path = "/assets/index-0zev2lBh.js" # fallback
            
        bundle_url = urllib.parse.urljoin(main_url, bundle_path)
        print(f"[SC_CARGO] Fetching app bundle from {bundle_url}...", flush=True)
        
        b_req = urllib.request.Request(bundle_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(b_req, timeout=15) as b_resp:
            return b_resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"[SC_CARGO] Error fetching bundle: {e}", flush=True)
        return ""

def parse_cargo_ships(js):
    if not js:
        return []

    # 1. String mapping
    str_map = {}
    for m in re.finditer(r'\b([a-zA-Z0-9_$]+)\s*=\s*(?:"([^"]+)"|\'([^\']+)\')', js):
        var_name = m.group(1)
        val = m.group(2) if m.group(2) is not None else m.group(3)
        str_map[var_name] = val

    # 2. Object definitions (capacity & groups)
    obj_map = {}
    for m in re.finditer(r'\b([a-zA-Z0-9_$]+)\s*=\s*(\{capacity:\s*(\d+)\s*,\s*groups:\s*\[.*?\](?:,\s*labels:\s*\[.*?\])?\s*\})', js):
        var_name = m.group(1)
        raw_obj = m.group(2)
        cap = int(m.group(3))
        
        # Extract labels: e.g. labels:[{value:"Pod 1", ...}, {value:"Cargo Hold", ...}]
        labels = []
        l_match = re.search(r'labels:\s*\[(.*?)\]', raw_obj)
        if l_match:
            for lbl_m in re.finditer(r'\{[^{}]*value\s*:\s*(?:"([^"]+)"|\'([^\']+)\')[^{}]*\}', l_match.group(1)):
                lbl_v = lbl_m.group(1) if lbl_m.group(1) is not None else lbl_m.group(2)
                if lbl_v and "${" not in lbl_v:
                    labels.append(lbl_v)

        groups = []
        for g_match in re.finditer(r'\{[^{}]*x\s*:\s*(-?\d+)\s*,\s*z\s*:\s*(-?\d+)\s*,\s*grids\s*:\s*\[(.*?)\]\s*\}', raw_obj):
            gx = int(g_match.group(1))
            gz = int(g_match.group(2))
            raw_grids = g_match.group(3)
            grids = []
            for grid_m in re.finditer(r'\{[^{}]*width\s*:\s*(\d+)\s*,\s*height\s*:\s*(\d+)\s*,\s*length\s*:\s*(\d+)[^{}]*\}', raw_grids):
                gw = int(grid_m.group(1))
                gh = int(grid_m.group(2))
                gl = int(grid_m.group(3))
                
                x_m = re.search(r'\bx\s*:\s*(-?\d+)', grid_m.group(0))
                y_m = re.search(r'\by\s*:\s*(-?\d+)', grid_m.group(0))
                z_m = re.search(r'\bz\s*:\s*(-?\d+)', grid_m.group(0))
                grid_x = int(x_m.group(1)) if x_m else 0
                grid_y = int(y_m.group(1)) if y_m else 0
                grid_z = int(z_m.group(1)) if z_m else 0
                
                max_s_m = re.search(r'\bmaxSize\s*:\s*(\d+)', grid_m.group(0))
                max_size = int(max_s_m.group(1)) if max_s_m else None

                unsec = "unsecured" in grid_m.group(0)

                name_m = re.search(r'\bname\s*:\s*["\']([^"\']+)["\']', grid_m.group(0))
                g_name = name_m.group(1) if name_m else "Cargo Grid"

                grids.append({
                    "name": g_name,
                    "x": grid_x, "y": grid_y, "z": grid_z,
                    "width": gw, "height": gh, "length": gl,
                    "volume_scu": gw * gh * gl,
                    "max_box_size": max_size,
                    "unsecured": unsec
                })
            groups.append({
                "x": gx, "z": gz,
                "grids": grids
            })
        
        obj_map[var_name] = {
            "capacity": cap,
            "groups": groups,
            "labels": labels
        }

    # 3. Ship definition regex matching
    ships = []
    seen = set()

    for m in re.finditer(r'\{\s*manufacturer\s*:\s*([a-zA-Z0-9_$]+)\s*,\s*name\s*:\s*([a-zA-Z0-9_$]+)\s*,\s*official\s*:\s*([a-zA-Z0-9_$]+)(?:,\s*unofficial\s*:\s*([a-zA-Z0-9_$]+))?', js):
        m_var = m.group(1)
        n_var = m.group(2)
        o_var = m.group(3)
        u_var = m.group(4)
        
        man = str_map.get(m_var, m_var)
        sname = str_map.get(n_var, n_var)
        grid_obj = obj_map.get(o_var, {"capacity": 0, "groups": [], "labels": []})
        unoff_obj = obj_map.get(u_var, None) if u_var else None
        
        full_name = f"{man} {sname}" if (man and not sname.lower().startswith(man.lower())) else sname
        
        ship_key = full_name.lower().strip()
        if ship_key not in seen:
            seen.add(ship_key)
            ships.append({
                "name": sname,
                "full_name": full_name,
                "manufacturer": man,
                "cargo_scu": grid_obj["capacity"],
                "unofficial_cargo_scu": unoff_obj["capacity"] if unoff_obj else grid_obj["capacity"],
                "bay_labels": grid_obj.get("labels", []),
                "grid_layout": grid_obj["groups"]
            })

    ships.sort(key=lambda x: x["full_name"].lower())
    return ships

def run_sccargo_sync():
    print("=" * 70, flush=True)
    print("=== EXECUTING SC-CARGO (SC-CARGO.SPACE) SHIPS & GRIDS SYNC ===", flush=True)
    print("=" * 70, flush=True)

    js_bundle = fetch_sccargo_bundle()
    if not js_bundle:
        print("[ERR] Could not fetch sc-cargo.space bundle.", flush=True)
        return False

    ships = parse_cargo_ships(js_bundle)
    print(f"[SC_CARGO] Parsed {len(ships)} Star Citizen ships with 3D cargo grid layouts!", flush=True)

    # 1. Save sc_cargo_ships_db.json
    out_path = os.path.join(RES_DIR, "sc_cargo_ships_db.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ships, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved -> {out_path} ({len(ships)} ships)", flush=True)

    # 2. Update uex_ships_db.json
    uex_ships_path = os.path.join(RES_DIR, "uex_ships_db.json")
    try:
        with open(uex_ships_path, "r", encoding="utf-8") as f:
            uex_ships = json.load(f)
    except Exception:
        uex_ships = []

    uex_map = {}
    if isinstance(uex_ships, list):
        for s in uex_ships:
            if isinstance(s, dict) and s.get("name"):
                uex_map[s["name"].lower().strip()] = s
    elif isinstance(uex_ships, dict):
        uex_map = {k.lower().strip(): v for k, v in uex_ships.items()}

    for s in ships:
        k_low = s["full_name"].lower().strip()
        k_short = s["name"].lower().strip()
        
        entry = uex_map.get(k_low) or uex_map.get(k_short) or {}
        entry["name"] = s["full_name"]
        entry["model"] = s["name"]
        entry["manufacturer"] = s["manufacturer"]
        entry["scu"] = s["cargo_scu"]
        entry["cargo_capacity"] = s["cargo_scu"]
        entry["grid_layout"] = s["grid_layout"]
        entry["bay_labels"] = s.get("bay_labels", [])
        
        uex_map[k_low] = entry

    with open(uex_ships_path, "w", encoding="utf-8") as f:
        json.dump(list(uex_map.values()) if isinstance(uex_ships, list) else uex_map, f, indent=2, ensure_ascii=False)
    print(f"[OK] Updated uex_ships_db.json with sc-cargo 3D grid layouts ({len(uex_map)} ships)", flush=True)

    # 3. Update cargo_bay_dimensions.json with bounding boxes from 3D grids
    bay_dims_path = os.path.join(RES_DIR, "cargo_bay_dimensions.json")
    try:
        with open(bay_dims_path, "r", encoding="utf-8") as f:
            bay_dims = json.load(f)
    except Exception:
        bay_dims = {}

    for s in ships:
        max_w, max_h, max_l = 0, 0, 0
        for grp in s.get("grid_layout", []):
            for g in grp.get("grids", []):
                max_w = max(max_w, g.get("width", 0) * 1.25)
                max_h = max(max_h, g.get("height", 0) * 1.25)
                max_l = max(max_l, g.get("length", 0) * 1.25)
        
        if max_l > 0 and max_w > 0:
            k_low = s["name"].lower().strip()
            if k_low not in bay_dims:
                bay_dims[k_low] = {
                    "length": round(max_l, 1),
                    "width": round(max_w, 1),
                    "height": round(max_h, 1),
                    "access": "ramp"
                }

    with open(bay_dims_path, "w", encoding="utf-8") as f:
        json.dump(bay_dims, f, indent=2, ensure_ascii=False)
    print(f"[OK] Synchronized cargo_bay_dimensions.json ({len(bay_dims)} bays)", flush=True)

    print("=" * 70, flush=True)
    print("=== SC-CARGO SHIPS & GRIDS SYNC COMPLETED SUCCESSFULLY ===", flush=True)
    print("=" * 70, flush=True)
    return True

if __name__ == "__main__":
    run_sccargo_sync()
