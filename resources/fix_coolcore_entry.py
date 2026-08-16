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

    pb_terms = [
        {"terminal": "Platinum Bay - Seraphim Station", "price": 195000, "location": "Seraphim Station", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Platinum Bay - Everus Harbor", "price": 195000, "location": "Everus Harbor", "parent": "Hurston", "system": "Stanton"},
        {"terminal": "Platinum Bay - Port Tressler", "price": 195000, "location": "Port Tressler", "parent": "microTech", "system": "Stanton"},
        {"terminal": "Platinum Bay - Baijini Point", "price": 195000, "location": "Baijini Point", "parent": "ArcCorp", "system": "Stanton"},
        {"terminal": "Cousin Crow's - Orison", "price": 195000, "location": "Orison", "parent": "Crusader", "system": "Stanton"},
        {"terminal": "Dumper's Depot - Area18", "price": 195000, "location": "Area18", "parent": "ArcCorp", "system": "Stanton"},
    ]

    for k in ["CoolCore Cooler (Size 3)", "coolcore cooler (size 3)", "CoolCore", "coolcore", "Coolcore Cooler (Size 3)"]:
        w[k] = list(pb_terms)
        u[k.lower()] = {
            "name": "CoolCore Cooler (Size 3)",
            "locations": [{"terminal": t["terminal"], "buy": 195000, "sell": 0} for t in pb_terms]
        }

    with open(w_path, "w", encoding="utf-8") as f:
        json.dump(w, f, indent=2, ensure_ascii=False)

    with open(u_path, "w", encoding="utf-8") as f:
        json.dump(u, f, indent=2, ensure_ascii=False)

    print("[OK] CoolCore Cooler (Size 3) properly mapped to Platinum Bay!")

if __name__ == "__main__":
    main()
