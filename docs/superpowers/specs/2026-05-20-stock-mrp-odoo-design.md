# Gestion de stock MRP centralisée — Odoo + Shopify

**Date** : 2026-05-20
**Auteur** : Yoann Durand (brainstorm avec Claude)
**Statut** : Design validé, prêt pour planification

## Contexte et objectif

MY.LAB centralise aujourd'hui ses ventes (Shopify B2C/B2B) et sa facturation (Odoo) mais n'a pas de gestion fine du stock matière première. Les produits sont reçus en bulk (50/100/200 kg) du laboratoire partenaire **FP Cosmetics** (sauf 4 produits fabriqués en interne : sérums, bain miraculeux, huile barbe, spray texturisant), puis conditionnés sur place en flacons selon le flux de commandes.

**Objectif** : disposer dans Odoo d'une vue temps réel du stock à tous les niveaux (bulk, packaging, produit fini), avec déclenchement automatique des commandes de réapprovisionnement vers FP Cosmetics et fournisseurs packaging quand un composant passe sous un seuil critique.

**Exigences fonctionnelles** :
- Décrémentation virtuelle du bulk à la confirmation des commandes Shopify (réservation)
- Saisie manuelle du conditionnement physique (consommation réelle)
- Alerte automatique de réapprovisionnement quand bulk < 20 kg (recommander 200 kg)
- Récap email hebdomadaire des RFQ à valider (lundi 8h)
- Sync Shopify avec stock projeté incluant la capacité de conditionnement (bulk + packaging disponibles)
- Traçabilité lot bulk conforme CPNP / règlement CE 1223/2009

## Architecture

### Modèle de données Odoo

```
┌──────────────────────┐                ┌────────────────────────┐
│  Bulk (matière 1ère) │  ──────────►   │  Produit fini (flacon) │
│  ex: "Bulk Shampoing │   BoM (conso)  │  ex: "Shampoing        │
│   Nourrissant" en kg │                │   nourrissant 200ml"   │
└──────────────────────┘                └────────────────────────┘
       ▲                                          ▲
       │ achat (PO)                               │ vente (SO)
       │                                          │
   FP Cosmetics                              Client Shopify/B2B
```

### Locations Odoo (warehouse unique, multi-emplacements)

- `WH/Stock/Bulk` — fûts reçus, kg, lots actifs
- `WH/Stock/Packaging` — flacons, bouchons, pompes (unités, sans lot)
- `WH/Stock/Fini` — bouteilles conditionnées prêtes à expédier (sans lot)

### Modules utilisés

- Inventory (natif)
- Manufacturing / MRP (natif)
- Purchase (natif)

Aucun module externe ou OCA requis.

## Produits à créer

### Bulks (~50 produits)

- Catégorie : `Matières premières / Bulk`
- Type : Storable Product
- Unité de mesure : kg
- Tracking : **By Lots**
- Route : `Buy` (FP Cosmetics) pour ~46 formules, `Manufacture` pour les 4 fab interne
- SKU : `BULK-{slug-formule}` (ex: `BULK-shampoing-nourrissant`)

### Packaging (~13-15 SKUs)

| SKU | Stock mini | Note |
|---|---|---|
| Flacon plastique 200ml | 1000 | Shampoings/crèmes/après-sham 200ml |
| Flacon plastique 500ml | 100 | Shampoings/crèmes/après-sham 500ml |
| Flacon plastique 1000ml | 50 | Shampoings/crèmes/après-sham 1000ml |
| Flacon ambré 200ml | TBD | Spray texturisant |
| Pot 200ml | 200 | Masques (jumelé Capot) |
| Capot 200ml | 200 | Masques (jumelé Pot) |
| Pot 400ml + Capot 400ml | TBD | Masques 400ml (à confirmer si distinct du 200ml) |
| Bouteille verre ambrée 50ml | 200 | Sérums + huile barbe + bain miraculeux |
| Bouchon 24/410 | 500 | Flacons 200/500ml |
| Bouchon 28/410 | 50 | Flacons 1000ml |
| Pompe 200/500ml | 200 | Crèmes/masques (option, mix usage 90/10) |
| Pompe 1000ml | TBD | Option, **aussi vendue seule comme produit fini** |
| Dispenser sérum | 100 | Sérum 50ml |
| Pipette | 100 | Huile barbe 50ml |
| Pulvérisateur spray | TBD | Spray texturisant |

