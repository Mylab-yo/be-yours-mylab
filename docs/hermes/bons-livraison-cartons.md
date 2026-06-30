---
name: bons-livraison-cartons
description: Comprendre et gérer les bons de livraison MyLab à répartition automatique en cartons (Odoo). Sert de référence à Hermes pour expliquer le système et pour changer le nombre d'articles par carton d'un produit. Use when on parle de "bon de livraison", "BL", "cartons", "colis", "répartir en cartons", "capacité carton", "combien d'articles par carton", "nombre d'unités par colis".
version: 1.0.0
platforms: [hermes]
metadata:
  hermes:
    tags: [odoo, logistique, expedition, bon-de-livraison, cartons]
---

# Bons de livraison MyLab — répartition automatique en cartons

> Document de référence pour Hermes. Décrit le système de BL « cartons » de MyLab dans
> Odoo et la procédure exacte pour **changer le nombre d'articles par carton** d'un produit.
> Source de vérité côté code : `scripts/odoo/` du repo `be-yours-mylab`.

## 1. Le principe en une phrase

Chaque produit expédiable porte une **capacité carton** (`x_carton_capacity`) = le **nombre
d'unités qui tiennent dans un carton d'expédition**. Quand on prépare une livraison, un bouton
Odoo répartit automatiquement les produits dans des cartons numérotés selon cette capacité, puis
on imprime un bon de livraison PDF qui détaille le contenu carton par carton.

## 2. Le modèle de données

| Élément | Détail |
|---|---|
| **Champ** | `x_carton_capacity` (entier) sur `product.template` |
| **Libellé Odoo** | « Capacité carton (unités) » |
| **Aide** | « Nombre d'unités par carton d'expédition. 0 = pas de carton défini. » |
| **Portée** | Au niveau du modèle produit → s'applique à toutes ses variantes |
| **Lecture** | L'action de répartition lit `ml.product_id.x_carton_capacity` au moment du clic |

La capacité **est en même temps la clé de la famille** : tous les produits qui partagent la même
valeur de capacité sont regroupés et empilés ensemble dans les mêmes cartons.

### Familles standard (valeurs actuelles)

| Capacité | Famille (libellé sur le BL) | Produits typiques |
|---:|---|---|
| `63` | 50ml sérum/huile | sérums, huiles, bain miraculeux 50 ml (barbe, repair oil, fortifiant, finition ultime…) |
| `40` | 200ml crème/shampoing | shampoings, crèmes, sprays 200 ml + masques 200 ml **sans rinçage** |
| `24` | 200/400ml masque | masques 200 ml et 400 ml (avec rinçage) |
| `23` | 500ml crème/shampoing | shampoings, crèmes 500 ml |
| `12` | 1L shampoing/masque | shampoings, crèmes, masques 1000 ml / 1 L |
| `0` | Divers | packs, coffrets, testeurs, duos/trios, pompes, frais, services, remises… |

**Capacité `0` = cas spécial** : le produit n'a pas de carton dédié. Tout ce qui est en `0`
est regroupé dans un carton « Carton X - Divers » et **n'est jamais scindé**.

## 3. Le workflow côté Odoo (utilisateur)

1. Ouvrir la livraison (`stock.picking`) — état **« Prêt » (assigned)** ou **« Fait » (done)**.
2. Cliquer le bouton **« Répartir en cartons »** dans l'en-tête (header) du formulaire.
   - Le bouton n'apparaît que si l'état est `assigned` ou `done`.
3. Imprimer le **bon de livraison PDF custom** (rapport `mylab.report_deliveryslip_document`,
   menu *Imprimer* du picking).

### Ce que fait le bouton (action serveur « Répartir en cartons »)

- **Purge** d'abord les cartons auto déjà créés (nom préfixé `Carton `) et **reconsolide** les
  lignes qui avaient été scindées lors d'un run précédent → **idempotent**, on peut recliquer
  autant de fois qu'on veut sans accumuler de fragments.
- Regroupe les lignes par **famille de capacité**.
- Remplit les cartons d'une famille jusqu'à la capacité, en **scindant une ligne** si besoin
  pour finir un carton (ex. 90 unités à 40/carton → carton plein 40, carton plein 40, carton 10).
- Crée des colis `stock.quant.package` nommés **`Carton X/Y - <libellé famille>`**
  (X = numéro, Y = total de cartons). Les « Divers » passent en dernier.

### Ce que montre le BL PDF

- En-tête : n° de BL, réf. commande, date d'expédition, client.
- **Badge résumé** : « N cartons — poids total kg — transporteur ».
- **Récapitulatif produits** : tableau agrégé (référence, désignation, qté, poids unit./total).
- **Détail par carton** : un bloc par carton avec case à cocher ☐, indicateur de remplissage
  `unités/capacité` (ex. `40/40`) ou `N unités` pour les Divers, poids, et la liste des produits.
- **Reliquat** : produits demandés mais non couverts sur ce bon (« expédiés dès réception du stock »).
- **Bloc signature** : « Reçu en bon état par / Date / Signature ».

