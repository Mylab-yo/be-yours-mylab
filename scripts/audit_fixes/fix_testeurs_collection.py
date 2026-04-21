"""Peupler la collection /collections/testeurs avec tous les produits taggés 'Les testeurs'
   + renommer son titre qui était mensonger ('Shampoings repigmentants testeurs')."""
import json
import os
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = os.environ["TOKEN"]
SHOP = "mylab-shop-3.myshopify.com"
BASE = f"https://{SHOP}/admin/api/2024-10"
COLLECTION_ID = 655493562702  # testeurs custom collection


def req(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("X-Shopify-Access-Token", TOKEN)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return (json.loads(raw) if raw else None), resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(errors="ignore")}, e.code


# Step 1: rename the collection title
print("=== Step 1 : renommer la collection ===")
payload = {
    "custom_collection": {
        "id": COLLECTION_ID,
        "title": "Tous les testeurs",
    }
}
d, status = req("PUT", f"/custom_collections/{COLLECTION_ID}.json", payload)
print(f"  PUT title='Tous les testeurs' status={status}")

# Step 2: list all products with tag "Les testeurs"
print("=== Step 2 : lister produits tag 'Les testeurs' ===")
# Paginate
all_prods = []
since_id = 0
while True:
    d, _ = req("GET", f"/products.json?limit=250&since_id={since_id}&fields=id,handle,tags,template_suffix")
    batch = d.get("products", [])
    if not batch:
        break
    all_prods.extend(batch)
    if len(batch) < 250:
        break
    since_id = batch[-1]["id"]

testeurs = [p for p in all_prods if "Les testeurs" in (p.get("tags") or "")]
testeurs_by_suffix = [p for p in all_prods if p.get("template_suffix") == "testeur"]
print(f"  {len(testeurs)} produits taggés 'Les testeurs'")
print(f"  {len(testeurs_by_suffix)} produits avec template_suffix='testeur'")

# Union: products with either the tag OR the template_suffix
wanted_ids = set(p["id"] for p in testeurs) | set(p["id"] for p in testeurs_by_suffix)
print(f"  Union: {len(wanted_ids)} produits à ajouter")

# Step 3: list currently in collection via Collects
print("=== Step 3 : produits déjà dans la collection ===")
d, _ = req("GET", f"/collects.json?collection_id={COLLECTION_ID}&limit=250&fields=id,product_id")
current_collects = d.get("collects", [])
current_ids = set(c["product_id"] for c in current_collects)
print(f"  {len(current_ids)} produits actuellement dans la collection")

# Step 4: add missing ones
to_add = wanted_ids - current_ids
print(f"=== Step 4 : ajouter {len(to_add)} produits ===")
added = 0
for pid in to_add:
    d, status = req("POST", "/collects.json", {"collect": {"collection_id": COLLECTION_ID, "product_id": pid}})
    if status in (200, 201):
        added += 1
    else:
        print(f"  FAIL pid={pid} status={status} {d}")
print(f"  OK — {added}/{len(to_add)} ajoutés")

# Final count
d, _ = req("GET", f"/collects.json?collection_id={COLLECTION_ID}&limit=250&fields=id")
print(f"\nFinal collection count: {len(d.get('collects', []))} products")
