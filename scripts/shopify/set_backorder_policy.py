"""Met inventory_policy=continue sur les variantes des produits de 'boutique-adherents'
SAUF ceux tagues 'no-backorder' (-> deny). Idempotent.

Usage :
  python set_backorder_policy.py                 # BULK (tous les produits de la collection) -- go-live
  python set_backorder_policy.py <handle>        # un seul produit (test QA dev)

Token write_products auto-selectionne (cf. create_pump_products.py).
"""
import json, re, sys, time, urllib.request
from pathlib import Path

STORE = "mylab-shop-3.myshopify.com"
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
API = f"https://{STORE}/admin/api/2024-07"
ONLY_HANDLE = sys.argv[1] if len(sys.argv) > 1 else None

def candidate_tokens():
    return [m.group(1) for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
            for m in [re.match(r'\s*SHOPIFY_ADMIN_TOKEN\s*=\s*"?(shpat_[A-Za-z0-9]+)', line)] if m]

def api(token, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method,
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())

def token_scopes(token):
    r = urllib.request.Request(f"https://{STORE}/admin/oauth/access_scopes.json",
        headers={"X-Shopify-Access-Token": token})
    with urllib.request.urlopen(r) as resp:
        return [s["handle"] for s in json.loads(resp.read())["access_scopes"]]

TOKEN = next((t for t in candidate_tokens() if "write_products" in token_scopes(t)), None)
assert TOKEN, "pas de token write_products"
print(f"token {TOKEN[:10]}...  mode={'SINGLE ' + ONLY_HANDLE if ONLY_HANDLE else 'BULK collection'}")

if ONLY_HANDLE:
    prods = api(TOKEN, "GET", f"/products.json?handle={ONLY_HANDLE}&fields=id,handle,tags,variants")["products"]
else:
    cols = (api(TOKEN, "GET", "/custom_collections.json?handle=boutique-adherents").get("custom_collections")
            or api(TOKEN, "GET", "/smart_collections.json?handle=boutique-adherents").get("smart_collections"))
    col_id = cols[0]["id"]
    prods, since = [], None
    while True:
        path = f"/products.json?collection_id={col_id}&limit=250&fields=id,handle,tags,variants"
        if since: path += f"&since_id={since}"
        data = api(TOKEN, "GET", path)["products"]
        if not data: break
        prods += data
        if len(data) < 250: break
        since = data[-1]["id"]; time.sleep(0.4)
print("produits:", len(prods))

changed = 0
for p in prods:
    tags = [t.strip().lower() for t in (p.get("tags") or "").split(",")]
    want = "deny" if "no-backorder" in tags else "continue"
    for v in p["variants"]:
        if v.get("inventory_policy") != want:
            api(TOKEN, "PUT", f"/variants/{v['id']}.json",
                {"variant": {"id": v["id"], "inventory_policy": want}})
            changed += 1
            print(f"  {p['handle']} v{v['id']} -> {want}")
            time.sleep(0.4)
print(f"variantes mises a jour : {changed}")
