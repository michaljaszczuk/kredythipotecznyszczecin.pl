import json, os, sys, base64, urllib.request, urllib.error, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

USERNAME = os.environ["DATAFORSEO_USERNAME"]
PASSWORD = os.environ["DATAFORSEO_PASSWORD"]
AUTH = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
BASE = "https://api.dataforseo.com"

def call(endpoint, payload, retries=2):
    req = urllib.request.Request(
        f"{BASE}{endpoint}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if attempt < retries and e.code >= 500:
                time.sleep(2)
                continue
            print(f"HTTP {e.code}: {body[:500]}", file=sys.stderr)
            return None
        except Exception as ex:
            if attempt < retries:
                time.sleep(2)
                continue
            print(f"Error: {ex}", file=sys.stderr)
            return None

OUT = os.path.dirname(os.path.abspath(__file__))

QUERIES = [
    "kredyt hipoteczny szczecin",
    "doradca kredytowy szczecin",
    "broker kredytowy szczecin",
    "pośrednik kredytowy szczecin",
]

all_businesses = {}

for query in QUERIES:
    print(f"=== Google Maps: {query} ===")
    resp = call("/v3/serp/google/maps/live/advanced", [{
        "keyword": query,
        "language_code": "pl",
        "location_code": 2616,
        "device": "desktop",
        "os": "windows",
        "depth": 40,
    }])
    if resp and resp.get("tasks"):
        for task in resp["tasks"]:
            if task.get("result"):
                for res in task["result"]:
                    for item in (res.get("items") or []):
                        if item.get("type") == "maps_search":
                            title = item.get("title", "")
                            cid = item.get("cid") or item.get("place_id") or title
                            if cid not in all_businesses:
                                all_businesses[cid] = {
                                    "title": title,
                                    "cid": item.get("cid", ""),
                                    "place_id": item.get("place_id", ""),
                                    "address": item.get("address", ""),
                                    "phone": item.get("phone", ""),
                                    "url": item.get("url", ""),
                                    "domain": item.get("domain", ""),
                                    "rating": item.get("rating", {}).get("value", 0) if isinstance(item.get("rating"), dict) else item.get("rating", 0),
                                    "reviews_count": item.get("rating", {}).get("votes_count", 0) if isinstance(item.get("rating"), dict) else item.get("reviews_count", 0),
                                    "category": item.get("category", ""),
                                    "latitude": item.get("latitude", 0),
                                    "longitude": item.get("longitude", 0),
                                    "snippet": item.get("snippet", ""),
                                    "work_hours": item.get("work_hours", {}),
                                    "is_claimed": item.get("is_claimed", False),
                                    "found_for_query": query,
                                }
                                print(f"  + {title} | {item.get('address', '')}")
    time.sleep(0.5)

businesses = list(all_businesses.values())

with open(os.path.join(OUT, "gmb_listings.json"), "w", encoding="utf-8") as f:
    json.dump(businesses, f, ensure_ascii=False, indent=2)

print(f"\nTotal unique businesses: {len(businesses)}")
print(f"Saved to {os.path.join(OUT, 'gmb_listings.json')}")

# Print summary
print("\n=== BUSINESSES FOUND ===")
print(f"{'Name':<45} {'Rating':>6} {'Reviews':>8} {'Phone':<15}")
print("-" * 80)
for b in sorted(businesses, key=lambda x: x.get("reviews_count", 0) or 0, reverse=True):
    print(f"{b['title'][:44]:<45} {b.get('rating', 0) or 0:>6.1f} {b.get('reviews_count', 0) or 0:>8} {b.get('phone', ''):15}")