**Stock max suggéré** : 10× stock mini (à ajuster en setup en fonction des MOQ fournisseurs).

**Étiquettes** : **exclues du stock** (imprimées à la demande).

**Coffrets / duos / trios** : **exclus du modèle** (assemblage de bouteilles déjà conditionnées, à modéliser en Phase 2 si besoin).

### Fournisseurs packaging

Plusieurs fournisseurs distincts (verrerie, packaging spécialisé). À créer un par un dans Odoo lors du setup avec leurs coordonnées et lead times respectifs.

## Nomenclatures (BoMs)

Une BoM par SKU fini qui consomme du bulk → **~150 BoMs**.

### Structure type — Shampoing nourrissant 200ml

| Composant | Quantité | Unité |
|---|---|---|
| `BULK-shampoing-nourrissant` | 0,2 | kg |
| `FLACON-PLA-200` | 1 | unité |
| `BOUCHON-24-410` | 1 | unité |
| **Produit fabriqué** : Shampoing nourrissant 200ml | 1 | unité |

### Cas fab interne

Identique, mais le `BULK-*` correspondant a une route `Manufacture` (au lieu de `Buy`). Un MO préalable de fabrication du bulk est nécessaire avant le MO de conditionnement. Le bulk fab interne n'a pas de BoM matières premières (gestion ad-hoc en Phase 1).

### Pompes

Pas dans les BoMs des bouteilles (option client séparée, vendue en ligne supplémentaire ou produit annexe).

### Yield

100% (perte négligeable < 2%, corrigée par inventaires mensuels). BoM = 0,2 kg pile pour 200ml.

## Mix de répartition par famille de bulk

Utilisé pour calculer le stock projeté Shopify quand le bulk peut être conditionné en plusieurs contenances.

| Famille de bulk | Contenances | Mix |
|---|---|---|
| Shampoings / crèmes / après-shampoing | 200 / 500 / 1000ml | 77% / 7% / 16% |
| Masques | 200 / 400 / 1000ml | 80% / 3% / 17% |
| Sérums / huiles (fab interne) | 50ml uniquement | 100% |

Source : données de ventes 2024-2025 (top contenances 200ml=59,6% / 1000ml=12,4% / 50ml=7,3% / 500ml=5,1% / 400ml=2,7%), recalculées par famille.

Le mix est stocké en configuration dans le workflow n8n de sync Shopify et modifiable sans code.

## Flux de décrémentation

### Mode 1 — Réservation automatique au paiement Shopify

```
Commande Shopify payée
   → webhook orders/paid
   → n8n workflow Xj8T5a7aO8drZk5v (existant)
   → XML-RPC : sale.order créé + confirmé Odoo
   → stock.move "réservation" sur produit fini (natif)
   → virtual_available diminue
```

Aucune modification du workflow n8n existant.

### Mode 2 — Saisie manuelle du conditionnement (Phase 1 = UI Odoo standard)

1. Manufacturing → Ordres de fabrication → Nouveau
2. Produit fini + quantité
3. Odoo pré-remplit les composants depuis la BoM
4. Sélection du lot bulk consommé (n° de lot du fût en cours)
5. Valider → décrément bulk + packaging, incrément fini

Pour les 4 produits fab interne : MO préalable de fabrication du bulk avant le MO de conditionnement.

### Annulation de commande

Mini-workflow n8n à ajouter : écoute `orders/cancelled` Shopify → annule la SO Odoo → libère automatiquement la réservation.

## Règles de réapprovisionnement

### Bulks

- Stock mini : 20 kg (pour les 50 bulks)
- Stock max : 200 kg (recommandation)
- Action : RFQ draft générée automatiquement vers FP Cosmetics (ou MO pour les 4 fab interne)

