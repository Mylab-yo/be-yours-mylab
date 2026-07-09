# Skill Hermes `gerer-bl` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter dans Hermes un skill `gerer-bl` qui gère le cycle de vie des bons de livraison Odoo depuis Telegram (annuler / régénérer / modifier qté-lots avec confirmation ; préparer l'expédition en aperçu seulement).

**Architecture:** Un `SKILL.md` déclaratif (l'agent LLM fait l'extraction NL de l'opération + référence BL ; les snippets Python `xmlrpc.client` font les appels Odoo déterministes), enregistré dans `deploy_skills_to_hermes.py`. Vérification = validation read-only contre Odoo réel (mirroir de `validate_faire_of_preview.py`) + smoke test Telegram.

**Tech Stack:** Markdown (SKILL.md), Python `xmlrpc.client`, paramiko/SFTP (déploiement), Hermes gateway Docker.

**Référence spec:** `docs/superpowers/specs/2026-06-12-hermes-gerer-bl-skill-design.md`. Pièges Odoo XML-RPC : voir memory `feedback-odoo-mrp-xmlrpc-lot-production` (create reçoit un dict ; read d'une liste d'ids ne re-wrappe pas ; copy(id) renvoie le nouvel id).

---

### Task 1: Écrire `scripts/hermes/skills/gerer-bl/SKILL.md`

**Files:**
- Create: `scripts/hermes/skills/gerer-bl/SKILL.md`

- [ ] **Step 1: Créer le fichier avec ce contenu exact**

````markdown
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
mls = call('stock.move.line', 'read',
           call('stock.move.line', 'search', [('picking_id', '=', p['id'])]),
           fields=['product_id', 'quantity', 'lot_id'])
# rendu :
#  BL {p['name']} | client {p['partner_id'][1]} | commande {p['origin']} | état {p['state']}
#  Lignes :
#    1. {ml.product_id[1]} : {ml.quantity}  lot={ml.lot_id and ml.lot_id[1] or '—'}
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
  Résous la `stock.move.line` ciblée (`ml_id`) et le champ.
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
````

- [ ] **Step 2: Commit**

```bash
git add scripts/hermes/skills/gerer-bl/SKILL.md
git commit -m "feat(hermes): skill gerer-bl (annuler/régénérer/modifier BL + préparer expédition)"
```

---

### Task 2: Enregistrer `gerer-bl` dans le déployeur

**Files:**
- Modify: `scripts/hermes/deploy_skills_to_hermes.py`

- [ ] **Step 1: Ajouter `gerer-bl` à la liste SKILLS**

Remplacer :
```python
SKILLS = ["check-order", "check-customer", "relance-impayes", "faire-of"]
```
par :
```python
SKILLS = ["check-order", "check-customer", "relance-impayes", "faire-of", "gerer-bl"]
```

- [ ] **Step 2: Ajouter `gerer-bl` au grep de vérification**

Dans la ligne `verify skills`, remplacer le motif `grep -iE '...faire-of|installed|name'`
par `grep -iE 'check-order|check-customer|relance-impayes|faire-of|gerer-bl|installed|name'`.

- [ ] **Step 3: Sanity check syntaxe**

Run: `python -c "import ast; ast.parse(open('scripts/hermes/deploy_skills_to_hermes.py', encoding='utf-8').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add scripts/hermes/deploy_skills_to_hermes.py
git commit -m "chore(hermes): enregistre gerer-bl dans le déployeur"
```

---

### Task 3: Valider la logique read-only contre Odoo réel + corriger

**Files:**
- Create: `scripts/odoo/validate_gerer_bl_preview.py`

- [ ] **Step 1: Écrire le validateur (réplique les snippets read du SKILL.md, AUCUNE écriture)**

```python
"""Valide (READ-ONLY) la logique d'identification + état BL du skill gerer-bl.
N'exécute AUCUNE action (pas de cancel/copy/write). Mirroir de validate_faire_of_preview.py."""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from _client import _models, DB, UID, API_KEY

def call(model, method, *args, **kw):
    return _models.execute_kw(DB, UID, API_KEY, model, method, list(args), kw)

PICKING_TYPE_OUT = 10

def identify(term):
    print(f"\n########## TERM: {term!r}")
    dom = ['|', '|',
           ('name', 'ilike', term),
           ('partner_id.name', 'ilike', term),
           ('origin', 'ilike', term),
           ('picking_type_id', '=', PICKING_TYPE_OUT)]
    pks = call('stock.picking', 'search_read', dom,
               fields=['name', 'state', 'partner_id', 'origin', 'sale_id', 'move_ids'],
               order='id desc')
    print(f"{len(pks)} BL trouvés")
    for p in pks[:5]:
        print(f"  {p['name']} | état={p['state']} | client={p['partner_id']} | cmd={p['origin']}")
    if not pks:
        return
    p = pks[0]
    ml_ids = call('stock.move.line', 'search', [('picking_id', '=', p['id'])])
    mls = call('stock.move.line', 'read', ml_ids,
               fields=['product_id', 'quantity', 'lot_id']) if ml_ids else []
    print(f"--- état BL {p['name']} ({p['state']}) ---")
    for i, ml in enumerate(mls, 1):
        lot = ml['lot_id'][1] if ml['lot_id'] else '—'
        print(f"  {i}. {ml['product_id'][1][:40]:40} qty={ml['quantity']} lot={lot}")

# par numéro, par client, par commande
identify("00132")
identify("Hairdex")
identify("S00566")
```

- [ ] **Step 2: Lancer et vérifier**

Run: `cd /d/be-yours-mylab/scripts/odoo && python validate_gerer_bl_preview.py`
Expected: les 3 termes résolvent le(s) BL Hairdex ; pour `00132`, l'état affiché est `assigned`
avec les 4 lignes shampoing (qty 40). AUCUNE erreur XML-RPC.

- [ ] **Step 3: Corriger toute erreur de signature dans le SKILL.md ET le validateur**

Si une erreur apparaît (ex. liste d'ids double-wrappée, `read` mal formé), corriger
DANS LES DEUX fichiers (le validateur doit rester un miroir fidèle des snippets du SKILL.md).
Re-vérifier que les blocs python du SKILL.md parsent :
Run: `cd /d/be-yours-mylab && python -c "import ast,re; [ast.parse(b) for b in re.findall(r'\x60\x60\x60python\n(.*?)\x60\x60\x60', open('scripts/hermes/skills/gerer-bl/SKILL.md',encoding='utf-8').read(), re.S)]; print('blocs OK')"`
Expected: `blocs OK`

- [ ] **Step 4: Commit**

```bash
git add scripts/hermes/skills/gerer-bl/SKILL.md scripts/odoo/validate_gerer_bl_preview.py
git commit -m "test(hermes): validation read-only gerer-bl contre Odoo réel + fixes éventuels"
```

---

### Task 4: Déployer + vérifier le listing (ops, contrôleur)

**Files:** (aucun)

- [ ] **Step 1: Déployer**

Run: `python scripts/hermes/deploy_skills_to_hermes.py`
Expected: `pushed gerer-bl -> /opt/data/skills/gerer-bl/SKILL.md`, chown rc=0, restart rc=0,
et la ligne `gerer-bl` apparaît dans `verify skills`.

- [ ] **Step 2: Pousser la branche**

Run: `git push`
Expected: les commits gerer-bl sont sur `origin/feature/stock-mrp-setup`.

---

### Task 5: Smoke test Telegram (Yoann) + memory

**Files:** (aucun)

- [ ] **Step 1: Tests Telegram depuis @mylab_hermes_bot**

- « le BL de Hairdex » → affiche l'état du BL courant (00132, assigned).
- « sur le BL 00132, mets shampoing volume à 30 » → aperçu diff (40 → 30) → `confirme` → ligne modifiée (vérifier Odoo).
- « prépare le BL 00132 » → aperçu prêt + « clique Valider dans Odoo » (aucune validation exécutée).
- « annule le BL 00132 » → aperçu → `confirme` → BL annulé (vérifier Odoo).
- « régénère le BL de Hairdex » → aperçu → `confirme` → nouveau BL prêt.

- [ ] **Step 2: Mettre à jour la memory Hermes**

Ajouter à `project_hermes_agent_vps.md` (section Skills portés) : `gerer-bl` porté
(2ᵉ skill écriture, annuler/régénérer/modifier + préparer en aperçu). Mettre à jour le pointeur MEMORY.md.

---

## Self-Review

**Spec coverage :**
- Nom `gerer-bl` + déclencheurs ✓ (Task 1 frontmatter).
- 4 ops (cancel/regen/modify/prepare) ✓ — Étape 3 a/b/c/d.
- Validation = aperçu seulement, jamais mark-done ✓ — Étape 3d + Règle 2.
- Lecture d'abord ✓ — Étape 2 + Règle 3.
- Identification par n°/client/commande + désambiguïsation ✓ — Étapes 1-2.
- Refus sur états interdits (cancel sur done, modify sur done/cancel) ✓ — Étape 3 a/c + Règle 4.
- Régénération par copie (group_id/sale_id préservés) ✓ — Étape 3b.
- Modify = `stock.move.line.quantity` (qté à expédier) / `lot_id` ✓ — Étape 3c.
- Hors périmètre facture/expédition réelle/multi-BL ✓ — Règles 2/5/6.
- Runtime os.environ / picking_type 10 ✓ — Runtime.
- Déploiement + validation read-only ✓ — Tasks 2-4.

**Placeholder scan :** aucun TBD/TODO ; snippets complets. L'extraction NL (op + term) est
volontairement confiée à l'agent LLM (sa force), les snippets ne font que le déterministe Odoo.

**Type consistency :** helper `call()` unique partout, signatures conformes à ce qui a été
validé en prod le 2026-06-12 : `action_cancel([id])`, `copy(id)→new_id`, `write([id],{...})`,
`read(ids_list,...)` (liste NON re-wrappée), `create({...})` (dict, pas `[dict]`). Le validateur
(Task 3) est le miroir exact des snippets read du SKILL.md.
