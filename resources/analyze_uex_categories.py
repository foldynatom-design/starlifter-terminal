# Analyze items_prices_all to understand category distribution
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

print("Fetching items_prices_all (6 MB)...")
req = urllib.request.Request(
    'https://uexcorp.space/api/2.0/items_prices_all',
    headers={'User-Agent': 'StarlifterBot/0.6'}
)
resp = urllib.request.urlopen(req, timeout=60)
data = json.loads(resp.read())['data']
print(f"Got {len(data)} records")

# Count per category
from collections import Counter, defaultdict
cat_counts = Counter()
cat_examples = defaultdict(list)

for r in data:
    cat = r.get('id_category', 0)
    cat_counts[cat] += 1
    if len(cat_examples[cat]) < 3:
        cat_examples[cat].append(r.get('item_name', '?'))

print(f"\n{'id_category':>12} {'Count':>7}  Sample Items")
print("-" * 80)
for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
    examples = ", ".join(cat_examples[cat])
    print(f"  {cat:>10} {count:>7}  {examples[:65]}")

# Unique items per category
unique_items = defaultdict(set)
for r in data:
    unique_items[r.get('id_category', 0)].add(r.get('item_name', '?'))

print(f"\n{'id_category':>12} {'Unique':>7}  First 3 unique items")
print("-" * 80)
for cat in sorted(unique_items.keys()):
    items = sorted(unique_items[cat])
    print(f"  {cat:>10} {len(items):>7}  {', '.join(items[:3])[:65]}")
