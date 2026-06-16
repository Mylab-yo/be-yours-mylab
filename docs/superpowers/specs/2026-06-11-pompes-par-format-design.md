# Pompes par format — fiche produit + commande express

**Date :** 2026-06-11
**Statut :** design validé (maquette + décisions confirmées par Yoann)
**Maquette de référence :** `docs/mockups/pompes-mockup.html`

## Objectif

Permettre aux clients pro de commander des **pompes doseuses au format du flacon
sélectionné** (pompe 200 ml pour les flacons 200 ml, etc.), sur la fiche produit
et sur la page Commande Express. Une pompe par flacon, ajoutée comme ligne panier
distincte, à la même quantité que les flacons.

## Décisions verrouillées

| Sujet | Décision |
|---|---|
| Formats équipés d'une pompe | **200, 500, 1000 ml** (50 et 400 exclus) |
| Granularité | **Une pompe par format** (partagée entre tous les produits du format) |
| Prix de vente HT | 200 = **0,50 €** · 500 = **0,50 €** · 1000 = **1,00 €** |
| Quantité pompe | **Alignée** sur la quantité de flacons (1 pompe / flacon) |
| Ajout panier | Ligne panier **distincte** (flacon palier + pompe prix fixe) |
| UX fiche produit | Case à cocher add-on entre paliers et carte prix |
| UX commande express | Colonne « Pompe » avec case à cocher par ligne |
| Source produits | Réutiliser les produits **Odoo existants** |

### Produits Odoo réutilisés

| Format | Produit Odoo | tmpl / variant | SKU à poser | Prix HT |
|---|---|---|---|---|
| 200 | Pompe 200ml | 2440 / 2486 | `POMPE-200` | 0,50 € |
| 500 | Pompe 500ml | 2364 / 2410 | `POMPE-500` | 0,50 € |
| 1000 | Pompe 1000ml | 2518 / 2564 | `POMPE-1000` (existe déjà) | 1,00 € |

> ⚠️ Doublons connus à ne PAS utiliser : « Pompe 200/500ml » (POMPE-200-500, sale_ok=False),
> « Dispenser pompe sérum » (sale_ok=False), « Pompe 125ml ». Ne pas y toucher.

## Architecture

Tout le système (fiche, contenances, commande express, drawer) lit déjà une seule
source de vérité : `assets/ml-product-map.json`. On ajoute un bloc `_pumps` qui mappe
**format → handle de la pompe Shopify**. Le prix et le variant ID sont lus **en direct**
via `/products/{handle}.js` (pas de duplication de prix → pas de dérive avec Shopify/Odoo).

### Modèle de données — `ml-product-map.json`

```json
"_pumps": {
  "200":  { "handle": "pompe-200ml" },
  "500":  { "handle": "pompe-500ml" },
  "1000": { "handle": "pompe-1000ml" }
}
```

Clé `_pumps` préfixée `_` comme `_doc` (les itérations existantes sur le map
ignorent déjà les entrées sans `sizes`, donc `_pumps` ne perturbe pas les boucles —
**à vérifier** dans chaque consommateur, voir Risques).

## Prérequis — produits pompes (hors thème)

1. **Odoo** : poser les SKU `POMPE-200`, `POMPE-500` sur les variantes 2486 / 2410
   (POMPE-1000 existe déjà). Vérifier `sale_ok=True`, `taxes_id=[103]` (20% G),
   `list_price` conforme. Idempotent.
2. **Shopify** : créer 3 produits (handles `pompe-200ml`, `pompe-500ml`, `pompe-1000ml`),
   prix HT fixe, `taxes_included=False` cohérent avec le catalogue, dans une collection
   cachée (non listée), SKU alignés sur Odoo pour la sync. Récupérer les variant IDs.
3. Vérifier que la sync produit Shopify↔Odoo matche bien par SKU.

## Composants

### 1. Fiche produit — `main-product.liquid` + `mylab-product.js`

- **Markup** (`main-product.liquid`, dans le bloc `[data-mylab-pricing]`, entre
  `#ml-qty-btns` et `.ml-pricing-card`) : un `<label class="ml-pump">` masqué par défaut
  (`hidden`), révélé par le JS si `_pumps[format]` existe.
- **CSS** (`mylab-product.css`) : classes `.ml-pump`, `.ml-pump__check/body/title/sub/price`,
  `.ml-pump-line` (cf. maquette).
