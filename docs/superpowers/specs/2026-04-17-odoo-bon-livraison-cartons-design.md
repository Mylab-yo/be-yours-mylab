# Bon de livraison Odoo avec répartition en cartons — Design

**Date :** 2026-04-17
**Projet :** MyLab Shop (SARL STARTEC) — Odoo 17
**Auteur :** Yoann Durand + Claude

## Problème

Aujourd'hui, le bon de livraison (BL) par défaut d'Odoo liste les produits et leurs quantités totales, sans indiquer comment la marchandise est physiquement répartie dans les cartons. Côté client B2B, la vérification à réception est fastidieuse : il faut ouvrir chaque carton et recompter l'ensemble par rapport au BL global.

Côté STARTEC, la logistique est structurée par conditionnement carton : chaque produit a un nombre fixe d'unités par carton d'expédition. On veut un BL qui reflète cette réalité physique pour accélérer la vérification à la réception.

## Objectif

Générer un BL PDF à partir d'un `stock.picking` Odoo qui :
- Calcule automatiquement la répartition en cartons selon les capacités de conditionnement définies par produit.
- Permet à l'opérateur entrepôt de corriger la répartition avant impression via l'UI Odoo standard.
- Affiche un récapitulatif produits + un détail carton par carton compact et facile à cocher à la réception.
- Fonctionne pour toute commande, quelle que soit l'origine (devis Odoo, commande Shopify synchronisée, picking manuel).

## Familles de carton

Chaque produit appartient à une famille définie par sa capacité de carton (unités par carton) :

| Famille | Capacité | Produits concernés |
|---|---:|---|
| 50ml huile/sérum | 50 | Huiles et sérums 50ml |
| 200ml crème/shampoing | 40 | Shampoings et crèmes 200ml |
| 200/400ml masque | 24 | Masques 200ml et masques 400ml |
| 500ml crème/shampoing | 23 | Shampoings et crèmes 500ml |
| 1000ml shampoing/masque | 12 | Shampoings et masques 1000ml |
| Divers | 0 (non défini) | Packs, coffrets, testeurs, trios, duos — hors conditionnement standard |

## Architecture

3 pièces techniques, toutes intégrées dans Odoo (aucun développement hors Odoo).

### 1. Champ custom `x_carton_capacity`

- **Modèle :** `product.template`
- **Type :** integer
- **Sémantique :** nombre d'unités par carton. `0` = produit sans conditionnement carton défini (va dans la famille "Divers").
- **Création :** via `ir.model.fields.create()` par API XML-RPC — pas de module Odoo à développer.
- **Initialisation :** script Python one-shot qui parse les noms produits existants et affecte la bonne capacité selon les règles de famille. Exceptions corrigeables manuellement depuis l'UI Odoo après le script.

### 2. Action serveur "Répartir en cartons" sur `stock.picking`

- **Type :** `ir.actions.server` de type `code`
- **Binding :** modèle `stock.picking`, accessible via bouton custom dans la vue picking
- **Comportement :**
  1. Purge les `result_package_id` et packages orphelins précédents (idempotence si relancé).
  2. Groupe les `stock.move.line` par `product_id.x_carton_capacity`.
  3. Pour chaque famille avec capacité > 0 : calcule N cartons pleins + 1 partiel éventuel par division entière, crée les `stock.quant.package`, remplit séquentiellement les move lines (en splittant si nécessaire).
  4. Pour la famille "Divers" (capacité 0) : un seul package contenant toutes les move lines concernées.
  5. Numérote les packages `Carton X/Y - <label famille>` (ex. `Carton 2/5 - 200ml crème/shampoing (panaché)`).

### 3. Template PDF `mylab_report_deliveryslip`

