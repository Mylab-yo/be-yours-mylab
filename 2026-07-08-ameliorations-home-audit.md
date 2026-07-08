# Plan d'amélioration home mylab-shop.com (suite audit UX/conversion) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Traiter les 6 points d'attention de l'audit du 08/07/2026 : segmentation offre standard vs gros volume, catalogue visible depuis la home, hiérarchie CTA unique (« Prendre rendez-vous »), extrait vidéo témoignage sur la home, liens légaux au footer, restructuration du menu « ACHETER ».

**Architecture:** Le site est un thème Shopify Be Yours customisé (couche `ml-`/`mylab-`). Les changements sont quasi exclusivement des éditions de templates JSON (`templates/index.json`, `sections/footer-group.json`) qui composent des sections Liquid existantes — aucun nouveau fichier Liquid n'est nécessaire. Deux points (menu de navigation, pages légales/Règles) se règlent dans l'admin Shopify, pas dans le repo : ils sont documentés en Task 6 comme checklist admin.

**Tech Stack:** Shopify Liquid / templates JSON OS 2.0, Shopify CLI (`shopify theme dev` / `push --development`), Python pour valider le JSON. Pas de bundler, pas de test runner.

## Global Constraints

- **Priorité absolue aux modules natifs du thème** : toute modification doit utiliser une section/un module existant du thème (Be Yours ou couche `ml-`) via ses settings de schema. Interdits sauf impossibilité démontrée : `custom-liquid`, HTML avec styles inline, nouveau fichier Liquid. Si un besoin ne rentre dans aucun module existant, le signaler à Yoann avant d'implémenter.
- Store : `mylab-shop-3.myshopify.com`. Vérification visuelle via `shopify theme dev --store mylab-shop-3.myshopify.com` ; déploiement de validation via `shopify theme push --store mylab-shop-3.myshopify.com --development`. Ne JAMAIS pousser sur le thème live dans ce plan.
- Palette : beige `#f5f0eb`, noir `#1a1a1a`, or `#c5a467`, blanc `#ffffff`. Polices : `'Cormorant Garamond', serif` (titres), `'DM Sans'` (corps).
- Pas de test runner : le cycle « test » de chaque tâche = validation JSON par Python + contrôle visuel dans le préview `theme dev` avec résultat attendu explicite.
- Ne pas toucher à `assets/mylab-product.js`, au cart drawer MyLab, ni réactiver le `<cart-drawer>` natif Be Yours.
- Toute nouvelle section dans `templates/index.json` doit être ajoutée **à la fois** dans l'objet `"sections"` et dans le tableau `"order"` (sinon Shopify l'ignore ou plante le template).
- Les URL internes dans les templates JSON utilisent le format déjà présent dans le fichier : `shopify://pages/...` dans `index.json`, chemins relatifs `/pages/...` dans `footer-group.json`.
- Un commit par tâche, messages en français, convention existante du repo (`feat(home): ...`, `fix(footer): ...`).

---

### Task 0 : Préparation — branche et préview

**Files:**
- Aucun fichier modifié (setup uniquement).

**Interfaces:**
- Consumes: rien.
- Produces: branche `feat/audit-home-2026-07-08` active + serveur `theme dev` qui tourne pour toutes les vérifications visuelles des tâches 1 à 5.

- [x] **Step 1 : Créer la branche de travail depuis `master`** *(corrigé : le repo est `d:\be-yours-mylab`, et la branche courante `chore/odoo-colisage-capacite-effective` est du travail Odoo sans rapport — on part de master)*

```bash
git -C "d:/be-yours-mylab" checkout master
git -C "d:/be-yours-mylab" checkout -b feat/audit-home-2026-07-08
```

Attendu : `Switched to a new branch 'feat/audit-home-2026-07-08'`.

- [x] **Step 2 : Vérifications visuelles** *(adapté : exécution autonome sans navigateur — les contrôles visuels de chaque tâche sont remplacés par la validation JSON Python, puis un contrôle visuel unique par Yoann sur le thème de développement après le push de la Task 7)*

---

### Task 1 : Section « Deux façons de commander » (segmentation offre standard vs gros volume)

Point d'audit traité : *« Un prospect qui veut juste 6 flacons peut se sentir hors cible »* — la home doit montrer explicitement les deux parcours côte à côte, avec le ticket d'entrée de chacun.

**Files:**
- Modify: `templates/index.json` (objet `sections` + tableau `order`)