- **JS** (`mylab-product.js`) :
  - À l'init, après chargement du map + product JSON : déduire le **format** du produit
    courant (matcher `handle` dans `entry.sizes` → clé = format).
  - Si `map._pumps[format]` existe : fetch `/products/{pumpHandle}.js` → `variantId` + `price`.
    Remplir le libellé (« pompe {format} ml », « +{prix} €/u »), révéler le `<label>`.
  - Stocker `ctx.pump = { variantId, price }` et `ctx.pumpChecked`.
  - Sur changement de palier : mettre à jour la ligne `+ X € de pompes (qty × prix)`.
  - `handleAddToCart` : passer d'un item unique à un **tableau** ;
    si pompe cochée → `items: [{id: variantId, qty}, {id: pump.variantId, qty}]`.

### 2. Commande Express — `ml-quick-order.liquid` + `ml-qo-row.liquid`

- **Markup** : ajouter une colonne `<th class="col-c">Pompe</th>` après Quantité.
  Dans `ml-qo-row.liquid` et dans `buildLinkedRow()` (JS) : une cellule `col-c` avec
  une case `data-pump` + prix unitaire ; ou `—` si le format n'a pas de pompe.
- **JS** (script inline de la section) :
  - Charger `map._pumps` ; pour chaque format présent, fetch une fois la pompe
    (`variantId` + `price`), mise en cache.
  - Chaque ligne connaît son format (déjà calculé pour `sizeLabel`) → afficher/masquer
    la case pompe + prix.
  - `updateTotal()` : ajouter `pumpPrice × qty` pour chaque ligne pompe cochée ;
    afficher « · dont X € de pompes ».
  - Submit : pour chaque ligne sélectionnée + pompe cochée, pousser aussi
    `{id: pumpVariantId, quantity: rowQty}` dans `items`.

### 3. Cart drawer — aucune modification

Le chemin `ml_has_non_tiered` (`mini-cart.liquid:646`) affiche déjà le prix Shopify
natif pour tout produit hors paliers. La pompe (prix fixe, hors `_pumps` côté tiers)
s'affiche comme une ligne normale. Le prix Shopify de la pompe étant HT
(`taxes_included=False`), l'affichage et le total checkout sont cohérents.

## Flux de données

```
ml-product-map.json (_pumps: format→handle)
        │
        ├─ fiche produit : format courant → fetch pompe → case → 2 items au panier
        └─ commande express : formats présents → fetch pompes → colonne → N items au panier
        │
        ▼
/cart/add.js  {items:[ {flacon, qty}, {pompe, qty} ]}
        ▼
cart:refresh → mini-cart (pompe = ligne non-tiered, prix Shopify natif)
        ▼
checkout (BSS B2B pour flacons ; prix fixe Shopify pour pompes)
```

## Gestion d'erreurs

- `_pumps[format]` absent → pas de case pompe (silencieux).
- Fetch pompe échoue (`/products/{handle}.js` 404) → ne pas révéler la case, log console.
  Ne jamais bloquer l'ajout du flacon.
- Pompe en rupture (`available=false`) → masquer la case (ou désactiver avec mention),
  cohérent avec le traitement OOS existant en commande express.

## Tests / vérification

1. Fiche produit 200 ml : case visible « +0,50 €/u », coché → 2 lignes au panier, qty = palier.
2. Fiche produit 50 ml (sérum) : **pas** de case pompe.
3. Bascule contenance 200→1000 : libellé + prix pompe se mettent à jour (0,50 → 1,00 €).
4. Commande express : colonne pompe, 50 ml = `—`, total inclut « dont X € de pompes ».
5. Panier : pompe affichée comme ligne normale à son prix Shopify, total checkout correct.
6. Sans JS : la case n'apparaît pas (dégradation propre).

## Risques

- **Itérations sur `ml-product-map.json`** : vérifier que `_pumps` (sans `sizes`) ne
  casse aucun consommateur. `main-product.liquid:723` et `ml-utils.findProductEntry`
  bouclent sur les entrées et `continue` si `!e.sizes` → OK a priori, **à confirmer**
  fichier par fichier avant édition.
- **Prix Shopify ≠ prix Odoo** : la pompe doit avoir le même prix HT des deux côtés
  pour éviter un écart facture. Sync par SKU.
- **Cache section Shopify** : après push, re-save la page en Theme Editor pour invalider
  le rendu (cf. feedback connu).

## Hors scope (YAGNI)

- Pas de palier dégressif sur les pompes (prix fixe).
- Pas de pompe pour 50/400 ml.
- Pas de configurateur / choix de couleur de pompe (≠ configurateur Takemoto).
