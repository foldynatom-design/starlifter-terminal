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

    # 1. Base / Standard Aril (Blue/Grey) -> Sold at Providence Surplus (Orison), Tammany & Sons (Lorville), Shubin (New Babbage)
    base_aril_locs = [
        {"terminal": "Providence Surplus", "location": "Orison", "parent": "Crusader", "system": "Stanton", "price": 3000},
        {"terminal": "Tammany and Sons - Lorville", "location": "Lorville", "parent": "Hurston", "system": "Stanton", "price": 3000},
        {"terminal": "Shubin Interstellar - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton", "price": 3000},
    ]

    # 2. Hazard Aril (Yellow/Black) -> Sold at Refinery Shops (HUR-L1, CRU-L1, ARC-L1, MIC-L1, MIC-L2) and Shubin
    hazard_aril_locs = [
        {"terminal": "Refinery Shop - CRU-L1", "location": "CRU-L1", "parent": "Crusader", "system": "Stanton", "price": 3200},
        {"terminal": "Refinery Shop - HUR-L1", "location": "HUR-L1", "parent": "Hurston", "system": "Stanton", "price": 3200},
        {"terminal": "Refinery Shop - ARC-L1", "location": "ARC-L1", "parent": "ArcCorp", "system": "Stanton", "price": 3200},
        {"terminal": "Refinery Shop - MIC-L1", "location": "MIC-L1", "parent": "microTech", "system": "Stanton", "price": 3200},
        {"terminal": "Refinery Shop - MIC-L2", "location": "MIC-L2", "parent": "microTech", "system": "Stanton", "price": 3200},
        {"terminal": "Shubin Interstellar - New Babbage", "location": "New Babbage", "parent": "microTech", "system": "Stanton", "price": 3200},
    ]

    parts_prices = {
        "Helmet": 2924,
        "Core": 5168,
        "Arms": 923,
        "Legs": 1790,
        "Backpack": 1900,
    }

    for p, price in parts_prices.items():
        # Standard
        std_name = f"Aril {p}"
        std_entries = []
        for l in base_aril_locs:
            e = dict(l)
            e["price"] = price
            std_entries.append(e)
        w[std_name] = std_entries
        w[std_name.lower()] = std_entries
        u[std_name.lower()] = {
            "name": std_name,
            "locations": [{"terminal": e["terminal"], "buy": price, "sell": 0} for e in std_entries]
        }

        # Hazard
        haz_name = f"Aril {p} Hazard"
        haz_entries = []
        for l in hazard_aril_locs:
            e = dict(l)
            e["price"] = price
            haz_entries.append(e)
        w[haz_name] = haz_entries
        w[haz_name.lower()] = haz_entries
        u[haz_name.lower()] = {
            "name": haz_name,
            "locations": [{"terminal": e["terminal"], "buy": price, "sell": 0} for e in haz_entries]
        }

    with open(w_path, "w", encoding="utf-8") as f:
        json.dump(w, f, indent=2, ensure_ascii=False)
    with open(u_path, "w", encoding="utf-8") as f:
        json.dump(u, f, indent=2, ensure_ascii=False)

    print("[OK] Aril Base (Providence Surplus) and Aril Hazard (Refinery Shops) synchronized accurately!")

if __name__ == "__main__":
    main()
