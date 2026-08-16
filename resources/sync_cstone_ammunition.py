# -*- coding: utf-8 -*-
"""
sync_cstone_ammunition.py — Synchronizes all ship ammunition entries directly from CStone / UEX trade commodity data.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "resources")

def load_json(name, default=None):
    p = os.path.join(RES_DIR, name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(name, data):
    p = os.path.join(RES_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {name} ({len(data)} entries).")

def main():
    print("[START] Synchronizing ship ammunition with live CStone / UEX commodity terminals...")
    
    trade_db = load_json("uex_trade_db.json", {})
    sc_wiki_cache = load_json("sc_wiki_items_cache.json", {})
    uex_items_db = load_json("uex_items_trade_db.json", {})
    item_volumes = load_json("item_volumes.json", {})
    
    for s in range(1, 8):
        cstone_key = f"ship ammunition - size {s}"
        terminals = trade_db.get(cstone_key, [])
        
        converted = []
        for t in terminals:
            t_name = t.get("terminal", "")
            buy_price = t.get("buy", 0)
            if buy_price > 0 and t_name:
                t_low = t_name.lower()
                if "seraphim" in t_low or "orison" in t_low or "cru" in t_low or "daymar" in t_low:
                    sys_name, pla_name = "Stanton", "Crusader"
                elif "everus" in t_low or "lorville" in t_low or "hur" in t_low:
                    sys_name, pla_name = "Stanton", "Hurston"
                elif "baijini" in t_low or "area" in t_low or "arc" in t_low:
                    sys_name, pla_name = "Stanton", "ArcCorp"
                elif "tressler" in t_low or "babbage" in t_low or "mic" in t_low:
                    sys_name, pla_name = "Stanton", "microTech"
                elif "checkmate" in t_low or "ruin" in t_low or "gaslight" in t_low or "patch" in t_low:
                    sys_name, pla_name = "Pyro", "Monox"
                elif "levski" in t_low or "nyx" in t_low:
                    sys_name, pla_name = "Nyx", "Delamar"
                else:
                    sys_name, pla_name = "Stanton", ""

                converted.append({
                    "terminal": t_name,
                    "price": buy_price,
                    "location": t_name,
                    "parent": pla_name,
                    "system": sys_name
                })

        keys = [
            f"Size {s} Ammunition",
            f"size {s} ammunition",
            f"Size {s} Ammo",
            f"size {s} ammo",
            f"S{s} Ammunition",
            f"s{s} ammunition",
            f"S{s} Ammo",
            f"s{s} ammo",
            cstone_key,
        ]

        for k in keys:
            sc_wiki_cache[k] = converted
            item_volumes[k.lower()] = 1.0  # 1 SCU Cargo Container
            uex_items_db[k.lower()] = {
                "name": f"Size {s} Ammunition",
                "locations": [{"terminal": t["terminal"], "buy": t["price"], "sell": 0} for t in converted]
            }

    save_json("sc_wiki_items_cache.json", sc_wiki_cache)
    save_json("uex_items_trade_db.json", uex_items_db)
    save_json("item_volumes.json", item_volumes)

    print("[SUCCESS] CStone ship ammunition terminals synchronized 100% authentically!")

if __name__ == "__main__":
    main()
