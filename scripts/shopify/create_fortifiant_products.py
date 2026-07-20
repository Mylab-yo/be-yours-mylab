# -*- coding: utf-8 -*-
"""Cree les fiches Shopify de la gamme Fortifiante, en brouillon. Idempotent.

Source du texte : docs/produits/fiches-fortifiant.md (valide par Yoann le 20/07/2026).
SKU = default_code Odoo, aligne sur scripts/odoo/create_fortifiant.py.

Necessite un token avec le scope write_products. Le token Theme sync ne l'a pas.

Usage:
    python scripts/shopify/create_fortifiant_products.py [--apply]

Sans --apply : dry-run, affiche ce qui serait cree/modifie sans rien ecrire.
"""
import argparse
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API = "2024-10"
VENDOR = "MyLab"
PRODUCT_TYPE = "Gamme mixte > Les Fortifiants"

SHAMPOING_BODY = (
    "<p>Le <strong>Shampoing fortifiant</strong> à l'<strong>extrait de Swertia Japonica</strong> "
    "est un soin lavant formulé pour les cheveux affaiblis et les cuirs chevelus qui manquent de tonus. "
    "Sa base lavante douce, sans sulfates, nettoie sans agresser la fibre ni décaper le cuir chevelu. "
    "Sa texture souple s'émulsionne facilement et se rince sans résidu, laissant les cheveux légers "
    "et faciles à coiffer. Il constitue la première étape de la routine fortifiante, avant "
    "l'application du sérum.</p><ul>\n"
    "<li>\n<strong>Type de cheveux :</strong> Cheveux affaiblis ou fins — cuir chevelu en manque de tonus</li>\n"
    "<li>\n<strong>Résultat :</strong> Cheveux propres, souples et légers — cuir chevelu respecté</li>\n"
    "</ul><p><strong>Conseil d'utilisation :</strong> Répartir sur cheveux mouillés, émulsionner, "
    "laisser poser 3 minutes puis rincer. Renouveler si nécessaire. En routine : 2 à 3 lavages par "
    "semaine pendant 7 à 8 semaines, en association avec le sérum fortifiant.</p>"
    "<p><em>Produit professionnel • Sans sulfate • Sans parabène • Sans silicone • "
    "Sans phénoxyéthanol • Sans colorant • Marque blanche disponible</em></p>"
)

SERUM_BODY = (
    "<p>Le <strong>Sérum fortifiant</strong> à l'<strong>extrait de Swertia Japonica</strong> "
    "est un soin sans rinçage destiné au cuir chevelu, à appliquer raie par raie après le "
    "shampoing. Sa texture fluide pénètre instantanément et ne laisse aucun résidu : ni effet "
    "gras, ni cheveux alourdis, ni contrainte de coiffage. Il complète le shampoing fortifiant au sein "
    "d'une routine à mener sur 7 à 8 semaines.</p><ul>\n"
    "<li>\n<strong>Type de cheveux :</strong> Tous types de cheveux — application sur cuir chevelu</li>\n"
    "<li>\n<strong>Résultat :</strong> Cuir chevelu traité en profondeur, sans effet gras ni résidu</li>\n"
    "</ul><p><strong>Conseil d'utilisation :</strong> Appliquer par raies sur cheveux essorés ou secs, "
    "après le shampoing fortifiant. Masser du bout des doigts pour faire pénétrer. Ne pas rincer. "
    "Laisser sécher à l'air libre ou procéder au brushing. 2 à 3 applications par semaine "
    "pendant 7 à 8 semaines.</p>"
    "<p><em>Produit professionnel • Sans sulfate • Sans parabène • Sans silicone • "
    "Sans phénoxyéthanol • Sans colorant • Marque blanche disponible</em></p>"
)

