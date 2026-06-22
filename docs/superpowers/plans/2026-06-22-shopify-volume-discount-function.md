# Moteur de paliers volume + remise client (Shopify Function) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire en sorte que le prix facturé au checkout corresponde toujours aux paliers volume affichés (tous clients), plus −10 % pour les clients taggés `remise-10`, via une Shopify discount function alimentée par les paliers de `ml-product-map.json`.

**Architecture:** Un script Python pousse les paliers de `assets/ml-product-map.json` dans un metafield produit `mylab.volume_tiers`. Une Shopify Function (cible `cart.lines.discounts.generate.run`, projet app séparé) lit, par ligne de panier, la quantité + le prix unitaire + ce metafield + le tag client, calcule le prix cible (palier, ×0,9 si taggé) et émet une remise en pourcentage. Une remise automatique active la fonction. La remise descend en `discount_allocations` → n8n → Odoo.

**Tech Stack:** Python 3 (requests) pour le sync ; JavaScript ESM + Shopify CLI (Functions, Javy/Wasm) pour la fonction ; Node `node:test` pour les tests unitaires JS ; Shopify Admin GraphQL API.

## Global Constraints

- Boutique : `mylab-shop-3.myshopify.com`. Admin API version `2025-10`.
- Token Admin lu depuis l'env `SHOPIFY_ADMIN_TOKEN` — utiliser le token « modifs site » (`shpat_bb6245bc…`), **pas** le token customer-data. Jamais de token en dur dans un fichier commité.
- Tous les prix sont en **centimes** (entiers). `850` = 8,50 €.
- Tag client cible : `remise-10`.
- Metafield : namespace `mylab`, key `volume_tiers`, type `json`, owner `PRODUCT`. Valeur = tableau de paires `[[qty, prixCentimes], …]` triées par quantité croissante.
- L'app Shopify Function vit dans un **projet sibling** : `d:/mylab-discount-app` (repo git séparé). Le script de sync, la spec et ce plan vivent dans le repo thème `d:/be-yours-mylab` (branche `feat/volume-discount-function`).
- La fonction ne **majore jamais** un prix (remise bornée à ≥ 0) et ignore silencieusement toute ligne sans metafield valide.

---

## File Structure

**Repo thème `d:/be-yours-mylab`** (branche `feat/volume-discount-function`) :
- Create `scripts/shopify/sync_volume_tiers.py` — transforme `ml-product-map.json` → metafields produit ; garde-fou écart prix base.
- Create `scripts/shopify/test_sync_volume_tiers.py` — tests unitaires des fonctions pures de transformation.

**Repo app sibling `d:/mylab-discount-app`** (créé par `shopify app init`) :
- Create `extensions/volume-discount/shopify.extension.toml` — config extension (target + export).
- Create `extensions/volume-discount/src/input.graphql` — requête d'entrée.
- Create `extensions/volume-discount/src/discount-logic.js` — logique pure (testable).
- Create `extensions/volume-discount/src/discount-logic.test.js` — tests `node:test`.
- Create `extensions/volume-discount/src/run.js` — wrapper d'entrée de la fonction.

---

## Task 1 : Script de synchronisation des paliers → metafields

**Files:**
- Create: `scripts/shopify/sync_volume_tiers.py`
- Test: `scripts/shopify/test_sync_volume_tiers.py`

**Interfaces:**
- Consumes: `assets/ml-product-map.json` (dict `handle → {sizes:{size:handle}, tiers:{size:"q:p,q:p"}}`).
- Produces (fonctions pures réutilisées par les steps réseau) :
  - `parse_tier_string(s: str) -> list[list[int]]`
  - `build_metafield_payloads(product_map: dict) -> list[dict]` où chaque dict = `{"handle": str, "size": str, "tiers": list[list[int]], "base_price": int|None}`

- [ ] **Step 1: Écrire le test qui échoue (fonctions pures)**

