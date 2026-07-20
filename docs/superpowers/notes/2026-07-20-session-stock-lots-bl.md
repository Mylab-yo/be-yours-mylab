# Session 2026-07-20 — Stock retail/bulk, OF, lots et bons de livraison

**Branche** : `feat/stock-retail-bulk-split` (worktree `d:/be-yours-mylab-stock-split`)
**Contexte** : parti d'un stock Shopify négatif bloquant les ventes, dérivé sur plusieurs
chantiers Odoo connexes au fil des constats de Yoann.

---

## 1. Problème initial — stock Shopify négatif

**Cause racine** : les commandes bulk (≥ 50 L, remplies à la volée au labo, jamais dans le
stock physique MyLab) décrémentaient le **même pool** que le retail — l'emplacement parent
`MYVO/Stock` (28) — le poussant à **−662** sur le shampoing nourrissant 200ml.
Le sync n8n, avec son filtre `eff > 0`, ne poussait alors plus rien vers Shopify, qui restait
bloqué sur le négatif laissé par ses propres décréments de commande.

**Solution retenue (approche B)** : corriger à la source plutôt que maquiller côté sync.

- Une ligne est **bulk** si `qty × contenance ≥ 50 000 ml` **OU** tag commande `bulk-labo`.
- Le bulk pouvant être **mélangé** à une commande retail → routage **ligne par ligne**.
- Emplacements déjà existants : retail = `MYVO/Stock/Fini` (**47**), bulk = `MYVO/Stock/Bulk` (**45**).
- Le sync lira les quants de Fini(47) : `dispo = quantity − reserved_quantity`.

**Livré** : spec, plan (8 tasks), classificateur pur testé, routeur dry-run + `--apply`.

### Canari — risque technique levé

Commande test jetable mélangée (200ml ×6 retail + 500ml ×100 bulk) :

| Vérification | Résultat |
| --- | --- |
| Source mixte Fini/Bulk dans un même picking | **ACCEPTÉE** par Odoo 18 |
| Ligne bulk après `--apply` | repointée sur Bulk(45), re-réservée (`assigned`) |
| Ligne retail | intacte |
| Stock physique / autres commandes | inchangés, zéro collatéral |

→ Le repli « split-picking » n'est pas nécessaire.

⚠️ Le canari a **brûlé les numéros S00661 et MYVO/OUT/00239** (séquence consommée
irréversiblement malgré la suppression). Cleanup complet ensuite : commande, partner et
picking supprimés, aucune réservation fantôme.

---

## 2. Ordres de fabrication

