# Rupture de stock — affichage + backorder + capture « prévenez-moi » (SP1)

**Date :** 2026-06-11
**Statut :** design validé (Yoann, « go »)
**Périmètre :** SP1 uniquement. SP2 (workflow n8n notif email au retour de stock) = spec séparée ultérieure.

## Objectif

Mieux informer les clients sur les produits en rupture, et leur offrir **deux actions** :
1. **Commander et recevoir dès retour en stock** (backorder) — pour les produits backorderables.
2. **Être prévenu du retour** par email — capture de la demande (l'email automatique au retour = SP2).

Surfaces : **fiche produit**, **boutique pro** (collection filtrable), **commande express**.

## Décisions verrouillées

| Sujet | Décision |
|---|---|
| Modèle rupture | Les **deux** : backorder + bouton « prévenez-moi » |
| Portée backorder | **Tous** les produits par défaut (`inventory_policy=continue`), sauf tag `no-backorder` |
| Suivi stock | Fiable dans Shopify → détection par `inventory_quantity` |
| Stockage demandes prévenez-moi | **Airtable** (table `back-in-stock`) |
| Notif email au retour | Custom n8n + Gmail — **SP2**, hors de ce spec |
| Label bouton backorder | **« Commander et recevoir dès retour en stock »** |

## Architecture

`inventory_policy = continue` rend `product.available = true` même à 0 stock (nécessaire pour que `/cart/add` accepte un backorder). La rupture se détecte donc par **`inventory_quantity <= 0`** (et `inventory_management == 'shopify'`), pas par `available`.

**Source de détection — côté serveur (Liquid)** :
- **Fiche produit** : `product.variants.first.inventory_quantity` lu directement.
- **Boutique pro & commande express** : un map rendu en Liquid `window.MlOos = { "<handle>": true, … }` couvrant les **73 produits** de `boutique-adherents` (toutes contenances confirmées présentes). Nécessaire car `products.json` / `/products/{h}.js` **n'exposent pas** `inventory_quantity` — donc le JS (contenances liées) lit `MlOos`.
- **Backorderable ?** : `product.tags` ne contient pas `no-backorder`. Rendu aussi dans un map `window.MlNoBackorder = { "<handle>": true }` (uniquement les exclus) pour les surfaces JS.

## Config Shopify (prérequis)

Script bulk (Admin API, token `write_products` = `shpat_5768…`, cf. [[feedback_shopify_token_customer_scope]]) :
- Pour chaque variante de produit de `boutique-adherents` **sans** tag `no-backorder` : `inventory_policy = "continue"`.
- Pour les produits tagués `no-backorder` : `inventory_policy = "deny"`.
- Idempotent (n'écrit que si différent). Script `scripts/shopify/set_backorder_policy.py`.

## Comportement par surface

### Fiche produit (`main-product.liquid` + `mylab-product.js`)
État rupture (`inventory_quantity <= 0`) :
- **Backorderable** : carte prix + paliers normaux ; CTA principal **« Commander et recevoir dès retour en stock »** (ajout panier fonctionne car `continue`) ; bandeau *« En rupture — expédié dès réapprovisionnement »* ; lien secondaire **« Ou être prévenu du retour »** → modale.
- **No-backorder** : pas d'ajout (CTA masqué/désactivé) ; bouton **« Prévenez-moi du retour »** → modale.
En stock : comportement actuel inchangé.

### Boutique pro (`ml-collection-filterable.liquid`)
Badge overlay calculé en Liquid par produit :
- Backorderable + rupture → badge **« Sur commande »**.
- No-backorder + rupture → badge **« Rupture »**.
La carte reste cliquable ; les actions (backorder / prévenez-moi) se font sur la fiche.

### Commande express (`ml-quick-order.liquid` + `ml-qo-row.liquid`)
Remplace la logique OOS actuelle (basée sur `available`) par une logique basée sur `MlOos` :
- Backorderable + rupture → ligne **commandable** (sélecteur de palier actif) + tag *« sur commande »* sous le nom.
- No-backorder + rupture → ligne **grisée** (traitement actuel `applyOosTreatment`) + lien **« Prévenez-moi → »** vers la fiche.

## Capture « prévenez-moi » (moitié capture incluse dans SP1)

- Snippet `ml-notify-modal.liquid` (modale unique, rendue globalement ou dans `main-product`) + JS léger.
- Champs : email (requis), handle + variant_id (pré-remplis), titre produit affiché.
- Submit → `POST` JSON vers un **webhook n8n** dont l'URL est un **réglage de section/thème** (`notify_webhook_url`).
- Workflow n8n minimal (SP1) : webhook → upsert Airtable table `back-in-stock` `{ email, handle, variant_id, product_title, created_at, status: "pending" }` (dédup email+variant). Réponse 200 → message succès dans la modale.
- L'email automatique au retour = **SP2**.

## Erreurs / dégradation
- `MlOos` absent ou JS désactivé → fallback sur `available` (correct pour les no-backorder/deny ; les backorderables apparaîtront simplement « disponibles »).
- `notify_webhook_url` vide → bouton « prévenez-moi » masqué (pas de bouton mort).
- POST capture en échec → message « réessayez » dans la modale ; jamais bloquant pour la navigation ni l'ajout panier.
- Délai de réappro : message générique, **aucune date promise** (pas de metafield date — YAGNI).

## Fichiers

| Fichier | Action |
|---|---|
| `scripts/shopify/set_backorder_policy.py` | Create — config `inventory_policy` bulk |
| `sections/main-product.liquid` | Modify — bandeau + CTA backorder/prévenez-moi (rupture) |
| `assets/mylab-product.js` | Modify — détecter rupture, basculer CTA, ouvrir modale |
| `assets/mylab-product.css` | Modify — styles bandeau rupture + états CTA |
| `sections/ml-collection-filterable.liquid` | Modify — badges « Sur commande » / « Rupture » |
| `sections/ml-quick-order.liquid` | Modify — `MlOos`/`MlNoBackorder` map + logique backorder |
| `snippets/ml-qo-row.liquid` | Modify — tag « sur commande » / lien prévenez-moi |
| `snippets/ml-notify-modal.liquid` | Create — modale capture email |
| `assets/ml-notify.js` | Create — ouverture modale + POST webhook |
| n8n workflow `back-in-stock-capture` | Create — webhook → Airtable upsert |

## Tests / vérification (pas de test runner — QA navigateur sur dev)
1. Produit en rupture backorderable : fiche → CTA « Commander et recevoir dès retour en stock », ajout panier OK ; bandeau visible ; lien prévenez-moi → modale.
2. Produit `no-backorder` en rupture : fiche → pas d'ajout, bouton « Prévenez-moi » seul.
3. Boutique pro : badges « Sur commande » vs « Rupture » selon le tag.
4. Commande express : ligne backorderable commandable + tag « sur commande » ; ligne no-backorder grisée + lien.
5. Modale : email → POST → ligne créée dans Airtable `back-in-stock`.
6. Webhook vide → bouton prévenez-moi absent (pas de bouton mort).
7. Produit en stock : aucun changement de comportement.

## Hors scope (YAGNI / SP2)
- Email automatique au retour de stock (SP2).
- Date de réappro estimée.
- Notify-me inline dans le tableau commande express (lien vers la fiche à la place).