- **Type :** `ir.actions.report` qweb-pdf, binding sur `stock.picking`.
- **Vue QWeb :** nouvelle vue `mylab.report_deliveryslip_document` (pas d'héritage — override complet pour lisibilité).
- **Branding :** reprend les couleurs du devis customisé (`#1a1a1a` noir profond, `#c9a96e` or doré) et le footer de `res.company` ID 3.
- **Structure :** en-tête → récapitulatif produits → détail par carton → cadre signature.

## Algorithme de répartition

Entrée : un `stock.picking` avec N `move.line` (une par produit réservé).

**Étape 1 — Regroupement par famille**
Grouper les move lines par `product_id.x_carton_capacity`. Les produits à `0` forment le groupe "Divers".

**Étape 2 — Calcul par famille**
Pour chaque famille avec capacité `C > 0` :
```
total_units = somme des quantités des move lines du groupe
nb_cartons_pleins = total_units // C
reste = total_units % C
nb_cartons = nb_cartons_pleins + (1 si reste > 0 sinon 0)
```

**Étape 3 — Remplissage séquentiel**
Parcourir les move lines de la famille dans l'ordre. Remplir un carton courant jusqu'à `C` unités ; dès qu'il est plein, ouvrir un nouveau carton. Si une move line déborde, la splitter (`copy()` d'une partie avec la quantité qui va dans le carton courant, l'autre continue dans le carton suivant).

**Résultat attendu :** cartons aussi homogènes que possible (remplissage séquentiel), seul le dernier carton d'une famille peut être panaché.

**Exemple** — Commande : 46 × shampoing 200ml + 30 × crème 200ml + 6 × masque 1000ml.
- Famille 200ml (C=40) : 76 unités → 2 cartons.
  - Carton 1/3 : 40 × shampoing (plein).
  - Carton 2/3 : 6 × shampoing + 30 × crème = 36 (panaché).
- Famille 1000ml (C=12) : 6 unités → 1 carton partiel.
  - Carton 3/3 : 6 × masque 1000ml.

**Étape 4 — Création des packages Odoo**
Pour chaque carton calculé :
- `stock.quant.package.create({'name': '...'})` avec nom lisible.
- Affecter les move lines (ou portions de move lines après split) au `result_package_id` du package.

**Idempotence** : si le bouton est relancé après modification du picking, tous les `result_package_id` sont remis à `False` et les packages précédemment créés par l'action sont supprimés avant recalcul.

## Layout PDF

**Format A4 portrait. Branding noir/or cohérent avec le devis.**

### En-tête (page 1 uniquement)
- Logo MyLab + numéro BL (ex. `WH/OUT/00042`).
- Bloc gauche : client + adresse livraison.
- Bloc droit : date expédition, transporteur, référence commande origine, poids total.
- Badge compact en haut à droite : **"📦 3 cartons — 18.4 kg"**.

### Section 1 — Récapitulatif produits
Tableau compact :

| Référence | Désignation | Qté | Poids unit. | Poids total |
|---|---|---:|---:|---:|

Une ligne par produit (move line agrégée), total en pied.

### Section 2 — Détail par carton
Un bloc par carton, ~4-6 lignes chacun :

```
┌──────────────────────────────────────────────────────────────┐
│ ☐ CARTON 1/3 — 200ml crème/shampoing      40/40 — 10.00 kg  │
├──────────────────────────────────────────────────────────────┤
│  • shampoing nourrissant 200ml  ×40                          │
└──────────────────────────────────────────────────────────────┘
```

**Règles de compacité :**
- Police 9pt corps, 10pt en-têtes carton.
- Bordures fines (0.5pt) or (`#c9a96e`) sur les blocs carton.
- Padding minimal (4px).
- `page-break-inside: avoid` sur chaque bloc carton (jamais coupé entre pages).
- Cible : 3-4 cartons par page selon densité produits.

### Pied de page
- Cadre signature : "Reçu en bon état par : _____ Date : _____ Signature :"
- Coordonnées STARTEC depuis `res.company.footer`.

## Flux utilisateur

```
[Picking créé depuis n'importe quelle source]
      ↓
[Opérateur clique "Répartir en cartons"]
      ↓
[Packages auto-générés, move lines assignées]
      ↓
[Opérateur vérifie et ajuste via UI "Opérations détaillées" standard Odoo]
      ↓
[Opérateur clique "Imprimer BL"]
      ↓
[PDF généré avec récap + détail cartons]
```

L'édition manuelle utilise exclusivement l'UI native Odoo (champ `Colis` / `result_package_id` sur chaque move line) — aucune UI custom à maintenir.

## Ordre d'implémentation

1. Créer le champ `x_carton_capacity` via API Odoo.
2. Script d'initialisation des valeurs sur tous les produits existants (avec log de vérification).
3. Créer l'action serveur "Répartir en cartons" + tester manuellement sur un picking test.
4. Créer le template PDF QWeb + action report + binding.
5. Ajouter le bouton "Répartir en cartons" dans la vue picking (vue héritée XML).
6. Test end-to-end avec une commande réelle.
7. Itération sur le layout après revue visuelle du PDF.

## Hors scope (prototype initial)

- Code-barres / QR code sur les packages pour scan à la réception.
- Intégration avec l'étiquetage DPD (labels transporteur).
- Gestion des kits Odoo (BOM phantom) — pour l'instant, les kits sont en famille "Divers".
- Multi-langue du template PDF (FR uniquement pour le prototype).
- Gestion des retours / reprises (le BL est généré pour un outgoing picking uniquement).

## Risques et points d'attention

- **Fiabilité des poids produits** — le badge "poids total" dépend de `product.weight` en kg. Vérifié lors de la sync du 14/04, mais un nouveau produit mal renseigné donnera un poids faux sur le BL.
- **Split de move lines** — splitter une `stock.move.line` réservée demande une logique Odoo précise (gestion des quantités réservées vs. faites). Le prototype teste ce cas sur un picking simple d'abord.
- **Packages orphelins** — si l'opérateur clique plusieurs fois sur le bouton, il faut nettoyer les packages vides pour éviter l'accumulation. À valider dans la logique de purge.
- **Produits sans `x_carton_capacity` après script** — liste à contrôler manuellement après le script d'init pour éviter de mettre des produits "normaux" dans "Divers" par erreur.
