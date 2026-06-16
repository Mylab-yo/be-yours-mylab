# MyLab Tier Discount — Shopify Product Discount Function

Cette Shopify Function applique automatiquement les **tarifs paliers MY.LAB** au checkout, pour TOUS les clients (anonymes ou logés-in). Elle remplace la logique partielle de BSS B2B qui ne couvre que certains produits/quantités.

## Source de vérité

Les paliers viennent de `assets/ml-product-map.json` (le même fichier lu par `mylab-product.js` côté cart). Le mapping est compilé dans `src/tier-map.js` via :

```bash
python scripts/build_tier_map.py
```

Lance ce script à chaque modification de `ml-product-map.json`, puis redéploie la function.

## Architecture

- **Input** (`src/run.graphql`) : pour chaque ligne du cart, on récupère le handle du produit, la quantité, et le prix unitaire.
- **Logic** (`src/run.js`) : on cherche le palier applicable pour la quantité actuelle, on calcule `discount = prix_shopify - prix_palier`, on retourne la liste des discounts à appliquer.
- **Output** : un array de `discounts` au format Shopify Product Discount.

## Déploiement initial (à faire une seule fois)

1. **Prérequis** :
   - Shopify CLI ≥ 3.91 (`shopify version`)
   - Compte Shopify Partners associé à la boutique mylab-shop-3
   - Node.js ≥ 18

2. **Installer les dépendances** :
   ```bash
   cd shopify-functions/tier-discount
   npm install
   ```

3. **Initialiser comme app Shopify** (depuis ce dossier) :
   ```bash
   shopify app init --name=mylab-tier-discount
   ```
   - Choisir : "Build an extension into an existing app" si tu as déjà une app Partners
   - OU : "Create a new app"

4. **Générer les types TypeScript** :
   ```bash
   npm run typegen
   ```

5. **Tester localement** (optionnel) :
   ```bash
   shopify app function run --input fixtures/cart-1000ml-qty3.json
   ```

6. **Déployer** :
   ```bash
   shopify app deploy
   ```
   - Suivre les prompts pour créer/lier l'app sur Partners
   - L'app sera installée sur mylab-shop-3.myshopify.com

7. **Activer la function dans Shopify Admin** :
   - Aller dans Admin → Discounts → Create discount → Automatic
   - Choisir "MyLab Tier Discount" dans la liste des Functions
   - Configurer le titre (ex: "Tarifs paliers MY.LAB")
   - Sauvegarder

## Mises à jour ultérieures

Quand tu modifies les paliers dans `ml-product-map.json` :

```bash
# Depuis la racine du repo
python scripts/build_tier_map.py

# Puis depuis le dossier de la function
cd shopify-functions/tier-discount
shopify app deploy
```

## Tests à faire après déploiement

1. **Cart anonyme** avec 3× Shampoing Déjaunisseur Platine 1000ml
   - Cart : 27,45 €/u × 3 = 82,35 € ✓
   - Checkout : doit aussi afficher 82,35 € (et non 86,70 €)

2. **Cart anonyme** avec 6× Crème Boucles 200ml
   - Cart : 8,50 €/u × 6 = 51,00 € ✓
   - Checkout : doit aussi afficher 51,00 €

3. **Cart anonyme** avec 24× Crème Boucles 200ml
   - Cart : 7,65 €/u × 24 = 183,60 € ✓
   - Checkout : doit aussi afficher 183,60 € (et non 204,00 €)

## Coexistence avec BSS B2B

BSS continue à fonctionner. La Function s'applique en plus (Shopify combine les remises selon la `discountApplicationStrategy`). On a mis `FIRST` qui prend la première remise applicable — donc si BSS a une remise et nous aussi, c'est BSS qui gagne sur cette ligne.

Si tu veux que la Function prenne le dessus partout, change `FIRST` en `MAXIMUM` dans `src/run.js`.

## Désactivation

Si besoin :
1. Admin → Discounts → MyLab Tier Discount → Désactiver
2. Ou `shopify app deploy --skip-build` après avoir commenté la function dans `shopify.extension.toml`