**Interfaces:**
- Consumes: la section Liquid existante `sections/multicolumn.liquid` (mêmes clés de settings que la section `etiquettes_section` déjà présente dans `index.json`).
- Produces: une clé de section `offres_segmentation` dans `index.json`, placée dans `order` entre `intro_text` et `guarantees_section`. Les tâches suivantes ne dépendent pas d'elle mais Task 2 insère `featured_bestsellers` juste après elle dans `order`.

- [x] **Step 1 : Ajouter la section dans l'objet `sections` de `templates/index.json`**

Insérer l'objet suivant juste après le bloc `"intro_text": { ... },` (après son accolade fermante et sa virgule, ligne ~258) :

```json
    "offres_segmentation": {
      "type": "multicolumn",
      "blocks": {
        "offre_boutique": {
          "type": "column",
          "settings": {
            "background_color": "#f5f0eb",
            "heading_color": "#1a1a1a",
            "text_color": "#333333",
            "title": "Dès 6 unités — La boutique pro",
            "title_size": "h3",
            "text": "<p>Commandez vos produits en marque blanche directement en ligne, à partir de 6 unités par référence. Étiquette à votre logo, réassort en autonomie, expédition rapide.</p>",
            "show_popup": false,
            "popup_image_position": "top",
            "justify_text": false,
            "button_label": "Accéder à la boutique",
            "button_link": "shopify://pages/la-boutique-my-lab",
            "button_style_secondary": false,
            "enable_highlight": false,
            "highlight_style": "marker"
          }
        },
        "offre_volume": {
          "type": "column",
          "settings": {
            "background_color": "#1a1a1a",
            "heading_color": "#c5a467",
            "text_color": "#ffffff",
            "title": "Dès 50 kg — Production en série",
            "title_size": "h3",
            "text": "<p>Lancez votre production en gros volume : packaging Takemoto, tarifs dégressifs, formules exclusives. Devis personnalisé sous 72 h.</p>",
            "show_popup": false,
            "popup_image_position": "top",
            "justify_text": false,
            "button_label": "Configurer ma commande",
            "button_link": "shopify://pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici",
            "button_style_secondary": true,
            "enable_highlight": false,
            "highlight_style": "marker"
          }
        }
      },
      "block_order": [
        "offre_boutique",
        "offre_volume"
      ],
      "settings": {
        "image_ratio": "adapt",
        "image_position": "center center",
        "text_alignment": "center",
        "show_divider": false,
        "image_width": "full",
        "columns_desktop": 2,
        "open_in_new_tab": false,
        "heading": "Deux façons de <strong>commander</strong>",
        "heading_size": "h1",
        "heading_alignment": "center",
        "heading_tag": "h2",
        "mobile_text_alignment": "left",
        "columns_mobile": "1",
        "swipe_on_mobile": false,
        "colors_highlight": "#c5a467",
        "padding_top": 40,
        "padding_bottom": 40,
        "card_border_radius": 12,
        "enable_highlight": true,
        "highlight_style": "solid-color"
      }
    },
```

- [x] **Step 2 : Ajouter la section dans le tableau `order`**

Dans le tableau `"order"` en fin de fichier, insérer `"offres_segmentation",` entre `"intro_text",` et `"guarantees_section",` :

```json
    "intro_text",
    "offres_segmentation",
    "guarantees_section",
```

