# Shopify Order → Odoo Sale Order (workflow n8n) — Design

**Date :** 2026-04-17
**Projet :** MyLab Shop (SARL STARTEC) — n8n + Odoo 18 + Shopify
**Auteur :** Yoann Durand + Claude

## Problème

Aujourd'hui, les commandes payées sur Shopify (mylab-shop-3.myshopify.com) ne remontent pas dans Odoo. Pour les expédier avec le bon de livraison MyLab (le BL cartons custom qu'on vient de mettre en place), Yoann doit actuellement recréer manuellement chaque commande dans Odoo : saisie du client, des produits, des quantités, des prix. C'est fastidieux et source d'erreurs.

## Objectif

Créer un workflow n8n qui, à chaque commande Shopify payée, crée automatiquement un `sale.order` Odoo **confirmé** (ce qui génère nativement le `stock.picking`), pour que Yoann puisse immédiatement cliquer "Répartir en cartons" et imprimer le BL. Zéro saisie manuelle dans le cas nominal.

## Hors scope

- **Création de facture Odoo** : le workflow ne génère qu'un sale.order + picking. La facture (Odoo `account.move`) reste manuelle ou fera l'objet d'un workflow séparé plus tard.
- **Annulations / remboursements Shopify** : pas de traitement du webhook `orders/cancelled` ou `refunds/create` en v1. Si une commande est annulée sur Shopify, Yoann annule manuellement le sale.order et le picking dans Odoo.
- **Child partners delivery/invoice** : un seul `res.partner` par client (adresse de livraison utilisée). Pas de séparation billing/shipping dans Odoo.
- **Réconciliation nocturne** (filet de sécurité job) : pas en v1. L'idempotence + les retries automatiques Shopify (48h) couvrent les cas de panne n8n.

## Architecture globale

Un **nouveau workflow n8n** autonome : `MY.LAB - Shopify → Commande Odoo`. Déclenché par un **webhook Shopify `orders/paid`** (temps réel), avec vérification HMAC SHA256 pour la sécurité. Crée le partenaire (ou le matche), les lignes de commande (produits matchés + frais livraison + notes pour non-matchés), puis confirme automatiquement si tout est propre.

**Flux :**

```
[Shopify customer paid]
  → POST /webhook/mylab-shopify-order
  → n8n: verify HMAC → parse payload → check idempotence (Odoo)
  → find/create res.partner (fiscal position auto)
  → match products + build order lines
  → create sale.order (Odoo)
  → if all matched: action_confirm → picking created
    else: leave draft + mail.activity "Corriger produits"
  → mail.activity on picking "Répartir en cartons et imprimer BL"
  → log row in Google Sheet
```

**Patterns réutilisés** depuis les workflows n8n existants (devis manuel, devis email) :
- Matching client par email normalisé
- `PRODUCT_ALIASES` pour noms commerciaux → noms Odoo
- Fiscal position auto-détection (FR / UE VAT / Export)
- `this.helpers.httpRequest()` (pas `fetch()`) dans les Code nodes

## Configuration Shopify webhook

Dans Shopify admin :
- **Event** : `Order payment` (= commande payée)
- **Format** : JSON
- **URL** : `https://n8n.startec-paris.com/webhook/mylab-shopify-order`
- **API version** : dernière stable
- **Secret HMAC** : copié dans les credentials n8n comme `Shopify Webhook HMAC Secret`

Shopify retry automatiquement les webhooks en échec pendant 48h → panne n8n de courte durée tolérée sans perte de commande.

## Mapping des champs

### Commande Shopify → `sale.order` Odoo

| Champ Shopify | Champ Odoo | Remarque |
|---|---|---|
| `id` | `client_order_ref` | Clé d'idempotence (string) |
| `order_number` | `origin` | Format `"Shopify #1234"` |
| `created_at` | `date_order` | |
| `customer.email` (lowercased) | → via `partner_id` | Clé de matching |
| `note` / `note_attributes` | `note` | Commentaires client |
| (constant) | `company_id` = 3 | SARL STARTEC |
| (constant) | `pricelist_id` = 3 | TARIFS DEGRESSIFS MYLAB (pour affichage, prix forcés ligne par ligne) |
| (auto-détecté) | `fiscal_position_id` | FR/UE/Export |

### Line item Shopify → `sale.order.line`

| Champ Shopify | Champ Odoo | Remarque |
|---|---|---|
| `sku` | match `product.product.default_code` | exact match d'abord |
| `variant_title` / `title` | fallback matching via alias (ilike) | via `PRODUCT_ALIASES` |
| `quantity` | `product_uom_qty` | |
| `price` | `price_unit` | **Source de vérité — on force depuis Shopify** |

**Frais de livraison** : `shipping_lines[0].price` → ligne avec `product_id = 2413` (Frais de livraison DPD existant), `qty = 1`.

