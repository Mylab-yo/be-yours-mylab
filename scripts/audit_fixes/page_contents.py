"""Contenus pour les corrections d'audit MyLab Shopify.

Seuls les contenus RÉELLEMENT nécessaires sont ici — les pages vides
selon l'audit qui avaient déjà du contenu réel ne sont pas retouchées.
"""

# /products/coffret-decouverte : réécriture du texte IA brut (audit §4.3)
COFFRET_DECOUVERTE_BODY = """<p>Le <strong>coffret découverte MY.LAB</strong> vous permet de tester l'ensemble de nos gammes capillaires professionnelles avant de vous lancer dans la création de votre marque.</p>

<h3>Nos 9 gammes capillaires</h3>
<ul>
  <li><strong>Gamme Nourrissante</strong> — shampoing, masque et crème de coiffage (200 ml)</li>
  <li><strong>Gamme HA Repulpe</strong> — shampoing, masque et crème de coiffage (200 ml)</li>
  <li><strong>Gamme Purifiante</strong> — shampoing et spray (200 ml)</li>
  <li><strong>Gamme Boucles</strong> — shampoing, masque et crème de coiffage (200 ml)</li>
  <li><strong>Gamme Lissante</strong> — shampoing, masque et crème de coiffage (200 ml)</li>
  <li><strong>Gamme Volumatrice</strong> — shampoing, masque et crème de coiffage (200 ml)</li>
  <li><strong>Gamme Protectrice de Couleur</strong> — shampoing, masque et crème de coiffage (200 ml)</li>
  <li><strong>Gamme Finition</strong> — Bain miraculeux et sérum finition (50 ml)</li>
  <li><strong>Gamme Déjaunisseur</strong> — shampoing et masque (200 ml)</li>
</ul>

<p>Ainsi qu'un <strong>masque réparateur sans rinçage</strong> (200 ml).</p>

<h3>Pourquoi commander le coffret ?</h3>
<ul>
  <li>Valider nos textures, parfums et performances sur cheveux avant de passer en production</li>
  <li>Tester les formules auprès de vos clients ou testeurs</li>
  <li>Constituer une base de travail concrète pour choisir les gammes de votre marque</li>
</ul>

<h3>Caractéristiques</h3>
<ul>
  <li><strong>Origine :</strong> 100 % made in France</li>
  <li><strong>Formulation :</strong> vegan, sans sulfates, sans silicones, sans parabènes</li>
  <li><strong>Conformité :</strong> CPNP et PIF gérés par MY.LAB</li>
  <li><strong>Marque blanche :</strong> toutes ces formules sont disponibles avec votre branding dès 6 unités</li>
</ul>

<p><em>Idéal pour démarrer votre marque capillaire professionnelle.</em></p>
"""


# /pages/creation-dossier-cosmetologique : 207 chars -> contenu complet
DOSSIER_COSMETO_BODY = """<h2>Créer votre dossier cosmétologique avec MY.LAB</h2>

<p><strong>Le dossier cosmétologique est l'étape réglementaire indispensable pour commercialiser légalement vos produits capillaires en Europe. Paiement unique à vie : 389 € HT.</strong></p>

<h3>À quoi sert le dossier cosmétologique&nbsp;?</h3>
<p>Conformément au <strong>règlement CE n°1223/2009</strong>, tout produit cosmétique mis sur le marché européen doit être&nbsp;:</p>
<ul>
  <li>Déclaré au <strong>CPNP (Cosmetic Products Notification Portal)</strong> de la Commission européenne</li>
  <li>Accompagné d'un <strong>Dossier d'Information Produit (PIF)</strong> conservé pendant 10 ans</li>
  <li>Associé à un <strong>responsable qualifié</strong> établi dans l'Union européenne</li>
</ul>

<h3>Ce que MY.LAB prend en charge</h3>
<p>Pour <strong>389 € HT payés une seule fois (à vie)</strong>, MY.LAB&nbsp;:</p>
<ul>
  <li>Enregistre votre marque sur votre compte MY.LAB</li>
  <li>Dépose votre marque au CPNP pour chaque référence</li>
  <li>Crée vos codes-barres (EAN-13)</li>
  <li>Conserve le PIF pendant 10 ans en tant que responsable qualifié</li>
  <li>Assure la conformité réglementaire tout au long de la durée de vie de votre marque</li>
</ul>

<p><strong>Pas de transfert de responsabilité MY.LAB &rarr; client&nbsp;:</strong> nous restons responsables de la formule et de la conformité, vous restez responsable de votre marque (communication, ventes, après-vente).</p>

<h3>Délais</h3>
<ul>
  <li>Enregistrement CPNP&nbsp;: 5 à 10 jours ouvrés après transmission des informations</li>
  <li>Création des codes-barres&nbsp;: sous 48&nbsp;h</li>
</ul>

<p><a href="/products/dossier-cosmetologique">Commander mon dossier cosmétologique &rarr;</a></p>
"""


# Pages à supprimer : slugs erronés dans le sitemap (audit §4.7)
PAGES_TO_DELETE = [
    "https-mylab-configurateur-vercel-app-configurateur-mode-studio",
    "https-mylab-configurateur-vercel-app-configurateur-mode-template",
    "https-mylab-configurateur-vercel-app-configurateur-mode-template-1",
]

# Page content updates : handle -> (title, body_html)
# On ne mets à jour que les pages vraiment problématiques.
PAGE_UPDATES = {
    "creation-dossier-cosmetologique": (
        "Créer votre dossier cosmétologique",
        DOSSIER_COSMETO_BODY,
    ),
}

# Produits à mettre à jour (handle -> new body_html)
PRODUCT_UPDATES = {
    "coffret-decouverte": COFFRET_DECOUVERTE_BODY,
}

# Slugs à renommer + 301 automatique
PAGE_SLUG_RENAMES = {
    "creer-sa-marque-de-cosmetique-capillaire-profesionnel-en-ligne":
        "creer-sa-marque-de-cosmetique-capillaire-professionnel-en-ligne",
}

COLLECTION_SLUG_RENAMES = {
    "cremes-des-coiffage-sans-rincage": "cremes-de-coiffage-sans-rincage",
    "cremes-des-coiffage-sans-rincage-testeurs": "cremes-de-coiffage-sans-rincage-testeurs",
}