PRODUCTS = [
    dict(handle="shampoing-fortifiant", title="Shampoing fortifiant",
         sku="shampoing-fortifiant-200-ml", price="8.00", grams=250, body=SHAMPOING_BODY,
         tags=["200ml", "Les Fortifiants", "fortifiant", "shampoing", "Shampoings"]),
    dict(handle="shampoing-fortifiant-500ml", title="Shampoing fortifiant 500ml",
         sku="shampoing-fortifiant-500-ml", price="16.90", grams=600, body=SHAMPOING_BODY,
         tags=["500ml", "Les Fortifiants", "fortifiant", "shampoing", "Shampoings"]),
    dict(handle="shampoing-fortifiant-1000-ml", title="Shampoing fortifiant 1000ml",
         sku="shampoing-fortifiant-1000-ml", price="27.90", grams=1100, body=SHAMPOING_BODY,
         tags=["1000ml", "Les Fortifiants", "fortifiant", "shampoing", "Shampoings"]),
    dict(handle="serum-fortifiant", title="Sérum fortifiant",
         sku="serum-fortifiant-50-ml", price="12.50", grams=120, body=SERUM_BODY,
         tags=["50ml", "Les Fortifiants", "fortifiant", "sérum", "Soins"]),
]


def load_env():
    path = os.path.join(ROOT, ".env.local")
    env = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="ecrit reellement dans Shopify")
    args = ap.parse_args()

    env = load_env()
    store = env.get("SHOPIFY_STORE", "mylab-shop-3.myshopify.com")
    token = env.get("SHOPIFY_ADMIN_TOKEN")
    if not token:
        sys.exit("SHOPIFY_ADMIN_TOKEN absent de .env.local")

    base = "https://%s/admin/api/%s" % (store, API)
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}

    scopes = requests.get("https://%s/admin/oauth/access_scopes.json" % store,
                          headers=headers, timeout=20)
    if not scopes.ok:
        sys.exit("ERREUR : token refuse par %s (%s). Rien n'a ete fait."
                 % (store, scopes.status_code))
    handles = [s["handle"] for s in scopes.json()["access_scopes"]]
    print("scopes du token :", ", ".join(handles))
    if "write_products" not in handles:
        sys.exit("ERREUR : ce token n'a pas le scope write_products. Rien n'a ete fait.")

    for p in PRODUCTS:
        existing = requests.get("%s/products.json" % base, headers=headers,
                                params={"handle": p["handle"], "fields": "id,handle,title,status"},
                                timeout=30)
        existing.raise_for_status()
        found = existing.json()["products"]

        payload = {"product": {
            "title": p["title"],
            "handle": p["handle"],
            "body_html": p["body"],
            "vendor": VENDOR,
            "product_type": PRODUCT_TYPE,
            "tags": ", ".join(p["tags"]),
            "status": "draft",
            "variants": [{
                "sku": p["sku"],
                "price": p["price"],
                "grams": p["grams"],
                "weight": p["grams"] / 1000.0,
                "weight_unit": "kg",
                "taxable": True,
                "requires_shipping": True,
                "inventory_management": "shopify",
            }],
        }}

        if found:
            pid = found[0]["id"]
            action = "UPDATE tmpl %s" % pid
        else:
            pid = None
            action = "CREATE"

        if not args.apply:
            print("[dry-run] %-12s %s (%s, %s EUR, %sg)"
                  % (action, p["handle"], p["sku"], p["price"], p["grams"]))
            continue

        if pid:
            payload["product"]["id"] = pid
            r = requests.put("%s/products/%s.json" % (base, pid), headers=headers,
                             json=payload, timeout=30)
        else:
            r = requests.post("%s/products.json" % base, headers=headers,
                              json=payload, timeout=30)
        if not r.ok:
            print("ECHEC %s : %s %s" % (p["handle"], r.status_code, r.text[:300]))
            continue
        prod = r.json()["product"]
        print("%-12s %s -> id %s (status %s)" % (action, p["handle"], prod["id"], prod["status"]))

    if not args.apply:
        print("\nDry-run. Relancer avec --apply pour ecrire.")


if __name__ == "__main__":
    main()
