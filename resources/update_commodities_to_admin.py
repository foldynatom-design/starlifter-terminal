import json, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

def main():
    w_path = os.path.join(RES_DIR, "sc_wiki_items_cache.json")
    u_path = os.path.join(RES_DIR, "uex_items_trade_db.json")

    with open(w_path, "r", encoding="utf-8") as f:
        w = json.load(f)
    with open(u_path, "r", encoding="utf-8") as f:
        u = json.load(f)

    admin_terms = [
        {"terminal": "Admin Center - Seraphim Station", "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Admin Center - Port Tressler", "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Admin Center - Everus Harbor", "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Admin Center - Baijini Point", "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Admin Center - Grim HEX", "location": "Grim HEX", "parent": "Crusader", "system": "Stanton"},
    ]

    target_items = {
        "Hydrogen Fuel": 200,
        "Quantum Fuel": 950,
        "Decoy Countermeasures": 150,
        "Noise Countermeasures": 300,
    }

    for item_name, def_price in target_items.items():
        keys = [item_name, item_name.lower()]
        entries = []
        for t in admin_terms:
            entries.append({
                "terminal": t["terminal"],
                "price": def_price,
                "location": t["location"],
                "parent": t["parent"],
                "system": t["system"]
            })
        for k in keys:
            w[k] = list(entries)
            u[k.lower()] = {
                "name": item_name,
                "locations": [{"terminal": t["terminal"], "buy": def_price, "sell": 0} for t in admin_terms]
            }

    with open(w_path, "w", encoding="utf-8") as f:
        json.dump(w, f, indent=2, ensure_ascii=False)
    with open(u_path, "w", encoding="utf-8") as f:
        json.dump(u, f, indent=2, ensure_ascii=False)

    print("[OK] Fuel and Countermeasures synchronized to Admin Center!")

if __name__ == "__main__":
    main()
