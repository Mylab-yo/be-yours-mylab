---
name: check-order
description: "Récap unifié d'UNE commande MyLab : croise Shopify (status, paiement, lignes, gateway, client) + Odoo (sale.order, facture liée, état paiement) + tracking expédition. Use when: check order, check commande, où en est la commande, status commande, info commande, récap commande, tracking commande, détails commande X."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [shopify, odoo, orders, b2b, mylab, support]
    related_skills: [check-customer]
---

# Check Order — Récap unifié d'une commande

## Runtime (Hermes)

Tu tournes dans l'agent Hermes (VPS, contexte Telegram). Les credentials sont
déjà dans l'environnement (`/opt/data/.env`, chargé dans `os.environ`) — **ne
jamais les hardcoder ni les afficher** :
`SHOPIFY_ADMIN_TOKEN`, `SHOPIFY_STORE`, `ODOO_URL`, `ODOO_DB`, `ODOO_UID`,
`ODOO_API_KEY`. `requests` et `xmlrpc.client` sont disponibles.

## Contexte

Une commande MyLab vit dans 3 systèmes :
- **Shopify** (`SHOPIFY_STORE`) — checkout, paiement, fulfillment
- **Odoo** (`ODOO_URL`) — sale.order + account.move (facture), pipeline via le workflow n8n `Xj8T5a7aO8drZk5v`
- **Transporteur** — DPD (FR) ou Mondial Relay (relais)

Le rapprochement Shopify↔Odoo se fait via :
- `sale.order.client_order_ref` = numéro Shopify (ex: `#11234`)
- OU `sale.order.origin` = contient la ref Shopify

## Procédure

### Étape 1 : Parser l'input

L'utilisateur passe soit :
- `11234` / `#11234` / `MYLAB11234` → numéro Shopify
- `S00567` → référence Odoo (sale.order.name)
- `email@client.com` → email client (prend la dernière commande)

Tester d'abord comme numéro de commande Shopify (cas le plus fréquent).

### Étape 2 : Fetch Shopify

```python
import os, requests
SHOP = os.environ.get('SHOPIFY_STORE', 'mylab-shop-3.myshopify.com')
TOKEN = os.environ['SHOPIFY_ADMIN_TOKEN']
headers = {'X-Shopify-Access-Token': TOKEN}

order_num = '11234'  # extrait de l'input, sans le #
url = f'https://{SHOP}/admin/api/2024-10/orders.json'
params = {'name': f'#{order_num}', 'status': 'any', 'limit': 5}
r = requests.get(url, params=params, headers=headers, timeout=15)
orders = r.json().get('orders', [])
```

Si 0 orders : retourner "commande introuvable sur Shopify".

Extraire : `id`, `name`, `created_at`, `customer.email`, `customer` (prénom+nom),
`total_price`, `financial_status`, `fulfillment_status`, `payment_gateway_names`,
`line_items[]` (title, quantity, price), `shipping_address.city/zip`,
`fulfillments[]` (tracking_number, tracking_url, tracking_company).

### Étape 3 : Fetch Odoo (sale.order + facture)

```python
import os, xmlrpc.client
ODOO = os.environ.get('ODOO_URL', 'https://odoo.startec-paris.com')
DB = os.environ.get('ODOO_DB', 'OdooYJ')
UID = int(os.environ.get('ODOO_UID', '8'))
KEY = os.environ['ODOO_API_KEY']
obj = xmlrpc.client.ServerProxy(f'{ODOO}/xmlrpc/2/object')

shopify_ref = f'#{order_num}'
domain = ['|', '|',
          ('client_order_ref', '=', shopify_ref),
          ('origin', 'ilike', shopify_ref),
          ('name', '=', shopify_ref)]
so_ids = obj.execute_kw(DB, UID, KEY, 'sale.order', 'search', [domain])
if so_ids:
    so = obj.execute_kw(DB, UID, KEY, 'sale.order', 'read', [so_ids[0]],
                        {'fields': ['name', 'state', 'amount_total', 'invoice_status',
                                    'invoice_ids', 'partner_id', 'date_order']})[0]
    if so['invoice_ids']:
        inv = obj.execute_kw(DB, UID, KEY, 'account.move', 'read', [so['invoice_ids']],
                             {'fields': ['name', 'state', 'payment_state',
                                         'amount_total', 'amount_residual', 'invoice_date']})
```

Note : pour les commandes **antérieures à 2026-05-12** (avant fix WP→Shopify) ou
`source_name=wc_migration`, le matching peut échouer (refs différentes). Le mentionner
si commande introuvable côté Odoo.

### Étape 4 : Tracking (si fulfillment existe)

Les fulfillments Shopify contiennent `tracking_number`, `tracking_url`,
`tracking_company` (DPD, Mondial Relay…). Pas besoin d'appeler les APIs
transporteur — afficher juste le `tracking_url`.

### Étape 5 : Synthétiser

```
📦 Commande #11234 — 10/06/2026

👤 Client
  Jean Dupont (jean@example.com)
  Lyon 69000, FR

💰 Shopify
  Status : paid, fulfilled
  Gateway : Stripe (shopify_payments)
  Total : 247,50 € TTC

📄 Odoo
  Devis : SO00342, état "done"
  Facture : INV/2026/00185, payée intégralement
  Total : 247,50 € TTC ✅ cohérent Shopify

📋 Lignes
  • Shampoing nourrissant 200ml × 5 — 35,00 €
  • ... (3 autres)

📮 Expédition
  Transporteur : DPD
  Tracking : 250012345678901 → https://www.dpd.fr/...

⚠️ Anomalies détectées : aucune
```

Si **incohérence** (montants Shopify ≠ Odoo, pas de facture sur commande payée,
TVA suspecte) : la flagger en gras avec recommandation d'action.

## Règles

1. **Read-only strict** : aucune modification Shopify ni Odoo.
2. **Mention vivante** : commande >6 mois → préciser qu'elle est ancienne (matching potentiellement incomplet).
3. **Privacy** : ne jamais afficher numéro CB, hash mot de passe, adresse postale complète (juste ville/cp) sauf demande explicite.
4. **Source de vérité** : Shopify pour paiement encaissé/fulfillment, Odoo pour la facture finale.

## Gotchas connus

- **Double TVA héritage WP** : commandes `source_name=wc_migration` ont parfois `total_tax=0` dans Shopify mais TTC dans Odoo. Écart de 20% → probablement ça.
- **Discount codes non propagés** : remise Shopify mais pas Odoo = fix node n8n récent. Flagger.
- **Bug Aruba** : ancien client Odoo en Aruba (héritage import) → TVA était 0%. Devrait être fixé, mais checker.
- **Workflow n8n** : Odoo n'a pas la commande mais Shopify oui → vérifier le workflow `Xj8T5a7aO8drZk5v` (utiliser le connecteur MCP n8n : `recent_failures` / `get_execution`).
