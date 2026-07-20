# Design — Séparation stock retail / bulk labo (sync Odoo → Shopify)

**Date** : 2026-07-20
**Statut** : validé (design), à planifier
**Branche** : `feat/stock-retail-bulk-split`

## Problème

Le stock affiché sur Shopify part en négatif et bloque la vente des petites
commandes retail, alors que le stock physique existe. Cause racine identifiée :

- Les grosses commandes « bulk » (CENDREE & co) sont commandées en vrac au labo
  et remplies à la volée. Elles **ne font jamais partie du stock physique MyLab**.
- Pourtant, dans Odoo, leurs livraisons décrémentent le **même pool de stock** que
  le retail (l'emplacement parent `MYVO/Stock`), le poussant très négatif
  (ex. shampoing nourrissant 200ml : **−662** en `qty_available`, dont −668 sur le
  parent `MYVO/Stock` et +6 sur `MYVO/Stock/Fini`).
- Le sync n8n `sync-stock-odoo-shopify` lit `qty_available` (agrégé tous
  emplacements) et applique un filtre `eff > 0` : quand Odoo est négatif, il ne
  pousse **rien**, donc Shopify reste bloqué sur le négatif laissé par ses propres
  décréments de commande, jamais corrigé.

## Objectif

Le stock poussé vers Shopify doit refléter :

```
dispo Shopify(SKU) = stock physique retail(SKU) − réservations des petites commandes(SKU)
```

Les commandes bulk sont **exclues partout** : ni du stock physique retail, ni des
réservations. On corrige la cause à la source (Odoo) plutôt que de la maquiller
côté sync (approche B retenue par Yoann).

## Définition « bulk »

Une **ligne** de commande est bulk si :

- `quantité × contenance_ml ≥ 50 000` (≥ 50 L/kg — le MOQ labo réel, seuil
  configurable), **OU**
- sa commande porte le tag `bulk-labo` (override manuel, `sale.order.tag_ids`).

Le tag permet aussi de **forcer en retail** une ligne ≥ 50 L exceptionnellement
gardée en stock (tag inverse `retail-force`, optionnel — à confirmer au besoin).

Contexte confirmé par Yoann : une ligne bulk **peut être mélangée** dans une
commande retail normale → le routage se fait **ligne par ligne** (au niveau
`stock.move`), pas commande entière.

## État Odoo réel (constaté le 2026-07-20)

- Entrepôt : **MYLAB (MYVO)**, `lot_stock_id = MYVO/Stock` (id **28**), `company_id = 3`.
- `MYVO/Stock` (id **28**) — parent, emplacement source par défaut des livraisons.
  Porte le négatif fictif (surtirage bulk).
- `MYVO/Stock/Fini` (id **47**) — **stock retail fini** (les vrais flacons vendables).
  Ex. 200ml : `quantity=6, reserved=6`.
- `MYVO/Stock/Bulk` (id **45**) — **existe déjà**, cible pour le bulk.
- `MYVO/Stock/Packaging` (id **46**) — hors périmètre.

Conséquence : aucun emplacement à créer. On réutilise Fini (47) comme source
retail et Bulk (45) comme puits bulk.

## Composants

### 1. Classificateur (fonction pure, partagée)
Entrée : ligne (produit, qté, contenance, tags commande). Sortie : `bulk` | `retail`
| `ambiguous`. Contenance parsée depuis le SKU (`-200-ml`) ou le nom produit
(`200ml`). Seuil `BULK_THRESHOLD_ML = 50000` en constante/env.
- Contenance **non déterminable** → `ambiguous` : on ne route pas, on **signale**
  (on ne devine jamais — un mauvais classement = pollution retail ou survente).

### 2. Routeur de lignes bulk (script cron VPS)
Style des scripts `scripts/odoo/*` (client `_client.py`, idempotent, `--dry-run`
par défaut puis `--apply`). Pour chaque commande confirmée (`state=sale`) dont la
livraison n'est **pas** validée :
- classe chaque ligne ;
- pour chaque `stock.move` d'une ligne **bulk** encore réservable, met
  `location_id = MYVO/Stock/Bulk (45)` (puis `do_unreserve` + `action_assign`
  pour re-réserver depuis le bon emplacement) ;
- laisse les lignes retail sourcer depuis Fini (47) ;
- **idempotent** : skip si `location_id` déjà = 45 ; ne touche jamais un picking
  `done`/`cancel` ;
- lignes `ambiguous` → skip + notification (log + éventuel message Telegram Hermes).

Pourquoi un cron script et pas une action serveur Odoo « live » : historique de
writes Odoo non fiables (Hermes local, UID 8 partagé). Un script contrôlé
dry-run → apply est plus sûr qu'un déclenchement automatique.

### 3. Sync n8n modifié (`scripts/n8n/sync-stock-odoo-shopify/`)
- **Node 01** : ne lit plus `qty_available` (agrégé). Lit `stock.quant` filtré sur
  `location_id = MYVO/Stock/Fini (47)` et calcule
  `dispo = Σ(quantity − reserved_quantity)` par produit. Ça donne d'un coup le
  physique retail **moins les réservations des petites commandes** (les
  réservations bulk sont sur l'emplacement 45, donc absentes).
- **Nodes 02/03** : inchangés dans la structure ; on pousse la nouvelle `dispo`.
  Révision du garde `eff > 0` : autoriser un vrai **0** (rupture réelle retail)
  **sans** zéroter les ~72 produits « stock non saisi ». Discriminant à définir
  (ex. produit ayant au moins un quant sur Fini vs aucun quant du tout).

## Migration one-time

1. (Aucun emplacement à créer — Fini 47 et Bulk 45 existent.)
2. **Repointer les lignes bulk encore ouvertes** (commandes confirmées non
   livrées, ex. CENDREE S00626 200ml×1380) vers Bulk (45) via le routeur, pour
   que leurs futures livraisons ne repolluent pas le retail.
3. **Ajustement d'inventaire retail** : Yoann pose les vrais comptes physiques sur
   `MYVO/Stock/Fini` (47). Le négatif fictif du parent `MYVO/Stock` (28) est
   soldé (absorbé par l'ajustement / transféré sur Bulk selon ce que révèle le
   canari).
4. L'historique déjà livré reste tel quel.

## Flux nominal (après migration)

```
Commande confirmée
  → routeur cron classe chaque ligne
  → repointe les moves bulk sur MYVO/Stock/Bulk (45)
  → Yoann valide la livraison (Fini 47 intact, sauf lignes retail)
  → sync cron lit quants Fini (47) = quantity − reserved
  → pousse dispo vers Shopify
```

## Gestion d'erreur & garde-fous

- Routeur idempotent, `--dry-run` par défaut, jamais sur picking validé.
- Contenance non parsable → skip + notification, pas de devinette.
- Respect du verrou UID 8 : ne pas router pendant une édition manuelle de commande.
- Ne jamais `git add -A` (checkout partagé) ; déployer le sync n8n **en set** des
  3 nodes.

## Canari obligatoire (avant tout déploiement large)

1. Une commande test **mélangée** : 1 petite ligne retail + 1 ligne ≥ 50 L.
2. Passer le routeur en `--apply` sur cette seule commande.
3. Valider la livraison.
4. **Vérifier** que le `quantity` de Fini (47) ne bouge **que** de la petite ligne,
   et que le bulk a bien décrémenté Bulk (45).
5. Vérifier que le sync pousse la dispo attendue pour ce SKU.

Ne généraliser qu'après ce canari vert.

## Risque technique à lever par le canari

Confirmer qu'Odoo 18 accepte un `stock.move` avec `location_id` différent des
autres moves du même picking (source mixte Fini/Bulk dans un même bon), et que
`do_unreserve` + `action_assign` re-réservent bien depuis le nouvel emplacement.
Si Odoo refuse la source mixte : repli = **split du picking** (un bon retail depuis
Fini, un bon bulk depuis Bulk).

## Hors périmètre

- Refonte de la logique de production/OF vrac (`creer_of_production_lot.py`, etc.).
- Produits sans `default_code` (100/125/300/5000ml) : déjà exclus du sync côté
  node 01, non concernés par le push Shopify (mais le routeur les classe quand
  même pour garder Odoo propre).

## Points à confirmer côté Odoo pendant l'implémentation

- Comportement exact de réservation depuis le parent `MYVO/Stock` (28) vs enfants
  (removal strategy) — le canari le révélera.
- Emplacement source réel des livraisons retail actuelles (parent 28 ou Fini 47 ?).
- Tag override : `sale.order.tag_ids` valeur `bulk-labo` (créer le tag si absent).
