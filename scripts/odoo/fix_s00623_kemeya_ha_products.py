# -*- coding: utf-8 -*-
"""Fix 1+2 : créer les fiches produit HA manquantes et repointer les lignes de S00623."""
import os, sys, xmlrpc.client
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('d:/Configurateur Designs MyLab/mylab-configurateur/.env.local')

ODOO = 'https://odoo.startec-paris.com'
DB, UID = 'OdooYJ', 8
KEY = os.environ.get('ODOO_API_KEY') or os.environ.get('ODOO_PASSWORD')
obj = xmlrpc.client.ServerProxy(f'{ODOO}/xmlrpc/2/object')

FIELDS = ['name', 'type', 'categ_id', 'uom_id', 'uom_po_id', 'list_price',
          'taxes_id', 'supplier_taxes_id', 'sale_ok', 'purchase_ok', 'company_id',
          'invoice_policy', 'is_storable']

# Modèles : 2613 (crème nourrissante créée ce matin par Yoann) et 2606 (masque nourrissant créé avec le devis)
models = {p['id']: p for p in obj.execute_kw(DB, UID, KEY, 'product.product', 'read',
    [[2613, 2606]], {'fields': FIELDS})}
print('Produits modèles :')
for pid, p in models.items():
    print(f"  [{pid}] {p['name']} type={p['type']} storable={p.get('is_storable')} categ={p['categ_id']} "
          f"uom={p['uom_id']} taxes={p['taxes_id']} company={p['company_id']} list_price={p['list_price']}")

def make_vals(model, name, list_price):
    return {
        'name': name,
        'type': model['type'],
        'is_storable': model.get('is_storable', False),
        'categ_id': model['categ_id'][0],
        'uom_id': model['uom_id'][0],
        'uom_po_id': model['uom_po_id'][0],
        'list_price': list_price,
        'taxes_id': [(6, 0, model['taxes_id'])],
        'supplier_taxes_id': [(6, 0, model['supplier_taxes_id'])],
        'sale_ok': model['sale_ok'],
        'purchase_ok': model['purchase_ok'],
        'company_id': model['company_id'][0] if model['company_id'] else False,
        'invoice_policy': model.get('invoice_policy') or 'order',
    }

# Garde-fou : ne pas recréer si déjà existants
existing = obj.execute_kw(DB, UID, KEY, 'product.product', 'search_read',
    [[('name', 'in', ['Formule Crème de Coiffage HA Repulpe 200ml', 'Formule Masque HA Repulpe 300ml'])]],
    {'fields': ['name']})
existing_names = {e['name']: e['id'] for e in existing}

if 'Formule Crème de Coiffage HA Repulpe 200ml' in existing_names:
    creme_id = existing_names['Formule Crème de Coiffage HA Repulpe 200ml']
    print(f'Crème HA déjà existante: {creme_id}')
else:
    creme_id = obj.execute_kw(DB, UID, KEY, 'product.product', 'create',
        [make_vals(models[2613], 'Formule Crème de Coiffage HA Repulpe 200ml', 3.6)])
    print(f'✓ Créé produit crème HA: [{creme_id}] Formule Crème de Coiffage HA Repulpe 200ml (3.60 €)')

if 'Formule Masque HA Repulpe 300ml' in existing_names:
    masque_id = existing_names['Formule Masque HA Repulpe 300ml']
    print(f'Masque HA déjà existant: {masque_id}')
else:
    masque_id = obj.execute_kw(DB, UID, KEY, 'product.product', 'create',
        [make_vals(models[2606], 'Formule Masque HA Repulpe 300ml', 6.3)])
    print(f'✓ Créé produit masque HA: [{masque_id}] Formule Masque HA Repulpe 300ml (6.30 €)')

# Repointer les lignes de S00623 (order_id=590) — vérif desc avant écriture
lines = obj.execute_kw(DB, UID, KEY, 'sale.order.line', 'search_read',
    [[('order_id', '=', 590), ('product_id', 'in', [2484, 2573])]],
    {'fields': ['name', 'product_id', 'product_uom_qty', 'price_unit']})
for l in lines:
    desc = (l['name'] or '')
    if l['product_id'][0] == 2484 and 'HA Repulpe' in desc:
        obj.execute_kw(DB, UID, KEY, 'sale.order.line', 'write', [[l['id']], {'product_id': creme_id}])
        print(f"✓ Ligne {l['id']} (crème HA, qty={l['product_uom_qty']}, {l['price_unit']} €) : 2484 → {creme_id}")
    elif l['product_id'][0] == 2573 and 'Masque HA Repulpe' in desc:
        obj.execute_kw(DB, UID, KEY, 'sale.order.line', 'write', [[l['id']], {'product_id': masque_id}])
        print(f"✓ Ligne {l['id']} (masque HA, qty={l['product_uom_qty']}, {l['price_unit']} €) : 2573 → {masque_id}")
    else:
        print(f"⚠️ Ligne {l['id']} inattendue, non touchée : product={l['product_id']} desc={desc[:80]}")

# Relecture de contrôle : toutes les lignes produit + total
so = obj.execute_kw(DB, UID, KEY, 'sale.order', 'read', [[590]],
    {'fields': ['amount_untaxed', 'amount_total']})[0]
print(f"\nContrôle totaux : HT={so['amount_untaxed']} TTC={so['amount_total']} (attendu 10206.6 / 12247.92)")
check = obj.execute_kw(DB, UID, KEY, 'sale.order.line', 'search_read',
    [[('order_id', '=', 590), ('display_type', '=', False)]],
    {'fields': ['product_id', 'name', 'product_uom_qty', 'price_unit'], 'order': 'sequence, id'})
print('\nLignes produit après fix :')
for l in check:
    desc = (l['name'] or '').replace(chr(10), ' | ')[:70]
    print(f"  [{l['product_id'][0]}] {l['product_id'][1][:55]:55} qty={l['product_uom_qty']:>6} @ {l['price_unit']}")
