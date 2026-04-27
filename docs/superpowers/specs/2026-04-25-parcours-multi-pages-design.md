# Parcours « Créons ensemble votre marque » — Refonte multi-pages

**Date** : 2026-04-25
**Statut** : Spec validée, prêt pour implementation plan
**Prototype visuel** : `docs/superpowers/prototypes/parcours-multi-pages.html`

## Contexte

La page `/pages/creons-ensemble-votre-marque` actuelle est un monolithe scroll-driven (~1950 lignes dans `sections/ml-cem-parcours.liquid`) regroupant hero, dossier cosmétologique, étiquette, forfait impression, produits et récap. Yoann la juge **trop chargée, manque de lisibilité et d'aération**.

Objectif : transformer ce parcours en une expérience **multi-pages, ludique et aérée**, où chaque étape est un moment dédié qu'il faut finaliser avant de passer à la suivante.

## Décisions architecturales

### 1. Découpage en 4 étapes + landing

| Page | Handle Shopify | Rôle |
| --- | --- | --- |
| Landing | `/pages/creons-ensemble-votre-marque` (existant, refonte) | Hero, présentation des 4 étapes, CTA « Démarrer mon projet » |
| Étape 01 — Dossier | `/pages/parcours-dossier` (nouveau) | Pédagogie DIP/CPNP/Tests + accordéon des 8 docs |
| Étape 02 — Étiquette + Forfait | `/pages/parcours-etiquette` (nouveau) | 3 cards étiquette (Standard/Modèles/Sur-mesure) + bloc forfait impression |
| Étape 03 — Produits | `/pages/parcours-produits` (nouveau) | Tabs catégories + grid produits avec sélecteurs de paliers |
| Étape 04 — Récap | `/pages/parcours-recap` (nouveau) | Timeline 3 jalons, table des items du panier, CTA « Valider notre projet » |

**Logique de fusion étape 02** : forfait impression dépend du choix de l'étiquette, donc présenté dans la même étape pour cohérence décisionnelle.

### 2. Verrouillage soft (hybride)

L'utilisateur peut **naviguer librement** entre les étapes via le stepper (cliquer sur une étape future est autorisé). En revanche, le bouton **« Valider notre projet »** de l'étape 04 reste **désactivé** tant que les 3 premières étapes n'ont pas été validées (réutilisation du blocker existant de `ml-forfait-gate.js`).

Pas de redirect forcé : permet l'exploration depuis un lien partagé (ads, social), ne casse pas le SEO sur les sous-étapes, garde la sensation de progression sans frustrer.

### 3. État persistant via cart Shopify (source de vérité)

Pas de localStorage. Chaque validation d'étape **add immédiatement au cart Shopify**. À chaque page load, on lit `/cart.js` pour reconstituer l'état du parcours.

**Mapping validation → produit dans le cart** :

| Étape | Critère de validation |
| --- | --- |
| Dossier | item handle `creation-du-dossier-cosmetologique` présent |
| Étiquette + Forfait | au moins 1 produit de la collection `modeles-detiquettes` présent (le forfait est ajouté automatiquement par `ml-forfait-gate.js`) |
| Produits | au moins 1 produit de la collection `boutique-adherents` présent |
| Récap | n/a (étape de finalisation) |

**Avantages** : état ultra-fiable (Shopify gère), survit au reload/back/forward, fonctionne cross-device pour customer connecté, cohérent avec la philosophie « commit progressif ».

### 4. Stepper léger + récap drawer dépliable

**Stepper** sticky en haut (sous la topbar) :

- 4 pastilles numérotées en DM Mono
- Lignes de progression entre les pastilles, qui se remplissent au fur et à mesure
- État `done` : pastille noire pleine + ✓
- État `current` : pastille noire pleine + numéro blanc + ring extérieur + scale 1.08x
- État `locked` (étape future) : pastille outline + opacity 0.5
- Labels visibles sur desktop, masqués sur mobile
- Toggle « Voir mon projet en cours » → ouvre/ferme le récap drawer

**Récap drawer** : sticky sous le stepper, dépliable. Affiche les choix faits, le total HT à ce stade, et le lien « Abandonner et vider mon projet » (vide les items du parcours uniquement).

### 5. Pages Shopify natives (pas de routing JS)

5 pages Shopify séparées avec leurs propres templates JSON. Navigation = full reload classique. Acceptable car le cart Shopify préserve l'état, et chaque page bénéficie d'un meta title/description propre pour le SEO.

### 6. Cart drawer invisible sur les 5 pages parcours

Comme aujourd'hui sur la page monolithe : `ml-forfait-gate.js` étendu pour reconnaître les 5 nouvelles paths et :

- Empêcher l'ouverture du cart drawer (`open: false` dans `mylab:cart:refresh`)
- Masquer l'icône cart de la topbar (CSS conditionnel via classe `body.is-parcours`)

Le récap drawer du stepper joue déjà le rôle de « visibilité du panier » dans le contexte parcours.

### 7. Auto-add du dossier à l'entrée + sortie réversible

**Au click sur « Démarrer mon projet »** depuis la landing (ou à l'arrivée directe sur l'étape 01) :

