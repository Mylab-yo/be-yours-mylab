# Spec — Moteur de paliers volume + remise client via Shopify Function

**Date :** 2026-06-22
**Auteur :** Yoann / Claude
**Statut :** Design validé, prêt pour plan d'implémentation

## Problème

Les prix dégressifs par quantité (« paliers volume ») affichés sur les fiches produit et
dans le drawer MyLab sont **purement cosmétiques** : ils sont calculés côté client en JS à
partir de `assets/ml-product-map.json` et **ne sont jamais facturés** par Shopify. Le variant
Shopify a un prix unique (ex. Bain Miraculeux 50ml = 8,50 €). À 6 unités le 1er palier coïncide
avec le prix de base, mais dès 12 unités le client voit 8,05 €/u et Shopify encaisse 8,50 €/u.

BSS B2B Volume Pricing assurait jusqu'ici l'application réelle des paliers au checkout ; il a été
retiré (« trop compliqué pour les clients »). Plus rien n'enforce donc les paliers.

En parallèle, on veut accorder **−10 % supplémentaires** à 4 clients spécifiques, **par-dessus**
le prix palier.

### Données catalogue
- 79 combinaisons produit×format avec paliers, **17 structures de paliers distinctes**.
- Seuils non uniformes : 6/12/24/48/96 (200ml), 1/3/6/12 (1000ml), 6/14/28/42, etc.
- Pourcentages non uniformes d'un produit à l'autre.
- → Les remises **automatiques natives Shopify sont écartées** (il faudrait des dizaines de
  remises par produit, et le « minimum de quantité » natif se calcule sur le total du panier,
  pas par ligne).

## Objectif

Au checkout, le prix réellement facturé doit **toujours** correspondre au palier volume affiché
(pour tous les clients), **plus** une remise de 10 % pour les 4 clients ciblés. Le tout avec une
**source unique** de tarifs et **zéro casse-tête de cumul**.

## Solution retenue — Approche A : Shopify Function de réduction maison

Une seule *discount function* (cible `cart.lines.discounts.generate.run`) qui, au checkout, pour
chaque ligne du panier :
1. lit la **quantité**, le **prix unitaire**, les **paliers du produit** (metafield) et le **tag
   client** ;
2. trouve le palier applicable (plus grand seuil ≤ quantité) → prix cible ;
3. si le client porte le tag `remise-10` → prix cible × 0,9 ;
4. émet une remise en **pourcentage** sur la ligne pour atteindre ce prix.

Le 10 % est **fusionné dans la fonction** (pas une remise séparée) → un seul calcul déterministe,
aucun problème de cumulabilité.

### Pourquoi cette approche
- **Source unique** : `ml-product-map.json` reste la vérité ; un script pousse les paliers en
  metafields. Plus de divergence affichage ↔ checkout.
- **Plan Grow OK** : seule la cible *fetch réseau* des Functions est réservée à Plus ; on lit des
  metafields produit, pas de réseau.
- **Flux Odoo intact** : la remise descend en `discount_allocations` par ligne → le workflow n8n
  existant la passe déjà en `sale.order.line.discount`. Émettre un **pourcentage** donne une
  fidélité maximale côté Odoo (le champ `discount` y est un %).
- **Rien côté client** : pas d'app installée, pas de mur de login (contraire de BSS).

## Architecture / flux

```
ml-product-map.json  ──(sync_volume_tiers.py)──►  metafield produit  mylab.volume_tiers (JSON)
       (source unique)                                       │
                                                             ▼
client au checkout ──► Function  cart.lines.discounts.generate.run
   par ligne :  qty + prix unitaire + metafield + hasAnyTag(["remise-10"])
   → palier (plus grand seuil ≤ qty) → prix cible
   → si tag : × 0,9
   → remise % pour atteindre le prix cible
                                                             ▼
   checkout exact ──► discount_allocations/ligne ──► n8n ──► sale.order.line.discount Odoo
```

## Composants (unités isolées)

### 1. Définition de metafield `mylab.volume_tiers`
- Namespace `mylab`, key `volume_tiers`, type **JSON**.
- Owner : `PRODUCT`.
- Valeur : tableau de paires `[quantité, prix_unitaire_centimes]`, triées par quantité croissante.
  Exemple Bain Miraculeux : `[[6,850],[12,805],[24,765],[48,680],[96,610]]`.
- Lisible par la fonction via `merchandise.product.metafield(namespace:"mylab", key:"volume_tiers").jsonValue`.

### 2. `scripts/shopify/sync_volume_tiers.py`
- Lit `assets/ml-product-map.json`.
- Pour chaque entrée et chaque `size` de `entry.sizes` : `handle = entry.sizes[size]`,
  `tierString = entry.tiers[size]` (ex. `"6:850,12:805,..."`).
- Parse `tierString` → `[[6,850],...]`.
- Résout le produit par handle (Admin GraphQL `productByHandle`) → id + prix variant.
- Écrit le metafield (`metafieldsSet`).
- **Garde-fou** : compare le prix du variant (centimes) au prix du **1er palier** (base) et
  **signale** tout écart (le variant devrait égaler la base ; sinon la fonction recalerait le prix).
