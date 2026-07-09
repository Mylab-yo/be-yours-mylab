"""Fetch Spray Texturisant 200ml from Shopify Admin API to check tags + collection membership."""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Use the n8n full-scope token explicitly (the last SHOPIFY_ADMIN_TOKEN line
# in .env.local is the Storefront one, which 403s on /admin).
TOKEN = os.environ["SHOPIFY_ADMIN_TOKEN"]  # full-scope (read_products/orders); n8n token
STORE = "mylab-shop-3.myshopify.com"
HDR = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# 1) Look up the product by handle
handle = "spray-texturisant"
r = requests.get(
    f"https://{STORE}/admin/api/2024-10/products.json",
    params={"handle": handle, "fields": "id,title,handle,tags,status,published_scope"},
    headers=HDR,
)
r.raise_for_status()
products = r.json().get("products", [])
if not products:
    print(f"No product with handle={handle!r}")
    sys.exit(1)

p = products[0]
print(f"Product: {p['title']!r}  id={p['id']}  handle={p['handle']}  status={p['status']}")
print(f"  Tags ({len(p['tags'].split(','))}):")
for t in sorted(t.strip() for t in p["tags"].split(",")):
    print(f"    - {t}")

# 2) Check whether it is in collection 'boutique-adherents'
r = requests.get(
    f"https://{STORE}/admin/api/2024-10/custom_collections.json",
    params={"handle": "boutique-adherents", "fields": "id,handle,title"},
    headers=HDR,
)
custom = r.json().get("custom_collections", [])
r2 = requests.get(
    f"https://{STORE}/admin/api/2024-10/smart_collections.json",
    params={"handle": "boutique-adherents", "fields": "id,handle,title,rules,disjunctive"},
    headers=HDR,
)
smart = r2.json().get("smart_collections", [])
print(f"\nCollection 'boutique-adherents':  custom={len(custom)}  smart={len(smart)}")
for c in custom + smart:
    print(f"  id={c['id']} title={c['title']!r} handle={c['handle']}")
    if "rules" in c:
        print(f"    disjunctive={c.get('disjunctive')}  rules:")
        for rule in c["rules"]:
            print(f"      {rule}")

# 3) Is the product currently inside that collection?
all_cols = custom + smart
for col in all_cols:
    col_id = col["id"]
    r = requests.get(
        f"https://{STORE}/admin/api/2024-10/collects.json",
        params={"collection_id": col_id, "product_id": p["id"]},
        headers=HDR,
    )
    collects = r.json().get("collects", [])
    print(f"  Membership via /collects in {col_id}: {len(collects)} entry "
          f"(custom collections only)")
