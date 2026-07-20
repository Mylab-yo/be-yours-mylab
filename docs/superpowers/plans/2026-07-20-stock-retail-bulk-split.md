# Séparation stock retail / bulk labo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Empêcher les commandes bulk (≥50 L/réf) de polluer le stock retail Odoo, et faire remonter vers Shopify le vrai stock retail (physique Fini − réservations petites commandes).

**Architecture:** Un classificateur pur (bulk/retail/ambiguous par ligne) partagé entre un script routeur Odoo (repointe les `stock.move` bulk vers `MYVO/Stock/Bulk` id 45) et le sync n8n modifié (ne lit plus que les quants de `MYVO/Stock/Fini` id 47). Tout write Odoo passe par `--dry-run` puis `--apply`, gardé par un canari.

**Tech Stack:** Python 3.12 + XML-RPC (`scripts/odoo/_client.py`), n8n Code nodes (JS, `this.helpers.httpRequest`), Shopify Admin REST 2024-01.

## Global Constraints

- Seuil bulk : `BULK_THRESHOLD_ML = 50000` (50 L), configurable via env `BULK_THRESHOLD_ML`.
- Emplacements Odoo (company_id=3, entrepôt MYLAB/MYVO) : retail = `MYVO/Stock/Fini` **id 47** ; bulk = `MYVO/Stock/Bulk` **id 45** ; parent pollué = `MYVO/Stock` **id 28**.
- Tag override commande : `sale.order.tag_ids` valeur `bulk-labo`.
- Client Odoo : `import` depuis `scripts/odoo/_client.py` (helpers `search_read`, `execute`, `write`). UID 8 partagé → ne jamais tourner un `--apply` pendant une édition manuelle.
- Jamais `git add -A` (checkout partagé). Déployer les 3 nodes n8n **en set**.
- Tout write Odoo : `--dry-run` par défaut, `--apply` explicite, idempotent.
- Réponses/logs en français.

---

### Task 1: Classificateur de ligne (fonction pure + parser contenance)

**Files:**
- Create: `scripts/odoo/stock_bulk/__init__.py` (vide)
- Create: `scripts/odoo/stock_bulk/classify_bulk.py`
- Test: `scripts/odoo/stock_bulk/test_classify_bulk.py`

**Interfaces:**
- Produces:
  - `parse_contenance_ml(text: str) -> int | None` — extrait la contenance en ml depuis un nom/SKU (`shampoing nourrissant 200ml`, `shampoing-nourrissant-1000-ml` → 200 / 1000). `None` si introuvable.
  - `classify_line(name: str, sku: str, qty: float, order_tags: list[str], threshold_ml: int = 50000) -> tuple[str, int | None, str]` — renvoie `(kind, contenance_ml, reason)` où `kind ∈ {"bulk","retail","ambiguous"}`.

- [ ] **Step 1: Write the failing test**

Create `scripts/odoo/stock_bulk/test_classify_bulk.py`:

```python
# -*- coding: utf-8 -*-
"""Test standalone (sans pytest) : `python test_classify_bulk.py` -> 'OK' ou AssertionError."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from classify_bulk import parse_contenance_ml, classify_line

# --- parse_contenance_ml ---
assert parse_contenance_ml("shampoing nourrissant 200ml") == 200
assert parse_contenance_ml("shampoing-nourrissant-1000-ml") == 1000
assert parse_contenance_ml("shampoing-hydratant-200ml") == 200
assert parse_contenance_ml("shampoing nourrissant 5000ml") == 5000
assert parse_contenance_ml("shampoing-nourrissant-125ml") == 125
assert parse_contenance_ml("shampoing-nourrissant-testeur") is None
assert parse_contenance_ml("coffret sans contenance") is None

# --- classify_line ---
# 200ml x 250 = 50 L -> bulk (seuil atteint)
assert classify_line("shampoing nourrissant 200ml", "shampoing-nourrissant-200-ml", 250, [])[0] == "bulk"
# 200ml x 200 = 40 L -> retail
assert classify_line("shampoing nourrissant 200ml", "shampoing-nourrissant-200-ml", 200, [])[0] == "retail"
# 500ml x 100 = 50 L -> bulk (marche pour les autres formats)
assert classify_line("shampoing nourrissant 500ml", "shampoing-nourrissant-500-ml", 100, [])[0] == "bulk"
# testeur -> toujours retail (jamais bulk)
assert classify_line("shampoing nourrissant testeur", "shampoing-nourrissant-testeur", 5, [])[0] == "retail"
# tag bulk-labo force bulk meme sous le seuil
assert classify_line("shampoing nourrissant 200ml", "shampoing-nourrissant-200-ml", 6, ["bulk-labo"])[0] == "bulk"
# contenance introuvable + pas testeur -> ambiguous
assert classify_line("produit mystere", "produit-mystere", 300, [])[0] == "ambiguous"

print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/odoo/stock_bulk/test_classify_bulk.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'classify_bulk'`