- Si le dossier (`creation-du-dossier-cosmetologique`) n'est pas déjà dans le cart → ajout automatique via `/cart/add.js`
- Toast confirmation « ✓ Dossier ajouté à votre projet »
- Redirect vers `/pages/parcours-dossier`

**Lien « Quitter le parcours »** disponible dans :

- La topbar sur les 5 pages
- Le récap drawer

Au click → modale de confirmation : « Voulez-vous abandonner votre projet ? Le dossier (389,90 €), l'étiquette et le forfait en cours seront retirés du panier. Les produits ajoutés à l'étape 03 restent dans votre panier — vous pourrez les retirer manuellement si besoin. »

Items retirés au « Quitter le parcours » :

- `creation-du-dossier-cosmetologique` (handle exact)
- Tout item de la collection `modeles-detiquettes`
- `forfait-dimpression-standard` et/ou `forfait-dimpression` (le `ml-forfait-gate` retirera l'orphelin automatiquement après le retrait de l'étiquette, mais on force le retrait explicite par sécurité)

Les produits de la collection `boutique-adherents` ne sont **pas** retirés — l'utilisateur peut avoir une intention d'achat indépendante du parcours, et la suppression silencieuse de produits pro déjà ajoutés serait surprenante.

## Direction artistique

### Règles strictes (mémoire `feedback_mylab_typography_dm_sans_only.md`)

- **DM Sans uniquement** pour titres, body, UI, prix
- **DM Mono** pour kickers, codes étape, badges, chips, métas mono-graphiques
- **Aucun italique** (pas de `font-style: italic`)
- **Aucun Cormorant** (ni en accent ni en chiffres)
- **Aucun or** `#c5a467` sur cette refonte (différent du reste de la home — décision explicite Yoann)
- **Aucun rouge brick** ni couleur d'accent saturée
- Hiérarchie typographique par **poids** (400/500/600/700) et taille uniquement

### Palette monochrome cream / noir / blanc

| Variable | Valeur | Usage |
| --- | --- | --- |
| `--cream` | `#f5f0eb` | Background principal (identique aux sections home) |
| `--cream-2` | `#ede6dd` | Background sections alternées, cards, drawer |
| `--cream-3` | `#e0d6c8` | Backgrounds chips, placeholders |
| `--ink` | `#1a1a1a` | Texte principal, CTAs, sections inversées |
| `--ink-soft` | `#333333` | Texte secondaire (lede, body) |
| `--muted` | `#6b665e` | Métas, kickers, footer |
| `--line` | `rgba(26,26,26,.10)` | Bordures, dividers |

### Patterns visuels

- **Highlights `<em>` dans les titres** : rendu en bandeau plein **noir sur fond clair** ou **blanc sur fond noir** (reproduit le pattern `<strong>` + `highlight_style: solid-color` de la home)
- **Cartouches d'étape** : DM Mono uppercase letter-spacing 0.16em, fond noir solid + texte blanc, padding 0.7rem 1.1rem (pattern existant de `ml-cem-parcours`)
- **Cards étiquette** : pattern home `multicolumn` étiquettes — opt_1 cream / opt_2 noir-on-blanc (featured) / opt_3 cream
- **Section récap finale** : bloc `#1a1a1a` avec texte blanc, accent par contraste, timeline avec dots blancs

## Architecture technique

### Fichiers Shopify à créer

```text
templates/
  page.creons-ensemble-votre-marque.json    (refonte — landing)
  page.parcours-dossier.json                 (nouveau)
  page.parcours-etiquette.json               (nouveau)
  page.parcours-produits.json                (nouveau)
  page.parcours-recap.json                   (nouveau)

sections/
  ml-parcours-landing.liquid                 (hero + 4 étapes preview + CTA)
  ml-parcours-dossier.liquid                 (3 piliers + accordéon docs)
  ml-parcours-etiquette.liquid               (3 cards + forfait + integration configurateur Vercel iframe)
  ml-parcours-produits.liquid                (tabs + grid produits + paliers)
  ml-parcours-recap.liquid                   (timeline + table récap + CTA validation)

snippets/
  ml-parcours-shell.liquid                   (topbar parcours + stepper + récap drawer — inclus dans theme.liquid via gating sur path)

assets/
  ml-parcours.css                            (styles partagés des 5 pages)
  ml-parcours.js                             (state cart, sync stepper, drawer toggle, auto-add dossier, gestion sortie)
```

### Fichiers à modifier

- `layout/theme.liquid` : `{% render 'ml-parcours-shell' %}` conditionnel sur path `/pages/creons-ensemble-votre-marque` ou `/pages/parcours-*`
- `assets/ml-forfait-gate.js` : étendre la regex de détection path pour inclure les 5 nouvelles pages, masquer cart drawer, gérer le blocker checkout sur les 5 paths
- `sections/mylab-cart-drawer.liquid` : aucune modif, déjà géré par le forfait-gate

### Fichiers à retirer / archiver