Create `scripts/shopify/test_sync_volume_tiers.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sync_volume_tiers import parse_tier_string, build_metafield_payloads


def test_parse_tier_string_basic():
    assert parse_tier_string("6:850,12:805,24:765") == [[6, 850], [12, 805], [24, 765]]


def test_parse_tier_string_sorts_and_trims():
    assert parse_tier_string(" 12:805 , 6:850 ") == [[6, 850], [12, 805]]


def test_build_metafield_payloads():
    product_map = {
        "bain-miraculeux": {
            "sizes": {"50": "bain-miraculeux"},
            "tiers": {"50": "6:850,12:805"},
        },
        "shampoing-nourrissant": {
            "sizes": {"200": "shampoing-nourrissant", "500": "shampoing-nourrissant-500ml"},
            "tiers": {"200": "6:700,12:665", "500": "6:1490,12:1340"},
        },
    }
    out = build_metafield_payloads(product_map)
    by_handle = {p["handle"]: p for p in out}
    assert by_handle["bain-miraculeux"]["tiers"] == [[6, 850], [12, 805]]
    assert by_handle["bain-miraculeux"]["base_price"] == 850
    assert by_handle["shampoing-nourrissant-500ml"]["base_price"] == 1490
    assert len(out) == 3
```

- [ ] **Step 2: Lancer le test, vérifier qu'il échoue**

Run: `python -m pytest scripts/shopify/test_sync_volume_tiers.py -v`
Expected: FAIL — `ModuleNotFoundError` / `cannot import name 'parse_tier_string'`.

- [ ] **Step 3: Écrire les fonctions pures dans le script**