- [ ] **Step 3: Write minimal implementation**

Create `scripts/odoo/stock_bulk/classify_bulk.py`:

```python
# -*- coding: utf-8 -*-
"""Classificateur pur bulk/retail pour le split de stock MyLab.

Une ligne est 'bulk' si qty x contenance_ml >= seuil (defaut 50 L), OU si la
commande porte le tag 'bulk-labo'. Les testeurs sont toujours 'retail'.
Contenance introuvable (hors testeur) -> 'ambiguous' (a signaler, jamais deviner).
"""
import os
import re

BULK_THRESHOLD_ML = int(os.environ.get("BULK_THRESHOLD_ML", "50000"))
BULK_TAG = "bulk-labo"

_CONT_RE = re.compile(r"(\d+)\s*ml\b")


def parse_contenance_ml(text):
    """Extrait la contenance en ml depuis un nom/SKU, sinon None."""
    if not text:
        return None
    norm = text.lower().replace("-", " ")
    m = _CONT_RE.search(norm)
    return int(m.group(1)) if m else None


def classify_line(name, sku, qty, order_tags, threshold_ml=BULK_THRESHOLD_ML):
    """Renvoie (kind, contenance_ml, reason). kind in bulk|retail|ambiguous."""
    tags = [t.lower() for t in (order_tags or [])]
    blob = f"{name or ''} {sku or ''}".lower()

    if BULK_TAG in tags:
        return ("bulk", parse_contenance_ml(blob), "tag")
    if "testeur" in blob:
        return ("retail", None, "testeur")

    cont = parse_contenance_ml(name) or parse_contenance_ml(sku)
    if cont is None:
        return ("ambiguous", None, "no-contenance")

    volume = (qty or 0) * cont
    if volume >= threshold_ml:
        return ("bulk", cont, f"volume={volume}ml>=seuil")
    return ("retail", cont, f"volume={volume}ml<seuil")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/odoo/stock_bulk/test_classify_bulk.py`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/odoo/stock_bulk/__init__.py scripts/odoo/stock_bulk/classify_bulk.py scripts/odoo/stock_bulk/test_classify_bulk.py
