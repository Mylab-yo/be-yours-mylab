"""Cree 3 produits pompes sur Shopify (mylab-shop-3), prix fixe HT, SKU alignes Odoo,
publies mais hors collections listees. Idempotent : skip si le handle existe deja.

Selectionne automatiquement, parmi les SHOPIFY_ADMIN_TOKEN du .env.local configurateur,
celui qui dispose du scope write_products (les autres sont theme/customer-only).
Affiche handles + variant IDs.
"""
import json, time, re, urllib.request
from pathlib import Path

STORE = "mylab-shop-3.myshopify.com"
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")

PUMPS = [
    {"handle": "pompe-200ml",  "title": "Pompe doseuse 200 ml",  "sku": "POMPE-200",  "price": "0.50"},
    {"handle": "pompe-500ml",  "title": "Pompe doseuse 500 ml",  "sku": "POMPE-500",  "price": "0.50"},
    {"handle": "pompe-1000ml", "title": "Pompe doseuse 1000 ml", "sku": "POMPE-1000", "price": "1.00"},
]

def candidate_tokens():
    out = []
    for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r'\s*SHOPIFY_ADMIN_TOKEN\s*=\s*"?(shpat_[A-Za-z0-9]+)', line)
        if m:
            out.append(m.group(1))
    return out

def api(token, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"https://{STORE}/admin/api/2024-07{path}", data=data, method=method,
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())

def token_scopes(token):
    # access_scopes vit hors du path versionne (/admin/oauth/...), pas /admin/api/<ver>/
    r = urllib.request.Request(f"https://{STORE}/admin/oauth/access_scopes.json",
        headers={"X-Shopify-Access-Token": token})
    with urllib.request.urlopen(r) as resp:
        return [s["handle"] for s in json.loads(resp.read())["access_scopes"]]

def pick_token():
    for t in candidate_tokens():
        try:
            if "write_products" in token_scopes(t):
                return t
        except Exception:
            continue
    raise SystemExit("Aucun SHOPIFY_ADMIN_TOKEN avec write_products trouve dans .env.local")

TOKEN = pick_token()
print(f"Token write_products OK ({TOKEN[:10]}...)")

for p in PUMPS:
    existing = api(TOKEN, "GET", f"/products.json?handle={p['handle']}")
    if existing.get("products"):
        prod = existing["products"][0]; v = prod["variants"][0]
        print(f"EXISTE  {p['handle']}: product={prod['id']} variant={v['id']} prix={v['price']}")
        continue
    payload = {"product": {
        "title": p["title"], "handle": p["handle"], "status": "active",
        "vendor": "MY.LAB", "product_type": "Pompe",
        "tags": "pompe, accessoire, masquer-collection",
        "variants": [{"price": p["price"], "sku": p["sku"],
                      "inventory_management": None, "requires_shipping": True, "taxable": True}],
    }}
    created = api(TOKEN, "POST", "/products.json", payload)["product"]
    v = created["variants"][0]
    print(f"CREE    {p['handle']}: product={created['id']} variant={v['id']} prix={v['price']}")
    time.sleep(0.6)
