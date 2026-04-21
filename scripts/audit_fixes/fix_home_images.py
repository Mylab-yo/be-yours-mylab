"""Patch chirurgical sur templates/index.json : remplace les refs mortes
   shampoing-dejaunisseur-home.png par huile-goutte.jpg (qui existe).

Approche : read → modify in-place uniquement sur les champs 'image' et 'image_mobile'
du slide_main et slide_shampooing → PUT.
"""
import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = os.environ["TOKEN"]
THEME = "184014340430"
SHOP = "mylab-shop-3.myshopify.com"
KEY = "templates/index.json"

OLD = "shopify://shop_images/shampoing-dejaunisseur-home.png"
NEW = "shopify://shop_images/huile-goutte.jpg"

# Fetch live
url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json?asset%5Bkey%5D={KEY.replace('/', '%2F')}"
r = urllib.request.Request(url)
r.add_header("X-Shopify-Access-Token", TOKEN)
with urllib.request.urlopen(r) as resp:
    live_value = json.loads(resp.read())["asset"]["value"]

print(f"Live file size: {len(live_value)}")
before_count = live_value.count(OLD)
print(f"Occurrences of OLD ref: {before_count}")

# Parse → modify → serialize
parsed = json.loads(live_value)

# Track specific changes
changes = []

def maybe_replace(settings_obj, keys, label):
    for k in keys:
        if settings_obj.get(k) == OLD:
            settings_obj[k] = NEW
            changes.append(f"  {label}.{k}: {OLD} -> {NEW}")

# slideshow_hero.slide_main image + image_mobile
sh = parsed["sections"].get("slideshow_hero", {})
for block_key, block in sh.get("blocks", {}).items():
    maybe_replace(block.get("settings", {}), ["image", "image_mobile"], f"slideshow_hero.{block_key}")

# dual_scroll_products.slide_shampooing image
ds = parsed["sections"].get("dual_scroll_products", {})
for block_key, block in ds.get("blocks", {}).items():
    maybe_replace(block.get("settings", {}), ["image", "image_mobile"], f"dual_scroll_products.{block_key}")

# brand_story top-level image (image-with-text)
bs = parsed["sections"].get("brand_story", {})
maybe_replace(bs.get("settings", {}), ["image", "video_cover"], "brand_story")

print(f"\nChanges applied ({len(changes)}):")
for c in changes:
    print(c)

if not changes:
    print("\nNo changes — aborting PUT")
    sys.exit(0)

# Serialize back (use indent=2 to match Shopify's style roughly)
new_value = json.dumps(parsed, indent=2, ensure_ascii=False)
after_count = new_value.count(OLD)
print(f"\nOccurrences of OLD ref after: {after_count}")

# PUT
put_url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json"
payload = json.dumps({"asset": {"key": KEY, "value": new_value}}).encode()
req = urllib.request.Request(put_url, data=payload, method="PUT")
req.add_header("X-Shopify-Access-Token", TOKEN)
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read())
    print(f"\nPUT status={resp.status} updated_at={res['asset'].get('updated_at')}")