Create `scripts/shopify/sync_volume_tiers.py` (partie pure d'abord) :

```python
#!/usr/bin/env python3
"""Synchronise les paliers volume de ml-product-map.json vers les metafields produit
Shopify (mylab.volume_tiers, type json). Idempotent.

Usage:
  SHOPIFY_ADMIN_TOKEN=shpat_... python scripts/shopify/sync_volume_tiers.py --dry-run
  SHOPIFY_ADMIN_TOKEN=shpat_... python scripts/shopify/sync_volume_tiers.py
"""
import argparse
import json
import os
import sys

SHOP = "mylab-shop-3.myshopify.com"
API_VERSION = "2025-10"
NAMESPACE = "mylab"
KEY = "volume_tiers"
MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ml-product-map.json")


def parse_tier_string(s):
    """'6:850,12:805' -> [[6, 850], [12, 805]] trié par quantité croissante."""
    pairs = []
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        qty_str, price_str = chunk.split(":")
        pairs.append([int(qty_str), int(price_str)])
    pairs.sort(key=lambda p: p[0])
    return pairs


def build_metafield_payloads(product_map):
    """Aplati le map en une liste de metafields à écrire, un par (handle, size)."""
    out = []
    for entry in product_map.values():
        sizes = entry.get("sizes", {})
        tiers = entry.get("tiers", {})
        for size, handle in sizes.items():
            ts = tiers.get(size)
            if not ts:
                continue
            parsed = parse_tier_string(ts)
            out.append({
                "handle": handle,
                "size": size,
                "tiers": parsed,
                "base_price": parsed[0][1] if parsed else None,
            })
    return out
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `python -m pytest scripts/shopify/test_sync_volume_tiers.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Ajouter la couche réseau (définition + résolution + écriture + garde-fou)**

Append to `scripts/shopify/sync_volume_tiers.py` :

```python
import requests  # noqa: E402

GRAPHQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"


def _gql(token, query, variables=None):
    r = requests.post(
        GRAPHQL_URL,
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def ensure_definition(token):
    q = """
    mutation Def {
      metafieldDefinitionCreate(definition: {
        name: "Volume tiers", namespace: "%s", key: "%s", type: "json", ownerType: PRODUCT
      }) { createdDefinition { id } userErrors { code message } }
    }""" % (NAMESPACE, KEY)
    data = _gql(token, q)
    errs = data["metafieldDefinitionCreate"]["userErrors"]
    for e in errs:
        if e.get("code") != "TAKEN":
            raise RuntimeError(f"definition error: {e}")
    print("definition OK")


def resolve_product(token, handle):
    q = """
    query P($q: String!) {
      products(first: 1, query: $q) {
        nodes { id title variants(first: 1) { nodes { price } } }
      }
    }"""
    data = _gql(token, q, {"q": f"handle:{handle}"})
    nodes = data["products"]["nodes"]
    if not nodes:
        return None
    p = nodes[0]
    variant_price_cents = None
    vnodes = p["variants"]["nodes"]
    if vnodes:
        variant_price_cents = round(float(vnodes[0]["price"]) * 100)
    return {"id": p["id"], "variant_price": variant_price_cents}


def write_metafield(token, product_id, tiers):
    q = """
    mutation Set($m: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $m) { userErrors { field message } }
    }"""
    variables = {"m": [{
        "ownerId": product_id, "namespace": NAMESPACE, "key": KEY,
        "type": "json", "value": json.dumps(tiers),
    }]}
    data = _gql(token, q, variables)
    errs = data["metafieldsSet"]["userErrors"]
    if errs:
        raise RuntimeError(f"metafieldsSet error: {errs}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("SHOPIFY_ADMIN_TOKEN")
    if not token:
        print("ERREUR: SHOPIFY_ADMIN_TOKEN manquant", file=sys.stderr)
        sys.exit(1)

    with open(os.path.abspath(MAP_PATH), encoding="utf-8") as f:
        product_map = json.load(f)
    payloads = build_metafield_payloads(product_map)

    if not args.dry_run:
        ensure_definition(token)

    mismatches, missing, written = [], [], 0
    for p in payloads:
        prod = resolve_product(token, p["handle"])
        if not prod:
            missing.append(p["handle"])
            continue
        if prod["variant_price"] is not None and prod["variant_price"] != p["base_price"]:
            mismatches.append((p["handle"], prod["variant_price"], p["base_price"]))
        if args.dry_run:
            print(f"[dry] {p['handle']}: tiers={p['tiers']}")
        else:
            write_metafield(token, prod["id"], p["tiers"])
            written += 1
            print(f"écrit {p['handle']}")

    print(f"\n--- Résumé ---")
    print(f"metafields {'planifiés' if args.dry_run else 'écrits'}: {len(payloads) if args.dry_run else written}")
    if missing:
        print(f"⚠️ handles introuvables ({len(missing)}): {missing}")
    if mismatches:
        print(f"⚠️ écarts prix variant ≠ base palier ({len(mismatches)}):")
        for h, vp, bp in mismatches:
            print(f"    {h}: variant={vp} base_palier={bp}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Vérifier que les tests unitaires passent toujours**

Run: `python -m pytest scripts/shopify/test_sync_volume_tiers.py -v`
Expected: PASS (3 tests) — l'ajout réseau ne casse pas les fonctions pures.

- [ ] **Step 7: Dry-run réel (lecture seule) contre la boutique**

Run: `SHOPIFY_ADMIN_TOKEN=shpat_… python scripts/shopify/sync_volume_tiers.py --dry-run`
Expected: liste de ~79 lignes `[dry] handle: tiers=…`, 0 handle introuvable (sinon corriger les handles dans le map), et le rapport d'écarts prix base. **Noter les écarts** : ils devront être corrigés (prix de variant Shopify recalés sur la base palier) avant la mise en prod, sinon la fonction recalera ces lignes.

- [ ] **Step 8: Commit**

```bash
git add scripts/shopify/sync_volume_tiers.py scripts/shopify/test_sync_volume_tiers.py
git commit -m "feat(pricing): script sync paliers volume -> metafields produit Shopify"
```

---

## Task 2 : Écrire les metafields en prod + définition

**Files:** aucun fichier — exécution + vérification.

**Interfaces:**
- Consumes: `scripts/shopify/sync_volume_tiers.py` (Task 1).
- Produces: metafield `mylab.volume_tiers` peuplé sur tous les produits à paliers.

- [ ] **Step 1: Corriger les écarts de prix base signalés au dry-run**

Pour chaque écart `variant ≠ base_palier` remonté en Task 1 Step 7 : décider si le **prix de variant Shopify** doit être recalé sur la base palier (cas normal) ou si la base palier est fausse dans `ml-product-map.json`. Appliquer la correction à la bonne source. Re-lancer le dry-run jusqu'à 0 écart (ou écarts explicitement acceptés).

- [ ] **Step 2: Exécuter le sync en écriture**

Run: `SHOPIFY_ADMIN_TOKEN=shpat_… python scripts/shopify/sync_volume_tiers.py`
Expected: `definition OK`, `écrit <handle>` pour chaque produit, résumé `metafields écrits: N`.

- [ ] **Step 3: Vérifier un metafield via l'API**

Run :
```bash
curl -s -X POST "https://mylab-shop-3.myshopify.com/admin/api/2025-10/graphql.json" \
  -H "X-Shopify-Access-Token: $SHOPIFY_ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ products(first:1, query:\"handle:bain-miraculeux\"){ nodes { metafield(namespace:\"mylab\", key:\"volume_tiers\"){ value } } } }"}'
