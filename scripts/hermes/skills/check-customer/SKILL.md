---
name: check-customer
description: "Vue 360° d'un client MyLab : commandes Shopify, devis/factures Odoo, impayés en cours, CA total, ancienneté, dernier contact. Use when: check customer, check client, vue client, récap client, qui est ce client, infos client, historique client, fiche client."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [shopify, odoo, crm, b2b, mylab, support]
    related_skills: [check-order, relance-impayes]
---

# Check Customer — Vue 360° d'un client

## Runtime (Hermes)

Tu tournes dans l'agent Hermes (VPS, contexte Telegram). Credentials déjà dans
`os.environ` (via `/opt/data/.env`) — **ne jamais les hardcoder ni les afficher** :
`SHOPIFY_ADMIN_TOKEN`, `SHOPIFY_STORE`, `ODOO_URL`, `ODOO_DB`, `ODOO_UID`,
`ODOO_API_KEY`. `requests` + `xmlrpc.client` disponibles.

## Contexte

Un client est dédoublé entre **Shopify** (`customer`, lié par email) et **Odoo**
(`res.partner`, créé manuellement ou via le workflow n8n Shopify→Odoo). Le
matching se fait par **email principal** ; un client peut avoir plusieurs adresses
(perso vs pro), le mapping n'est pas toujours parfait.

## Procédure

### Étape 1 : Parser l'input

- `jean@example.com` → email exact (cas le plus fiable)
- `"Jean Dupont"` → nom (potentiellement plusieurs matches)
- `"LA TRESSE PARISIENNE"` → nom société (B2B fréquent)
- `0612345678` → téléphone

### Étape 2 : Fetch Shopify

```python
import os, requests
SHOP = os.environ.get('SHOPIFY_STORE', 'mylab-shop-3.myshopify.com')
TOKEN = os.environ['SHOPIFY_ADMIN_TOKEN']
headers = {'X-Shopify-Access-Token': TOKEN}

q = 'email:jean@example.com'  # ou name:"Jean Dupont" ou phone:0612345678
r = requests.get(f'https://{SHOP}/admin/api/2024-10/customers/search.json',
                 params={'query': q, 'limit': 10}, headers=headers, timeout=15)
customers = r.json().get('customers', [])

if not customers:
    print("⚠️ Aucun customer Shopify pour cette recherche")
else:
    cust = customers[0]  # si plusieurs matches : lister + demander de préciser
    cust_id = cust['id']
    r2 = requests.get(f'https://{SHOP}/admin/api/2024-10/customers/{cust_id}/orders.json',
                      params={'status': 'any', 'limit': 250}, headers=headers, timeout=20)
    orders = r2.json().get('orders', [])
```

Si plusieurs matches Shopify : afficher la liste (nom, email, last_order_at,
total_spent) et demander de préciser.

### Étape 3 : Fetch Odoo

