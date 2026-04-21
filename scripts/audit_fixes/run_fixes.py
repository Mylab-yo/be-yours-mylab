"""Applique les corrections d'audit via Shopify Admin API."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Force UTF-8 sur stdout Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_contents import (
    PAGES_TO_DELETE,
    PAGE_UPDATES,
    PRODUCT_UPDATES,
    PAGE_SLUG_RENAMES,
    COLLECTION_SLUG_RENAMES,
)

TOKEN = os.environ.get("TOKEN") or os.environ.get("SHOPIFY_ADMIN_TOKEN")
SHOP = os.environ.get("SHOP", "mylab-shop-3.myshopify.com")
BASE = f"https://{SHOP}/admin/api/2024-10"

if not TOKEN:
    print("ERROR: set TOKEN env var")
    sys.exit(1)


def req(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("X-Shopify-Access-Token", TOKEN)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return (json.loads(raw) if raw else None), resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(errors="ignore")}, e.code


def list_all(resource, fields):
    items = []
    since_id = 0
    while True:
        data, _ = req("GET", f"/{resource}.json?limit=250&since_id={since_id}&fields={fields}")
        batch = data.get(resource, [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 250:
            break
        since_id = batch[-1]["id"]
    return items


def find_page(handle):
    data, _ = req("GET", f"/pages.json?handle={handle}&fields=id,handle,title,body_html")
    pages = data.get("pages", [])
    return pages[0] if pages else None


def find_product(handle):
    data, _ = req("GET", f"/products.json?handle={handle}&fields=id,handle,title,body_html")
    prods = data.get("products", [])
    return prods[0] if prods else None


def create_redirect(from_path, to_path):
    payload = {"redirect": {"path": from_path, "target": to_path}}
    data, status = req("POST", "/redirects.json", payload)
    if status in (200, 201):
        print(f"    redirect 301 {from_path} -> {to_path} OK")
    elif status == 422:
        print(f"    redirect 301 {from_path} -> {to_path} (already exists or invalid)")
    else:
        print(f"    redirect FAIL status={status} {data}")


# ==== 1. Suppression pages erronées ====
print("=== 1. Suppression pages vercel-app erronees ===")
for handle in PAGES_TO_DELETE:
    p = find_page(handle)
    if not p:
        print(f"  SKIP (not found): {handle}")
        continue
    _, status = req("DELETE", f"/pages/{p['id']}.json")
    print(f"  DELETE {handle} id={p['id']} status={status}")
print()

# ==== 2. Mise à jour contenu pages vides ====
print("=== 2. Mise a jour pages institutionnelles ===")
for handle, (title, body) in PAGE_UPDATES.items():
    p = find_page(handle)
    if not p:
        print(f"  SKIP (not found): {handle}")
        continue
    current_len = len((p.get("body_html") or "").strip())
    if current_len > 1500:
        print(f"  SKIP already has content ({current_len} chars): {handle}")
        continue
    payload = {"page": {"id": p["id"], "title": title, "body_html": body}}
    data, status = req("PUT", f"/pages/{p['id']}.json", payload)
    status_ok = "OK" if status == 200 else f"FAIL {status} {data}"
    print(f"  UPDATE page {handle} id={p['id']} -> {status_ok}")
print()

# ==== 3. Mise à jour body des produits (coffret, etc.) ====
print("=== 3. Mise a jour body produits (texte IA brut) ===")
for handle, new_body in PRODUCT_UPDATES.items():
    p = find_product(handle)
    if not p:
        print(f"  SKIP (not found): {handle}")
        continue
    payload = {"product": {"id": p["id"], "body_html": new_body}}
    data, status = req("PUT", f"/products/{p['id']}.json", payload)
    status_ok = "OK" if status == 200 else f"FAIL {status} {data}"
    print(f"  UPDATE product {handle} id={p['id']} -> {status_ok}")
print()

# ==== 4. Renommage slugs pages + 301 ====
print("=== 4. Renommage slugs pages (fautes) + 301 ===")
for old_handle, new_handle in PAGE_SLUG_RENAMES.items():
    p = find_page(old_handle)
    if not p:
        # Try new one — might already be renamed
        if find_page(new_handle):
            print(f"  ALREADY RENAMED: {old_handle} -> {new_handle}")
            create_redirect(f"/pages/{old_handle}", f"/pages/{new_handle}")
        else:
            print(f"  SKIP (not found): {old_handle}")
        continue
    payload = {"page": {"id": p["id"], "handle": new_handle}}
    data, status = req("PUT", f"/pages/{p['id']}.json", payload)
    if status == 200:
        got = data.get("page", {}).get("handle", "?")
        print(f"  RENAME page {old_handle} -> {got} status={status}")
        create_redirect(f"/pages/{old_handle}", f"/pages/{got}")
    else:
        print(f"  FAIL rename {old_handle} status={status} {data}")
print()

# ==== 5. Renommage slugs collections + 301 ====
print("=== 5. Renommage slugs collections + 301 ===")
# Pre-load all collections
all_colls = []
for ep in ("custom_collections", "smart_collections"):
    since_id = 0
    while True:
        data, _ = req("GET", f"/{ep}.json?limit=250&since_id={since_id}&fields=id,handle,title")
        batch = data.get(ep, [])
        if not batch:
            break
        for c in batch:
            c["_ep"] = ep
        all_colls.extend(batch)
        if len(batch) < 250:
            break
        since_id = batch[-1]["id"]
by_handle = {c["handle"]: c for c in all_colls}

for old_handle, new_handle in COLLECTION_SLUG_RENAMES.items():
    if old_handle not in by_handle:
        if new_handle in by_handle:
            print(f"  ALREADY RENAMED: {old_handle} -> {new_handle}")
            create_redirect(f"/collections/{old_handle}", f"/collections/{new_handle}")
        else:
            print(f"  SKIP (not found): {old_handle}")
        continue
    c = by_handle[old_handle]
    ep = c["_ep"]
    resource_key = "custom_collection" if ep == "custom_collections" else "smart_collection"
    payload = {resource_key: {"id": c["id"], "handle": new_handle}}
    data, status = req("PUT", f"/{ep}/{c['id']}.json", payload)
    if status == 200:
        got = data.get(resource_key, {}).get("handle", "?")
        print(f"  RENAME collection {old_handle} -> {got} status={status}")
        create_redirect(f"/collections/{old_handle}", f"/collections/{got}")
    else:
        print(f"  FAIL rename {old_handle} status={status} {data}")
print()

print("Done.")
