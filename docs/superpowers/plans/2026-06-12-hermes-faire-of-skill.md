# Skill Hermes `faire-of` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter dans l'agent Telegram Hermes un skill `faire-of` qui lance un Ordre de Fabrication Odoo (conditionnement vrac → fini, consommation composants + pose du lot) avec confirmation obligatoire en 2 temps.

**Architecture:** Un fichier `SKILL.md` déclaratif (instructions + snippets Python XML-RPC lisant les creds depuis `os.environ`, à l'image de `relance-impayes`), enregistré dans `deploy_skills_to_hermes.py` et poussé sur le VPS. Pas de code applicatif testable unitairement : la logique vit dans le SKILL.md interprété par l'agent. Vérification = déploiement + smoke test Telegram + contrôle Odoo.

**Tech Stack:** Markdown (SKILL.md), Python `xmlrpc.client` (snippets), paramiko/SFTP (déploiement), Hermes (NousResearch) gateway Docker sur VPS.

**Référence spec:** `docs/superpowers/specs/2026-06-12-hermes-faire-of-skill-design.md`

---

### Task 1: Écrire `scripts/hermes/skills/faire-of/SKILL.md`

**Files:**
- Create: `scripts/hermes/skills/faire-of/SKILL.md`

- [ ] **Step 1: Créer le fichier avec ce contenu exact**

````markdown
---
name: faire-of
description: "Lance un Ordre de Fabrication Odoo (conditionnement vrac → produit fini) depuis Telegram : consomme les composants, pose le n° de lot. ÉCRITURE EN PROD — confirmation obligatoire en 2 temps (aperçu → 'confirme'). Use when: faire un OF, OF, ordre de fabrication, produire, conditionner, lancer une production, fabriquer, mettre en flacon."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [odoo, mrp, production, fabrication, stock, mylab]
    related_skills: [check-order]
---

# Faire un OF — Lancer une production Odoo (ÉCRITURE, confirmation obligatoire)

## ⚠️ Règle dure Hermes

Cet acte **écrit en production** : il consomme du vrac + packaging et produit du
fini, et un OF terminé est **quasi impossible à annuler** (il faut une intervention
odoo shell sur le poste). Donc :

- **JAMAIS d'exécution sans un « confirme » explicite** après l'aperçu.
- Toute réponse autre qu'une confirmation affirmative (`confirme`, `oui`, `ok`, `go`)
  ⇒ annulation, **aucune** écriture Odoo.
- Un seul OF par demande.
- Ne jamais afficher/logguer les creds.

## Runtime

Creds déjà dans `os.environ` (via `/opt/data/.env`) — ne pas hardcoder/afficher :
`ODOO_URL`, `ODOO_DB` (= `OdooYJ`), `ODOO_UID` (= 8), `ODOO_API_KEY`. `xmlrpc.client`
dispo. Emplacement fini = `MYVO/Stock/Fini` (id 47). Pas de `company_id` forcé.

```python
import os, re, xmlrpc.client
ODOO = os.environ.get('ODOO_URL', 'https://odoo.startec-paris.com')
DB   = os.environ.get('ODOO_DB', 'OdooYJ')
UID  = int(os.environ.get('ODOO_UID', '8'))
KEY  = os.environ['ODOO_API_KEY']
obj  = xmlrpc.client.ServerProxy(f'{ODOO}/xmlrpc/2/object', allow_none=True)
def call(model, method, *args, **kw):
    return obj.execute_kw(DB, UID, KEY, model, method, list(args), kw)
FINISHED_LOCATION_ID = 47
```

## Étape 1 : Parser l'input

Format : `OF <produit> <qté>` ou `OF <produit> <qté> lot <numéro>`.

```python
def parse(msg):
    m = re.search(r'\blot\s+(\S+)', msg, re.I)
    lot_override = m.group(1) if m else None
    msg2 = re.sub(r'\blot\s+\S+', '', msg, flags=re.I)
    qm = re.search(r'(\d+(?:[.,]\d+)?)', msg2)
    qty = float(qm.group(1).replace(',', '.')) if qm else None
    name = re.sub(r'\b(of|ordre de fabrication|produire|conditionner|fabriquer|lancer( une)? production)\b',
                  '', msg2, flags=re.I)
    name = re.sub(r'\d+(?:[.,]\d+)?', '', name).strip(' -:')
    return name, qty, lot_override
```

Si `qty` manquante ou `name` vide → demander la précision (ne rien faire).

## Étape 2 : Résoudre le produit fini + sa nomenclature (lecture seule)

```python
# variantes matchant le nom ET ayant une BoM
tmpl_ids = call('product.template', 'search', [('name', 'ilike', name)])
candidates = []
for t in tmpl_ids:
    boms = call('mrp.bom', 'search', [('product_tmpl_id', '=', t)], limit=1)
    if not boms:
        continue
    tmpl = call('product.template', 'read', [t], fields=['name', 'product_variant_id'])[0]
    candidates.append({'tmpl': t, 'name': tmpl['name'],
                       'variant': tmpl['product_variant_id'][0], 'bom': boms[0]})
```

- 0 candidat → « *{name}* n'est pas un produit fabriqué (pas de nomenclature). Je ne peux pas faire d'OF dessus. »
- >1 candidat → lister les noms et demander lequel.
- 1 candidat → continuer.

## Étape 3 : Besoins composants + déduction du lot vrac (lecture seule)

```python
bom = call('mrp.bom', 'read', [c['bom']], fields=['product_qty', 'bom_line_ids'])[0]
ratio = qty / bom['product_qty']
lines = call('mrp.bom.line', 'read', [bom['bom_line_ids']],
             fields=['product_id', 'product_qty', 'product_uom_id'])
comps = []          # {pid, name, need, avail, tracking, uom}
bulk_lot = None     # lot proposé pour le fini
for l in lines:
    pid = l['product_id'][0]
    p = call('product.product', 'read', [pid],
             fields=['name', 'qty_available', 'tracking', 'uom_id'])[0]
    need = l['product_qty'] * ratio
    comps.append({'pid': pid, 'name': p['name'], 'need': need,
                  'avail': p['qty_available'], 'tracking': p['tracking'],
                  'uom': l['product_uom_id'][1]})
    if p['tracking'] == 'lot' and bulk_lot is None:
        # lots de ce composant en stock interne, le plus ancien d'abord
        q = call('stock.quant', 'search_read',
                 [('product_id', '=', pid), ('location_id.usage', '=', 'internal'),
                  ('quantity', '>', 0)],
                 fields=['lot_id', 'quantity'], order='in_date asc')
        lots = [r for r in q if r['lot_id']]
        if lots:
            bulk_lot = {'name': lots[0]['lot_id'][1],
                        'others': [r['lot_id'][1] for r in lots[1:]]}

finished_lot = lot_override or (bulk_lot['name'] if bulk_lot else None)
```

Si `finished_lot` reste `None` (aucun composant suivi par lot et pas d'override) →
demander explicitement le n° de lot à Yoann (ne rien faire).

## Étape 4 : APERÇU + attendre « confirme »

Afficher (puis STOP, attendre la réponse) :

```
🏭 OF — {nom produit} × {qty}
Lot fini proposé : {finished_lot}   (vrac : {bulk_lot.name}{, autres lots: ...})

Composants consommés :
  • {comp.name} : {need} {uom}   (stock {avail} → {avail-need}){⚠️ si <0}
  ...

Réponds « confirme » pour lancer, autre chose pour annuler.
```

Pour chaque composant où `avail - need < 0` : ajouter `⚠️ passera en négatif`. On
**n'empêche pas** (négatifs tolérés sur composants `consu`), on prévient.

## Étape 5 : Exécution (UNIQUEMENT sur confirmation affirmative)

```python
# 1. lot fini (get-or-create sur le variant fini)
lot_ids = call('stock.lot', 'search',
               [('name', '=', finished_lot), ('product_id', '=', variant)])
lot_id = lot_ids[0] if lot_ids else call('stock.lot', 'create',
               [{'name': finished_lot, 'product_id': variant}])

# 2. création + confirmation (explose la BoM, réserve, auto-assigne lots composants)
mo_id = call('mrp.production', 'create',
             [{'product_id': variant, 'product_qty': qty, 'bom_id': c['bom'],
               'product_uom_id': 1}])
call('mrp.production', 'action_confirm', [mo_id])

# 3. qté à produire + lot fini
call('mrp.production', 'write', [mo_id], {'qty_producing': qty, 'lot_producing_id': lot_id})
mo = call('mrp.production', 'read', [mo_id],
          fields=['name', 'move_raw_ids', 'move_finished_ids'])[0]

# 4. PIÈGE CLÉ : composants prélevés (sinon non consommés)
call('stock.move', 'write', mo['move_raw_ids'], {'picked': True})
# fini -> emplacement Fini
call('stock.move', 'write', mo['move_finished_ids'], {'location_dest_id': FINISHED_LOCATION_ID})

# 5. terminer — skip_backorder car qté exacte ; JAMAIS skip_consumption
obj.execute_kw(DB, UID, KEY, 'mrp.production', 'button_mark_done', [[mo_id]],
               {'context': {'skip_backorder': True}})

st = call('mrp.production', 'read', [mo_id], fields=['name', 'state'])[0]
```

## Étape 6 : Rapport final

```
✅ OF {st.name} terminé.
{nom produit} : +{qty} (lot {finished_lot}) → stock {nouveau qty_available}
Consommé : {comp.name} −{need}{uom} (...)
```

(relire `qty_available` du fini + des composants pour les chiffres réels)

## Règles

1. **Confirmation obligatoire** : aucune écriture sans réponse affirmative explicite.
2. **Jamais `skip_consumption`** (annule les composants → produit du vide).
3. Un seul OF par demande.
4. Produit sans BoM = refus clair (pas un produit fabriqué).
5. Lot fini = lot du vrac consommé (le plus ancien si plusieurs), surchargé par `lot X`.
6. Si pas de lot déductible et pas d'override → demander, ne pas inventer de numéro.
````

- [ ] **Step 2: Commit**

```bash
git add scripts/hermes/skills/faire-of/SKILL.md
git commit -m "feat(hermes): skill faire-of (lancer un OF depuis Telegram, confirm 2 temps)"
```

---

### Task 2: Enregistrer `faire-of` dans le déployeur

**Files:**
- Modify: `scripts/hermes/deploy_skills_to_hermes.py` (ligne `SKILLS = [...]`)

- [ ] **Step 1: Ajouter `faire-of` à la liste SKILLS**

Remplacer :

```python
SKILLS = ["check-order", "check-customer", "relance-impayes"]
```

par :

```python
SKILLS = ["check-order", "check-customer", "relance-impayes", "faire-of"]
```

- [ ] **Step 2: Sanity check syntaxe du script (pas d'exécution réseau)**

Run: `python -c "import ast; ast.parse(open('scripts/hermes/deploy_skills_to_hermes.py', encoding='utf-8').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add scripts/hermes/deploy_skills_to_hermes.py
git commit -m "chore(hermes): enregistre faire-of dans le déployeur de skills"
```

---

### Task 3: Déployer sur le VPS et vérifier le listing

**Files:** (aucun — exécution d'ops)

- [ ] **Step 1: Déployer**

Run: `python scripts/hermes/deploy_skills_to_hermes.py`
Expected: lignes `pushed faire-of -> /opt/data/skills/faire-of/SKILL.md`, `chown` rc=0, `restart gateway` rc=0.

- [ ] **Step 2: Vérifier que Hermes liste le skill**

Run: `python scripts/hermes/ssh_run.py "docker exec hermes-gateway hermes skills list 2>&1 | grep -i faire-of"`
(si `ssh_run.py` ne prend pas d'argument, utiliser le pattern paramiko des autres scripts hermes)
Expected: une ligne mentionnant `faire-of`.

---

### Task 4: Smoke test depuis Telegram + contrôle Odoo (manuel, Yoann)

**Files:** (aucun)

- [ ] **Step 1: Cas produit sans BoM**

Envoyer à @mylab_hermes_bot : `OF creme volume testeur 10`
Expected : refus clair « pas un produit fabriqué » (pas de BoM), aucun OF créé.

- [ ] **Step 2: Aperçu + annulation**

Envoyer : `OF <un produit fabriqué> <petite qté>` (ex. un fini avec BoM et un peu de vrac en stock).
Expected : aperçu avec lot vrac proposé + composants/stock. Répondre `non` → vérifier qu'aucun OF n'est créé (`MYVO/MO/...` inchangé côté Odoo).

- [ ] **Step 3: Aperçu + confirmation**

Refaire la demande, répondre `confirme`.
Expected : rapport `✅ OF MYVO/MO/xxxxx terminé`. Vérifier côté Odoo (Fabrication → l'OF est `done`, composants décrémentés, fini +qté sous le bon lot dans MYVO/Stock/Fini).

- [ ] **Step 4: Mettre à jour la memory Hermes**

Ajouter une note à `project_hermes_agent_vps.md` : skill `faire-of` porté (écriture OF, confirm 2 temps). Mettre à jour le pointeur MEMORY.md.

---

## Self-Review

**Spec coverage :**
- Nom `faire-of` ✓ (frontmatter + déclencheurs) — Task 1.
- Confirmation 2 temps ✓ — Étapes 4/5 + Règle 1.
- Lot = vrac, plus ancien, surchargeable ✓ — Étape 3 + Règle 5.
- Stock insuffisant = avertir mais laisser passer ✓ — Étape 4.
- Produits avec BoM uniquement ✓ — Étape 2.
- Flux canonique picked=True / pas skip_consumption ✓ — Étape 5 + Règle 2.
- Runtime os.environ / Fini 47 / pas de company ✓ — section Runtime.
- Déploiement via deploy_skills_to_hermes.py ✓ — Tasks 2-3.
- Test manuel Telegram + Odoo ✓ — Task 4.

**Placeholder scan :** aucun TBD/TODO ; les snippets sont complets. Les variables
inter-étapes (`name`, `qty`, `lot_override`, `c`, `variant`, `finished_lot`, `comps`,
`bulk_lot`) sont définies en Étapes 1-3 et réutilisées en 5 de façon cohérente.

**Type consistency :** `c['bom']` (Étape 2) réutilisé en Étape 5 ; `variant` = `c['variant']`
(à lier explicitement à l'exécution : `variant = c['variant']`). `call()` helper unique
partout. `button_mark_done` via `obj.execute_kw` direct pour passer le contexte.