```python
import os, xmlrpc.client
ODOO = os.environ.get('ODOO_URL', 'https://odoo.startec-paris.com')
DB = os.environ.get('ODOO_DB', 'OdooYJ')
UID = int(os.environ.get('ODOO_UID', '8'))
KEY = os.environ['ODOO_API_KEY']
obj = xmlrpc.client.ServerProxy(f'{ODOO}/xmlrpc/2/object')

email = cust['email']
partner_ids = obj.execute_kw(DB, UID, KEY, 'res.partner', 'search',
    [[('email', '=ilike', email), ('company_id', 'in', [3, False])]])
if not partner_ids:
    name = (cust.get('first_name', '') + ' ' + cust.get('last_name', '')).strip()
    partner_ids = obj.execute_kw(DB, UID, KEY, 'res.partner', 'search',
        [[('name', 'ilike', name), ('company_id', 'in', [3, False])]])

if partner_ids:
    partner = obj.execute_kw(DB, UID, KEY, 'res.partner', 'read', [partner_ids[0]],
        {'fields': ['name', 'email', 'phone', 'mobile', 'country_id', 'city', 'zip',
                    'vat', 'is_company', 'parent_id', 'create_date', 'category_id',
                    'property_payment_term_id', 'property_account_position_id']})[0]
    so_ids = obj.execute_kw(DB, UID, KEY, 'sale.order', 'search',
        [[('partner_id', '=', partner_ids[0])]], {'limit': 50, 'order': 'date_order desc'})
    sales = obj.execute_kw(DB, UID, KEY, 'sale.order', 'read', [so_ids],
        {'fields': ['name', 'date_order', 'state', 'amount_total', 'invoice_status']})
    inv_ids = obj.execute_kw(DB, UID, KEY, 'account.move', 'search',
        [[('partner_id', '=', partner_ids[0]),
          ('move_type', 'in', ['out_invoice', 'out_refund']),
          ('state', '!=', 'cancel')]], {'limit': 50, 'order': 'invoice_date desc'})
    invoices = obj.execute_kw(DB, UID, KEY, 'account.move', 'read', [inv_ids],
        {'fields': ['name', 'invoice_date', 'state', 'payment_state',
                    'amount_total', 'amount_residual', 'invoice_date_due']})
    msg_ids = obj.execute_kw(DB, UID, KEY, 'mail.message', 'search',
        [[('model', '=', 'res.partner'), ('res_id', '=', partner_ids[0]),
          ('message_type', 'in', ['comment', 'email'])]],
        {'limit': 5, 'order': 'date desc'})
```

### Étape 4 : Calculer les stats

```python
from datetime import datetime, timezone
total_ca = sum(float(o['total_price']) for o in orders if o.get('financial_status') == 'paid')
n = len(orders)
avg = total_ca / n if n else 0
first = min((o['created_at'] for o in orders), default=None)
last = max((o['created_at'] for o in orders), default=None)
unpaid = [i for i in invoices if i['payment_state'] in ('not_paid', 'partial')]
unpaid_total = sum(i['amount_residual'] for i in unpaid)
```

### Étape 5 : Synthétiser

```
👤 LA TRESSE PARISIENNE — fiche au JJ/MM/AAAA

📇 Identité
  Société : LA TRESSE PARISIENNE (B2B)
  Contact : Jean Dupont — jean@latresse.fr — 06 12 34 56 78
  Adresse : Paris 75003, FR · TVA FR12345678901
  Client depuis : 14/01/2025 (≈ 17 mois)

📊 Activité
  • CA total payé : 8 247 € sur 12 commandes · panier moyen 687 €
  • Dernière commande : 28/05/2026 (il y a 13 j)

📦 Commandes Shopify (12) — récentes
  • #11234 — 28/05/2026 — 847 € — paid, fulfilled
  • ... (demander la liste complète si besoin)

📄 Factures Odoo (10)
  • FAC/2026/00185 — 28/05/2026 — 847 € — payée ✅

💸 Impayés en cours
  ⚠️ 2 factures, 1 459 € à recouvrer :
  • FAC/2026/00102 — 759 € (j+90, ÉCHU)

💬 Derniers échanges
  • 02/06 : relance n°2 envoyée

⚠️ Signaux : 2 factures impayées >90j → escalation envisageable
```

## Règles

1. **Read-only strict** : aucune modification.
2. **Privacy** : jamais de numéro CB, IBAN client, adresse complète (juste ville/zip).
3. **Multi-matches** : plusieurs partners possibles → lister tous + demander lequel.
4. **Pas de spam** : 50+ commandes → 10 dernières + total agrégé.
5. **Flag actionable** : impayés, échéance proche (15j), dormant (>12 mois sans commande), CA en chute (-50% YoY).

## Gotchas

- Email peut différer Shopify ↔ Odoo (perso vs pro, typo héritée). Pas de match email → retomber sur le nom.
- B2B vs particulier : Odoo `is_company=True`. Si le partner a un `parent_id`, remonter au parent pour les vraies factures.
- Pricelist B2B : `property_product_pricelist` = `TARIFS DÉGRESSIFS MYLAB` (id=3). Le mentionner si applicable.
- Impayés / relance : enchaîner sur le skill `relance-impayes` si pertinent.