git commit -m "feat(stock): classificateur pur bulk/retail par volume + tag"
```

---

### Task 2: Routeur de lignes bulk (dry-run) — lecture & classification

**Files:**
- Create: `scripts/odoo/stock_bulk/route_bulk_moves.py`

**Interfaces:**
- Consumes: `classify_bulk.classify_line`.
- Produces: script CLI `route_bulk_moves.py [--apply] [--order S00626]`. Sans `--apply` = dry-run (liste seulement). En dry-run, imprime pour chaque commande confirmée non livrée les `stock.move` bulk à repointer, et signale les lignes `ambiguous`.

Cette task s'arrête au **dry-run** (aucun write). Le `--apply` est ajouté en Task 3, gardé par le canari.

- [ ] **Step 1: Écrire le script en mode lecture seule**

Create `scripts/odoo/stock_bulk/route_bulk_moves.py`:

```python
# -*- coding: utf-8 -*-
"""Repointe les stock.move des lignes BULK vers MYVO/Stock/Bulk (45).

Dry-run par defaut. --apply pour ecrire (ajoute en Task 3).
Idempotent : skip un move deja sur 45 ou un picking done/cancel.
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # scripts/odoo
sys.path.insert(0, os.path.dirname(__file__))                   # stock_bulk
from _client import search_read, execute
from classify_bulk import classify_line

LOC_BULK = 45   # MYVO/Stock/Bulk
LOC_FINI = 47   # MYVO/Stock/Fini


def get_order_tags(order):
    tag_ids = order.get("tag_ids") or []
    if not tag_ids:
        return []
    tags = search_read("crm.tag", [("id", "in", tag_ids)], ["name"])
    return [t["name"] for t in tags]


def collect(order_filter=None):
    """Retourne la liste des moves bulk a repointer + les ambigus."""
    domain = [("state", "=", "sale")]
    if order_filter:
        domain.append(("name", "=", order_filter))
    orders = search_read("sale.order", domain,
                         ["id", "name", "tag_ids", "picking_ids"])
    to_route, ambiguous = [], []
    for o in orders:
        tags = get_order_tags(o)
        pickings = search_read("stock.picking",
            [("id", "in", o.get("picking_ids") or []),
             ("state", "not in", ["done", "cancel"])],
            ["id", "name", "state"])
        pick_ids = [p["id"] for p in pickings]
        if not pick_ids:
            continue
        moves = search_read("stock.move",
            [("picking_id", "in", pick_ids), ("state", "not in", ["done", "cancel"])],
            ["id", "product_id", "product_uom_qty", "location_id", "picking_id", "sale_line_id"])
        for mv in moves:
            pname = mv["product_id"][1]
            # SKU via product.product.default_code
            prod = search_read("product.product", [("id", "=", mv["product_id"][0])], ["default_code"])
            sku = (prod[0]["default_code"] if prod else "") or ""
            kind, cont, reason = classify_line(pname, sku, mv["product_uom_qty"], tags)
            if kind == "ambiguous":
                ambiguous.append((o["name"], pname, mv["product_uom_qty"]))
            elif kind == "bulk":
                if mv["location_id"][0] == LOC_BULK:
                    continue  # deja route
                to_route.append({
                    "order": o["name"], "move_id": mv["id"], "product": pname,
                    "qty": mv["product_uom_qty"], "from_loc": mv["location_id"][1],
                    "reason": reason,
                })
    return to_route, ambiguous


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--order", default=None, help="Limiter a une commande (ex: S00626)")
    args = ap.parse_args()

    to_route, ambiguous = collect(args.order)

    print(f"=== MOVES BULK A REPOINTER vers Bulk(45) : {len(to_route)} ===")
    for r in to_route:
        print(f"  {r['order']:8} move {r['move_id']:6} | {r['product'][:34]:34} "
              f"x{r['qty']:g} | depuis {r['from_loc']} | {r['reason']}")
    if ambiguous:
        print(f"\n=== LIGNES AMBIGUES (contenance inconnue) — A TRAITER MANUELLEMENT : {len(ambiguous)} ===")
        for oname, pname, qty in ambiguous:
            print(f"  {oname:8} | {pname} x{qty:g}")

    if not args.apply:
        print("\n(DRY-RUN — aucun write. Relancer avec --apply apres canari.)")
        return
    # --apply implemente en Task 3
    raise SystemExit("--apply pas encore implemente (Task 3)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lancer le dry-run et observer**

Run: `python scripts/odoo/stock_bulk/route_bulk_moves.py`
Expected: liste des moves bulk (doit inclure CENDREE S00626 200ml x1380, Diaby S00623 200ml x250, Kevin Kayne S00617 500ml x100) et 0 (ou peu) d'ambigus. **Vérifier manuellement** qu'aucune petite commande (ex. 200ml x6) n'apparaît dans « à repointer ».

- [ ] **Step 3: Corriger si le dry-run révèle un mauvais classement**

Si une petite commande apparaît ou un bulk manque : ajuster `classify_bulk.py` (parser/seuil), relancer Task 1 test + ce dry-run. Sinon, continuer.

- [ ] **Step 4: Commit**

```bash
git add scripts/odoo/stock_bulk/route_bulk_moves.py
git commit -m "feat(stock): routeur bulk moves (dry-run) — lecture & classification"
```

---

### Task 3: Routeur — mode `--apply` (repointage réel, idempotent)

**Files:**
- Modify: `scripts/odoo/stock_bulk/route_bulk_moves.py` (remplacer le bloc `--apply`)

**Interfaces:**
- Consumes: `collect()` de Task 2.
- Produces: `--apply` repointe chaque move bulk : `do_unreserve` sur le picking, `write` `location_id=45` sur le move, `action_assign` sur le picking pour re-réserver depuis Bulk.

- [ ] **Step 1: Remplacer le stub `--apply`**

Dans `route_bulk_moves.py`, remplacer la ligne `raise SystemExit("--apply pas encore implemente (Task 3)")` par :

```python
    # Grouper par picking pour unreserve/assign une seule fois par bon
    from collections import defaultdict
    moves_by_pick = defaultdict(list)
    mv_full = search_read("stock.move",
        [("id", "in", [r["move_id"] for r in to_route])],
        ["id", "picking_id"])
    for m in mv_full:
        moves_by_pick[m["picking_id"][0]].append(m["id"])

    for pick_id, move_ids in moves_by_pick.items():
        # 1) liberer les reservations du bon
        execute("stock.picking", "do_unreserve", [[pick_id]])
        # 2) repointer les moves bulk vers Bulk(45)
        execute("stock.move", "write", [move_ids, {"location_id": LOC_BULK}])
        # 3) re-reserver (depuis les bons emplacements)
        execute("stock.picking", "action_assign", [[pick_id]])
        print(f"  picking {pick_id} : {len(move_ids)} move(s) repointe(s) sur Bulk(45)")
    print(f"\n=== {len(to_route)} move(s) repointe(s). ===")
    return
```

- [ ] **Step 2: Canari — appliquer sur UNE commande test mélangée**

Prérequis : Yoann crée (ou désigne) une commande test avec 1 petite ligne retail + 1 ligne ≥50 L, la confirme.

Run: `python scripts/odoo/stock_bulk/route_bulk_moves.py --order <SO_TEST> --apply`
Expected : `1 move(s) repointe(s)` (la ligne bulk), la petite ligne intacte.

- [ ] **Step 3: Vérifier l'effet sur les quants (avant/après livraison)**

Run (probe Task 4 réutilisé) : `python scripts/odoo/stock_bulk/probe_retail_availability.py --product <ID>`
Puis Yoann valide la livraison du bon test. Re-run le probe.
Expected : le `quantity` de Fini(47) ne bouge **que** de la petite ligne ; la ligne bulk a décrémenté Bulk(45).

**GATE canari** : si Odoo refuse la source mixte (moves Fini+Bulk dans un même picking), appliquer le repli du spec = split du picking. Ne pas généraliser tant que ce point n'est pas vert.

- [ ] **Step 4: Généraliser aux commandes ouvertes existantes**

Run: `python scripts/odoo/stock_bulk/route_bulk_moves.py --apply`
Expected : toutes les lignes bulk ouvertes (CENDREE S00626, etc.) repointées sur Bulk(45).

- [ ] **Step 5: Commit**

```bash
git add scripts/odoo/stock_bulk/route_bulk_moves.py
git commit -m "feat(stock): routeur bulk moves --apply (unreserve+repoint+assign)"
```

---

### Task 4: Probe de disponibilité retail (Fini 47)

**Files:**
- Create: `scripts/odoo/stock_bulk/probe_retail_availability.py`

**Interfaces:**
- Produces: `probe_retail_availability.py [--product ID]` — imprime, par produit ayant un quant sur Fini(47), `dispo = Σ(quantity − reserved_quantity)` et le compare à `qty_available` global (montre l'écart corrigé). Sert de vérification humaine avant/après migration et de référence pour le sync.

- [ ] **Step 1: Écrire le probe**

Create `scripts/odoo/stock_bulk/probe_retail_availability.py`:

```python
# -*- coding: utf-8 -*-
"""Compare la dispo retail (Fini 47 : quantity - reserved) au qty_available global."""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _client import search_read
from collections import defaultdict

LOC_FINI = 47


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", type=int, default=None)
    args = ap.parse_args()

    qdom = [("location_id", "=", LOC_FINI)]
    if args.product:
        qdom.append(("product_id", "=", args.product))
    quants = search_read("stock.quant", qdom,
                         ["product_id", "quantity", "reserved_quantity"])
    agg = defaultdict(lambda: [0.0, 0.0])
    for q in quants:
        agg[q["product_id"][0]][0] += q["quantity"]
        agg[q["product_id"][0]][1] += q["reserved_quantity"]

    pids = list(agg.keys())
    prods = {p["id"]: p for p in search_read("product.product",
             [("id", "in", pids)], ["id", "name", "default_code", "qty_available"])}

    print(f"{'SKU':38} {'Fini_qty':>9} {'Fini_resv':>9} {'DISPO':>7} {'global':>8}")
    for pid, (qty, resv) in sorted(agg.items(), key=lambda kv: prods[kv[0]]["name"]):
        p = prods[pid]
        dispo = qty - resv
        print(f"{(p.get('default_code') or p['name'])[:38]:38} "
              f"{qty:9g} {resv:9g} {dispo:7g} {p['qty_available']:8g}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lancer et vérifier**

Run: `python scripts/odoo/stock_bulk/probe_retail_availability.py --product 2396`
Expected : ligne 200ml avec `DISPO = Fini_qty − Fini_resv` (avant migration : 6 − 6 = 0), colonne `global` = −662 (montre l'écart que la migration corrige).

- [ ] **Step 3: Commit**

```bash
git add scripts/odoo/stock_bulk/probe_retail_availability.py
git commit -m "feat(stock): probe dispo retail Fini(47) vs qty_available global"
```

---

### Task 5: Sync n8n — node 01 lit les quants Fini(47)

**Files:**
- Modify: `scripts/n8n/sync-stock-odoo-shopify/01-lire-stocks-odoo.js` (remplacement complet)

**Interfaces:**
- Produces: chaque item `{ json: { sku, name, product_id, has_fini_quant: bool, fini_available: int } }`. `has_fini_quant` = le produit a au moins un quant sur Fini(47) (même à 0) → discriminant « peut tomber à 0 » vs « stock non saisi, ne pas toucher ».

- [ ] **Step 1: Remplacer le contenu du node 01**

Replace `scripts/n8n/sync-stock-odoo-shopify/01-lire-stocks-odoo.js` par :

```javascript
// Node "Lire stocks Odoo" — lit les quants de MYVO/Stock/Fini (47) = stock retail.
// dispo = quantity - reserved_quantity (deduit les reservations des petites commandes).
// Les reservations bulk sont sur MYVO/Stock/Bulk (45), donc absentes ici.
// Secrets via $env. HTTP via this.helpers.httpRequest.
const ODOO_URL = 'https://odoo.startec-paris.com';
const ODOO_DB = 'OdooYJ';
const ODOO_UID = 8;
const ODOO_API_KEY = $env.ODOO_API_KEY;
const LOC_FINI = 47;

async function odoo(model, method, args, kwargs) {
  const r = await this.helpers.httpRequest({
    method: 'POST', url: ODOO_URL + '/jsonrpc',
    headers: { 'Content-Type': 'application/json' },
    body: { jsonrpc: '2.0', id: 1, method: 'call',
      params: { service: 'object', method: 'execute_kw',
        args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, model, method, args, kwargs || {}] } },
    json: true,
  });
  return (r && r.result) || [];
}

// 1) Quants sur Fini(47)
const quants = await odoo('stock.quant', 'search_read',
  [[['location_id', '=', LOC_FINI]]],
  { fields: ['product_id', 'quantity', 'reserved_quantity'], limit: 2000 });

// 2) Agreger par produit
const agg = {};
for (const q of quants) {
  const pid = q.product_id[0];
  if (!agg[pid]) agg[pid] = { qty: 0, resv: 0 };
  agg[pid].qty += q.quantity;
  agg[pid].resv += q.reserved_quantity;
}
const pids = Object.keys(agg).map(Number);
if (pids.length === 0) return [];

// 3) default_code + nom
const prods = await odoo('product.product', 'search_read',
  [[['id', 'in', pids]]],
  { fields: ['id', 'default_code', 'name'], limit: 2000 });

return prods
  .filter(p => p.default_code)
  .map(p => {
    const a = agg[p.id];
    return { json: {
      sku: p.default_code,
      name: p.name,
      product_id: p.id,
      has_fini_quant: true,
      fini_available: Math.floor(a.qty - a.resv),
    } };
  });
```

- [ ] **Step 2: Vérifier le node isolément**

Dans n8n, exécuter le node 01 seul (ou via `mcp__claude_ai_n8n__get_execution` après un test run). Comparer la sortie au probe Task 4 : les SKU et `fini_available` doivent correspondre.
Expected : le 200ml sort `fini_available` cohérent avec le probe (0 avant migration, positif après inventaire).

- [ ] **Step 3: Commit**

```bash
git add scripts/n8n/sync-stock-odoo-shopify/01-lire-stocks-odoo.js
git commit -m "feat(stock): sync node 01 lit quants Fini(47), dispo=qty-reserved"
```

---

### Task 6: Sync n8n — node 02 (testeurs + garde zéro révisé)

**Files:**
- Modify: `scripts/n8n/sync-stock-odoo-shopify/02-lire-shopify-comparer.js`

**Interfaces:**
- Consumes: items de Task 5 (`sku`, `name`, `has_fini_quant`, `fini_available`).
- Produces: updates `{ sku, name, inventory_item_id, location_id, odoo_qty, shopify_qty, diff }` où `odoo_qty = fini_available` (testeur = dispo du parent). Push autorisé si `odoo_qty >= 0` ET (`has_fini_quant` ou parent avec quant Fini). Produits sans quant Fini = jamais poussés (préserve les ~72 non saisis).

- [ ] **Step 1: Adapter le mapping qty et le garde**

Dans `02-lire-shopify-comparer.js` : le champ Odoo passe de `odoo_qty` à `fini_available`. Remplacer le bloc « 3) Produits Odoo matches » et « 5) Comparer » par :

```javascript
// 3) Produits Odoo matches + qty effective (testeur = dispo du parent Fini)
const matched = [];
for (const odoo of odooProducts) {
  const s = skuMap[odoo.sku];
  if (!s) continue;
  const parent = parentOf(odoo.sku);
  let eff, known;
  if (parent && odooBySku[parent]) {
    eff = odooBySku[parent].fini_available;
    known = odooBySku[parent].has_fini_quant;
  } else {
    eff = odoo.fini_available;
    known = odoo.has_fini_quant;
  }
  matched.push({ sku: odoo.sku, name: odoo.name, inv: s.inventory_item_id, eff, known });
}
```

Et dans la boucle de comparaison, remplacer `if (!(m.eff > 0)) continue;` par :

```javascript
  // Ne pousse QUE les produits connus dans Fini (peut valoir 0 = rupture reelle).
  // Produits sans quant Fini (stock non saisi) => jamais touches.
  if (!m.known) continue;
  if (m.eff < 0) continue; // garde-fou : Fini ne devrait jamais etre negatif
```

Le reste (`currentShopifyQty`, push si `currentShopifyQty !== m.eff`, objet `odoo_qty: m.eff`) reste identique.

- [ ] **Step 2: Vérifier la mise à jour de `odooBySku`**

En haut du node, `odooBySku[p.sku] = p` stocke maintenant des items avec `fini_available`/`has_fini_quant`. Confirmer qu'aucune référence à l'ancien `odoo_qty` ne subsiste dans le fichier (recherche `odoo_qty` → ne doit rester que dans l'objet `updates` poussé, = `m.eff`).

Run (grep local): `grep -n "odoo_qty\|fini_available\|has_fini_quant" scripts/n8n/sync-stock-odoo-shopify/02-lire-shopify-comparer.js`
Expected : `odoo_qty` uniquement dans l'objet `updates`; lectures Odoo via `fini_available`/`has_fini_quant`.

- [ ] **Step 3: Commit**

```bash
git add scripts/n8n/sync-stock-odoo-shopify/02-lire-shopify-comparer.js
git commit -m "feat(stock): sync node 02 — testeurs sur Fini + garde zero revise"
```

---

### Task 7: Déploiement n8n en set + vérification bout-en-bout

**Files:**
- Reference: workflow n8n `sync-stock-odoo-shopify` (les 3 nodes 01/02/03).

**Interfaces:**
- Consumes: nodes 01/02 modifiés (03 inchangé).

- [ ] **Step 1: Pousser les 3 nodes EN SET**

Via `patch_workflow.py` / MCP n8n (`mcp__claude_ai_n8n__update_workflow`), mettre à jour les jsCode des nodes 01 et 02 **dans le même déploiement**. Ne jamais pousser un node seul (node 01 émet `fini_available`, node 02 le consomme — désync = grille vide).

- [ ] **Step 2: Test run dry (sans écrire Shopify)**

Exécuter le workflow avec le node 03 (POST Shopify) **désactivé** ou en pin data. Inspecter la sortie du node 02 : liste des updates.
Expected : les SKU retail avec `diff` sensés ; aucune tentative de mettre à 0 un produit non saisi.

- [ ] **Step 3: Test run réel sur 1-2 SKU puis vérif Shopify**

Réactiver node 03, laisser tourner. Vérifier dans l'admin Shopify que le stock du 200ml (après migration/inventaire) reflète `fini_available`.
Expected : Shopify = dispo retail réelle, plus de négatif bloquant.

- [ ] **Step 4: Commit (doc de run si patch_workflow.py touché)**

```bash
git add scripts/n8n/sync-stock-odoo-shopify/
git commit -m "chore(stock): deploiement sync retail Fini en set (nodes 01+02)"
```

---

### Task 8: Documentation & mémoire

**Files:**
- Create: `scripts/odoo/stock_bulk/README.md`
- Modify: `CLAUDE.md` (section stock, 2-3 lignes)

- [ ] **Step 1: README du module**

Create `scripts/odoo/stock_bulk/README.md` : décrit le seuil 50 L, les emplacements (Fini 47 retail / Bulk 45), l'ordre d'exécution (routeur dry-run → canari → apply → sync), le repli split-picking, et le fait que le sync ne lit que Fini.

- [ ] **Step 2: Note dans CLAUDE.md**

Ajouter sous « Pricing logic » ou une nouvelle sous-section « Stock » : le sync Shopify lit `MYVO/Stock/Fini` (retail) ; les commandes ≥50 L sont routées vers `MYVO/Stock/Bulk` par `scripts/odoo/stock_bulk/route_bulk_moves.py` et ne comptent pas dans la dispo Shopify.

- [ ] **Step 3: Commit**

```bash
git add scripts/odoo/stock_bulk/README.md CLAUDE.md
git commit -m "docs(stock): README module stock_bulk + note CLAUDE.md"
```

---

## Ordre d'exécution récapitulatif

1. Task 1 (classificateur + test) — pur, sûr.
2. Task 2 (routeur dry-run) — lecture seule, valide le classement sur données réelles.
3. Task 4 (probe) — avant Task 3 pour disposer de l'outil de vérif du canari.
4. Task 3 (routeur --apply) — **canari d'abord** (1 commande test mélangée), puis généralisation.
5. **Inventaire Fini par Yoann** (manuel) — poser le vrai physique retail.
6. Task 5 + Task 6 (sync nodes) — puis Task 7 (déploiement set + vérif e2e).
7. Task 8 (doc).

> Note : Task 4 se fait avant Task 3 dans l'ordre réel (le probe sert au canari). Les numéros suivent la logique de dépendance de code, pas l'ordre chronologique strict.

## Self-Review (rempli)

- **Couverture spec** : classificateur (T1) ✓ ; routeur ligne-par-ligne vers Bulk 45 (T2/T3) ✓ ; emplacements existants réutilisés ✓ ; sync lit Fini 47 = quantity−reserved (T5) ✓ ; garde zéro révisé via `has_fini_quant` (T6) ✓ ; migration = routeur sur ouvertes + inventaire Fini manuel (ordre §) ✓ ; canari + repli split-picking (T3 step 3) ✓ ; tag `bulk-labo` (T1/T2) ✓ ; ambigus signalés (T2) ✓ ; déploiement en set (T7) ✓.
- **Placeholders** : aucun `<...>` sauf identifiants réels à fournir au moment du canari (`<SO_TEST>`, `<ID>`) — volontaires, choisis par Yoann.
- **Cohérence types** : `fini_available` / `has_fini_quant` définis en T5, consommés en T6 sous les mêmes noms ✓ ; `classify_line` signature identique T1↔T2 ✓ ; `LOC_FINI=47` / `LOC_BULK=45` constants partout ✓.