```
Expected: `"value":"[[6,850],[12,805],[24,765],[48,680],[96,610]]"`.

---

## Task 3 : Scaffolder l'app + l'extension discount function

**Files:** projet sibling `d:/mylab-discount-app` créé par la CLI.

**Interfaces:**
- Produces: une app Shopify avec une extension function (cible cart-lines discount) qui build, déployable sur la boutique.

- [ ] **Step 1: Initialiser l'app**

Run (depuis `d:/`) : `shopify app init --name mylab-discount-app`
Choisir le template « Start with Remix » ou « none/skeleton » selon le menu, langage **JavaScript**. Cela crée `d:/mylab-discount-app`.

- [ ] **Step 2: Générer l'extension discount function**

Run (depuis `d:/mylab-discount-app`) : `shopify app generate extension`
Choisir type **Function → Discounts** (template « cart and checkout / discount », langage **JavaScript**). Nommer l'extension `volume-discount`. Cela crée `extensions/volume-discount/` avec un `shopify.extension.toml`, `src/run.js`, `src/run.graphql` (ou `input.graphql`), et un `package.json`.

- [ ] **Step 3: Vérifier que l'extension par défaut build**

Run (depuis `extensions/volume-discount`) : `npm install` puis `shopify app function build`
Expected: build OK, un `.wasm` est produit (le template par défaut). Si le build échoue, résoudre les prérequis (Node ≥ 18, toolchain Javy téléchargée par la CLI) avant de continuer.

- [ ] **Step 4: Commit (repo app)**

```bash
cd /d/mylab-discount-app && git add -A && git commit -m "chore: scaffold app + extension volume-discount"
```

---

## Task 4 : Logique de remise pure + tests unitaires (TDD)

**Files:**
- Create: `extensions/volume-discount/src/discount-logic.js`
- Test: `extensions/volume-discount/src/discount-logic.test.js`

**Interfaces:**
- Produces:
  - `selectTier(tiers: number[][], quantity: number) -> number[]|null`
  - `computeLinePercentage(unitCents: number, tiers: number[][], quantity: number, tagged: boolean) -> number`
  - `buildOperations(input: object) -> { operations: object[] }`

- [ ] **Step 1: S'assurer que l'extension est en ESM**

Dans `extensions/volume-discount/package.json`, vérifier/ajouter `"type": "module"` (nécessaire pour que `import`/`node --test` fonctionnent sur les sources).

- [ ] **Step 2: Écrire les tests qui échouent**

Create `extensions/volume-discount/src/discount-logic.test.js` :

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { selectTier, computeLinePercentage, buildOperations } from "./discount-logic.js";

test("selectTier prend le plus grand seuil <= qty", () => {
  const tiers = [[6, 850], [12, 805], [24, 765]];
  assert.deepEqual(selectTier(tiers, 6), [6, 850]);
  assert.deepEqual(selectTier(tiers, 11), [6, 850]);
  assert.deepEqual(selectTier(tiers, 12), [12, 805]);
  assert.deepEqual(selectTier(tiers, 100), [24, 765]);
  assert.equal(selectTier(tiers, 5), null);
});

test("computeLinePercentage volume seul", () => {
  const tiers = [[6, 850], [12, 805]];
  assert.equal(computeLinePercentage(850, tiers, 6, false), 0);
  const pct = computeLinePercentage(850, tiers, 12, false);
  assert.ok(Math.abs(pct - 5.2941) < 0.001);
});

test("computeLinePercentage taggé ajoute 10%", () => {
  const tiers = [[6, 850], [12, 805]];
  assert.equal(computeLinePercentage(850, tiers, 6, true).toFixed(2), "10.00");
  const pct = computeLinePercentage(850, tiers, 12, true);
  assert.ok(Math.abs(pct - 14.7059) < 0.001);
});

test("computeLinePercentage sous le 1er palier -> 0", () => {
  assert.equal(computeLinePercentage(850, [[6, 850]], 5, false), 0);
});

test("computeLinePercentage ne majore jamais", () => {
  assert.equal(computeLinePercentage(800, [[6, 850]], 6, false), 0);
});

test("buildOperations ignore les lignes sans metafield", () => {
  const input = { cart: { buyerIdentity: { customer: { hasAnyTag: false } }, lines: [
    { id: "gid://shopify/CartLine/0", quantity: 12, cost: { amountPerQuantity: { amount: "8.50" } },
      merchandise: { __typename: "ProductVariant", product: { metafield: null } } },
  ] } };
  assert.deepEqual(buildOperations(input), { operations: [] });
});

test("buildOperations émet un candidat en pourcentage", () => {
  const input = { cart: { buyerIdentity: { customer: { hasAnyTag: false } }, lines: [
    { id: "gid://shopify/CartLine/0", quantity: 12, cost: { amountPerQuantity: { amount: "8.50" } },
      merchandise: { __typename: "ProductVariant", product: { metafield: { jsonValue: [[6, 850], [12, 805]] } } } },
  ] } };
  const out = buildOperations(input);
  assert.equal(out.operations.length, 1);
  const cand = out.operations[0].productDiscountsAdd.candidates[0];
  assert.equal(cand.targets[0].cartLine.id, "gid://shopify/CartLine/0");
  assert.equal(cand.value.percentage.value, "5.294");
});
```

