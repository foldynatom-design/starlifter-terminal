"""
SC-Cargo.space Grid Data Extractor
Parsuje minifikovaný JS bundle a extrahuje grid data pro všechny lodě.
Výstup: sc_cargo_grids.json (kompletní DB ze SC-Cargo.space)
"""
import re
import json
import sys
import os

def extract_grids(js_path):
    """Extract all ship grid data from SC-Cargo.space JS bundle."""
    
    with open(js_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    print(f"Bundle size: {len(content):,} chars")
    
    # Pattern: manufacturer="...", name="...", data={capacity:N, groups:[...]}
    # In minified JS, ship data appears as:
    #   varX="Manufacturer", varY="ShipName", varZ={capacity:N, groups:[{...}]}
    # Sometimes with "official" variant marker
    
    ships = {}
    
    # Strategy 1: Find all {capacity:NNN,groups:[...]} blocks
    # These are the grid data objects
    capacity_pattern = re.compile(r'\{capacity:(\d+),groups:\[')
    
    for match in capacity_pattern.finditer(content):
        start = match.start()
        cap = int(match.group(1))
        
        # Extract the full JSON-like object by counting braces
        brace_count = 0
        obj_start = start
        obj_end = start
        for i in range(start, min(start + 50000, len(content))):
            c = content[i]
            if c == '{':
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0:
                    obj_end = i + 1
                    break
        
        obj_str = content[obj_start:obj_end]
        
        # Convert JS object notation to JSON
        # Add quotes around keys: capacity: -> "capacity":
        json_str = re.sub(r'(\b)(x|y|z|width|height|length|capacity|groups|grids):', r'"\2":', obj_str)
        
        try:
            grid_data = json.loads(json_str)
        except json.JSONDecodeError:
            # Try harder — some objects have trailing data
            # Find the matching closing bracket for groups array
            try:
                # Minimal fix: ensure all keys are quoted
                json_str2 = re.sub(r'([{,])(\w+):', r'\1"\2":', obj_str)
                grid_data = json.loads(json_str2)
            except:
                continue
        
        # Look backwards for manufacturer and name
        # Pattern: varX="ManufacturerName", varY="ShipName", varZ={capacity:...}
        lookback = content[max(0, start-500):start]
        
        # Find the last two quoted strings before this object
        strings = re.findall(r'"([^"]{2,50})"', lookback)
        
        if len(strings) >= 2:
            manufacturer = strings[-2]
            name = strings[-1]
        elif len(strings) == 1:
            manufacturer = "Unknown"
            name = strings[-1]
        else:
            manufacturer = "Unknown"
            name = f"Ship_{cap}SCU"
        
        # Skip if name looks like a JS keyword/variable
        skip_names = {"Module", "value", "default", "module", "exports", "undefined",
                      "function", "object", "string", "number", "boolean"}
        if name in skip_names or manufacturer in skip_names:
            # Try alternative: look for ="Name" pattern
            alt_names = re.findall(r'="([A-Z][a-zA-Z0-9\- ]+)"', lookback)
            if len(alt_names) >= 2:
                manufacturer = alt_names[-2]
                name = alt_names[-1]
            elif len(alt_names) == 1:
                name = alt_names[-1]
            else:
                continue
        
        # Build ship key
        ship_key = f"{manufacturer} {name}" if manufacturer != "Unknown" else name
        
        # Validate grid data
        total_cells = 0
        for group in grid_data.get("groups", []):
            for grid in group.get("grids", []):
                w = grid.get("width", 0)
                h = grid.get("height", 0)
                l = grid.get("length", 0)
                total_cells += w * h * l
        
        if total_cells == 0:
            continue
        
        # Check for duplicates — keep the one with more groups (more detailed)
        if ship_key in ships:
            existing_groups = len(ships[ship_key].get("groups", []))
            new_groups = len(grid_data.get("groups", []))
            if new_groups <= existing_groups:
                continue
        
        ships[ship_key] = {
            "manufacturer": manufacturer,
            "name": name,
            "capacity": cap,
            "groups": grid_data["groups"],
            "_source": "sc-cargo.space",
            "_total_cells": total_cells,
            "_groups_count": len(grid_data.get("groups", [])),
        }
    
    return ships


def merge_with_existing(sc_cargo_ships, existing_db_path):
    """Merge SC-Cargo data with existing ship_grids_db.json."""
    
    with open(existing_db_path, "r", encoding="utf-8") as f:
        existing = json.load(f)
    
    stats = {"updated": 0, "added": 0, "kept": 0, "auto_replaced": 0}
    
    # Build lookup by normalized name
    sc_lookup = {}
    for key, val in sc_cargo_ships.items():
        # Normalize: "Aegis Idris-M" -> "idris-m", "Drake Caterpillar" -> "caterpillar"
        name_low = val["name"].lower().strip()
        full_low = key.lower().strip()
        sc_lookup[name_low] = (key, val)
        sc_lookup[full_low] = (key, val)
    
    merged = {}
    
    for key, val in existing.items():
        key_low = key.lower().strip()
        name_low = val.get("name", "").lower().strip()
        
        # Check if SC-Cargo has better data
        sc_match = sc_lookup.get(key_low) or sc_lookup.get(name_low)
        
        if not sc_match:
            # Try partial match
            for sc_name, sc_data in sc_lookup.items():
                if sc_name in key_low or key_low in sc_name:
                    sc_match = sc_data
                    break
        
        if sc_match:
            sc_key, sc_val = sc_match
            existing_auto = val.get("_auto_generated", False)
            existing_groups = len(val.get("groups", []))
            sc_groups = sc_val.get("_groups_count", 0)
            
            if existing_auto or sc_groups > existing_groups:
                # Replace with SC-Cargo data (better detail)
                merged[key] = {
                    "manufacturer": sc_val["manufacturer"],
                    "name": val.get("name", sc_val["name"]),
                    "capacity": sc_val["capacity"],
                    "groups": sc_val["groups"],
                    "_source": "sc-cargo.space",
                }
                if existing_auto:
                    stats["auto_replaced"] += 1
                else:
                    stats["updated"] += 1
            else:
                merged[key] = val
                stats["kept"] += 1
        else:
            merged[key] = val
            stats["kept"] += 1
    
    # Add new ships from SC-Cargo that aren't in existing DB
    for key, val in sc_cargo_ships.items():
        key_low = key.lower()
        found = False
        for mk in merged:
            if mk.lower() == key_low or val["name"].lower() in mk.lower():
                found = True
                break
        if not found:
            merged[key] = {
                "manufacturer": val["manufacturer"],
                "name": val["name"],
                "capacity": val["capacity"],
                "groups": val["groups"],
                "_source": "sc-cargo.space",
            }
            stats["added"] += 1
    
    return merged, stats


if __name__ == "__main__":
    resources_dir = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(resources_dir, "sc_cargo_bundle.js")
    db_path = os.path.join(resources_dir, "ship_grids_db.json")
    
    if not os.path.exists(js_path):
        print(f"ERROR: {js_path} not found. Download first.")
        sys.exit(1)
    
    print("=== SC-Cargo.space Grid Extractor ===")
    print(f"Bundle: {js_path}")
    
    # Step 1: Extract from JS bundle
    ships = extract_grids(js_path)
    print(f"\nExtracted {len(ships)} ships from SC-Cargo bundle:")
    for key, val in sorted(ships.items()):
        print(f"  {key}: {val['capacity']} SCU, {val['_groups_count']} groups, {val['_total_cells']} cells")
    
    # Step 2: Save raw SC-Cargo data
    raw_path = os.path.join(resources_dir, "sc_cargo_grids_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(ships, f, indent=2, ensure_ascii=False)
    print(f"\nRaw data saved: {raw_path}")
    
    # Step 3: Merge with existing DB
    if os.path.exists(db_path):
        merged, stats = merge_with_existing(ships, db_path)
        print(f"\nMerge results:")
        print(f"  Auto-generated replaced: {stats['auto_replaced']}")
        print(f"  Updated (better data):   {stats['updated']}")
        print(f"  Added (new ships):       {stats['added']}")
        print(f"  Kept (existing better):  {stats['kept']}")
        print(f"  Total ships in DB:       {len(merged)}")
        
        # Backup and save
        backup_path = db_path + ".backup"
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"  Backup: {backup_path}")
        
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        print(f"  Updated DB: {db_path}")
    else:
        print(f"No existing DB at {db_path}, saving SC-Cargo data as new DB")
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(ships, f, indent=2, ensure_ascii=False)
