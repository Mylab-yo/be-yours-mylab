#!/usr/bin/env python3
"""Synchronise les paliers volume de ml-product-map.json vers les metafields produit
Shopify (mylab.volume_tiers, type json). Idempotent.

Usage:
  SHOPIFY_ADMIN_TOKEN=shpat_... python scripts/shopify/sync_volume_tiers.py --dry-run
  SHOPIFY_ADMIN_TOKEN=shpat_... python scripts/shopify/sync_volume_tiers.py
"""
import argparse
import json
import os
import sys

import requests

SHOP = "mylab-shop-3.myshopify.com"
API_VERSION = "2025-10"
NAMESPACE = "mylab"
KEY = "volume_tiers"
MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ml-product-map.json")


def parse_tier_string(s):
    """'6:850,12:805' -> [[6, 850], [12, 805]] trié par quantité croissante."""
    pairs = []
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        qty_str, price_str = chunk.split(":")
        pairs.append([int(qty_str.strip()), int(price_str.strip())])
    pairs.sort(key=lambda p: p[0])
    return pairs


def build_metafield_payloads(product_map):
    """Aplati le map en une liste de metafields à écrire, un par (handle, size)."""
    out = []
    for entry in product_map.values():
        sizes = entry.get("sizes", {})
        tiers = entry.get("tiers", {})
        for size, handle in sizes.items():
            ts = tiers.get(size)
            if not ts:
                continue
            parsed = parse_tier_string(ts)
            out.append({
                "handle": handle,
                "size": size,
                "tiers": parsed,
                "base_price": parsed[0][1] if parsed else None,
            })
    return out


GRAPHQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"


def _gql(token, query, variables=None):
    r = requests.post(
        GRAPHQL_URL,
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def ensure_definition(token):
    q = """
    mutation Def {
      metafieldDefinitionCreate(definition: {
        name: "Volume tiers", namespace: "%s", key: "%s", type: "json", ownerType: PRODUCT
      }) { createdDefinition { id } userErrors { code message } }
    }""" % (NAMESPACE, KEY)
    data = _gql(token, q)
    errs = data["metafieldDefinitionCreate"]["userErrors"]
    for e in errs:
        if e.get("code") != "TAKEN":
            raise RuntimeError(f"definition error: {e}")
    print("definition OK")


def resolve_product(token, handle):
    q = """
    query P($q: String!) {
      products(first: 1, query: $q) {
        nodes { id title variants(first: 1) { nodes { price } } }
      }
    }"""
    data = _gql(token, q, {"q": f"handle:{handle}"})
    nodes = data["products"]["nodes"]
    if not nodes:
        return None
    p = nodes[0]
    variant_price_cents = None
    vnodes = p["variants"]["nodes"]
    if vnodes:
        variant_price_cents = round(float(vnodes[0]["price"]) * 100)
    return {"id": p["id"], "variant_price": variant_price_cents}


def write_metafield(token, product_id, tiers):
    q = """
    mutation Set($m: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $m) { userErrors { field message } }
    }"""
    variables = {"m": [{
        "ownerId": product_id, "namespace": NAMESPACE, "key": KEY,
        "type": "json", "value": json.dumps(tiers),
    }]}
    data = _gql(token, q, variables)
    errs = data["metafieldsSet"]["userErrors"]
    if errs:
        raise RuntimeError(f"metafieldsSet error: {errs}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("SHOPIFY_ADMIN_TOKEN")
    if not token:
        print("ERREUR: SHOPIFY_ADMIN_TOKEN manquant", file=sys.stderr)
        sys.exit(1)

    with open(os.path.abspath(MAP_PATH), encoding="utf-8") as f:
        product_map = json.load(f)
    payloads = build_metafield_payloads(product_map)

    if not args.dry_run:
        ensure_definition(token)

    mismatches, missing, written = [], [], 0
    for p in payloads:
        prod = resolve_product(token, p["handle"])
        if not prod:
            missing.append(p["handle"])
            continue
        if prod["variant_price"] is not None and prod["variant_price"] != p["base_price"]:
            mismatches.append((p["handle"], prod["variant_price"], p["base_price"]))
        if args.dry_run:
            print(f"[dry] {p['handle']}: tiers={p['tiers']}")
        else:
            write_metafield(token, prod["id"], p["tiers"])
            written += 1
            print(f"écrit {p['handle']}")

    print(f"\n--- Résumé ---")
    # In dry-run, missing handles are skipped, so actual count = total - missing
    planned_count = len(payloads) - len(missing) if args.dry_run else written
    print(f"metafields {'planifiés' if args.dry_run else 'écrits'}: {planned_count}")
    if missing:
        print(f"⚠️ handles introuvables ({len(missing)}): {missing}")
    if mismatches:
        print(f"⚠️ écarts prix variant ≠ base palier ({len(mismatches)}):")
        for h, vp, bp in mismatches:
            print(f"    {h}: variant={vp} base_palier={bp}")


if __name__ == "__main__":
    main()