- [ ] **Step 3: Lancer les tests, vérifier qu'ils échouent**

Run (depuis `extensions/volume-discount`) : `node --test src/discount-logic.test.js`
Expected: FAIL — `Cannot find module './discount-logic.js'`.

- [ ] **Step 4: Implémenter la logique**

Create `extensions/volume-discount/src/discount-logic.js` :

```js
// Logique pure de calcul de remise paliers volume (+10% taggé). Aucune dépendance
// Shopify : testable avec node:test.

export function selectTier(tiers, quantity) {
  let chosen = null;
  for (const pair of tiers) {
    if (quantity >= pair[0]) chosen = pair;
  }
  return chosen;
}

export function computeLinePercentage(unitCents, tiers, quantity, tagged) {
  const tier = selectTier(tiers, quantity);
  if (!tier) return 0;
  const target = Math.round(tier[1] * (tagged ? 0.9 : 1));
  if (!(unitCents > 0)) return 0;
  const pct = ((unitCents - target) / unitCents) * 100;
  return pct > 0 ? pct : 0;
}

export function buildOperations(input) {
  const customer = input?.cart?.buyerIdentity?.customer;
  const tagged = customer?.hasAnyTag === true;
  const candidates = [];
  for (const line of input?.cart?.lines ?? []) {
    const variant = line.merchandise;
    if (!variant || variant.__typename !== "ProductVariant") continue;
    const raw = variant.product?.metafield?.jsonValue;
    if (!Array.isArray(raw)) continue;
    const unit = Math.round(Number(line.cost.amountPerQuantity.amount) * 100);
    const pct = computeLinePercentage(unit, raw, line.quantity, tagged);
    if (pct <= 0) continue;
    candidates.push({
      targets: [{ cartLine: { id: line.id } }],
      value: { percentage: { value: pct.toFixed(3) } },
      message: tagged ? "Tarif volume + remise pro" : "Tarif volume",
    });
  }
  if (candidates.length === 0) return { operations: [] };
  return { operations: [{ productDiscountsAdd: { selectionStrategy: "FIRST", candidates } }] };
}
```

- [ ] **Step 5: Lancer les tests, vérifier qu'ils passent**

Run: `node --test src/discount-logic.test.js`
Expected: PASS (7 tests).

- [ ] **Step 6: Commit (repo app)**

```bash
cd /d/mylab-discount-app && git add extensions/volume-discount/src/discount-logic.js extensions/volume-discount/src/discount-logic.test.js extensions/volume-discount/package.json
git commit -m "feat: logique pure remise paliers volume + tests"
```

---

## Task 5 : Câbler la fonction (input + run + toml)

**Files:**
- Create/Overwrite: `extensions/volume-discount/src/input.graphql`
- Modify: `extensions/volume-discount/src/run.js`
- Modify: `extensions/volume-discount/shopify.extension.toml`

**Interfaces:**
- Consumes: `buildOperations` (Task 4).
- Produces: une fonction qui répond à `cart.lines.discounts.generate.run` avec la bonne sortie.

- [ ] **Step 1: Écrire la requête d'entrée**