- Idempotent. Réutilise le token Admin (cf. `reference_api_keys.md`).

### 3. App Shopify `mylab-discounts/` — extension *discount function*
- `shopify.extension.toml` : `api_version` courante, `targeting` =
  `cart.lines.discounts.generate.run`, **discountClasses = Product**.
- `src/input.graphql` :
  ```graphql
  query Input {
    cart {
      lines {
        id
        quantity
        cost { amountPerQuantity { amount } }
        merchandise {
          __typename
          ... on ProductVariant {
            id
            product {
              handle
              metafield(namespace: "mylab", key: "volume_tiers") { jsonValue }
            }
          }
        }
      }
      buyerIdentity {
        customer { hasAnyTag(tags: ["remise-10"]) }
      }
    }
  }
  ```
- `src/run.js` (logique déterministe) :
  - `tagged = cart.buyerIdentity.customer?.hasAnyTag === true`.
  - Pour chaque ligne avec un `volume_tiers` valide :
    - `unit = round(amountPerQuantity * 100)` (centimes).
    - `tier = max seuil ≤ quantity` ; si aucun (`quantity` < 1er seuil) → ligne ignorée.
    - `target = round(tierPrice * (tagged ? 0.9 : 1))`.
    - `pct = (unit - target) / unit * 100` ; si `pct ≤ 0` → ligne ignorée (jamais de majoration).
    - Candidat : `targets:[{cartLine:{id}}]`, `value:{percentage:{value: pct.toFixed(3)}}`,
      `message: tagged ? "Tarif volume + remise pro" : "Tarif volume"`.
  - Sortie : `operations:[{ productDiscountsAdd: { selectionStrategy: "FIRST", candidates } }]`.
- Tests unitaires (voir § Tests).

### 4. Remise automatique activant la fonction
- Créer une **remise automatique** (sans code) liée à la fonction
  (`discountAutomaticAppCreate` ou via l'UI Réductions).
- Combinaison : **autonome** (non cumulable avec d'autres remises produit) — le 10 % est déjà
  intégré. Décision révisable plus tard si on veut autoriser des codes ordre/livraison.

### 5. Décommissionnement
- Désactiver la promo native `mylab10` (le 10 % est désormais dans la fonction).
- Confirmer que les règles BSS sont inactives/supprimées.

## Décisions de conception

- **Stockage des paliers = metafield synchronisé** (et non bundlé dans le code) : changer un tarif
  = relancer le script, sans redéployer l'app.
- **Remise en pourcentage** (et non montant fixe) : meilleure fidélité Odoo (`discount` = %).
  Compromis assumé : l'arrondi monétaire de Shopify peut induire ±1 centime sur un prix cible ;
  acceptable et conforme à la pratique des apps de volume. Validé en tests d'intégration.
- **Prix unitaire de référence = prix réel de la ligne** (`amountPerQuantity`), borné à ≥ 0 :
  la fonction recale vers le palier mais ne majore **jamais**.

## Cas limites / erreurs

| Cas | Comportement |
|-----|--------------|
| Quantité entre deux paliers | Palier inférieur (plus grand seuil ≤ qty). |
| Quantité sous le 1er seuil | Aucune remise. |
| Plusieurs lignes d'un même produit | Évaluées indépendamment par leur quantité (= comportement JS actuel). |
| Client non connecté | Pas de tag → volume seul. |
| Metafield absent/invalide | Ligne ignorée (zéro remise, sécurisé). |
| Prix variant ≠ base palier | La fonction recale vers le palier, jamais de majoration ; le script de sync remonte l'écart pour correction des prix de base. |

## Tests

- **Unitaires** (`shopify app function run` avec inputs JSON) :
  bornes de paliers (5/6/11/12/23/24/47/48/95/96), taggé vs non, metafield manquant, qty sous le
  minimum, motif 1000ml (1/3/6/12), motif 200ml (6/12/24/48/96), prix variant ≠ base.
- **Intégration** (dev store) : commandes test à plusieurs quantités + client taggé `remise-10`
  → total checkout == table des paliers (et ×0,9 pour le client taggé).
- **Odoo** : 1 commande test via n8n → la remise atterrit par ligne, total net cohérent
  Shopify ↔ Odoo.

## Hors périmètre (phase 2, optionnel)

Afficher le −10 % des clients taggés **dans le drawer** MyLab. Aujourd'hui le drawer montrera le
prix palier ; le −10 % n'apparaîtra qu'au checkout pour ces clients (acceptable car B2B connectés).

## Déploiement / rollout

1. Créer la définition de metafield + lancer `sync_volume_tiers.py` (corriger les écarts base signalés).
2. Développer + tester la fonction en local, déployer l'app sur un **thème/dev** d'abord.
3. Créer la remise automatique, passer les commandes test (checkout + Odoo).
4. Désactiver `mylab10` native, confirmer BSS off.
5. Activer en prod, surveiller les premières commandes réelles.
