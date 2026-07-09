"""Patch `shipping_address.address2 = '-'` on Shopify orders where it's null.

Workaround pour bug DPD France Officiel (2026-06-09) : l'app crash 500
"Cannot read properties of null (reading 'replace')" sur l'action exportOrders
quand `shipping_address.address2` est null. Patcher avec '-' débloque l'export.

Cible par défaut : commandes open + unfulfilled (celles à expédier).
Dry-run par défaut. `--apply` pour exécuter.

Usage:
    python scripts/dpd_patch_null_address2.py            # dry-run
    python scripts/dpd_patch_null_address2.py --apply    # patch en prod
"""
import json
import os
import sys
import time
import urllib.request

SHOP = "mylab-shop-3.myshopify.com"
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
API_VERSION = "2024-10"
PLACEHOLDER = "-"


def shopify(method, path, body=None):
    url = f"https://{SHOP}/admin/api/{API_VERSION}/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def list_unfulfilled():
    """Page through open + unfulfilled orders. Returns those where shipping address2 is null."""
    targets = []
    params = "status=open&fulfillment_status=unfulfilled&limit=250&fields=id,name,shipping_address"
    path = f"orders.json?{params}"
    while path:
        # Extract Link header for pagination using lower-level call
        url = f"https://{SHOP}/admin/api/{API_VERSION}/{path}"
        req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": TOKEN})
        with urllib.request.urlopen(req) as r:
            link = r.headers.get("Link", "")
            data = json.loads(r.read())
        for o in data.get("orders", []):
            sa = o.get("shipping_address") or {}
            if sa.get("address2") is None:
                targets.append({"id": o["id"], "name": o["name"], "addr1": sa.get("address1", "")})
        # parse rel=next
        path = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().lstrip("<").rstrip(">")
                path = next_url.split(f"/admin/api/{API_VERSION}/")[1]
                break
    return targets


def patch_order(oid):
    body = {"order": {"id": oid, "shipping_address": {"address2": PLACEHOLDER}}}
    shopify("PUT", f"orders/{oid}.json", body)


def main(apply=False):
    targets = list_unfulfilled()
    print(f"Found {len(targets)} unfulfilled order(s) with shipping_address.address2 = null")
    for t in targets:
        print(f"  {t['name']:>8}  id={t['id']}  addr1={t['addr1'][:50]}")
    if not targets:
        return 0
    if not apply:
        print("\nDry-run. Re-run with --apply to actually patch.")
        return 0
    print(f"\nPatching {len(targets)} orders...")
    ok = ko = 0
    for t in targets:
        try:
            patch_order(t["id"])
            print(f"  OK  {t['name']}")
            ok += 1
        except Exception as e:
            print(f"  FAIL {t['name']}: {e}")
            ko += 1
        time.sleep(0.5)  # respect 2 req/s safe rate
    print(f"\nDone. ok={ok} fail={ko}")
    return 0 if ko == 0 else 1


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