Overwrite `extensions/volume-discount/src/input.graphql` (renommer/supprimer l'ancien `run.graphql` généré si présent et adapter le `input_query` du toml en Step 3) :

```graphql
query Input {
  cart {
    lines {
      id
      quantity
      cost { amountPerQuantity { amount } }
      merchandise {
        __typename
        ... on ProductVariant {
          id
          product {
            handle
            metafield(namespace: "mylab", key: "volume_tiers") { jsonValue }
          }
        }
      }
    }
    buyerIdentity {
      customer { hasAnyTag(tags: ["remise-10"]) }
    }
  }
}
```

- [ ] **Step 2: Écrire le wrapper run**

Overwrite `extensions/volume-discount/src/run.js` :

```js
import { buildOperations } from "./discount-logic.js";

export function run(input) {
  return buildOperations(input);
}
```

- [ ] **Step 3: Aligner le toml**

Dans `extensions/volume-discount/shopify.extension.toml`, s'assurer que la cible et l'export pointent sur nos fichiers :

```toml
api_version = "2025-10"

[[extensions]]
name = "volume-discount"
handle = "volume-discount"
type = "function"
description = "Paliers volume + remise client (tag remise-10)"

  [[extensions.targeting]]
  target = "cart.lines.discounts.generate.run"
  input_query = "src/input.graphql"
  export = "run"

  [extensions.build]
  command = ""
  watch = ["src/**/*.js", "src/**/*.graphql"]
```

(Conserver toute section générée nécessaire au build Javy ; ne modifier que `target`, `input_query`, `export`, et le chemin de l'input query.)

- [ ] **Step 4: Lancer les tests unitaires (non régressés)**

Run: `node --test src/discount-logic.test.js`
Expected: PASS (7 tests).

- [ ] **Step 5: Tester la fonction avec un input réaliste**

Create `extensions/volume-discount/fixtures/tagged-12u.json` :

```json
{
  "cart": {
    "buyerIdentity": { "customer": { "hasAnyTag": true } },
    "lines": [
      { "id": "gid://shopify/CartLine/0", "quantity": 12,
        "cost": { "amountPerQuantity": { "amount": "8.50" } },
        "merchandise": { "__typename": "ProductVariant",
          "product": { "handle": "bain-miraculeux", "metafield": { "jsonValue": [[6,850],[12,805],[24,765],[48,680],[96,610]] } } } }
    ]
  }
}
```

Run (depuis `extensions/volume-discount`) : `shopify app function run --input fixtures/tagged-12u.json` (après un `shopify app function build`).
Expected: sortie JSON avec `productDiscountsAdd` → un candidat ciblant `CartLine/0`, `value.percentage.value` ≈ `"14.706"`, `message: "Tarif volume + remise pro"`.

- [ ] **Step 6: Commit (repo app)**

```bash
cd /d/mylab-discount-app && git add extensions/volume-discount/
git commit -m "feat: câblage fonction discount (input/run/toml + fixture)"
```

---

## Task 6 : Déployer + activer la remise + recette checkout

**Files:** aucun — déploiement + vérification.

**Interfaces:**
- Consumes: l'extension (Tasks 3-5), les metafields (Task 2).
- Produces: une remise automatique active liée à la fonction sur la boutique.

- [ ] **Step 1: Déployer l'app**

Run (depuis `d:/mylab-discount-app`) : `shopify app deploy`
Expected: déploiement OK ; la fonction est enregistrée sur la boutique.

- [ ] **Step 2: Récupérer le functionId**

Run :
```bash
curl -s -X POST "https://mylab-shop-3.myshopify.com/admin/api/2025-10/graphql.json" \
  -H "X-Shopify-Access-Token: $SHOPIFY_ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ shopifyFunctions(first:10){ nodes { id title apiType } } }"}'
```
Expected: repérer le `id` de la fonction dont `apiType` correspond aux discounts. Le noter.

- [ ] **Step 3: Créer la remise automatique liée à la fonction**

Run (remplacer `FUNCTION_ID`) :
```bash
curl -s -X POST "https://mylab-shop-3.myshopify.com/admin/api/2025-10/graphql.json" \
  -H "X-Shopify-Access-Token: $SHOPIFY_ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"mutation($d: DiscountAutomaticAppInput!){ discountAutomaticAppCreate(automaticAppDiscount:$d){ automaticAppDiscount { discountId } userErrors { field message } } }","variables":{"d":{"title":"Paliers volume MyLab","functionId":"FUNCTION_ID","discountClasses":["PRODUCT"],"startsAt":"2026-06-22T00:00:00Z","combinesWith":{"productDiscounts":false,"orderDiscounts":false,"shippingDiscounts":false}}}}'
```
Expected: `discountId` retourné, `userErrors: []`. (Si `discountClasses` est rejeté par la version d'API, créer la remise via l'UI Réductions → « Remise automatique » → sélectionner la fonction `volume-discount`, classe Produit.)

- [ ] **Step 4: Recette checkout — volume seul (client non taggé)**

Sur le store, en navigation privée, **sans** compte taggé : ajouter `Bain Miraculeux 50ml`, choisir 12 u., aller jusqu'au **checkout**. Expected: prix unitaire facturé = 8,05 € (total ligne 96,60 €), remise « Tarif volume » visible. Tester aussi 24/48/96 u. → 7,65 / 6,80 / 6,10.

- [ ] **Step 5: Recette checkout — volume + 10% (client taggé)**

Tagger un compte test `remise-10` (Clients → le compte → Tags). Se connecter avec ce compte, même panier 12 u. Expected: prix facturé = `round(805×0,9)=7,25 €`/u, message « Tarif volume + remise pro ». Vérifier 6 u. → 7,65 €/u (= 850×0,9).

- [ ] **Step 6: Vérifier la cohérence affichage ↔ checkout**

Confirmer que le prix du drawer/fiche (paliers JS) == prix checkout pour un client non taggé. Pour un client taggé, le drawer montre le prix palier et le checkout le palier −10 % (écart attendu, phase 2).

---

## Task 7 : Décommissionner l'ancienne promo + BSS

**Files:** aucun — opérations admin.

- [ ] **Step 1: Désactiver la promo native `mylab10`**

Réductions → `mylab10` → Désactiver (le 10 % est désormais dans la fonction). Expected: statut « Inactif ».

- [ ] **Step 2: Confirmer BSS inactif**

Vérifier qu'aucune règle BSS B2B Custom Pricing / Volume n'est active (sinon double application). Expected: aucune règle BSS active sur les produits concernés.

- [ ] **Step 3: Re-test rapide post-décommission**

Refaire un checkout 12 u. (taggé + non taggé) pour confirmer qu'il n'y a **qu'une** remise (celle de la fonction) et le bon total.

---

## Task 8 : Vérification de bout en bout Odoo

**Files:** aucun — vérification d'intégration.

**Interfaces:**
- Consumes: le flux Shopify→Odoo n8n existant (lecture `discount_allocations` → `sale.order.line.discount`).

- [ ] **Step 1: Passer une vraie commande test**

Finaliser une commande test (client taggé, 12 u.) sur la boutique.

- [ ] **Step 2: Vérifier la propagation Odoo**

Dans Odoo, ouvrir le `sale.order` créé par n8n. Expected: la ligne porte un `discount` (%) correspondant à la remise, et le **total net de la ligne == total Shopify** (au centime près). Si écart : tracer le node n8n « Match Products » (lecture `discount_allocations`) — voir `project_shopify_discount_propagation.md`.

- [ ] **Step 3: Commit final de doc (repo thème)**

Mettre à jour la mémoire/doc si besoin, puis :
```bash
git add -A && git commit -m "docs(pricing): recette moteur paliers volume validée bout en bout"
```

---

## Self-Review

**Couverture spec :**
- Source unique → metafield depuis `ml-product-map.json` : Tasks 1-2. ✅
- Fonction lit qty/prix/metafield/tag : Tasks 4-5. ✅
- Palier + ×0,9 taggé, jamais de majoration : Task 4 (`computeLinePercentage`). ✅
- Remise en % (fidélité Odoo) : Task 4 `buildOperations`, Task 8 vérif. ✅
- Plan Grow / pas de fetch réseau : input.graphql sans fetch (Task 5). ✅
- Remise automatique, autonome : Task 6 Step 3 (`combinesWith` tout à false). ✅
- Décommission `mylab10` + BSS : Task 7. ✅
- Garde-fou prix base : Task 1 (rapport mismatch) + Task 2 Step 1 (correction). ✅
- Tests unitaires + intégration + Odoo : Tasks 4, 6, 8. ✅

**Cohérence des types :** `selectTier`/`computeLinePercentage`/`buildOperations` ont les mêmes signatures partout (def Task 4, usage Task 5). Metafield `mylab.volume_tiers` (json, paires `[qty,prix]`) identique entre script (Task 1), fonction (Task 5) et vérif (Task 2). ✅

**Placeholders :** aucun TODO/TBD ; tout le code est fourni. Les seules étapes sans bloc de code sont les recettes manuelles (checkout/Odoo), avec critères d'acceptation explicites. ✅
