"""Crée /pages/llms-txt + redirect /llms.txt → /pages/llms-txt
   + 301 redirects pour typos shampooing* → shampoing*."""
import json
import os
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = os.environ["TOKEN"]
SHOP = "mylab-shop-3.myshopify.com"
BASE = f"https://{SHOP}/admin/api/2024-10"


def req(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("X-Shopify-Access-Token", TOKEN)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return (json.loads(raw) if raw else None), resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(errors="ignore")}, e.code


# ==== 1. /pages/llms-txt ====
print("=== 1. Create /pages/llms-txt ===")

LLMS_TXT_CONTENT = """<pre style="font-family:monospace;font-size:13px;white-space:pre-wrap;background:#f8f8f8;padding:20px;border-radius:6px;line-height:1.5;">
# MY.LAB — Laboratoire cosmétique capillaire marque blanche (France)

> MY.LAB (exploité par STARTEC SARL) est un laboratoire français coordonnant la fabrication de produits capillaires professionnels en marque blanche pour coiffeurs, salons et créateurs de marque. Basé en Provence (Cavaillon, 84300), nous collaborons avec un réseau de façonniers français pour produire des formules à 96 % d'origine naturelle, vegan, conformes au règlement CE 1223/2009 (CPNP). Dès 6 unités par référence, paiement unique à vie du dossier cosmétologique (389 € HT), 7 gammes capillaires disponibles.

## Offre principale

- [Créer sa marque capillaire](https://mylab-shop-3.myshopify.com/pages/les-etapes-de-creation-de-marque): parcours complet en 4 étapes, du test au lancement, 4 à 6 semaines
- [Catalogue produits et tarifs](https://mylab-shop-3.myshopify.com/pages/catalogue-prix-et-formules-mylab): shampooings, masques, sérums, huiles, crèmes, produits de finition, gamme homme, dès 6 unités
- [Dossier cosmétologique CPNP](https://mylab-shop-3.myshopify.com/products/creation-du-dossier-cosmetologique): 389 € HT à vie, MY.LAB assume la personne responsable UE, PIF conservé 10 ans
- [Commandes gros volume](https://mylab-shop-3.myshopify.com/pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici): dès 50 kg par référence, packaging Takemoto, devis sous 72h
- [Coffret découverte](https://mylab-shop-3.myshopify.com/products/coffret-decouverte): tester les 9 gammes MY.LAB avant de se lancer

## Personnalisation étiquettes

- [Design MY.LAB](https://mylab-shop-3.myshopify.com/pages/designs-etiquettes): impression de votre logo sur modèle standard, inclus (0 €)
- [Modèles prêts-à-personnaliser](https://mylab-shop-3.myshopify.com/pages/modeles-etiquettes): 11 modèles (Black and Yellow, Green Floral, Aquarel, Finesse, Zebra, Golden Line, Prestige, Oliver, Fresh, Number, Azul), 99 € HT par modèle
- Création sur mesure : 390 € HT

## Guides et ressources

- [CPNP et règlement CE 1223/2009](https://mylab-shop-3.myshopify.com/blogs/actualites/cpnp-et-reglement-ce-1223-2009-ce-quil-faut-savoir-avant-de-lancer-sa-marque-capillaire): obligations réglementaires UE, dépôt CPNP, PIF 10 ans, personne responsable qualifiée
- [Lancer sa marque en 4 étapes](https://mylab-shop-3.myshopify.com/blogs/actualites/lancer-sa-marque-capillaire-en-4-etapes-le-parcours-complet-du-test-a-la-premiere-livraison): délais, coûts, process complet avec tarifs concrets
- [Mention "96 % d'origine naturelle" et ISO 16128](https://mylab-shop-3.myshopify.com/blogs/actualites/96-dorigine-naturelle-que-signifie-vraiment-cette-mention-sur-un-cosmetique): norme, ingrédients naturels vs dérivés, cas MY.LAB
- [FAQ B2B MY.LAB](https://mylab-shop-3.myshopify.com/pages/faq-my-lab): réponses détaillées sur MOQ, délais, personnalisation, conformité

## À propos

- [Notre histoire](https://mylab-shop-3.myshopify.com/pages/notre-histoire-mylab): fondation, coordination filière française, valeurs
- [Le laboratoire](https://mylab-shop-3.myshopify.com/pages/mylab-laboratoire-cosmetique-fabrication-de-produits-capillaires): façonniers français, conformité ISO 22716
- [Témoignages vidéo](https://mylab-shop-3.myshopify.com/pages/temoignages): Aurélien (Bonhomme Paris), Amandine (Salon Cannes), Minh (Paris)
- [Mentions légales](https://mylab-shop-3.myshopify.com/pages/mentions-legales): STARTEC SARL, SIRET 499 500 668 00060, RCS Avignon, capital 300 000 €

## Zones desservies

MY.LAB livre partout en France (7-15 jours ouvrés) et en Europe. Pages villes dédiées :

- [Région PACA](https://mylab-shop-3.myshopify.com/pages/laboratoire-cosmetique-paca)
- [Marseille](https://mylab-shop-3.myshopify.com/pages/laboratoire-cosmetique-a-marseille)
- [Lyon](https://mylab-shop-3.myshopify.com/pages/laboratoire-cosmetique-lyon)
- [Aix-en-Provence](https://mylab-shop-3.myshopify.com/pages/laboratoire-cosmetique-aix-en-provence)

## Contact

- Téléphone : +33 4 85 69 33 47
- Email : contact@mylab-shop.com
- Adresse : 231 Avenue de la Voguette, 84300 Cavaillon, France
- [Prendre rendez-vous](https://mylab-shop-3.myshopify.com/pages/prise-de-rendez-vous)
- [Formulaire de contact](https://mylab-shop-3.myshopify.com/pages/contact)

## Réseaux sociaux

- Facebook : https://www.facebook.com/mylabfrance
- Instagram : https://www.instagram.com/mylab.france/
</pre>
"""

