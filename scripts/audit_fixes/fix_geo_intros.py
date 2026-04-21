"""Différencie les intros des pages SEO géo Lyon et PACA.
Les autres pages (Marseille, Aix) ont déjà des intros bien différenciées."""
import json
import os
import sys
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
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read()), resp.status


# --- LYON : nouvelle intro centrée sur Lyon ---
LYON_INTRO_NEW = """<h1>Laboratoire cosmétique Lyon</h1>

<p><strong>Vous êtes coiffeur, gérant.e de salon ou créateur.trice de marque dans la région lyonnaise&nbsp;?</strong> MY.LAB accompagne les professionnels de la coiffure de Lyon et du Rhône dans la création de leur propre gamme capillaire en marque blanche, dès 6 unités par référence.</p>

<h2>Pourquoi passer par MY.LAB depuis Lyon</h2>
<p>Notre laboratoire, basé en Provence (Cavaillon), coordonne un réseau de façonniers français certifiés pour proposer aux salons lyonnais une alternative professionnelle aux grandes marques de distribution&nbsp;:</p>
<ul>
  <li><strong>Formules à 96&nbsp;% d'origine naturelle</strong> — vegan, sans sulfates, sans silicones, sans parabènes</li>
  <li><strong>Conformité réglementaire</strong> CPNP et règlement CE 1223/2009 intégralement gérée par MY.LAB</li>
  <li><strong>Livraison partout en région Auvergne-Rhône-Alpes</strong> sous 7 à 15 jours ouvrés, avec suivi dédié</li>
  <li><strong>Dès 6 unités par référence</strong> — testez votre marché lyonnais sans stock initial massif</li>
</ul>

<h2>De la formule à la livraison à Lyon</h2>
<p>En tant que coiffeur lyonnais, voici le parcours type pour lancer votre marque avec MY.LAB&nbsp;: test du coffret découverte (1-2 semaines), dossier cosmétologique (389&nbsp;€ HT à vie), personnalisation des étiquettes (dès 0&nbsp;€ pour le design MY.LAB), puis première commande livrée à Lyon en 6 à 8 semaines maximum.</p>

<p>Nous collaborons déjà avec plusieurs salons du Rhône et de la Loire, et connaissons les attentes spécifiques de la clientèle lyonnaise&nbsp;: finitions naturelles, packaging minimaliste, gammes barber premium. Nos 7 familles de produits (shampooings, masques, sérums, huiles, crèmes, produits de finition, gamme homme) couvrent tous les usages professionnels.</p>

<h2>Passer à l'action</h2>
<p>Pour discuter de votre projet de marque capillaire à Lyon, prenez rendez-vous avec notre équipe&nbsp;: <a href="tel:+33485693347">04 85 69 33 47</a> ou <a href="mailto:contact@mylab-shop.com">contact@mylab-shop.com</a>.</p>

<p>
  <a href="/pages/les-etapes-de-creation-de-marque">Voir les 4 étapes →</a><br>
  <a href="/pages/contact">Nous contacter →</a>
</p>
"""

# --- PACA : nouvelle intro centrée sur toute la région PACA (Nice, Marseille, Aix, Avignon, Toulon) ---
PACA_INTRO_NEW = """<h1>Laboratoire cosmétique PACA</h1>

<p><strong>MY.LAB est LE laboratoire français de cosmétiques capillaires en marque blanche basé en région Provence-Alpes-Côte d'Azur, à Cavaillon (Vaucluse).</strong> Nous servons quotidiennement les salons de coiffure, barbers et créateurs de marque de tout le Sud-Est&nbsp;: Nice, Marseille, Toulon, Avignon, Aix-en-Provence, Cannes, Monaco, Montpellier.</p>

<h2>Un laboratoire régional ancré en Provence</h2>
<p>Installés depuis 2017 au cœur de la Provence (231 Avenue de la Voguette, 84300 Cavaillon), nous coordonnons un réseau de façonniers français certifiés pour fabriquer des produits capillaires professionnels en marque blanche à des prix accessibles.</p>

<ul>
  <li><strong>Proximité géographique</strong>&nbsp;: livraison express en région PACA sous 4 à 7 jours, rendez-vous sur site possibles</li>
  <li><strong>Formules 96&nbsp;% naturelles</strong>, vegan, sans sulfate, sans silicone, sans parabène</li>
  <li><strong>Conformité CPNP et règlement CE 1223/2009</strong> entièrement prise en charge</li>
  <li><strong>Dès 6 unités par référence</strong>, avec tarifs dégressifs jusqu'à –29&nbsp;% sur le volume</li>
</ul>

<h2>Clients PACA qui nous font confiance</h2>
<p>Parmi nos clients de la région&nbsp;: Amandine (salon de coiffure à Cannes, qui commercialise sa gamme MY.LAB depuis 2 ans), Minh (professionnel des cheveux à Paris mais clients majoritairement azuréens), et plusieurs salons de Nice, Marseille, Aix et Avignon qui ont lancé leur propre marque. Découvrez leurs <a href="/pages/temoignages">témoignages vidéo</a>.</p>

<h2>Pages dédiées aux villes de la région</h2>
<ul>
  <li><a href="/pages/laboratoire-cosmetique-a-marseille">Laboratoire cosmétique Marseille</a></li>
  <li><a href="/pages/laboratoire-cosmetique-aix-en-provence">Laboratoire cosmétique Aix-en-Provence</a></li>
</ul>

<h2>Démarrer votre marque depuis la région PACA</h2>
<p>Nous vous accompagnons de la formulation à la livraison en 4 à 8 semaines selon la complexité du projet. Le dossier cosmétologique (paiement unique 389&nbsp;€ HT à vie) inclut CPNP, PIF et codes-barres.</p>

<p>
  <a href="/pages/les-etapes-de-creation-de-marque">Voir les étapes de création →</a><br>
  <a href="/pages/prise-de-rendez-vous">Prendre rendez-vous dans notre labo à Cavaillon →</a>
</p>
"""

updates = [
    ("laboratoire-cosmetique-lyon", LYON_INTRO_NEW),
    ("laboratoire-cosmetique-paca", PACA_INTRO_NEW),
]

for handle, new_body in updates:
    d, _ = req("GET", f"/pages.json?handle={handle}&fields=id")
    if not d.get("pages"):
        print(f"  SKIP {handle} (not found)")
        continue
    pid = d["pages"][0]["id"]
    _, status = req("PUT", f"/pages/{pid}.json", {"page": {"id": pid, "body_html": new_body}})
    print(f"  UPDATE {handle} id={pid} status={status}")
