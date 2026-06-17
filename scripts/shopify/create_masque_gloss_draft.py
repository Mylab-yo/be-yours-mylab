"""Cree le produit 'Masque Gloss 200ml' en BROUILLON sur Shopify.

Le gloss existe dans Odoo (consommable, non storable) mais pas sur le site.
On le cree en draft (non publie) avec SKU + prix + stock theorique 350 (70% des
100 L FP en livraison). vendor/type/tags calques sur un masque existant.
Le 100ml (300 u.) n'est pas cree ici (format secondaire, a ajouter plus tard).

Idempotent : si un produit avec ce SKU existe deja, ne recree pas.
"""
import json, re, urllib.request, urllib.error
from pathlib import Path

STORE = "mylab-shop-3.myshopify.com"
API = f"https://{STORE}/admin/api/2024-07"
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
SKU = "masque-gloss-200-ml"
LOCATION_ID = 107265032526
STOCK = 350
REF_SKU = "masque-nourrissant-200-ml"


def tokens():
    return [m.group(1) for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
            for m in [re.match(r'\s*SHOPIFY_ADMIN_TOKEN\s*=\s*"?(shpat_[A-Za-z0-9]+)', line)] if m]


def scopes(t):
    r = urllib.request.Request(f"https://{STORE}/admin/oauth/access_scopes.json",
                               headers={"X-Shopify-Access-Token": t})
    return [s["handle"] for s in json.loads(urllib.request.urlopen(r).read())["access_scopes"]]


TOKEN = next((t for t in tokens() if "write_products" in scopes(t) and "write_inventory" in scopes(t)), None)
assert TOKEN, "pas de token write_products + write_inventory"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method,
        headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:300]); raise


def gql(query):
    r = urllib.request.Request(API + "/graphql.json", data=json.dumps({"query": query}).encode(),
        method="POST", headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())


def find_by_sku(sku):
    q = '{ productVariants(first:1, query:"sku:%s"){ edges{ node{ id price inventoryItem{id} product{ id title vendor productType tags } } } } }' % sku
    edges = gql(q).get("data", {}).get("productVariants", {}).get("edges", [])
    return edges[0]["node"] if edges else None


# Idempotence : deja cree ?
existing = find_by_sku(SKU)
if existing:
    print(f"Produit deja present pour SKU {SKU}: {existing['product']['title']} ({existing['product']['id']}) — rien a faire.")
    raise SystemExit(0)

ref = find_by_sku(REF_SKU)
assert ref, f"reference {REF_SKU} introuvable"
vendor = ref["product"]["vendor"]
ptype = ref["product"]["productType"]
price = ref["price"]
print(f"Reference {REF_SKU}: vendor={vendor!r} type={ptype!r} price={price}")

# Creation draft
payload = {"product": {
    "title": "Masque Gloss 200ml",
    "vendor": vendor,
    "product_type": ptype,
    "status": "draft",
    "variants": [{
        "sku": SKU,
        "price": price,
        "inventory_management": "shopify",
        "inventory_policy": "deny",
        "taxable": True,
    }],
}}
prod = api("POST", "/products.json", payload)["product"]
v = prod["variants"][0]
inv_item = v["inventory_item_id"]
print(f"Cree (DRAFT): product {prod['id']} / variant {v['id']} / inventory_item {inv_item} / handle {prod['handle']}")

# Stock : connect + set
try:
    api("POST", "/inventory_levels/connect.json",
        {"location_id": LOCATION_ID, "inventory_item_id": inv_item})
except Exception:
    pass  # deja connecte
api("POST", "/inventory_levels/set.json",
    {"location_id": LOCATION_ID, "inventory_item_id": inv_item, "available": STOCK})
print(f"Stock mis a {STOCK} @ location {LOCATION_ID}")
print(f"\nOK. Brouillon cree, prix {price} EUR, stock {STOCK}. A completer : photos, description, paliers de prix, puis publier.")
