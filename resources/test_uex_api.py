# Test UEX API endpoints for trade data
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

endpoints = {
    "commodities": "https://uexcorp.space/api/2.0/commodities",
    "commodities_prices_all": "https://uexcorp.space/api/2.0/commodities_prices_all",
    "items_prices_all": "https://uexcorp.space/api/2.0/items_prices_all",
}

for name, url in endpoints.items():
    print(f"\n{'='*60}")
    print(f"Endpoint: {name}")
    print(f"URL: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StarlifterBot/0.6"})
        resp = urllib.request.urlopen(req, timeout=60)
        raw = resp.read()
        print(f"Response size: {len(raw)} bytes ({len(raw)/1024/1024:.1f} MB)")
        d = json.loads(raw)
        print(f"Status: {d.get('status')}")
        data = d.get('data', [])
        print(f"Records: {len(data)}")
        if data:
            print(f"Keys: {list(data[0].keys())}")
            print(f"Sample record:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False)[:600])
    except Exception as e:
        print(f"ERROR: {e}")
