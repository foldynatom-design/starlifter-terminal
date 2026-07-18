# -*- coding: utf-8 -*-
"""
Import ALL commodity data from UEX API into item_volumes.json + create commodity_prices.json.
UEX API provides: names, codes, kinds, weight_scu, buy/sell prices, flags.
"""
import json
import os
import urllib.request

def main():
    # Fetch UEX API
    url = "https://uexcorp.space/api/2.0/commodities"
    req = urllib.request.Request(url, headers={"User-Agent": "StarlifterBot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)

    if data.get("status") != "ok":
        print("UEX API error!")
        return

    commodities = data["data"]
    print(f"UEX returned {len(commodities)} commodities")

    # Load existing volume map
    base = os.path.join(os.path.dirname(__file__), '..')
    vol_path = os.path.join(base, 'resources', 'item_volumes.json')
    with open(vol_path, 'r', encoding='utf-8') as f:
        volume_map = json.load(f)

    # Build commodity price database
    commodity_db = {}
    updates = 0
    additions = 0

    for c in commodities:
        name = c.get("name", "")
        code = c.get("code", "")
        kind = c.get("kind", "")
        weight = c.get("weight_scu", 0)
        buy = c.get("price_buy", 0)
        sell = c.get("price_sell", 0)
        is_raw = c.get("is_raw", 0)
        is_refined = c.get("is_refined", 0)
        is_mineral = c.get("is_mineral", 0)
        is_illegal = c.get("is_illegal", 0)
        is_harvestable = c.get("is_harvestable", 0)
        is_buyable = c.get("is_buyable", 0)
        is_sellable = c.get("is_sellable", 0)
        is_temporary = c.get("is_temporary", 0)
        is_fuel = c.get("is_fuel", 0)
        is_volatile_qt = c.get("is_volatile_qt", 0)
        is_explosive = c.get("is_explosive", 0)

        if not name or is_temporary:
            continue

        key = name.lower().strip()

        # Commodity DB entry (for prices/trading)
        commodity_db[key] = {
            "name": name,
            "code": code,
            "kind": kind,
            "weight_scu": weight if weight else 1.0,
            "price_buy": buy,
            "price_sell": sell,
            "is_raw": bool(is_raw),
            "is_refined": bool(is_refined),
            "is_mineral": bool(is_mineral),
            "is_illegal": bool(is_illegal),
            "is_harvestable": bool(is_harvestable),
            "is_buyable": bool(is_buyable),
            "is_sellable": bool(is_sellable),
            "is_fuel": bool(is_fuel),
            "is_volatile": bool(is_volatile_qt),
            "is_explosive": bool(is_explosive),
        }

        # Volume map update — commodities are 1 SCU per unit (traded in SCU)
        # weight_scu is mass-per-SCU, not volume
        # All tradeable commodities = 1 SCU per unit on the cargo grid
        if key not in volume_map:
            volume_map[key] = 1.0
            additions += 1
            print(f"  ADD: {name} = 1.0 SCU")
        else:
            # Check if existing value makes sense
            current = volume_map[key]
            if isinstance(current, (int, float)) and current != 1.0 and is_buyable:
                # Buyable commodities are always 1 SCU per unit
                pass  # Don't override — some may have custom values

    # Save updated volume map
    with open(vol_path, 'w', encoding='utf-8') as f:
        json.dump(volume_map, f, indent=2, ensure_ascii=False)
    print(f"\nVolume map: {additions} additions, {len(volume_map)} total entries")

    # Save commodity price database
    prices_path = os.path.join(base, 'resources', 'commodity_prices.json')
    with open(prices_path, 'w', encoding='utf-8') as f:
        json.dump(commodity_db, f, indent=2, ensure_ascii=False)
    print(f"Commodity DB: {len(commodity_db)} entries saved to commodity_prices.json")

    # Print summary table
    print(f"\n{'='*80}")
    print(f"{'Name':<30} {'Code':<6} {'Kind':<12} {'Buy':>8} {'Sell':>8} {'Flags'}")
    print(f"{'-'*80}")
    for key in sorted(commodity_db.keys()):
        c = commodity_db[key]
        flags = []
        if c["is_raw"]: flags.append("RAW")
        if c["is_refined"]: flags.append("REF")
        if c["is_mineral"]: flags.append("MIN")
        if c["is_illegal"]: flags.append("ILL")
        if c["is_harvestable"]: flags.append("HAR")
        if c["is_explosive"]: flags.append("EXP")
        if c["is_volatile"]: flags.append("VOL")
        flag_str = ",".join(flags) if flags else "-"
        print(f"  {c['name']:<28} {c['code']:<6} {c['kind']:<12} {c['price_buy']:>8} {c['price_sell']:>8} {flag_str}")


if __name__ == "__main__":
    main()