- `sections/ml-cem-parcours.liquid` (1950 lignes) : conservé dans le repo pour rollback éventuel mais non référencé par les nouveaux templates
- `sections/ml-creons-ensemble-votre-marque.liquid` (monolithe pré-V4) : déjà non référencé, peut être supprimé proprement à l'occasion

### JS — état et flow

`assets/ml-parcours.js` (IIFE, vanilla, pattern existant MyLab) :

```text
1. À chaque page load sur une path /pages/parcours-* OU /pages/creons-ensemble-votre-marque :
   - fetch /cart.js
   - reconstitue l'état : { dossier: bool, etiquette: bool, produits: bool }
   - sync stepper (classes done/current/locked + remplissage des lignes)
   - sync récap drawer content (lignes ✓ Validé / Pending + total HT cumulé)

2. Au click sur « Démarrer mon projet » (landing) :
   - Si dossier absent du cart : POST /cart/add.js avec creation-du-dossier-cosmetologique
   - Toast « ✓ Dossier ajouté à votre projet »
   - window.location = /pages/parcours-dossier

3. Au click sur un bouton « Valider et continuer » de chaque étape :
   - L'étape effectue son add-to-cart (étiquette → modale configurateur ; produits → /cart/add batch des sélections)
   - Toast confirmation
   - window.location = page suivante

4. Au click sur « Quitter le parcours » :
   - Modale de confirmation avec liste des items qui seront retirés
   - Si confirm : itère /cart/change.js avec quantity:0 sur chaque item du parcours
   - window.location = /

5. Stepper : click sur une pastille → window.location = page correspondante (libre)
6. Récap drawer toggle : ouverture/fermeture via aria-expanded + max-height transition
```

### Edge cases couverts

| Cas | Comportement |
| --- | --- |
| Cart pré-existant non-vide à l'arrivée sur landing | On respecte les items hors parcours, on ne touche qu'à ce que le parcours ajoute |
| Dossier déjà dans le cart à l'arrivée | Skip auto-add, étape 01 directement marquée ✓ dans le stepper |
| Customer connecté avec tag `abo-impression-noire` ou `abo-impression-couleur` | Skip auto-add du forfait (logique existante de `ml-forfait-gate.js`) |
| Reload en plein parcours | État préservé via cart Shopify, stepper resynchronisé |
| Lien direct sur étape 03 sans étapes 01/02 validées | Page accessible (verrouillage soft), stepper montre les étapes manquantes en outline, pas de redirect |
| Sortie navigateur sans validation finale | Cart contient les items partiels — l'utilisateur les retrouve à son retour, ou peut « Quitter le parcours » pour cleanup |
| Cart contient le forfait mais l'étiquette est retirée hors parcours | Le `ml-forfait-gate` détecte et propose le retrait du forfait orphelin (logique existante) |

## Hors scope

- **Refonte du configurateur Vercel** : on conserve l'intégration iframe modale existante (Phase 1 SHIPPED 2026-04-23). Les cards étiquette de `ml-parcours-etiquette.liquid` réutilisent le même pattern d'ouverture modale + listener postMessage.
- **Phase 2 du configurateur** (mockups produits sur étape 03, hero composition étape 04, PDF récap) : roadmap séparée (`project_configurateur_integration_roadmap.md`).
- **Optimisation SEO** des 4 nouvelles pages : meta titles/descriptions à finaliser dans une session dédiée — le spec assume les valeurs par défaut Shopify pour la première itération.
- **Animations avancées** : le prototype montre des transitions CSS simples (fade + translateY). Pas de Motion library, pas d'animations scroll-triggered au-delà des hover states.

## Plan de migration

1. **Création** des 5 nouveaux templates + 5 nouvelles sections + 1 snippet shell + 2 assets, en parallèle de l'ancien monolithe
2. **Test** sur `--development` theme : vérifier flow complet landing → recap, edge cases cart pré-existant et sortie
3. **Test mobile** : vérifier responsive du stepper, bottom CTA bar, récap drawer
4. **Mise en prod** : push live → la landing existante `/pages/creons-ensemble-votre-marque` bascule sur le nouveau template ; les 4 nouvelles pages deviennent accessibles
5. **Rollback** disponible : repointer le template `page.creons-ensemble-votre-marque.json` vers `ml-cem-parcours` (encore présent dans le repo) pour revenir à l'ancien monolithe en 1 push

## Critères de succès

- Chaque étape est une page distincte au handle propre
- L'utilisateur peut naviguer librement via le stepper et reprendre son parcours après un reload
- L'add immédiat au cart fonctionne sur les 4 étapes, le forfait s'ajoute automatiquement selon le choix d'étiquette
- La sortie « Quitter le parcours » nettoie proprement les items du parcours sans toucher aux autres
- DA strictement alignée sur la home (DM Sans + DM Mono, palette monochrome cream/ink/blanc, zéro or, zéro brick, zéro italique, zéro Cormorant)
- Cart drawer invisible sur les 5 pages, le récap drawer du stepper joue le rôle de visibilité du panier
- Pas de régression sur le configurateur Vercel iframe (étape étiquette)
- Le bouton « Valider notre projet » de l'étape 04 reste désactivé tant que les 3 premières étapes ne sont pas validées
