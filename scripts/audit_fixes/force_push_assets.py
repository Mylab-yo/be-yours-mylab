"""Force-push des assets theme via Admin API (bypass CLI sync)."""
import json
import os
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = os.environ.get("TOKEN") or os.environ["SHOPIFY_ADMIN_TOKEN"]
SHOP = "mylab-shop-3.myshopify.com"
THEME = "184014340430"

FILES = [
    "templates/page.json",
    "templates/page.calculateur-marges.json",
    "templates/collection.json",
    "templates/index.json",
    "sections/ml-modeles-etiquettes.liquid",
]


def put_asset(key, value):
    url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json"
    payload = json.dumps({"asset": {"key": key, "value": value}}).encode()
    r = urllib.request.Request(url, data=payload, method="PUT")
    r.add_header("X-Shopify-Access-Token", TOKEN)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            d = json.loads(resp.read())
            return resp.status, d["asset"].get("updated_at")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="ignore")[:200]


for key in FILES:
    local_path = os.path.join("d:/be-yours-mylab", key)
    if not os.path.isfile(local_path):
        print(f"  SKIP (missing locally): {key}")
        continue
    with open(local_path, encoding="utf-8") as f:
        content = f.read()
    status, info = put_asset(key, content)
    print(f"  PUT {key} status={status} {info}")
