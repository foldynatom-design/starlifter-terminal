# Test new sync functions
import sys, json
sys.path.insert(0, 'source')
sys.stdout.reconfigure(encoding='utf-8')

from uex_sync import sync_commodity_trade_routes, sync_items_prices

def status(msg):
    print(f"  [{msg}]")

# 1) Commodity trade routes
print("=" * 60)
print("TEST 1: Commodity Trade Routes Sync")
print("=" * 60)
r1 = sync_commodity_trade_routes(status)
print(f"  Total API records: {r1['total']}")
print(f"  Commodities: {r1['commodities']}")
print(f"  Price points: {r1['locations']}")
print(f"  Errors: {r1['errors']}")

# 2) Items prices
print()
print("=" * 60)
print("TEST 2: Items Prices Sync")
print("=" * 60)
r2 = sync_items_prices(status)
print(f"  Total API records: {r2['total']}")
print(f"  Items classified: {r2['items']}")
print(f"  Skipped (digital): {r2['skipped']}")
print(f"  By cargo_type: {r2['by_cargo_type']}")
print(f"  By packing_cat: {r2['by_packing_cat']}")
print(f"  Errors: {r2['errors']}")

# Check saved files
import os
for fname in ['uex_trade_db.json', 'uex_items_trade_db.json']:
    fpath = os.path.join('resources', fname)
    if os.path.exists(fpath):
        size = os.path.getsize(fpath)
        data = json.load(open(fpath, encoding='utf-8'))
        print(f"\n  {fname}: {size/1024:.0f} KB, {len(data)} entries")
        # Show sample
        first_key = list(data.keys())[0]
        sample = data[first_key]
        if isinstance(sample, list):
            print(f"  Sample ({first_key}): {len(sample)} locations")
        elif isinstance(sample, dict):
            print(f"  Sample ({first_key}): type={sample.get('cargo_type')}, cat={sample.get('packing_cat')}, locs={len(sample.get('locations',[]))}")

print("\nDONE!")
