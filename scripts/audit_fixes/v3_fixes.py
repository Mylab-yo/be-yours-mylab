"""V3 fixes : page partez-a-la-decouverte + frontpage collection."""
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


# ==== 1. Page partez-a-la-decouverte ====
print("=== 1. Finir /pages/partez-a-la-decouverte-de-votre-marque ===")

PARTEZ_BODY = """<h2>Jeu concours MY.LAB</h2>

<p><strong>Vous êtes gérant.e de votre salon de coiffure ou barber et vous aimeriez créer votre marque, ou vous avez déjà créé votre marque avec MY.LAB&nbsp;?</strong></p>

<p>Partez à la découverte de votre marque grâce à notre jeu concours&nbsp;!</p>

<h3>Comment participer&nbsp;?</h3>
<p>Pour participer, il vous suffit de nous suivre sur un de nos réseaux sociaux et de nous envoyer un message privé avec votre projet&nbsp;:</p>

<ul>
  <li><a href="https://www.facebook.com/mylabfrance" target="_blank" rel="noopener"><strong>Facebook&nbsp;: @mylabfrance</strong></a></li>
  <li><a href="https://www.instagram.com/mylab_shop/" target="_blank" rel="noopener"><strong>Instagram&nbsp;: @mylab_shop</strong></a></li>
</ul>

<h3>Ce que vous pouvez gagner</h3>
<p>Les gagnants sont accompagnés gratuitement sur la première étape de création de leur marque capillaire avec MY.LAB (coffret découverte offert ou remise sur dossier cosmétologique).</p>

<h3>Plus d'informations</h3>
<p>Pour connaître les détails du prochain jeu concours ou participer dès maintenant, contactez-nous&nbsp;:</p>
<ul>
  <li>Par email&nbsp;: <a href="mailto:contact@mylab-shop.com">contact@mylab-shop.com</a></li>
  <li>Par téléphone&nbsp;: <a href="tel:+33485693347">04 85 69 33 47</a></li>
</ul>

<p><a href="/pages/contact">Nous contacter →</a></p>
"""

p, _ = req("GET", "/pages.json?handle=partez-a-la-decouverte-de-votre-marque&fields=id")
if p and p.get("pages"):
    pid = p["pages"][0]["id"]
    _, status = req("PUT", f"/pages/{pid}.json", {
        "page": {"id": pid, "body_html": PARTEZ_BODY}
    })
    print(f"  UPDATE partez-a-la-decouverte status={status}")
else:
    print("  SKIP: page not found")

# ==== 2. Remplir /collections/frontpage avec 6 produits phares ====
print()
print("=== 2. Peupler /collections/frontpage (6 produits phares) ===")

# 6 handles phares qui existent et sont actifs
FRONTPAGE_HANDLES = [
    "coffret-decouverte",
    "shampoing-nourrissant",
    "masque-nourrissant",
    "creme-nourrissante",
    "serum-finition-ultime",
    "bain-miraculeux",
]

# Get IDs
handles_str = ",".join(FRONTPAGE_HANDLES)
d, _ = req("GET", f"/products.json?handle={handles_str.replace(',','+OR+handle:')}&fields=id,handle,status")
# Actually, handle query accepts multiple via handle=x&handle=y but simpler: query each
prod_ids = []
for h in FRONTPAGE_HANDLES:
    d, _ = req("GET", f"/products.json?handle={h}&fields=id,handle,status")
    prods = d.get("products", [])
    if prods:
        p = prods[0]
        if p.get("status") == "active":
            prod_ids.append(p["id"])
            print(f"  found: {h} (id={p['id']}, status={p['status']})")
        else:
            print(f"  SKIP {h} (status={p.get('status')})")
    else:
        print(f"  SKIP {h} (not found)")

# Add each product to collection 654841413966 (frontpage)
FRONTPAGE_ID = 654841413966

# Check existing
d, _ = req("GET", f"/collects.json?collection_id={FRONTPAGE_ID}&limit=250&fields=product_id")
existing_ids = set(c["product_id"] for c in d.get("collects", []))
print(f"  existing in frontpage: {len(existing_ids)}")

added = 0
for pid in prod_ids:
    if pid in existing_ids:
        continue
    d, status = req("POST", "/collects.json", {
        "collect": {"collection_id": FRONTPAGE_ID, "product_id": pid}
    })
    if status in (200, 201):
        added += 1
    else:
        print(f"  FAIL add pid={pid} status={status}")

# Final count
d, _ = req("GET", f"/collects.json?collection_id={FRONTPAGE_ID}&limit=250&fields=id")
final = len(d.get("collects", []))
print(f"  added {added} → final collection size: {final}")

print()
print("Done.")
