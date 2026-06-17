"""Aligne le stock Shopify sur Odoo (qty_available -> inventory_levels.available).

Matching par SKU (Odoo default_code == Shopify variant.sku).
Location Shopify : 107265032526.

Dry-run par defaut (aucune ecriture). Passer --apply pour pousser reellement.

  python sync_stock_from_odoo.py            # DRY RUN : affiche les ecarts
  python sync_stock_from_odoo.py --apply    # pousse odoo_qty -> Shopify

Modele sur scripts/n8n/sync-stock-odoo-shopify/*.js
"""
import json, re, sys, time, urllib.request, urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "odoo"))
import _client as odoo  # noqa: E402

STORE = "mylab-shop-3.myshopify.com"
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
API = f"https://{STORE}/admin/api/2024-07"
LOCATION_ID = 107265032526
APPLY = "--apply" in sys.argv


def candidate_tokens():
    return [m.group(1) for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
            for m in [re.match(r'\s*SHOPIFY_ADMIN_TOKEN\s*=\s*"?(shpat_[A-Za-z0-9]+)', line)] if m]


def api(token, method, path, body=None, full=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method,
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


need = "write_inventory" if APPLY else "read_inventory"
TOKEN = None
for t in candidate_tokens():
    sc = token_scopes(t)
    if need in sc or "write_inventory" in sc:
        TOKEN = t; break
assert TOKEN, f"pas de token {need}"
print(f"token {TOKEN[:12]}...  mode={'APPLY' if APPLY else 'DRY RUN'}")

# 1) Odoo : qty_available par SKU
odoo_rows = odoo.search_read("product.product", [("is_storable", "=", True)],
                             ["default_code", "name", "qty_available", "virtual_available"], limit=1000)
odoo_by_sku = {}
for p in odoo_rows:
    sku = (p.get("default_code") or "").strip()
    if sku:
        odoo_by_sku[sku] = {"name": p["name"], "qty": int(p["qty_available"] // 1)}
print(f"Odoo : {len(odoo_by_sku)} produits stockables avec SKU")

# 2) Shopify : SKU -> inventory_item_id (pagination cursor via header Link)
sku_map = {}
url = "/products.json?limit=250&fields=id,title,variants"
while url:
    payload, headers = api(TOKEN, "GET", url, full=True)
    for prod in payload.get("products", []):
        for v in prod.get("variants", []):
            if v.get("sku"):
                sku_map[v["sku"].strip()] = {"inv": v["inventory_item_id"], "title": prod["title"]}
    link = headers.get("Link") or headers.get("link") or ""
    m = re.search(r'<([^>]+)>;\s*rel="next"', link)
    url = m.group(1).replace(API, "") if m else None
    time.sleep(0.3)
print(f"Shopify : {len(sku_map)} variantes avec SKU")

# 3) Matched
matched = [(sku, odoo_by_sku[sku], sku_map[sku]) for sku in odoo_by_sku if sku in sku_map]
only_odoo = [s for s in odoo_by_sku if s not in sku_map]
only_shop = [s for s in sku_map if s not in odoo_by_sku]
print(f"Matchs SKU : {len(matched)} | Odoo-only : {len(only_odoo)} | Shopify-only : {len(only_shop)}")

# 4) Niveaux Shopify actuels (batch 50)
level = {}
invs = [m[2]["inv"] for m in matched]
for i in range(0, len(invs), 50):
    batch = invs[i:i + 50]
    data = api(TOKEN, "GET",
               f"/inventory_levels.json?location_ids={LOCATION_ID}&inventory_item_ids={','.join(map(str, batch))}")
    for l in data.get("inventory_levels", []):
        if l["location_id"] == LOCATION_ID:
            level[l["inventory_item_id"]] = l.get("available") or 0
    time.sleep(0.4)

# 5) Diff
updates = []
for sku, od, sh in matched:
    cur = level.get(sh["inv"], 0)
    if cur != od["qty"]:
        updates.append({"sku": sku, "name": od["name"], "inv": sh["inv"],
                        "odoo": od["qty"], "shopify": cur, "diff": od["qty"] - cur})

updates.sort(key=lambda u: abs(u["diff"]), reverse=True)
print(f"\n=== {len(updates)} ecarts a corriger (Shopify -> Odoo) ===")
print(f"{'SKU':<38} {'Shopify':>8} {'Odoo':>8} {'Diff':>7}  Nom")
for u in updates:
    print(f"{u['sku']:<38} {u['shopify']:>8} {u['odoo']:>8} {u['diff']:>+7}  {u['name'][:40]}")

if only_odoo:
    print(f"\n[INFO] {len(only_odoo)} SKU Odoo sans correspondance Shopify (ignores)")
if only_shop:
    print(f"[INFO] {len(only_shop)} SKU Shopify sans correspondance Odoo (ignores)")

# 6) Apply
if not APPLY:
    print("\nDRY RUN : aucune ecriture. Relancer avec --apply pour pousser.")
    sys.exit(0)

# Strategie validee : ne corriger que les produits ayant un stock REEL dans Odoo (>0).
# On ne met JAMAIS un produit a 0 (testeurs + variantes non initialisees dans Odoo).
to_apply = [u for u in updates if u["odoo"] > 0]
skipped = len(updates) - len(to_apply)
print(f"\n=== APPLY : {len(to_apply)} niveaux pousses (Odoo>0) | {skipped} ignores (Odoo<=0) ===")
ok = err = 0
for u in to_apply:
    try:
        api(TOKEN, "POST", "/inventory_levels/set.json",
            {"location_id": LOCATION_ID, "inventory_item_id": u["inv"], "available": u["odoo"]})
        ok += 1
        print(f"  OK  {u['sku']:<36} {u['shopify']} -> {u['odoo']}")
    except Exception as e:
        err += 1
        print(f"  ERR {u['sku']:<36} {e}")
    time.sleep(0.4)
print(f"\nTermine : {ok} OK, {err} erreurs")