### Packaging

- Seuils min/max selon le tableau Section "Packaging" ci-dessus
- Action : RFQ draft générée automatiquement vers le fournisseur packaging concerné

### Comportement

- Calcul tourne via cron natif Odoo (`scheduler.run_scheduler`)
- Quand `virtual_available < min_qty` : RFQ ou MO créé en `draft`
- RFQ groupée par fournisseur (5 bulks FP Cosmetics sous seuil le même jour = 1 RFQ avec 5 lignes)

## RFQ groupé hebdomadaire (workflow n8n)

**Nouveau workflow** dans folder Yo (`Z2t5yT17QDhgf2XO`).

- **Trigger** : cron tous les lundis à 8h00 (UTC+1)
- **Logique** :
  1. XML-RPC Odoo : récupérer RFQ en draft créées depuis lundi précédent
  2. Grouper par fournisseur
  3. Composer un email récap par fournisseur (texte + lien Odoo pour validation)
  4. Envoyer à yoann@mylab-shop.com
- **Pas d'envoi direct au fournisseur** : Yoann valide manuellement chaque RFQ via le lien Odoo
- **Si aucune RFQ** : email court "Pas de réappro à faire cette semaine"

## Sync stock Odoo → Shopify (mode projeté)

### Modification du workflow existant `1AUxe9M9d9cNKz6W`

**Logique actuelle (à remplacer)** :
```
shopify.location.inventory_level = qty_available  # stock physique fini
```

**Logique nouvelle** :
```python
pour chaque produit fini Odoo:
    # 1. Lire BoM → bulk associé + flacon + bouchon
    # 2. Récupérer stocks disponibles
    # 3. Mix contenance par famille
    potentiel_via_bulk = bulk_kg * mix_contenance / poids_par_bouteille
    potentiel = min(potentiel_via_bulk, flacon_dispo, bouchon_dispo)
    stock_projeté = qty_available_fini + potentiel
    shopify.location.inventory_level = stock_projeté
```

### Configuration

- Mix par famille dans un node "Set" du workflow (modifiable sans code)
- Correspondance produit fini → bulk + packaging : champ custom `x_mylab_bom_summary` sur le produit Odoo, populé au setup
- Fréquence : **garder 5h** (suffisant pour le projeté)

### Cas particuliers

- Coffrets/duos/trios : pas de BoM → logique actuelle conservée (physique pur)
- Pompes vendues seules : produit fini classique, stock physique pur
- Bulks fab interne sans stock + sans MO en cours : stock projeté = stock fini physique uniquement

## Traçabilité lot (CPNP / CE 1223/2009)

### Configuration

- Suivi par lot **activé sur les bulks uniquement** (les 50 produits bulk)
- Pas de suivi par lot sur packaging ni produits finis (Niveau 1 — minimum CPNP)

### Flux

1. **Réception PO bulk** : à la validation, saisie du n° de lot fournisseur (`FP-2026-001`) + date de réception
2. **Conditionnement (MO)** : à la validation, sélection du lot bulk consommé
3. **Rapport de traçabilité descendante** : natif Odoo (lot bulk → MO → produit fini → BL client)

### Date de péremption

- Champ natif `use_date` à la réception bulk
- PAO (Period After Opening) géré au niveau de l'étiquette du produit fini (hors Odoo)

## Setup initial (ordre de déploiement)

Scripts Python XML-RPC dans `scripts/odoo/`, convention `stepNN_*.py`, tous idempotents.

### Phase A — Modélisation Odoo (1-2 jours)

| # | Script | Action |
|---|---|---|
| 1 | `step30_create_locations.py` | `WH/Stock/Bulk`, `WH/Stock/Packaging`, `WH/Stock/Fini` |
| 2 | `step31_install_modules.py` | Vérifier Manufacturing, Inventory, Purchase |
| 3 | `step32_create_vendors_packaging.py` | Fournisseurs packaging (CSV à valider) |
| 4 | `step33_create_bulk_products.py` | ~50 produits bulk |
| 5 | `step34_create_packaging_products.py` | ~15 SKUs packaging |
| 6 | `step35_create_boms.py` | ~150 BoMs |
| 7 | `step36_create_reorder_rules.py` | ~65 règles min/max |