## 4. ⭐ Changer le nombre d'articles par carton

C'est la question la plus fréquente. Trois niveaux selon ce qu'on veut faire.

### Cas A — un seul produit (le plus courant, sans code)

1. Odoo → **Inventaire/Ventes → Produit** concerné (`product.template`).
2. Champ **« Capacité carton (unités) »** → saisir le nouvel entier (ex. `36`).
3. Enregistrer.
4. Sur les livraisons **déjà existantes**, recliquer **« Répartir en cartons »** pour appliquer
   (la répartition ne se recalcule pas toute seule). Les nouvelles livraisons l'utilisent direct.

> ⚠️ Mettre `0` = le produit bascule dans le carton « Divers » et n'est plus scindé.

### Cas B — recalculer en masse depuis les noms de produits

Le script `scripts/odoo/step02_init_carton_capacity.py` déduit la capacité du **nom** du produit
(taille + type) et l'écrit sur tous les produits vendables.

- Pour ajuster les règles : éditer la fonction `detect_capacity()` (les `return (capacité, raison)`).
- Lancer : `python -m scripts.odoo.step02_init_carton_capacity`
- ⚠️ **Écrase les valeurs existantes** (y compris les exceptions saisies à la main). Le script
  écrit un journal `scripts/odoo/init_carton_capacity.csv` à relire avant de se fier au résultat.
- Bon réflexe : faire les exceptions une à une dans l'UI (Cas A) plutôt que de relancer le batch.

### Cas C — changer la capacité d'une famille entière

La capacité sert de **clé de famille** ET de **libellé** (table `FAMILY_LABELS`). Si on change la
valeur d'une famille (ex. 500 ml passe de `23` à `20`/carton), il faut :

1. Éditer `scripts/odoo/server_action_code.py` → table `FAMILY_LABELS` (mettre la nouvelle clé).
2. Éditer `scripts/odoo/step02_init_carton_capacity.py` → `detect_capacity()` (nouvelle valeur).
3. Redéployer l'action : `python -m scripts.odoo.step03_create_server_action`.
4. Réinitialiser les produits : `python -m scripts.odoo.step02_init_carton_capacity`.

> Si une capacité n'a pas d'entrée dans `FAMILY_LABELS`, le carton est libellé `Carton <N>u`
> (générique) — fonctionnel mais moins propre. D'où la mise à jour de la table.

## 5. Pièges à retenir

- **Pas d'auto-recalcul** : changer la capacité ne re-répartit pas les BL déjà faits → recliquer
  « Répartir en cartons ».
- **Capacité au niveau template** : vaut pour toutes les variantes du produit.
- **`0` ≠ « 0 article »** : c'est « pas de carton dédié » → va dans « Divers », jamais scindé.
- **Idempotent** : recliquer le bouton ne casse rien (purge + reconsolidation avant de refaire).
- **Modif simple = aucun redéploiement** : pour le Cas A, changer juste le champ suffit ; pas
  besoin de relancer un script (l'action lit la valeur à chaque clic).
- **Les scripts sont idempotents** et tournent en XML-RPC via `.env.local` (`ODOO_*`).

## 6. Fichiers source (repo be-yours-mylab)

| Fichier | Rôle |
|---|---|
| `scripts/odoo/step01_create_carton_field.py` | Crée le champ `x_carton_capacity` |
| `scripts/odoo/step02_init_carton_capacity.py` | Initialise les capacités depuis les noms |
| `scripts/odoo/server_action_code.py` | Logique « Répartir en cartons » (familles + remplissage) |
| `scripts/odoo/step03_create_server_action.py` | Déploie l'action serveur |
| `scripts/odoo/templates/bl_deliveryslip.xml` | Template QWeb du BL PDF |
| `scripts/odoo/step04_create_bl_report.py` | Déploie le rapport PDF |
| `scripts/odoo/step05_add_picking_button.py` | Ajoute le bouton dans la vue picking |
| `scripts/odoo/README.md` | Ordre d'exécution du setup |

---

## Note pour Hermes — transformer ce document en skill

Si tu en fais un skill activable :

- **But du skill** : répondre aux questions sur les BL/cartons et **modifier la capacité carton
  d'un produit** sur demande (« mets la capacité carton du shampoing X à 36 »).
- **Lecture (read-only)** : `search_read('product.template', [...], ['name','default_code','x_carton_capacity'])`
  pour afficher la capacité actuelle.
- **Écriture** : `write('product.template', [id], {'x_carton_capacity': N})` →
  **garde-fou obligatoire en 2 temps** : d'abord montrer le produit + l'ancienne et la nouvelle
  valeur (aperçu), attendre « confirme », **puis** écrire. (Convention skills écriture Hermes.)
- **Rappeler après écriture** : « recliquer *Répartir en cartons* sur les BL existants pour appliquer ».
- **Creds** : lire `ODOO_*` depuis `os.environ` (le `.env` Hermes les a déjà), pas le `.env.local`.
