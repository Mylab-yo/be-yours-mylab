---
name: gerer-bl
description: "Gère les bons de livraison Odoo (stock.picking sortants) depuis Telegram : annuler, régénérer, modifier qté/lots, préparer l'expédition. ÉCRITURE EN PROD — confirmation obligatoire. La validation/expédition finale reste un clic dans Odoo. Use when: BL, bon de livraison, livraison, annule le BL, régénère le BL, recommencer la livraison, modifier le BL, préparer la livraison, expédition."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [odoo, stock, livraison, bl, picking, mylab]
    related_skills: [check-order, faire-of]
---

# Gérer les BL — bons de livraison Odoo (ÉCRITURE, confirmation obligatoire)

## ⚠️ Règle dure Hermes

Ces opérations **écrivent en production** (stock, livraison). Donc :
- **Lecture d'abord** : toujours afficher l'état du BL avant toute action.
- **JAMAIS d'écriture sans « confirme » explicite** après l'aperçu.
- **Valider/expédier n'est JAMAIS exécuté ici** : Hermes prépare et vérifie, le
  mark-done (bouton Valider) se fait dans Odoo.
- Une opération sur **un seul** BL par demande.
- Ne jamais toucher la facture. Ne jamais afficher/logguer les creds.

## Runtime

Creds dans `os.environ` (via `/opt/data/.env`) — ne pas hardcoder/afficher :
`ODOO_URL`, `ODOO_DB` (= `OdooYJ`), `ODOO_UID` (= 8), `ODOO_API_KEY`. `xmlrpc.client`
dispo. Pickings sortants = `picking_type_id` 10 (`MYLAB: Bons de livraison`).

```python
import os, xmlrpc.client
ODOO = os.environ.get('ODOO_URL', 'https://odoo.startec-paris.com')
DB   = os.environ.get('ODOO_DB', 'OdooYJ')
UID  = int(os.environ.get('ODOO_UID', '8'))
KEY  = os.environ['ODOO_API_KEY']
obj  = xmlrpc.client.ServerProxy(f'{ODOO}/xmlrpc/2/object', allow_none=True)
def call(model, method, *args, **kw):
    return obj.execute_kw(DB, UID, KEY, model, method, list(args), kw)
PICKING_TYPE_OUT = 10
```

## Étape 1 : Déterminer l'opération + la référence du BL

Depuis le message, déduis :
- **op** ∈ `cancel` (annule), `regen` (régénère / recommence), `modify` (modifie /
  change / mets … à), `prepare` (prépare / expédie / valide → APERÇU SEULEMENT).
- **term** = la référence du BL : un numéro (`00132`, `MYVO/OUT/00132`), un nom de
  client (`Hairdex`), ou une commande (`S00566`).

Si l'opération ou la référence est ambiguë → demander, ne rien faire.

## Étape 2 : Identifier le BL + afficher son état (lecture seule, systématique)

```python
dom = ['|', '|',
       ('name', 'ilike', term),
       ('partner_id.name', 'ilike', term),
       ('origin', 'ilike', term),
       ('picking_type_id', '=', PICKING_TYPE_OUT)]
pks = call('stock.picking', 'search_read', dom,
           fields=['name', 'state', 'partner_id', 'origin', 'sale_id', 'move_ids'],
           order='id desc')
```

- 0 résultat → « aucun BL trouvé pour *{term}* ».
- >1 résultat → lister (n°, client, état) et demander lequel.
- 1 résultat → `p = pks[0]`. Afficher l'état + les lignes :

```python
p = pks[0]
ml_ids = call('stock.move.line', 'search', [('picking_id', '=', p['id'])])
mls = call('stock.move.line', 'read', ml_ids,
           fields=['product_id', 'quantity', 'lot_id']) if ml_ids else []
# rendu :
#  BL {p['name']} | client {p['partner_id'][1]} | commande {p['origin']} | état {p['state']}
#  Lignes :
#    1. {ml['product_id'][1]} : {ml['quantity']}  lot={ml['lot_id'][1] if ml['lot_id'] else '—'}
```

## Étape 3 : Exécuter l'opération (aperçu → « confirme » → action)

### a) `cancel` — Annuler

- Si `p['state'] == 'cancel'` → « déjà annulé », rien à faire.
- Si `p['state'] == 'done'` → **refus** : « ce BL est déjà expédié, je ne peux pas
  l'annuler ici — procédure retour dans Odoo. »
- Sinon : aperçu « j'annule {p['name']} ({client}, {commande}) » → attendre « confirme » →

```python
call('stock.picking', 'action_cancel', [p['id']])
```

### b) `regen` — Régénérer

- Vise une commande dont le BL est `cancel`. Si le BL identifié n'est pas annulé,
  demander confirmation que c'est bien celui à recopier.
- Aperçu « je crée un BL frais sur {origin} (mêmes lignes) » → « confirme » →

```python
new_id = call('stock.picking', 'copy', p['id'])      # nouveau brouillon, n° auto
call('stock.picking', 'action_confirm', [new_id])
call('stock.picking', 'action_assign', [new_id])
np = call('stock.picking', 'read', [new_id], fields=['name', 'state'])[0]
# rapport : « ✅ nouveau BL {np['name']} ({np['state']}) prêt sur {origin} »
```

### c) `modify` — Modifier qté / lot

- **Refus si** `p['state']` ∈ `done`, `cancel` : « BL {état}, non modifiable. »
- Lister les lignes numérotées (cf Étape 2). L'utilisateur exprime le changement
  (« ligne 2 → 30 », « shampoing volume → 30 », « lot de shampoing volume → 220A526C »).
  Résous la `stock.move.line` ciblée (`ml_id`), son produit (`prod_id`) et le champ.
- Aperçu du diff (avant → après) → « confirme » →

```python
# changer la quantité à expédier sur la ligne
call('stock.move.line', 'write', [ml_id], {'quantity': new_qty})

# OU changer le lot (le lot doit exister pour ce produit ; sinon le créer)
lot_ids = call('stock.lot', 'search', [('name', '=', lot_name), ('product_id', '=', prod_id)])
lot_id = lot_ids[0] if lot_ids else call('stock.lot', 'create',
             {'name': lot_name, 'product_id': prod_id})
call('stock.move.line', 'write', [ml_id], {'lot_id': lot_id})
```

### d) `prepare` — Préparer / expédier (APERÇU SEULEMENT, aucune écriture)

```python
ready = (p['state'] == 'assigned')
missing = []
for ml in mls:
    prod = call('product.product', 'read', [ml['product_id'][0]], fields=['tracking'])[0]
    if prod['tracking'] == 'lot' and not ml['lot_id']:
        missing.append(ml['product_id'][1])
```

- Montrer ce qui sera expédié (lignes + qté + lot) et ce qui manque (`state != assigned`,
  ou `missing` non vide).
- Conclure : « ✅ prêt — clique **Valider** sur {p['name']} dans Odoo. »
  **NE JAMAIS** appeler `button_validate` / mark-done.

## Règles

1. Confirmation explicite avant toute écriture (cancel/regen/modify).
2. **Valider/expédier : jamais exécuté** ici (prepare = aperçu + renvoi Odoo).
3. Lecture d'abord : toujours afficher l'état du BL avant d'agir.
4. Annuler refusé sur `done` ; modifier refusé sur `done`/`cancel`.
5. Ne jamais toucher la facture ; si l'erreur l'impacte → le signaler, renvoyer au poste.
6. Une opération, un seul BL par demande.