### Phase B — Workflows n8n (½ journée)

| # | Action |
|---|---|
| 8 | Patcher `1AUxe9M9d9cNKz6W` (sync stock projeté avec BoM + mix) |
| 9 | Créer workflow "RFQ récap lundi" (cron 8h, XML-RPC, Gmail) |
| 10 | Ajouter mini-workflow `orders/cancelled` → annulation SO Odoo |

### Phase C — Inventaire initial (1 journée terrain)

| # | Action |
|---|---|
| 11 | Saisie inventaire physique bulk (kg par formule) |
| 12 | Saisie inventaire packaging |
| 13 | Saisie n° lot des fûts bulk en cours |

### Phase D — Mise en route (1 semaine d'observation)

| # | Action |
|---|---|
| 14 | Premier MO de conditionnement en suivant le flux Odoo |
| 15 | Premier récap RFQ du lundi → validation de 1-2 RFQ test |
| 16 | Vérification sync Shopify (stock projeté correct, commande test) |

### Phase E (post-launch, optionnel)

- Wizard "Conditionnement du jour" (UI custom) si UI Odoo standard trop lourde après 2-4 semaines
- Raffinage du mix par famille si dérives constatées
- Passage à seuils dynamiques (couverture en semaines) après 3-6 mois d'historique
- BoMs des coffrets/duos/trios si besoin

## Décisions clés et rationale

| Décision | Choix | Pourquoi |
|---|---|---|
| Approche globale | Odoo MRP natif | Infra déjà en place, traçabilité CPNP gratuite, pas de code custom |
| Modes de décrémentation | Mode 1 (réservation Shopify) + Mode 2 (conditionnement manuel) | Stock projeté correct sans risque d'oversell + reflète la réalité physique |
| Seuil de réappro | Statique en kg (20/200) | Démarrer simple, passer en dynamique quand on aura de la donnée |
| Granularité bulk | 1 formule = 1 bulk = N contenances | Cas standard, pas de bulks partagés |
| Façonniers | 1 partenaire (FP Cosmetics) + 4 produits fab interne | Reflet de l'état actuel |
| Packaging dans BoM | Flacon + bouchon (étiquettes exclues) | Étiquettes imprimées à la demande |
| Pompes | Produit annexe séparé (pas dans BoM) | Option client, évite les variants |
| Yield | 100% (perte ~2% par inventaires mensuels) | Précision suffisante, pas la peine de complexifier |
| UI mode 2 | UI Odoo standard (Phase 1) | YAGNI — wizard custom seulement si friction prouvée |
| Lot tracking | Niveau 1 (bulk uniquement) | Minimum CPNP, ajout fini possible plus tard |
| RFQ auto | Récap email hebdomadaire (lundi 8h) | Validation manuelle conservée, fréquence raisonnable |
| Mix par famille | Calculé depuis données ventes 2024-2025 | Évite l'oversell entre contenances |
| Sync Shopify | Stock projeté (fini + bulk × mix + packaging) | Yoann ne veut pas louper de ventes alors qu'on a la matière |

## TBD à valider lors du setup

- Stock mini/max pour : flacon ambré 200ml (spray texturisant), pompe 1000ml, pulvérisateur spray, pot 400ml (si distinct du 200ml)
- Fournisseur par SKU packaging (nom, email, lead time, MOQ)
- Liste complète des formules → bulk (depuis `ml-product-map.json` actuel, à valider)

## Hors scope (Phase 2 ou plus tard)

- BoMs des coffrets, duos, trios (~12 produits assemblés)
- Wizard custom "Conditionnement du jour"
- Mix par formule (au lieu de par famille)
- Seuils dynamiques en couverture de semaines
- BoMs matières premières pour les 4 produits fab interne
- Suivi par lot des produits finis (Niveau 2 CPNP)
- Suivi PAO automatisé
- Tableau de bord Odoo dédié (couverture par formule, top consommations, etc.)
