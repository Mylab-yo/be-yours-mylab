"""Verifie que les produits 400/500 ml < 10 unites (ou negatif) sont bien
notifies en rupture sur le storefront mylab-shop.

Le theme detecte la rupture par : inventory_management=='shopify' && inventory_quantity<=0
(cf. main-product.liquid / ml-collection-filterable / ml-quick-order). Il N'Y A PAS
de seuil "<10" : un produit a 1-9 unites reste vendable et N'affiche PAS la rupture.

Ce script tire la valeur Shopify reelle (celle que lit le storefront), la confronte
a Odoo (source du stock) et a la regle utilisateur (<10 ou negatif), et liste les ecarts.

Lecture seule.
  python verify_rupture_400_500.py
"""
import json, re, sys, time, urllib.request, urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "odoo"))
import _client as odoo  # noqa: E402

STORE = "mylab-shop-3.myshopify.com"
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
API = f"https://{STORE}/admin/api/2024-07"
PAT = re.compile(r"(?<!\d)(400|500)\s*-?\s*ml\b", re.IGNORECASE)
THRESHOLD = 10  # regle utilisateur : <10 unites => doit etre en rupture


def candidate_tokens():
    return [m.group(1) for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
            for m in [re.match(r'\s*SHOPIFY_ADMIN_TOKEN\s*=\s*"?(shpat_[A-Za-z0-9]+)', line)] if m]


def api(token, method, path, full=False):
    r = urllib.request.Request(API + path, method=method,
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(r) as resp:
                payload = json.loads(resp.read())
                return (payload, resp.headers) if full else payload
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(0.8 * (attempt + 1)); continue
            raise


def token_scopes(token):
    r = urllib.request.Request(f"https://{STORE}/admin/oauth/access_scopes.json",
        headers={"X-Shopify-Access-Token": token})
    with urllib.request.urlopen(r) as resp:
        return [s["handle"] for s in json.loads(resp.read())["access_scopes"]]


# token avec read inventory/products
TOKEN = None
for t in candidate_tokens():
    sc = token_scopes(t)
    if "read_products" in sc or "read_inventory" in sc:
        TOKEN = t; break
assert TOKEN, "pas de token read_products/read_inventory"
print(f"token {TOKEN[:12]}...\n")

# 1) Odoo : produits 400/500 stockables
odoo_rows = odoo.search_read("product.product", [("is_storable", "=", True)],
    ["default_code", "name", "qty_available", "virtual_available"], limit=2000)
odoo_by_sku = {}
for p in odoo_rows:
    sku = (p.get("default_code") or "").strip()
    hay = f"{p.get('name') or ''} {sku}"
    m = PAT.search(hay)
    if sku and m:
        odoo_by_sku[sku] = {"name": p["name"], "fmt": m.group(1),
                            "qty": int(p["qty_available"]), "virt": int(p["virtual_available"])}

# 2) Shopify : SKU -> variante (inventory_quantity / management / policy)
sku_map = {}
url = "/products.json?limit=250&fields=id,title,variants"
while url:
    payload, headers = api(TOKEN, "GET", url, full=True)
    for prod in payload.get("products", []):
        for v in prod.get("variants", []):
            if v.get("sku"):
                sku_map[v["sku"].strip()] = {
                    "title": prod["title"],
                    "qty": v.get("inventory_quantity"),
                    "mgmt": v.get("inventory_management"),
                    "policy": v.get("inventory_policy"),
                }
    link = headers.get("Link") or headers.get("link") or ""
    m = re.search(r'<([^>]+)>;\s*rel="next"', link)
    url = m.group(1).replace(API, "") if m else None
    time.sleep(0.3)

# 3) Croisement
print(f"=== Verif rupture — formats 400/500 ml (regle : <{THRESHOLD} ou negatif => doit etre en rupture) ===\n")
hdr = (f"{'SKU':<34} {'Odoo':>5} {'Shop':>5} {'Mgmt':>7} {'Policy':>9} "
       f"{'RuptStore':>10} {'DevraitRupt':>11}  Verdict")
print(hdr); print("-" * len(hdr))

problems = []
rows_out = []
for sku, od in sorted(odoo_by_sku.items(), key=lambda x: (x[1]["fmt"], x[0])):
    sh = sku_map.get(sku)
    if not sh:
        rows_out.append((sku, od["qty"], None, "-", "-", "?", "", "PAS sur Shopify (ignore)"))
        continue
    shop_qty = sh["qty"]
    tracked = sh["mgmt"] == "shopify"
    store_rupture = tracked and shop_qty is not None and shop_qty <= 0
    should_rupture = shop_qty is not None and shop_qty < THRESHOLD  # <10 inclut negatif
    if should_rupture and not store_rupture:
        if not tracked:
            verdict = "[!] stock NON suivi -> jamais rupture"
        else:
            verdict = f"[!] {shop_qty} u. en vente, PAS de rupture (1-9)"
        problems.append((sku, sh, shop_qty, verdict))
    elif store_rupture:
        verdict = "OK rupture affichee"
    else:
        verdict = "OK stock suffisant"
    rows_out.append((sku, od["qty"], shop_qty, sh["mgmt"] or "-", sh["policy"] or "-",
                     "OUI" if store_rupture else "non", "OUI" if should_rupture else "non", verdict))

for r in rows_out:
    sku, oq, sq, mgmt, pol, rs, dr, verdict = r
    print(f"{sku:<34} {str(oq):>5} {str(sq):>5} {mgmt:>7} {pol:>9} {rs:>10} {dr:>11}  {verdict}")

print(f"\n--- {len(problems)} produit(s) NON notifies en rupture alors qu'ils le devraient (regle <{THRESHOLD}) ---")
for sku, sh, q, verdict in problems:
    print(f"  {sku:<34} Shopify={q}  policy={sh['policy']}  -> {verdict}")
if not problems:
    print("  (aucun)")