# Check if page already exists
d, _ = req("GET", "/pages.json?handle=llms-txt&fields=id")
if d.get("pages"):
    pid = d["pages"][0]["id"]
    _, status = req("PUT", f"/pages/{pid}.json", {
        "page": {"id": pid, "title": "MY.LAB — llms.txt", "body_html": LLMS_TXT_CONTENT}
    })
    print(f"  UPDATE /pages/llms-txt id={pid} status={status}")
else:
    d, status = req("POST", "/pages.json", {
        "page": {
            "title": "MY.LAB — llms.txt",
            "handle": "llms-txt",
            "body_html": LLMS_TXT_CONTENT,
            "published": True,
        }
    })
    if status in (200, 201):
        pid = d["page"]["id"]
        print(f"  CREATE /pages/llms-txt id={pid}")
    else:
        print(f"  FAIL create status={status} {d}")

# ==== 2. Redirect /llms.txt → /pages/llms-txt ====
print()
print("=== 2. 301 /llms.txt → /pages/llms-txt ===")
_, status = req("POST", "/redirects.json", {
    "redirect": {"path": "/llms.txt", "target": "/pages/llms-txt"}
})
print(f"  status={status}")

# ==== 3. 301 redirects shampooing-* (double o) → shampoing-* ====
print()
print("=== 3. 301 shampooing-* → shampoing-* ===")

# Get list of products with 'shampoing' handle
d, _ = req("GET", "/products.json?limit=250&fields=id,handle")
shampoing_handles = [p["handle"] for p in d.get("products", []) if p["handle"].startswith("shampoing-")]
print(f"  Found {len(shampoing_handles)} shampoing-* products")

added = 0
for h in shampoing_handles:
    typo_h = h.replace("shampoing-", "shampooing-")
    _, status = req("POST", "/redirects.json", {
        "redirect": {
            "path": f"/products/{typo_h}",
            "target": f"/products/{h}",
        }
    })
    if status in (200, 201):
        added += 1
        print(f"  301 /products/{typo_h} → /products/{h}")
    elif status == 422:
        # already exists
        pass
    else:
        print(f"  FAIL {typo_h} status={status}")

# Also the /products/shampoing-* handle itself (without suffix)
_, status = req("POST", "/redirects.json", {
    "redirect": {"path": "/products/shampooing", "target": "/pages/la-boutique-my-lab"}
})

# Collections
d, _ = req("GET", "/custom_collections.json?limit=250&fields=handle")
d2, _ = req("GET", "/smart_collections.json?limit=250&fields=handle")
coll_handles = [c["handle"] for c in d.get("custom_collections", []) + d2.get("smart_collections", []) if c["handle"].startswith("shampoings-")]
print(f"\n  Found {len(coll_handles)} shampoings-* collections")
for h in coll_handles:
    typo_h = h.replace("shampoings-", "shampooings-")
    _, status = req("POST", "/redirects.json", {
        "redirect": {"path": f"/collections/{typo_h}", "target": f"/collections/{h}"}
    })
    if status in (200, 201):
        added += 1
        print(f"  301 /collections/{typo_h} → /collections/{h}")

print(f"\n  Total redirects added: {added}")
