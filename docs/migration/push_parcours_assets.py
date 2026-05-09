"""Push restored parcours files via Shopify Admin REST API.

Set the token in env:
  $env:SHOPIFY_CONTENT_TOKEN = "shpat_..."   # PowerShell
  export SHOPIFY_CONTENT_TOKEN=shpat_...      # bash
"""
import os, json, sys, urllib.request, urllib.error

SHOP = "mylab-shop-3.myshopify.com"
TOKEN = os.environ.get("SHOPIFY_CONTENT_TOKEN", "")
if not TOKEN:
    sys.exit("ERROR: set SHOPIFY_CONTENT_TOKEN env var (Shopify Admin API token with write_themes scope)")
THEME_ID = 184014340430
REPO = r"d:\be-yours-mylab"

FILES = [
    "sections/ml-parcours-recap.liquid",
]

for rel in FILES:
    path = os.path.join(REPO, rel.replace("/", os.sep))
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    body = json.dumps({"asset": {"key": rel, "value": content}}).encode("utf-8")
    url = f"https://{SHOP}/admin/api/2025-04/themes/{THEME_ID}/assets.json"
    req = urllib.request.Request(url, data=body, method="PUT",
        headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            a = data.get("asset", {})
            print(f"  OK   {rel}  size={a.get('size','?')}  updated={a.get('updated_at','?')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  FAIL {rel}  HTTP {e.code}: {body[:200]}")