*(corrigé : l'extrait initial omettait `stats_banner`, `perimeter_intro` et `perimeter_columns` présents en tête d'`order` — seule compte l'insertion entre `intro_text` et `guarantees_section`)*

- [x] **Step 3 : Valider le JSON**

```bash
python -c "import json; json.load(open('templates/index.json', encoding='utf-8')); print('OK')"
```

Attendu : `OK`. En cas d'erreur, corriger la virgule/accolade fautive avant de continuer.

- [ ] **Step 4 : Vérifier visuellement dans le préview**

Recharger `http://127.0.0.1:9292`. Attendu : sous le texte d'intro « Votre marque capillaire clé en main », une section « Deux façons de commander » avec deux cartes côte à côte — carte beige « Dès 6 unités » (bouton plein « Accéder à la boutique ») et carte noire « Dès 50 kg » (bouton secondaire « Configurer ma commande »). Sur mobile (réduire la fenêtre < 750 px) : les deux cartes s'empilent.

- [x] **Step 5 : Commit**

```bash
git add templates/index.json
git commit -m "feat(home): section segmentation offre boutique vs gros volume"
```

---

### Task 2 : Catalogue visible depuis la home (featured collection avec prix)

Points d'audit traités : *« Catalogue de 70+ formules pas visible depuis la home »* et *« Pas de prix affichés »* — une grille de produits best-sellers montre à la fois les formules et leurs prix réels, sans inventer de fourchette de prix en dur.

**Files:**
- Modify: `templates/index.json` (objet `sections` + tableau `order`)

**Interfaces:**
- Consumes: la section Liquid existante `sections/featured-collection.liquid` (settings : `collection`, `products_to_show`, `show_view_all`, `heading`, `heading_size`, `heading_alignment`, `heading_tag` — les autres settings prennent leur valeur par défaut du schema). ~~La collection Shopify `best-sellers`~~ **Corrigé (vérifié le 08/07 via `/collections.json`) : la collection `best-sellers` existe mais est VIDE. On utilise `frontpage` (« Page d'accueil », 6 produits phares avec prix). Quand Yoann aura peuplé `best-sellers`, il suffira de changer la collection dans l'éditeur de thème.**
- Produces: une clé de section `featured_bestsellers` dans `index.json`, placée dans `order` juste après `offres_segmentation` (créée en Task 1).

- [x] **Step 1 : Ajouter la section dans l'objet `sections` de `templates/index.json`**

Insérer juste après le bloc `"offres_segmentation": { ... },` (ajouté en Task 1) :

```json
    "featured_bestsellers": {
      "type": "featured-collection",
      "settings": {
        "collection": "frontpage",
        "products_to_show": 8,
        "show_view_all": true,
        "heading": "Nos formules <strong>best-sellers</strong>",
        "heading_size": "h1",
        "heading_alignment": "center",
        "heading_tag": "h2",
        "padding_top": 40,
        "padding_bottom": 40
      }
    },
```

- [x] **Step 2 : Ajouter la section dans le tableau `order`**

Dans `"order"`, insérer `"featured_bestsellers",` juste après `"offres_segmentation",` :

```json
    "intro_text",
    "offres_segmentation",
    "featured_bestsellers",
    "guarantees_section",
```

- [x] **Step 3 : Valider le JSON**

```bash
python -c "import json; json.load(open('templates/index.json', encoding='utf-8')); print('OK')"
```

Attendu : `OK`.

- [ ] **Step 4 : Vérifier visuellement dans le préview**

Recharger le préview. Attendu : une grille « Nos formules best-sellers » avec jusqu'à 8 cartes produit **affichant les prix**, et un bouton « Voir tout » menant à la collection. Cliquer une carte produit : la page produit s'ouvre avec la couche de tarifs dégressifs MyLab intacte (boutons de quantité `ml-qty-btn` visibles).

**Si la grille est vide** : la collection `best-sellers` n'existe plus ou n'a pas de produits publiés — le vérifier dans Admin Shopify > Produits > Collections, et remplacer `"collection": "best-sellers"` par le handle d'une collection peuplée (les handles se lisent dans l'URL de la collection dans l'admin). Ne pas laisser la section vide en préview.

- [x] **Step 5 : Commit**

```bash
git add templates/index.json
git commit -m "feat(home): grille best-sellers avec prix depuis la home"
```

---

### Task 3 : Extrait vidéo témoignage sur la home (module natif `video`)

> **⚠️ ANNULÉE après revue visuelle de Yoann (08/07)** : la vidéo (format portrait, miniature démesurée) n'était pas esthétique sur la home — section retirée (commit `36c4b0d`). Le parcours témoignages reste couvert par la section `temoignages_video` (bouton « Découvrir les interviews »).

Point d'audit traité : *« aucun extrait directement visible »* — on embarque la vidéo d'Aurélien (Bonhomme Paris), déjà hébergée dans les fichiers Shopify (`montage-bonhomme-v4_ygCa9teq.mp4`, utilisée sur `/pages/temoignages`), via la **section native `video` du thème** (`sections/video.liquid`) : poster + lecture au clic (`deferred-media`), aucun HTML custom. Le contexte texte (qui est Aurélien, bouton « Découvrir les interviews ») est déjà fourni par la section `temoignages_video` juste au-dessus — la section vidéo n'a donc pas besoin de titre propre.

**Files:**
- Modify: `templates/index.json` (objet `sections` + tableau `order`)

**Interfaces:**
- Consumes: la section native `sections/video.liquid` (settings : `video` (type `video`, vidéo hébergée Shopify), `description` (texte d'accessibilité), `enable_video_looping`, `full_width`, `heading`, `padding_top`, `padding_bottom`). Le fichier vidéo Shopify `montage-bonhomme-v4_ygCa9teq.mp4` (Contenu > Fichiers).
- Produces: une clé de section `temoignage_video_home` dans `index.json`, placée dans `order` entre `temoignages_video` et `cta_final`.

- [x] **Step 1 : Ajouter la section dans l'objet `sections` de `templates/index.json`**

Insérer juste après le bloc `"temoignages_video": { ... },` (après son accolade fermante et sa virgule, ligne ~788) :

```json
    "temoignage_video_home": {
      "type": "video",
      "settings": {
        "video": "shopify://files/videos/montage-bonhomme-v4_ygCa9teq.mp4",
        "description": "Interview d'Aurélien, fondateur de Bonhomme Paris, client MY.LAB",
        "enable_video_looping": false,
        "full_width": false,
        "heading": "",
        "padding_top": 0,
        "padding_bottom": 60
      }
    },
```

- [x] **Step 2 : Ajouter la section dans le tableau `order`**

Dans `"order"`, insérer `"temoignage_video_home",` entre `"temoignages_video",` et `"cta_final",` :

```json
    "testimonials_section",
    "temoignages_video",
    "temoignage_video_home",
    "cta_final",
```

- [x] **Step 3 : Valider le JSON**

```bash
python -c "import json; json.load(open('templates/index.json', encoding='utf-8')); print('OK')"
```

Attendu : `OK`.

- [ ] **Step 4 : Vérifier visuellement dans le préview**

Recharger le préview, descendre sous « Les témoignages de nos clients ». Attendu : un lecteur vidéo avec la miniature de l'interview d'Aurélien, lecture au clic (pas d'autoplay). Lancer la lecture pour confirmer que le fichier se charge.

**Si la vidéo ne s'affiche pas** (la référence `shopify://files/videos/...` peut ne pas résoudre si le mp4 n'est pas enregistré comme média vidéo) : NE PAS retomber sur du `custom-liquid`. Sélectionner la vidéo via l'éditeur de thème — `shopify theme push --store mylab-shop-3.myshopify.com --development --only templates/index.json`, puis Admin > Boutique en ligne > Thèmes > thème de développement > Personnaliser > page d'accueil > section Vidéo > choisir `montage-bonhomme-v4_ygCa9teq.mp4` dans le picker, enregistrer, puis rapatrier la valeur exacte : `shopify theme pull --store mylab-shop-3.myshopify.com --development --only templates/index.json`.

- [x] **Step 5 : Commit**

```bash
git add templates/index.json
git commit -m "feat(home): extrait video temoignage Bonhomme Paris via section native video"
```

---

### Task 4 : Hiérarchie CTA — « Prendre rendez-vous » comme CTA principal unique

Point d'audit traité : *« Le parcours n'est pas linéaire […] Un CTA principal unique (probablement Prendre RDV) »*. Le CTA primaire (bouton plein) devient partout « Prendre rendez-vous » → `/pages/prise-de-rendez-vous` (page dédiée existante, section `ml-rendez-vous`) ; « Découvrir la boutique » passe en CTA secondaire. Corrige aussi un lien incohérent : la section RDV de la home étiquetée « Prendre un RDV » pointe aujourd'hui vers `/pages/contact` au lieu de la page de prise de rendez-vous.

**Files:**
- Modify: `templates/index.json` (blocs `slideshow_hero.blocks.slide_main`, `rdv_section.blocks.button`, `cta_final.blocks.button`)

> **Corrigé :** les extraits ci-dessous montrent des URLs échappées `shopify:\/\/pages\/...` — le fichier réel utilise `shopify://pages/...` (non échappé). Appliquer les remplacements avec le format réel du fichier.

**Interfaces:**
- Consumes: la page existante `/pages/prise-de-rendez-vous` (template `templates/page.prise-de-rendez-vous.json`).
- Produces: rien pour les autres tâches (modification de copy/liens uniquement).

- [x] **Step 1 : Hero — slide principal**

Dans `slideshow_hero.blocks.slide_main.settings`, remplacer :

```json
            "button_label": "Découvrir la boutique",
            "button_link": "shopify:\/\/pages\/la-boutique-my-lab",
            "button_size": "medium",
            "button_style_secondary": false,
            "button_alt_label": "Les étapes de création",
            "button_alt_link": "shopify:\/\/pages\/etapes-creation",
```

par :

```json
            "button_label": "Prendre rendez-vous",
            "button_link": "shopify:\/\/pages\/prise-de-rendez-vous",
            "button_size": "medium",
            "button_style_secondary": false,
            "button_alt_label": "Découvrir la boutique",
            "button_alt_link": "shopify:\/\/pages\/la-boutique-my-lab",
```

- [x] **Step 2 : Section RDV — corriger le lien du bouton**

Dans `rdv_section.blocks.button.settings`, remplacer :

```json
            "button_label": "Prendre un RDV",
            "button_link": "shopify:\/\/pages\/contact",
```

par :

```json
            "button_label": "Prendre rendez-vous",
            "button_link": "shopify:\/\/pages\/prise-de-rendez-vous",
```

- [x] **Step 3 : CTA final — RDV en primaire**

Dans `cta_final.blocks.button.settings`, remplacer :

```json
            "button_label": "Nous contacter",
            "button_link": "shopify:\/\/pages\/contact",
```

par :

```json
            "button_label": "Prendre rendez-vous",
            "button_link": "shopify:\/\/pages\/prise-de-rendez-vous",
```

(le bouton secondaire « Découvrir la boutique » de `cta_final` reste inchangé).

- [x] **Step 4 : Valider le JSON**

```bash
python -c "import json; json.load(open('templates/index.json', encoding='utf-8')); print('OK')"
```

Attendu : `OK`.

- [ ] **Step 5 : Vérifier visuellement dans le préview**

Recharger le préview et vérifier les trois emplacements : (1) hero slide 1 — bouton plein « Prendre rendez-vous », bouton contour « Découvrir la boutique » ; (2) section noire « Prenez rendez-vous avec un conseiller » — le bouton mène à `/pages/prise-de-rendez-vous` (cliquer pour confirmer que la page de prise de RDV se charge) ; (3) CTA final « Lancez-vous dans l'aventure ! » — bouton or « Prendre rendez-vous ». Aucun CTA primaire de la home ne doit plus pointer vers `/pages/contact`.

- [x] **Step 6 : Commit**

```bash
git add templates/index.json
git commit -m "feat(home): CTA principal unique Prendre rendez-vous + fix lien section RDV"
```

---

### Task 5 : Footer — activer le lien Mentions légales

Point d'audit traité : *« Pas de liens vers les mentions légales, CGV, politique de retour »*. Le code de `sections/ml-footer.liquid` (lignes 342-362) affiche **déjà** automatiquement toutes les règles Shopify (`shop.policies` : CGV, confidentialité, remboursement, expédition) dès qu'elles sont remplies dans l'admin, plus un lien « Mentions légales » optionnel piloté par le setting `mentions_legales_link`. Côté repo il n'y a donc qu'un setting à renseigner ; le remplissage des Règles est une action admin (Task 6).

**Files:**
- Modify: `sections/footer-group.json` (settings de la section `ml-footer`)

**Interfaces:**
- Consumes: le setting `mentions_legales_link` défini dans le schema de `sections/ml-footer.liquid:475-478`. La page `/pages/mentions-legales` (créée dans l'admin en Task 6, Step 2 — les deux étapes peuvent se faire dans n'importe quel ordre, le footer masque le lien tant que le setting est vide mais affiche un 404 si la page n'existe pas encore).
- Produces: rien pour les autres tâches.

- [x] **Step 1 : Renseigner le setting dans `sections/footer-group.json`** *(corrigé : les clés `mentions_legales_link` (vide) et `mentions_legales_text` existent DÉJÀ dans le fichier — l'insertion prévue par le plan initial aurait créé des clés JSON dupliquées. On remplit simplement la valeur existante.)*

Dans `sections.ml-footer.settings`, remplacer :

```json
        "mentions_legales_link": "",
```

par :

```json
        "mentions_legales_link": "/pages/mentions-legales",
```

- [x] **Step 2 : Valider le JSON**

```bash
python -c "import json; json.load(open('sections/footer-group.json', encoding='utf-8')); print('OK')"
```

Attendu : `OK`.

- [ ] **Step 3 : Vérifier visuellement dans le préview**

Recharger le préview, descendre au footer. Attendu : au-dessus du copyright, une ligne de liens légaux contenant au minimum « Mentions légales ». Si les Règles Shopify sont déjà remplies dans l'admin, les liens CGV / Politique de confidentialité / Politique de remboursement apparaissent aussi automatiquement. **Corrigé : la page `/pages/mentions-legales` existe déjà en ligne (vérifiée en 200 le 08/07) — aucun 404 attendu, la Task 6 Step 2 est obsolète.**

- [x] **Step 4 : Commit**

```bash
git add sections/footer-group.json
git commit -m "fix(footer): lien mentions legales dans la ligne legale du ml-footer"
```

---

### Task 6 : Actions admin Shopify (hors repo) — menu « ACHETER », pages légales, Règles

Points d'audit traités : *« Navigation ACHETER → page Commandes gros volume »* et le volet admin des liens légaux. Le menu principal (handle `main-menu`, référencé par `sections/header-group.json`) et les Règles se gèrent dans l'admin Shopify — rien à committer. Exécuter cette checklist dans l'admin (`https://admin.shopify.com/store/mylab-shop-3`).

**Files:**
- Aucun (actions admin uniquement).

**Interfaces:**
- Consumes: les pages existantes `/pages/la-boutique-my-lab`, `/pages/commande-express`, `/pages/catalogue-prix-et-formules-mylab`, `/pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici`.
- Produces: la page `/pages/mentions-legales` consommée par le setting footer de Task 5.

- [ ] **Step 1 : Restructurer l'entrée « ACHETER » du menu principal**

Admin > Boutique en ligne > Navigation > menu `main-menu`. Transformer l'entrée « ACHETER » en menu déroulant :

| Niveau | Libellé | Lien |
|---|---|---|
| Parent | ACHETER | `/pages/la-boutique-my-lab` (l'offre standard devient la destination par défaut, plus le gros volume) |
| Enfant 1 | La boutique pro — dès 6 unités | `/pages/la-boutique-my-lab` |
| Enfant 2 | Catalogue & prix | `/pages/catalogue-prix-et-formules-mylab` |
| Enfant 3 | Commande express | `/pages/commande-express` |
| Enfant 4 | Gros volume — dès 50 kg | `/pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici` |

Vérification : sur le préview, survoler « ACHETER » → le déroulant affiche les 4 entrées ; un clic direct sur « ACHETER » mène à la boutique pro, plus à la page gros volume.

- [x] **Step 2 : ~~Créer la page Mentions légales~~ DÉJÀ FAIT** — la page `https://www.mylab-shop.com/pages/mentions-legales` existe et répond 200 (vérifié le 08/07). Optionnel : relire son contenu (raison sociale, SIREN, hébergeur, contact) pour s'assurer qu'il est complet.

- [ ] **Step 3 : Remplir les Règles Shopify (CGV, confidentialité, remboursement, expédition)**

Admin > Paramètres > Règles. Renseigner : Conditions générales de vente, Politique de confidentialité, Politique de remboursement, Politique d'expédition (les modèles Shopify peuvent servir de base, à adapter au contexte B2B — notamment la politique de retour sur produits personnalisés à l'étiquette du client).

Vérification : recharger le footer sur le préview → les liens CGV / confidentialité / remboursement / expédition apparaissent automatiquement dans la ligne légale (rendus par `shop.policies` dans `ml-footer.liquid`, aucun code à toucher).

- [ ] **Step 4 : Peupler la collection `best-sellers` (optionnel)**

**Corrigé : vérifiée le 08/07 — la collection `best-sellers` existe mais est vide ; la grille de Task 2 pointe donc sur `frontpage` (6 produits phares).** Si Yoann préfère une vraie collection best-sellers : y ajouter les formules phares dans Admin > Produits > Collections, puis changer la collection de la section « Nos formules best-sellers » dans l'éditeur de thème.

---

### Task 7 : Recette finale et push sur le thème de développement

**Files:**
- Aucun nouveau fichier (vérification + push).

**Interfaces:**
- Consumes: toutes les modifications des tâches 1 à 6.
- Produces: thème de développement à jour pour validation par Yoann avant mise en live (la mise en live se fait manuellement dans l'admin, hors périmètre de ce plan).

- [ ] **Step 1 : Relecture complète de la home en préview**

Parcourir la home de haut en bas sur desktop puis mobile (fenêtre < 750 px). Checklist attendue :
1. Hero : CTA plein « Prendre rendez-vous », contour « Découvrir la boutique ».
2. Section « Deux façons de commander » : 2 cartes (6 unités / 50 kg).
3. Grille « Nos formules best-sellers » : produits avec prix + « Voir tout ».
4. Section témoignages : extrait vidéo Aurélien lisible au clic.
5. CTA final : bouton or « Prendre rendez-vous ».
6. Footer : ligne légale avec « Mentions légales » (+ règles si Task 6 Step 3 faite).
7. Le cart drawer MyLab fonctionne toujours : ajouter un produit au panier depuis une page produit → le drawer `ml-drawer-*` s'ouvre, pas le drawer natif Be Yours.

- [x] **Step 2 : Pousser sur le thème de développement** *(corrigé : `--nodelete` obligatoire sur ce store, et le push CLI rapatrie les JSON pilotés par le Theme Editor en local — faire un `git status` + `git restore` des fichiers resynchronisés après le push)*

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete
git status   # si le push a resynchronisé des JSON non voulus : git restore <fichiers>
```

Attendu : push sans erreur, URL de préview du thème de développement affichée. Envoyer cette URL à Yoann pour validation avant publication sur le thème live.

- [x] **Step 3 : Commit final éventuel et récapitulatif**

```bash
git status
```

Attendu : arbre propre (chaque tâche a déjà son commit). Récapituler dans la réponse : les 5 commits, les actions admin restantes de Task 6 non faites, et le rappel que la mise en live du thème est une action manuelle de Yoann.

---

## Retours QA visuels de Yoann (08/07, après premier push dev)

1. ✅ Espace manquant entre le bandeau défilant et le bloc « Notre modèle » → bandeau passé sur fond blanc + padding 24/48 (les deux sections étaient le même beige `#f5f0eb` et fusionnaient, marge inter-sections globale = 0).
2. ✅ Multicolonne périmètre : heading par défaut « Multicolumn » retiré (`"heading": ""`), bouton par défaut « Button label » remplacé par « Découvrir la boutique » → `/pages/la-boutique-my-lab` (style `button--tertiary`, le seul style bouton du module multicolumn, déjà utilisé partout ailleurs).
3. ✅ Carte « Dès 50 kg » : bouton `button_style_secondary: true` (lien souligné noir sur noir) → `false` (bouton tertiaire clair, visible sur fond noir).
4. ✅ Section vidéo témoignage supprimée (voir Task 3 annulée).
5. ✅ Bascule Calendly → cal.com : embed inline officiel cal.com dans `sections/ml-rendez-vous.liquid` (l'id de setting `calendly_url` est conservé pour compatibilité) + `templates/page.prise-de-rendez-vous.json` pointe sur `https://cal.com/yoann-durand-ry0bng/etude-projet-marque-capillaire`.

## Mise en live (08/07, sur demande explicite de Yoann)

- Le thème LIVE avait **dérivé** de master (retouches Theme Editor : 2 sections `empty-space` pour l'espacement, titres `<em>` + highlight sur la multicolonne périmètre, bouton « Découvrez nos formules en marque blanche », vitesse bandeau 2.2, « Testez » au lieu de « Goûtez »). Fusion faite : base = live + deltas validés du plan ; les `empty-space` sont remplacés par le bandeau restylé (validé sur le thème dev). Commit `8e280c6`.
- Déploiement par PUT REST (CLI `--only` non fiable) : `templates/index.json` (fusionné), `sections/footer-group.json`, `templates/page.prise-de-rendez-vous.json`, `sections/ml-rendez-vous.liquid` → thème 184014340430. Rendu live vérifié par curl : 12/12 checks OK.
- Décision Yoann : le menu « ACHETER » reste tel quel (Task 6 Step 1 abandonnée).

## Hors périmètre (assumé)

- **Fourchettes de prix en dur sur les pages vitrine** : plutôt que d'inventer un « à partir de X € » statique (qui divergerait des tarifs dégressifs réels, gérés par produit), le plan rend les prix réels visibles via la grille best-sellers (Task 2) et le catalogue & prix accessible depuis le menu (Task 6). Si Yoann veut en plus un prix d'appel en dur dans le hero, c'est une décision business à prendre avec un montant précis.
- **Refonte du footer au-delà des liens légaux** : le footer actuel couvre déjà 4 colonnes de liens ; l'audit ne pointait que l'absence de liens légaux.
- **Publication sur le thème live** : validation humaine requise après recette sur le thème de développement.
