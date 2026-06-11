---
name: relance-impayes
description: "Triage des factures Odoo impayées (>N jours, défaut 7) : groupe par client, catégorise par ancienneté (courtois / ferme / mise en demeure / contentieux), montre le dernier contact. LECTURE SEULE — n'envoie jamais d'email. Use when: relance impayés, impayés, factures impayées, recouvrement, qui me doit de l'argent, facture en retard, outstanding invoices."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [odoo, recouvrement, comptabilite, b2b, mylab, finance]
    related_skills: [check-customer]
---

# Relance Impayés — Triage recouvrement (LECTURE SEULE dans Hermes)

## ⚠️ Règle dure Hermes

Cette version (agent Telegram) est **strictement read-only**. Tu **n'envoies
JAMAIS** d'email, tu ne crées **JAMAIS** de `mail.mail`, tu ne modifies **rien**
dans Odoo. Tu produis un tableau de triage + tu peux *rédiger le texte* d'une
relance si on te le demande, mais l'envoi se fait sur le poste de Yoann / dans
Odoo, pas ici. (Cf. l'incident « email à 200k clients » — un bot ne déclenche
pas d'envoi client.)

## Runtime

Creds déjà dans `os.environ` (via `/opt/data/.env`) — ne pas hardcoder/afficher :
`ODOO_URL`, `ODOO_DB`, `ODOO_UID`, `ODOO_API_KEY`. `xmlrpc.client` dispo.
Company SARL STARTEC = `company_id=3`.

## Procédure

### Étape 1 : Parser l'input

- `impayés` → seuil par défaut 7 jours, tous tiers
- `impayés 14` → seuil 14 jours
- `impayés <client>` → focus 1 client

### Étape 2 : Fetch les impayés Odoo

```python
import os, xmlrpc.client
from datetime import datetime, timedelta
ODOO = os.environ.get('ODOO_URL', 'https://odoo.startec-paris.com')
DB = os.environ.get('ODOO_DB', 'OdooYJ')
UID = int(os.environ.get('ODOO_UID', '8'))
KEY = os.environ['ODOO_API_KEY']
obj = xmlrpc.client.ServerProxy(f'{ODOO}/xmlrpc/2/object')

days_threshold = 7
threshold_date = (datetime.now() - timedelta(days=days_threshold)).strftime('%Y-%m-%d')
domain = [
    ('move_type', '=', 'out_invoice'),
    ('state', '=', 'posted'),
    ('payment_state', 'in', ['not_paid', 'partial']),
    ('invoice_date', '<=', threshold_date),
    ('company_id', '=', 3),
]
inv_ids = obj.execute_kw(DB, UID, KEY, 'account.move', 'search', [domain],
                         {'order': 'invoice_date asc'})
invoices = obj.execute_kw(DB, UID, KEY, 'account.move', 'read', [inv_ids],
    {'fields': ['name', 'invoice_date', 'invoice_date_due', 'amount_total',
                'amount_residual', 'partner_id', 'payment_state']})
```

### Étape 3 : Grouper par client + catégoriser par tier

```python
from collections import defaultdict
now = datetime.now().date()
by_partner = defaultdict(lambda: {'invoices': [], 'total_residual': 0, 'max_days': 0})
for inv in invoices:
    pid = inv['partner_id'][0]
    d = (now - datetime.strptime(inv['invoice_date'], '%Y-%m-%d').date()).days
    by_partner[pid]['invoices'].append({**inv, 'days': d})
    by_partner[pid]['total_residual'] += inv['amount_residual']
    by_partner[pid]['max_days'] = max(by_partner[pid]['max_days'], d)

def tier(days):
    if days <= 14: return 1   # courtois
    if days <= 30: return 2   # ferme
    if days <= 60: return 3   # pré-contentieux
    return 4                  # contentieux
for pid, data in by_partner.items():
    data['tier'] = tier(data['max_days'])
```

### Étape 4 : Dernier contact (anti-spam, info seulement)

```python
for pid in by_partner:
    msg_ids = obj.execute_kw(DB, UID, KEY, 'mail.message', 'search',
        [[('model', '=', 'res.partner'), ('res_id', '=', pid),
          ('message_type', '=', 'email'), ('subject', 'ilike', 'relance')]],
        {'limit': 1, 'order': 'date desc'})
    if msg_ids:
        m = obj.execute_kw(DB, UID, KEY, 'mail.message', 'read', [msg_ids[0]], {'fields': ['date']})[0]
        by_partner[pid]['last_relance_days'] = (now - datetime.strptime(m['date'][:10], '%Y-%m-%d').date()).days
```

### Étape 5 : Rapport de triage

```
💸 Impayés — JJ/MM/AAAA (seuil 7j) — LECTURE SEULE

Total : 12 clients, 18 factures, 24 750 € à recouvrer

🟡 TIER 1 — courtois (7-14j) — 4 clients, 3 200 €
  • Studio Coiffure — 850 € (j+11) — jamais relancé
🟠 TIER 2 — ferme (15-30j) — 5 clients, 8 950 €
  • XY Coiffure — 1 460 € (2 fact., j+25) — jamais relancé
🔴 TIER 3 — pré-contentieux (31-60j) — 2 clients, 4 600 €
  ⚠️ HOLICARE — 756 € (j+55) — relancé il y a 3j
🚨 TIER 4 — contentieux (>60j) — 1 client, 7 000 €
  ⚠️ CENDREE — 5 920 € (j+90) — relancé il y a 12j

→ Pour envoyer les relances : sur le poste (skill desktop relance-impayes) ou dans Odoo.
   Je peux te rédiger le texte d'une relance ici si tu veux (sans l'envoyer).
```

Tiers : 1 courtois (7-14j) · 2 ferme (15-30j) · 3 mise en demeure (31-60j) · 4 contentieux (>60j).

## Règles

1. **Read-only absolu** : aucun envoi, aucune écriture Odoo. Si on te demande d'envoyer, refuse et renvoie vers le poste/Odoo.
2. **Anti-spam (info)** : signaler les clients relancés < 7j, ne pas recommander de re-relance.
3. **Privacy** : jamais le montant total dans un objet d'email ; pas d'IBAN client.
4. **dossier-valide** : clients tagués `dossier-valide` (BSS B2B) ont des termes négociés → flagger, ne pas pousser à relancer sans vérif.
5. **Tier 4** : signaler mais ne rien suggérer d'automatique (peut être déjà en contentieux).

## Rédaction de texte (si demandé, sans envoi)

Tonalité par tier — rappel courtois / relance ferme / mise en demeure sous 8 jours.
RIB : IBAN `FR58 3000 2028 8000 0007 1073 R40`, BIC `CRLYFRPP`. Signature « Service Comptabilité — MY.LAB ».
