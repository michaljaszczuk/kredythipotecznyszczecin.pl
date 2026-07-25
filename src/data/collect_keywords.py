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

SEEDS = [
    "kredyt hipoteczny szczecin",
    "doradca kredytowy szczecin",
    "broker kredytowy szczecin",
    "pośrednik kredytowy szczecin",
    "kalkulator kredytu hipotecznego",
    "kredyt mieszkaniowy szczecin",
    "najlepszy kredyt hipoteczny",
    "refinansowanie kredytu hipotecznego",
]

all_keywords = {}
OUT = os.path.dirname(os.path.abspath(__file__))

# 1. Related keywords
print("=== Related Keywords ===")
for seed in SEEDS[:4]:
    print(f"  Fetching related: {seed}")
    resp = call("/v3/dataforseo_labs/google/related_keywords/live", [{
        "keyword": seed,
        "language_code": "pl",
        "location_code": 2616,  # Poland
        "limit": 80,
        "include_seed_keyword": True,
    }])
    if resp and resp.get("tasks"):
        for task in resp["tasks"]:
            if task.get("result"):
                for res in task["result"]:
                    for item in (res.get("items") or []):
                        kd = item.get("keyword_data") or item
                        ki = kd.get("keyword_info") or kd
                        kw = kd.get("keyword", item.get("keyword", ""))
                        if kw:
                            sv = ki.get("search_volume", 0) or 0
                            cpc = ki.get("cpc", 0) or 0
                            comp = ki.get("competition", 0) or 0
                            all_keywords[kw] = {
                                "keyword": kw,
                                "search_volume": sv,
                                "cpc": cpc,
                                "competition": comp,
                                "source_seed": seed,
                            }
    time.sleep(0.3)

# 2. Keyword suggestions
print("=== Keyword Suggestions ===")
for seed in SEEDS:
    print(f"  Fetching suggestions: {seed}")
    resp = call("/v3/dataforseo_labs/google/keyword_suggestions/live", [{
        "keyword": seed,
        "language_code": "pl",
        "location_code": 2616,
        "limit": 80,
        "include_seed_keyword": True,
    }])
    if resp and resp.get("tasks"):
        for task in resp["tasks"]:
            if task.get("result"):
                for res in task["result"]:
                    for item in (res.get("items") or []):
                        kd = item.get("keyword_data") or item
                        ki = kd.get("keyword_info") or kd
                        kw = kd.get("keyword", item.get("keyword", ""))
                        if kw and kw not in all_keywords:
                            sv = ki.get("search_volume", 0) or 0
                            cpc = ki.get("cpc", 0) or 0
                            comp = ki.get("competition", 0) or 0
                            all_keywords[kw] = {
                                "keyword": kw,
                                "search_volume": sv,
                                "cpc": cpc,
                                "competition": comp,
                                "source_seed": seed,
                            }
    time.sleep(0.3)

# 3. Search intent for top keywords
top_kws = sorted(all_keywords.values(), key=lambda x: x["search_volume"], reverse=True)[:200]
print(f"\n=== Search Intent (top {len(top_kws)} keywords) ===")
batch_size = 100
for i in range(0, len(top_kws), batch_size):
    batch = top_kws[i:i+batch_size]
    kw_list = [k["keyword"] for k in batch]
    resp = call("/v3/dataforseo_labs/google/search_intent/live", [{
        "keywords": kw_list,
        "language_code": "pl",
        "location_code": 2616,
    }])
    if resp and resp.get("tasks"):
        for task in resp["tasks"]:
            if task.get("result"):
                for res in task["result"]:
                    for item in (res.get("items") or []):
                        kw = item.get("keyword", "")
                        intent = item.get("keyword_intent", {})
                        if kw in all_keywords:
                            all_keywords[kw]["intent_label"] = intent.get("label", "")
                            all_keywords[kw]["intent_probability"] = intent.get("probability", 0)
    time.sleep(0.3)

# Sort by search_volume desc, then CPC desc
sorted_kws = sorted(all_keywords.values(), key=lambda x: (x["search_volume"], x["cpc"]), reverse=True)

# Save full JSON
with open(os.path.join(OUT, "keywords_full.json"), "w", encoding="utf-8") as f:
    json.dump(sorted_kws, f, ensure_ascii=False, indent=2)

# Save CSV
with open(os.path.join(OUT, "keywords.csv"), "w", encoding="utf-8") as f:
    f.write("keyword,search_volume,cpc,competition,intent,source_seed\n")
    for kw in sorted_kws:
        f.write(f'"{kw["keyword"]}",{kw["search_volume"]},{kw["cpc"]},{kw["competition"]},"{kw.get("intent_label","")}","{kw["source_seed"]}"\n')

print(f"\nTotal unique keywords: {len(sorted_kws)}")
print(f"Saved to {os.path.join(OUT, 'keywords.csv')}")

# Print top 30 for quick review
print("\n=== TOP 30 KEYWORDS ===")
print(f"{'Keyword':<55} {'Vol':>6} {'CPC':>6} {'Intent':<15}")
print("-" * 90)
for kw in sorted_kws[:30]:
    print(f"{kw['keyword']:<55} {kw['search_volume']:>6} {kw['cpc']:>6.2f} {kw.get('intent_label',''):15}")
