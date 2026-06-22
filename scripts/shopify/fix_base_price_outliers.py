#!/usr/bin/env python3
"""Correction ponctuelle des 3 prix de variant Shopify aberrants détectés par le
garde-fou de sync_volume_tiers.py (prix variant != base palier). Aligne chaque
produit sur le prix de base de sa famille. Idempotent : ne touche que si le prix
diffère.

Usage:
  $env:SHOPIFY_ADMIN_TOKEN="shpat_..."   # token avec write_products
  python scripts/shopify/fix_base_price_outliers.py            # dry-run
  python scripts/shopify/fix_base_price_outliers.py --apply    # applique
"""
import argparse
import os
import sys

import requests

SHOP = "mylab-shop-3.myshopify.com"
API_VERSION = "2025-10"
GRAPHQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"

# handle -> prix cible en euros (string Shopify). Aligné sur la famille produit.
TARGETS = {
    "masque-intense": "9.50",
    "shampoing-coloristeur-marron-noisette": "7.50",
    "masque-dejaunisseur-platine": "9.60",
}


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


def resolve_variant(token, handle):
    q = """
    query P($q: String!) {
      products(first: 1, query: $q) {
        nodes { id variants(first: 1) { nodes { id price } } }
      }
    }"""
    nodes = _gql(token, q, {"q": f"handle:{handle}"})["products"]["nodes"]
    if not nodes or not nodes[0]["variants"]["nodes"]:
        return None
    p = nodes[0]
    v = p["variants"]["nodes"][0]
    return {"product_id": p["id"], "variant_id": v["id"], "price": v["price"]}


def update_price(token, product_id, variant_id, price):
    q = """
    mutation U($pid: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $pid, variants: $variants) {
        productVariants { id price }
        userErrors { field message }
      }
    }"""
    variables = {"pid": product_id, "variants": [{"id": variant_id, "price": price}]}
    errs = _gql(token, q, variables)["productVariantsBulkUpdate"]["userErrors"]
    if errs:
        raise RuntimeError(f"update error: {errs}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="applique réellement (sinon dry-run)")
    args = ap.parse_args()

    token = os.environ.get("SHOPIFY_ADMIN_TOKEN")
    if not token:
        print("ERREUR: SHOPIFY_ADMIN_TOKEN manquant", file=sys.stderr)
        sys.exit(1)

    for handle, target in TARGETS.items():
        info = resolve_variant(token, handle)
        if not info:
            print(f"⚠️ {handle}: introuvable, ignoré")
            continue
        current = info["price"]
        if float(current) == float(target):
            print(f"= {handle}: déjà à {target} €, rien à faire")
            continue
        if args.apply:
            update_price(token, info["product_id"], info["variant_id"], target)
            print(f"✔ {handle}: {current} € -> {target} €")
        else:
            print(f"[dry] {handle}: {current} € -> {target} €")

    if not args.apply:
        print("\n(dry-run — relance avec --apply pour écrire)")


if __name__ == "__main__":
    main()