**10 OF en cours annulés** (aucun n'avait produit quoi que ce soit, `qty_produced=0` partout).
Effet de bord bénéfique : l'`incoming` fantôme de **2778 u** sur le 200ml a disparu
(MO/00035 + MO/00036), la prévision est redevenue cohérente.

---

## 3. Testeurs — garde-fou (exigence Yoann)

Règle : un testeur doit s'indexer sur le stock de son parent **200ml**, ou **50ml** pour les
produits de finition (sérum finition, sérum barbe, huile à barbe, bain miraculeux).

Vérification empirique sur les 39 testeurs réels : **36 OK, 3 cassés** par incohérence de
nommage SKU.

| Testeur | Classique réel | Écart |
| --- | --- | --- |
| `creme-protectrice-de-couleur-testeur` | `creme-protecteur-de-couleur-200-ml` | féminin/masculin |
| `shampoing-cuivre-intense-testeur` | `shampoing-coloristeur-cuivre-200-ml` | « intense » absent |
| `masque-cuivre-intense-testeur` | `masque-coloristeur-cuivre-200-ml` | tombait sur le 1000ml |

Yoann a confirmé que **« cuivre intense » = « cuivre »** (même produit).

Correctifs inscrits au plan (Task 6) : regex élargi à `-200ml` collé (4 SKU réels étaient
invisibles), table d'alias, et **refus de tout parent hors 200/50ml** avec alerte.
On ne renomme **pas** les SKU dans Odoo : le matching Odoo↔Shopify se fait par SKU.

---

## 4. Suivi d'inventaire manquant

Constat de Yoann : le shampoing nourrissant 500ml n'avait pas de suivi d'inventaire.
Audit → **7 produits** concernés, dont **4 vrais produits finis**.

Odoo **bloque** le passage consommable→stockable d'un produit déjà utilisé
(*« Vous ne pouvez pas modifier le suivi de l'inventaire d'un produit qui a déjà été utilisé »*),
UI comme XML-RPC. C'est une garde applicative, pas une contrainte de base.

**Contournement** (choix assumé vs « nouveau produit + repointer », qui aurait cassé
l'historique et le lien SKU) : backup → `UPDATE product_template SET is_storable = true` →
`docker restart odoo` (ormcache) → vérification via l'ORM.

Traités : tmpl **2365** (nourrissant 500ml), **2422** (gloss 100ml), **2426** (gloss 200ml),
**2457** (tulipe noire 1000ml). Laissés consommables volontairement : POMPE-200, POMPE-500,
étiquettes 115x50mm.

**Découverte au passage** : `masque-gloss-200-ml` a **1084 unités engagées** pour 0 stock —
totalement invisible tant que le produit n'était pas suivi. À investiguer côté Yoann.

---

## 5. Bons de livraison — deux causes distinctes

### a) Le reliquat non voulu = le flag `picked`

Odoo 17/18 ne valide pas d'après la quantité affichée mais d'après `stock.move.picked`.
Si **une seule** ligne est `picked=True`, Odoo considère les autres comme non expédiées et
propose un reliquat — alors que l'écran montre 6/6, 4/4… Constaté sur `MYVO/OUT/00218` ;
**180 lignes** concernées sur l'ensemble des BL prêts.

**Outil livré** : `scripts/odoo/prepare_picking_full.py` (dry-run par défaut).

```bash
python scripts/odoo/prepare_picking_full.py --picking MYVO/OUT/00218 --apply
```

À lancer **BL par BL au moment d'expédier**, jamais `--all-ready --apply` : ça déclarerait
d'un coup toutes les livraisons comme intégralement prêtes, faux en cas d'expédition partielle.

### b) Le blocage par les lots

Le type d'opération « Bons de livraison » (id 10) avait `use_create_lots=False` **ET**
`use_existing_lots=False` — la pire combinaison : Odoo exige un lot mais interdit à la fois
d'en créer un et d'en piocher un existant. Corrigé en `use_existing_lots=True`.

Puis, **décision assumée de Yoann** après trois rappels du risque de traçabilité CPNP :
le **suivi par lot a été retiré de tout le catalogue** — les **119** `product.template`
passés en `tracking='none'`. Odoo autorise ce changement par l'ORM.

**Effet vérifié** : l'outil ne réclame plus aucun lot (37 → 0). BL validables sans lot.

**Retour arrière** : backup `/root/OdooYJ_before_untrack.dump` (18 Mo, VPS, 20/07 13:29).
Les quants ont **conservé leur `lot_id`** → réactiver `tracking='lot'` retrouverait l'historique.

---

## Incidents de session

- **Checkout partagé** : une autre session a basculé `d:\be-yours-mylab` sur
  `feat/fiches-fortifiant` en cours de travail. Rien perdu (tout était poussé) → bascule sur
  un **worktree isolé** `d:/be-yours-mylab-stock-split`.
- **Cleanup du canari** : `action_cancel` seul ne suffit pas sur une SO confirmée en Odoo 18
  (wizard `sale.order.cancel` requis, picking à annuler d'abord). Trois passes nécessaires.

---

## Reste à faire

1. **Inventaire physique sur `MYVO/Stock/Fini` (47)** — par Yoann. Jalon bloquant : tout le
   reste en dépend. Inclure les 4 produits nouvellement suivis. (Simplifié désormais : plus
   de n° de lot à saisir.)
2. **Tasks 5-7 du plan** : bascule du sync n8n (nodes 01/02, déploiement **en set**),
   avec le garde-fou testeurs.
3. **Task 3 résiduelle** : confirmer sur une vraie livraison que Fini ne décrémente que de
   la ligne retail.
4. Points ouverts : quant orphelin `shampoing-gel-douche-1000-ml` (qty 1) ; les 1084 u de
   `masque-gloss-200-ml`.