**Produit non matché** : ligne avec `display_type = 'line_note'`, `name = '⚠ NON MATCHÉ — SKU: {sku} — {title} × {qty} @ {price} €'`. Aucun impact sur le total. Affichage distinctif dans l'UI Odoo (italique + emoji).

### Client Shopify → `res.partner`

Matching par **email normalisé (lowercase)**. Si trouvé → utilisé tel quel (aucune mise à jour des champs existants). Si adresse Shopify diffère de l'Odoo existant → commentaire info dans le chatter Odoo `ℹ Adresse de livraison Shopify diffère — vérifier avant expédition`.

Si absent → création avec :
- `name` : `shipping_address.company` si présent (B2B), sinon `first_name last_name` (B2C)
- `is_company = True` si company renseigné
- `email`, `phone`
- Adresse : `shipping_address` (`address1` → `street`, `address2` → `street2`, `zip`, `city`)
- `country_id` : depuis `country_code`
- `state_id` : depuis `province_code` (si Odoo a l'état)
- `vat` : depuis `customer.tax_exempt` ou champ VAT personnalisé Shopify

### Fiscal position (auto-détection)

Même logique que workflow devis manuel :
- `country_id` = France → pas de fiscal position (TVA 20% normale)
- `country_id` UE + `vat` renseigné valide → `Intracommunautaire` (0%)
- `country_id` hors UE → `Export` (0%)

Les fiscal positions "Intracommunautaire" et "Export" doivent exister dans Odoo (à vérifier avant le déploiement, à créer sinon).

## Cas limites

### Idempotence

Avant toute création, rechercher un `sale.order` avec `client_order_ref = shopify_order_id` + `company_id = 3`. Si trouvé → log `"Commande X déjà traitée (sale.order id=Y) — skip"` et retour 200 OK.

### Email client manquant

Cascade de fallback : `customer.email` → `billing_address.email` → `shipping_address.email` → `shopify-order-{order_id}@placeholder.mylab-shop.com`. Si placeholder → activité rouge "Corriger email client" + sale.order en brouillon.

### Confirmation conditionnelle

- **Tous produits matchés (pas de `display_type=line_note` dans les lignes)** → `action_confirm` → picking auto-créé par Odoo.
- **Au moins un produit non matché** → sale.order reste en brouillon. Activité "Corriger produits non matchés" assignée à UID 8 (Yoann). Yoann corrige → confirme lui-même → picking.

### mail.activity sur le picking

Quand un picking est créé (confirmation auto réussie), le workflow recherche ce picking (`origin = "Shopify #X"` ou via `sale.order_ids` → `picking_ids`) et crée une `mail.activity` :
- `activity_type_id` : "Todo" (id natif)
- `summary` : "Répartir en cartons et imprimer BL"
- `note` : "Commande Shopify #X — client <name> — <nb_items> articles"
- `user_id` : UID 8

Ça remonte dans le bandeau Activities de Yoann en haut à droite d'Odoo.

### Sécurité

HMAC SHA256 vérifié sur chaque webhook via le header `X-Shopify-Hmac-Sha256`. Secret stocké dans les credentials n8n. Signature invalide → réponse 401 + log alerte.

### Traçabilité

Chaque passage du workflow log une ligne dans un Google Sheet dédié (ou table n8n statique si préférée) :
- `timestamp`, `order_number`, `email`, `sale_order_id`, `status` (`confirmed` / `draft` / `error`), `unmatched_count`, `error_message`

Permet de consulter l'historique et diagnostiquer les incidents.

## Risques et points d'attention

- **Écarts de prix Shopify ↔ pricelist Odoo** : les prix du sale.order sont forcés depuis Shopify, donc cohérents avec ce que le client a payé. Si la pricelist Odoo est désynchronisée, c'est un autre problème (hors scope).
- **Écarts de TVA (arrondis)** : Odoo recalcule la TVA selon la fiscal position. Différence centime possible vs Shopify. Acceptable.
- **Adresse obsolète sur partenaire existant** : si un client a changé d'adresse côté Shopify, Odoo garde l'ancienne (pas de mise à jour auto). Le chatter flag la différence pour review manuelle.
- **Fiscal position Odoo manquante** : si les fiscal positions "Intracommunautaire" ou "Export" n'existent pas dans Odoo, la création plantera pour les clients UE/export. À vérifier en pré-déploiement.
- **Produit Shopify sans SKU** : un produit Shopify mal configuré (SKU vide) finira toujours en "non matché" → devis brouillon. Pas un bug, mais il faut que le catalogue Shopify soit propre.
- **Volume** : le workflow doit supporter des pics (ex. 20 commandes en 10 minutes le lundi matin). Chaque commande = 1 webhook = 1 exécution n8n indépendante. Pas de blocage prévu, mais monitoring à prévoir si ça sature.
- **Dépendance au n8n** : si n8n est down, Shopify retry 48h (pas de perte). Au-delà, possible perte si pas de réconciliation nocturne (hors scope v1).
