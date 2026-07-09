# Pompes par format — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre de commander une pompe doseuse au format du flacon (200/500/1000 ml), via une case à cocher sur la fiche produit et une colonne sur la Commande Express ; la pompe est ajoutée au panier comme ligne distincte à la même quantité que les flacons.

**Architecture:** Bloc `_pumps` (format → handle Shopify) ajouté à la source de vérité `assets/ml-product-map.json`. Les deux surfaces lisent ce bloc, déduisent le format du produit, fetchent la pompe (`/products/{handle}.js`) pour variant ID + prix, et poussent un 2e item dans `/cart/add.js`. Le cart drawer affiche déjà les produits non-tiered (prix Shopify natif), donc aucune modif drawer.

**Tech Stack:** Liquid (sections/snippets), JS vanilla IIFE (pas de bundler), Shopify Admin REST API (création produits), Odoo XML-RPC (SKU/prix), `shopify theme push --development --nodelete`.

**Pas de test runner** dans ce repo (cf. CLAUDE.md). Vérification = QA navigateur sur le thème de dev + comparaison avec la maquette `docs/mockups/pompes-mockup.html`.

**Référence :** spec `docs/superpowers/specs/2026-06-11-pompes-par-format-design.md`.

---

## File Structure

| Fichier | Action | Responsabilité |
|---|---|---|
| `scripts/odoo/set_pump_skus.py` | Create | Poser SKU `POMPE-200/500` + vérifier sale_ok/taxes/prix (idempotent) |
| `scripts/shopify/create_pump_products.py` | Create | Créer 3 produits pompes Shopify, retourner handles + variant IDs |
| `assets/ml-product-map.json` | Modify | Ajouter bloc `_pumps` |
| `assets/ml-utils.js` | Modify | Ajouter `getPumpForFormat()` + cache `loadPumpProduct()` |
| `assets/mylab-product.css` | Modify | Styles `.ml-pump*` |
| `sections/main-product.liquid` | Modify | Markup add-on pompe (bloc `[data-mylab-pricing]`) |
| `assets/mylab-product.js` | Modify | Détection format, fetch pompe, case, items[] au panier |
| `snippets/ml-qo-row.liquid` | Modify | Cellule colonne « Pompe » |
| `sections/ml-quick-order.liquid` | Modify | Header colonne + JS pompe (populate, total, submit) |

---

## Task 0 : Prérequis Odoo — SKU pompes

**Files:**
- Create: `scripts/odoo/set_pump_skus.py`

- [ ] **Step 1 : Écrire le script idempotent**

```python
"""Pose les SKU POMPE-200 / POMPE-500 sur les pompes Odoo réutilisées par le storefront.
POMPE-1000 (tmpl 2518) a déjà son SKU. Idempotent : ne réécrit que si différent."""
from _client import search_read, write

# variant_id -> (sku, prix HT attendu)
TARGETS = {
    2486: ("POMPE-200", 0.50),   # Pompe 200ml
    2410: ("POMPE-500", 0.50),   # Pompe 500ml
    2564: ("POMPE-1000", 1.00),  # Pompe 1000ml (SKU déjà posé normalement)
}

for var_id, (sku, price) in TARGETS.items():
    rows = search_read("product.product", [("id", "=", var_id)],
                       ["id", "name", "default_code", "lst_price", "sale_ok", "taxes_id"])
    if not rows:
        print(f"var {var_id}: INTROUVABLE"); continue
    p = rows[0]
    updates = {}
    if p.get("default_code") != sku:
        updates["default_code"] = sku
    if not p.get("sale_ok"):
        updates["sale_ok"] = True
    if 103 not in (p.get("taxes_id") or []):
        updates["taxes_id"] = [(6, 0, [103])]  # 20% G
    if updates:
        write("product.product", [var_id], updates)
        print(f"var {var_id} ({p['name']}): MAJ {list(updates)}")
    else:
        print(f"var {var_id} ({p['name']}): déjà OK (sku={p.get('default_code')}, "
              f"prix={p.get('lst_price')}, sale_ok={p.get('sale_ok')})")
    # prix : ne pas écraser automatiquement, juste alerter si écart
    if abs((p.get("lst_price") or 0) - price) > 0.001:
        print(f"  ⚠️ prix Odoo {p.get('lst_price')}€ ≠ attendu {price}€ — vérifier manuellement")
```

- [ ] **Step 2 : Lancer le script**

Run: `cd /d/be-yours-mylab/scripts/odoo && python set_pump_skus.py`
Expected : 3 lignes, SKU posés ou « déjà OK », pas de ⚠️ prix.

- [ ] **Step 3 : Commit**

```bash
git add scripts/odoo/set_pump_skus.py
git commit -m "feat(pompes): script Odoo pose SKU POMPE-200/500/1000"
```

---

## Task 1 : Créer les produits pompes sur Shopify

**Files:**
- Create: `scripts/shopify/create_pump_products.py`

> Token : utiliser le token Shopify « modifs site » (scope `write_products`). Lu depuis l'env `SHOPIFY_ADMIN_TOKEN`. Vérifier le scope AVANT (un token lecture renverra 403).

- [ ] **Step 1 : Écrire le script de création**

```python
"""Crée 3 produits pompes sur Shopify (mylab-shop-3), prix fixe HT, SKU alignés Odoo,
publiés mais hors collections listées. Idempotent : skip si le handle existe déjà.
Affiche handles + variant IDs (à reporter dans ml-product-map.json)."""
import os, json, time, urllib.request

STORE = "mylab-shop-3.myshopify.com"
TOKEN = os.environ["SHOPIFY_ADMIN_TOKEN"].strip()
API = f"https://{STORE}/admin/api/2024-07"

PUMPS = [
    {"handle": "pompe-200ml",  "title": "Pompe doseuse 200 ml",  "sku": "POMPE-200",  "price": "0.50"},
    {"handle": "pompe-500ml",  "title": "Pompe doseuse 500 ml",  "sku": "POMPE-500",  "price": "0.50"},
    {"handle": "pompe-1000ml", "title": "Pompe doseuse 1000 ml", "sku": "POMPE-1000", "price": "1.00"},
]

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method,
        headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())

for p in PUMPS:
    existing = req("GET", f"/products.json?handle={p['handle']}")
    if existing.get("products"):
        prod = existing["products"][0]
        v = prod["variants"][0]
        print(f"EXISTE  {p['handle']}: product={prod['id']} variant={v['id']} prix={v['price']}")
        continue
    payload = {"product": {
        "title": p["title"], "handle": p["handle"], "status": "active",
        "vendor": "MY.LAB", "product_type": "Pompe",
        "tags": "pompe, accessoire, masquer-collection",
        "variants": [{"price": p["price"], "sku": p["sku"],
                      "inventory_management": None, "requires_shipping": True,
                      "taxable": True}],
    }}
    created = req("POST", "/products.json", payload)["product"]
    v = created["variants"][0]
    print(f"CRÉÉ    {p['handle']}: product={created['id']} variant={v['id']} prix={v['price']}")
    time.sleep(0.6)  # throttle
```

- [ ] **Step 2 : Lancer le script**

Run: `python scripts/shopify/create_pump_products.py`
Expected : 3 lignes `CRÉÉ`/`EXISTE` avec les **variant IDs** (les noter pour vérif, mais le thème lit le prix en direct, donc ils ne sont pas hardcodés).

- [ ] **Step 3 : Vérifier que les produits répondent en JSON**

Run: `curl -s https://mylab-shop-3.myshopify.com/products/pompe-200ml.js | head -c 300`
Expected : JSON avec `"price":50` (centimes), `"available":true`.

- [ ] **Step 4 : Commit**

```bash
git add scripts/shopify/create_pump_products.py
git commit -m "feat(pompes): script création produits pompes Shopify"
```

---

## Task 2 : Bloc `_pumps` dans le product map + helpers ml-utils

**Files:**
- Modify: `assets/ml-product-map.json`
- Modify: `assets/ml-utils.js`

- [ ] **Step 1 : Ajouter `_pumps` au JSON**

Dans `assets/ml-product-map.json`, juste après la ligne `"_doc": ...,` (ligne 2), insérer :

```json
  "_pumps": {
    "200":  { "handle": "pompe-200ml" },
    "500":  { "handle": "pompe-500ml" },
    "1000": { "handle": "pompe-1000ml" }
  },
```

- [ ] **Step 2 : Vérifier que le JSON parse**

Run: `python -c "import json; d=json.load(open('assets/ml-product-map.json', encoding='utf-8')); print('OK', list(d['_pumps']))"`
Expected : `OK ['200', '500', '1000']`

- [ ] **Step 3 : Ajouter les helpers à `ml-utils.js`**

Dans `assets/ml-utils.js`, après `findTiers` (ligne 56) et avant `formatPrice`, insérer :

```javascript
  /** Retourne {handle} de la pompe pour un format ('200'/'500'/'1000'), ou null. */
  function getPumpForFormat(format, map) {
    if (!map || !map._pumps || !format) return null;
    return map._pumps[String(format)] || null;
  }

  var PUMP_CACHE = {};
  /** Fetch (mis en cache) le produit pompe Shopify → { variantId, price } ou null. */
  function loadPumpProduct(handle) {
    if (!handle) return Promise.resolve(null);
    if (PUMP_CACHE[handle]) return PUMP_CACHE[handle];
    PUMP_CACHE[handle] = fetch('/products/' + handle + '.js')
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (p) {
        var v = p.variants && p.variants[0];
        if (!v || v.available === false) return null;
        return { variantId: v.id, price: v.price, handle: handle };
      })
      .catch(function () { return null; });
    return PUMP_CACHE[handle];
  }
```

Puis ajouter les deux à l'export `window.MylabUtils` (ligne ~73) :

```javascript
    findTiers: findTiers,
    getPumpForFormat: getPumpForFormat,
    loadPumpProduct: loadPumpProduct,
    formatPrice: formatPrice,
```

- [ ] **Step 4 : Vérifier non-régression du map (contenance + commande express)**

Run: `shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only assets/ml-product-map.json,assets/ml-utils.js`
Puis ouvrir une fiche produit + la page commande-express sur le thème de dev : sélecteur de contenance et tableau s'affichent **comme avant** (le bloc `_pumps` ne casse rien).

- [ ] **Step 5 : Commit**

```bash
git add assets/ml-product-map.json assets/ml-utils.js
git commit -m "feat(pompes): bloc _pumps + helpers getPumpForFormat/loadPumpProduct"
```

---

## Task 3 : CSS add-on pompe (fiche produit)

**Files:**
- Modify: `assets/mylab-product.css`

- [ ] **Step 1 : Ajouter les styles**

À la fin de la section PRICING (juste avant le commentaire `CTA — pill style`, ~ligne 187), insérer :

```css
/* ============================================================
   ADD-ON POMPE
   ============================================================ */
.ml-pump {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 16px; margin-bottom: 20px;
  border: 1px solid var(--ml-line); border-radius: 12px;
  cursor: pointer; transition: all .15s;
}
.ml-pump:hover { border-color: #bbb; }
.ml-pump.is-checked { border-color: var(--ml-black); background: var(--ml-off); }
.ml-pump__check { width: 20px; height: 20px; accent-color: var(--ml-black); flex-shrink: 0; cursor: pointer; }
.ml-pump__body { flex: 1; }
.ml-pump__title { display: block; font-size: 1.4rem; font-weight: 600; color: var(--ml-black); line-height: 1.25; }
.ml-pump__sub { display: block; font-size: 1.15rem; color: var(--ml-muted); margin-top: 2px; }
.ml-pump__price { font-size: 1.5rem; font-weight: 700; color: var(--ml-black); white-space: nowrap; }
.ml-pump__price small { font-size: 1rem; font-weight: 600; color: var(--ml-muted); letter-spacing: .06em; }
.ml-pump-line { display: none; font-size: 1.25rem; color: var(--ml-mid); margin: -8px 0 16px; }
.ml-pump-line.is-visible { display: block; }
```

- [ ] **Step 2 : Commit**

```bash
git add assets/mylab-product.css
git commit -m "feat(pompes): styles add-on pompe fiche produit"
```

---

## Task 4 : Markup add-on pompe (fiche produit)

**Files:**
- Modify: `sections/main-product.liquid` (~ligne 759, entre `#ml-qty-btns` et `.ml-pricing-card`)

- [ ] **Step 1 : Insérer le markup**

Après la fermeture du groupe paliers (`</div>` qui suit `#ml-qty-btns`, ligne 759) et avant `{%- comment -%} ====== AFFICHAGE PRIX ====== {%- endcomment -%}` (ligne 761), insérer :

```liquid
              {%- comment -%} ====== ADD-ON POMPE (révélé par JS si le format a une pompe) ====== {%- endcomment -%}
              <label class="ml-pump" id="ml-pump" hidden>
                <input type="checkbox" class="ml-pump__check" id="ml-pump-check">
                <span class="ml-pump__body">
                  <span class="ml-pump__title">Ajouter une pompe doseuse <span id="ml-pump-fmt"></span></span>
                  <span class="ml-pump__sub">1 pompe par flacon · s'aligne sur votre quantité</span>
                </span>
                <span class="ml-pump__price">+<span id="ml-pump-unit">—</span>&nbsp;€ <small>HT/u</small></span>
              </label>
```

Puis, juste après le `</div>` de fermeture de `.ml-pricing-card` (ligne 780), insérer la ligne récap :

```liquid
              <div class="ml-pump-line" id="ml-pump-line"></div>
```

- [ ] **Step 2 : Commit**

```bash
git add sections/main-product.liquid
git commit -m "feat(pompes): markup add-on pompe dans le bloc pricing"
```

---

## Task 5 : JS add-on pompe (fiche produit)

**Files:**
- Modify: `assets/mylab-product.js`

- [ ] **Step 1 : Étendre le contexte + révéler la case après chargement**

Dans `initBlock` (après `var product = results[1];`, ~ligne 241), ajouter la détection format + pompe. Remplacer le bloc qui suit `toggleNativeBlocks(root, false); ctx.tiers = tiers;` par :

```javascript
        toggleNativeBlocks(root, false);
        ctx.tiers = tiers;

        /* ── ADD-ON POMPE ── */
        var found = U.findProductEntry(handle, map);
        var format = found && found.size ? found.size : null;
        var pumpCfg = U.getPumpForFormat(format, map);
        if (pumpCfg) {
          U.loadPumpProduct(pumpCfg.handle).then(function (pump) {
            if (!pump) return;
            ctx.pump = pump;
            var label = q(root, '#ml-pump');
            var fmtEl = q(root, '#ml-pump-fmt');
            var unitEl = q(root, '#ml-pump-unit');
            if (fmtEl) fmtEl.textContent = format + ' ml';
            if (unitEl) unitEl.textContent = U.formatPriceCompact(pump.price);
            if (label) label.hidden = false;
            var check = q(root, '#ml-pump-check');
            if (check) check.addEventListener('change', function () {
              ctx.pumpChecked = check.checked;
              label.classList.toggle('is-checked', check.checked);
              updatePumpLine(ctx);
            });
          });
        }
```

- [ ] **Step 2 : Ajouter `updatePumpLine` + appeler dans `selectQty`**

Avant `function handleAddToCart` (~ligne 168), ajouter :

```javascript
  function updatePumpLine(ctx) {
    var lineEl = q(ctx.root, '#ml-pump-line');
    if (!lineEl) return;
    if (ctx.pumpChecked && ctx.pump && ctx.selectedQty) {
      var total = ctx.pump.price * ctx.selectedQty;
      lineEl.textContent = '+ ' + U.formatPrice(total) + ' de pompes ('
        + ctx.selectedQty + ' × ' + U.formatPrice(ctx.pump.price) + ')';
      lineEl.classList.add('is-visible');
    } else {
      lineEl.classList.remove('is-visible');
    }
  }
```

Dans `selectQty` (après `updateCartButton(ctx, qty);`, ligne 95), ajouter :

```javascript
    updatePumpLine(ctx);
```

- [ ] **Step 3 : Ajouter la pompe à l'ajout panier**

Dans `handleAddToCart`, remplacer le `body: JSON.stringify(...)` (ligne 178) par une construction d'items :

```javascript
    var items = [{ id: ctx.variantId, quantity: ctx.selectedQty }];
    if (ctx.pumpChecked && ctx.pump) {
      items.push({ id: ctx.pump.variantId, quantity: ctx.selectedQty });
    }

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ items: items })
    })
```

- [ ] **Step 4 : Push dev + QA fiche produit**

Run: `shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only assets/mylab-product.js,sections/main-product.liquid,assets/mylab-product.css,assets/ml-product-map.json,assets/ml-utils.js`

QA navigateur (thème dev, connecté en client `dossier-valide`) :
- Fiche **shampoing-nourrissant** (200 ml) : case « +0,50 €/u » visible ; cochée → la ligne `+ X,XX € de pompes (N × 0,50 €)` apparaît, la case se surligne.
- Changer le palier → la ligne pompe se recalcule.
- Bouton ajouter → le panier contient **2 lignes** (flacon + pompe), même quantité.
- Fiche **serum-finition-ultime** (50 ml) : **pas** de case pompe.

- [ ] **Step 5 : Commit**

```bash
git add assets/mylab-product.js
git commit -m "feat(pompes): fiche produit — case pompe + 2e ligne panier"
```

---

## Task 6 : Colonne pompe (Commande Express) — markup

**Files:**
- Modify: `sections/ml-quick-order.liquid` (header + `buildLinkedRow`)
- Modify: `snippets/ml-qo-row.liquid`

- [ ] **Step 1 : Ajouter l'en-tête de colonne**

Dans `sections/ml-quick-order.liquid`, dans le `<thead>` (ligne 400-406), insérer `<th>Pompe</th>` après `<th>Quantité</th>` :

```liquid
            <th>Quantité</th>
            <th class="ml-qo__pump-col">Pompe</th>
            <th>Prix unit. HT</th>
```

Et mettre à jour les `colspan="5"` des en-têtes de catégorie en **`colspan="6"`** (le JS génère ces en-têtes, voir Step 4).

- [ ] **Step 2 : Ajouter la cellule pompe dans `ml-qo-row.liquid`**

Dans `snippets/ml-qo-row.liquid`, après la cellule Quantité (`</td>` ligne 46) et avant `<td class="ml-qo__price">` (ligne 47), insérer :

```liquid
  <td class="ml-qo__check ml-qo__pump-cell" data-pump-cell>
    {%- comment -%} rempli par JS selon le format (case ou —) {%- endcomment -%}
  </td>
```

- [ ] **Step 3 : Ajouter les styles colonne**

Dans le `<style>` de `ml-quick-order.liquid` (après `.ml-qo__check`, ~ligne 210), ajouter :

```css
  .ml-qo__pump-cell { text-align: center; }
  .ml-qo__pump-cell input { width: 18px; height: 18px; accent-color: #111; cursor: pointer; }
  .ml-qo__pump-price { display: block; font-size: 1rem; color: #888; margin-top: 3px; white-space: nowrap; }
  .ml-qo__pump-na { color: #ccc; font-size: 1.2rem; }
```

- [ ] **Step 4 : Mettre à jour `buildLinkedRow` (lignes contenances liées)**

Dans `buildLinkedRow` (ligne 616), ajouter une cellule pompe entre la cellule quantité (`'<td>' + qtyCell + '</td>'`, ligne 643) et la cellule prix unit. Remplacer cette portion par :

```javascript
            + '<td>' + qtyCell + '</td>'
            + '<td class="ml-qo__check ml-qo__pump-cell" data-pump-cell></td>'
            + '<td class="ml-qo__price"><span data-qo-unit>—</span><div class="ml-qo__price-unit">€ HT</div></td>'
```

- [ ] **Step 5 : Commit**

```bash
git add sections/ml-quick-order.liquid snippets/ml-qo-row.liquid
git commit -m "feat(pompes): commande express — colonne pompe (markup)"
```

---

## Task 7 : Colonne pompe (Commande Express) — JS

**Files:**
- Modify: `sections/ml-quick-order.liquid` (script inline)

- [ ] **Step 1 : Charger les pompes et remplir les cellules par format**

Dans le `U.loadProductMap().then(function (map) {` (ligne 649), juste après `var gammeRows = {};`, ajouter un helper de remplissage de cellule pompe :

```javascript
          function fillPumpCell(tr, format) {
            var cell = tr.querySelector('[data-pump-cell]');
            if (!cell) return;
            var cfg = U.getPumpForFormat(format, map);
            if (!cfg) { cell.innerHTML = '<span class="ml-qo__pump-na" title="Pas de pompe pour ce format">—</span>'; return; }
            U.loadPumpProduct(cfg.handle).then(function (pump) {
              if (!pump) { cell.innerHTML = '<span class="ml-qo__pump-na">—</span>'; return; }
              tr.dataset.pumpVariant = pump.variantId;
              tr.dataset.pumpUnit = pump.price;
              cell.innerHTML = '<input type="checkbox" class="ml-qo__pump-check" data-pump aria-label="Ajouter une pompe">'
                + '<span class="ml-qo__pump-price">+' + U.formatPriceRaw(pump.price) + ' €/u</span>';
            });
          }
```

- [ ] **Step 2 : Appeler `fillPumpCell` sur chaque ligne**

Dans la boucle `rows.forEach` (après avoir déterminé la taille via `sizeEl`, ~ligne 677), récupérer le format et appeler `fillPumpCell`. Juste après le bloc `if (sizeEl && ...) { ... }`, ajouter :

```javascript
            var rowFormat = null;
            if (entry.sizes) {
              var fk = Object.keys(entry.sizes);
              for (var fi = 0; fi < fk.length; fi++) {
                if (entry.sizes[fk[fi]] === handle) { rowFormat = fk[fi]; break; }
              }
            }
            fillPumpCell(tr, rowFormat);
```

Et pour les lignes liées créées par `buildLinkedRow` (insérées via `insertAdjacentHTML`, ligne 717), après l'insertion, remplir leur cellule. Remplacer le `.then` de la promesse de fetch (ligne 716-718) par :

```javascript
                  .then(function (product) {
                    item.tr.insertAdjacentHTML('afterend', buildLinkedRow(product, linkedTierStr, size));
                    var newTr = item.tr.nextElementSibling;
                    if (newTr) fillPumpCell(newTr, size);
                  })
```

- [ ] **Step 3 : Inclure les pompes dans le total**

Dans `updateTotal` (ligne 489), à l'intérieur du `if (checkbox && checkbox.checked && ...)`, après `total += price * qty;`, ajouter le coût pompe et l'affichage. Remplacer le corps de `updateTotal` par :

```javascript
        function updateTotal() {
          var rows = table.querySelectorAll('tbody tr[data-variant-id]:not([style*="display:none"])');
          var total = 0;
          var pumpTotal = 0;
          var count = 0;
          rows.forEach(function (tr) {
            var select = tr.querySelector('[data-qo-qty]');
            var checkbox = tr.querySelector('input[type="checkbox"]:not([data-pump])');
            if (checkbox && checkbox.checked && parseInt(select.value, 10) > 0) {
              var opt = select.options[select.selectedIndex];
              var price = parseInt(opt.dataset.price, 10);
              var qty = parseInt(select.value, 10);
              total += price * qty;
              count++;
              var pumpCheck = tr.querySelector('[data-pump]');
              if (pumpCheck && pumpCheck.checked && tr.dataset.pumpUnit) {
                pumpTotal += parseInt(tr.dataset.pumpUnit, 10) * qty;
              }
            }
          });
          totalEl.textContent = U.formatPriceRaw(total + pumpTotal);
          countEl.textContent = count;
          submitBtn.disabled = count === 0;
          var pumpNote = document.getElementById('ml-qo-pumpnote');
          if (pumpNote) pumpNote.textContent = pumpTotal > 0 ? ('· dont ' + U.formatPriceRaw(pumpTotal) + ' € de pompes') : '';
        }
```

Ajouter l'élément note dans le footer markup (`sections/ml-quick-order.liquid`, après `<span class="ml-qo__total-ht">€ HT</span>` ligne 435) :

```liquid
          <span id="ml-qo-pumpnote" class="ml-qo__total-ht" style="color:#2D4A2D;"></span>
```

- [ ] **Step 4 : Déclencher `updateTotal` au coche de la pompe + pousser les items pompe**

L'event delegation `table.addEventListener('change', ...)` (ligne 510) doit recalculer le total quand une case pompe change. Après le bloc `if (e.target.matches('input[type="checkbox"]'))` (ligne 516-526), ajouter :

```javascript
          if (e.target.matches('[data-pump]')) {
            updateTotal();
          }
```

⚠️ Attention : le handler checkbox existant (ligne 516) matche **tous** les `input[type="checkbox"]`, donc aussi la case pompe. Restreindre ce handler à la case produit en remplaçant sa condition par `e.target.matches('input[type="checkbox"]:not([data-pump])')`.

Dans le `submitBtn` click (ligne 530), ajouter les items pompe. Remplacer la boucle de collecte par :

```javascript
          table.querySelectorAll('tbody tr[data-variant-id]').forEach(function (tr) {
            var checkbox = tr.querySelector('input[type="checkbox"]:not([data-pump])');
            var select = tr.querySelector('[data-qo-qty]');
            if (checkbox && checkbox.checked && parseInt(select.value, 10) > 0) {
              var qty = parseInt(select.value, 10);
              items.push({ id: parseInt(tr.dataset.variantId, 10), quantity: qty });
              var pumpCheck = tr.querySelector('[data-pump]');
              if (pumpCheck && pumpCheck.checked && tr.dataset.pumpVariant) {
                items.push({ id: parseInt(tr.dataset.pumpVariant, 10), quantity: qty });
              }
            }
          });
```

- [ ] **Step 5 : Push dev + QA commande express**

Run: `shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only sections/ml-quick-order.liquid,snippets/ml-qo-row.liquid`

QA navigateur (page commande-express, client `dossier-valide`) :
- Colonne « Pompe » présente ; lignes 200/500/1000 ml = case + prix ; lignes 50 ml = `—`.
- Cocher produit + pompe → total = produit + pompe, note « · dont X € de pompes » affichée.
- Cocher pompe SANS quantité produit → pas d'effet (la pompe suit la quantité produit).
- Ajouter au panier → panier contient produit **et** pompe à la même quantité.

- [ ] **Step 6 : Commit**

```bash
git add sections/ml-quick-order.liquid
git commit -m "feat(pompes): commande express — JS pompe (total + items panier)"
```

---

## Task 8 : QA panier + invalidation cache + clôture

- [ ] **Step 1 : Vérifier l'affichage drawer**

Avec une pompe au panier (depuis fiche OU commande express), ouvrir le mini-cart :
la pompe s'affiche comme ligne normale à son prix Shopify (0,50/1,00 €), le total est cohérent.
(Aucune modif drawer attendue — chemin `ml_has_non_tiered`.)

- [ ] **Step 2 : Invalidation cache section**

Dans Theme Editor (thème dev), re-save la page **Commande Express** (toggle published off/on si besoin) pour invalider le cache de rendu section (cf. feedback connu).

- [ ] **Step 3 : Vérifier la cohérence prix Odoo↔Shopify**

Confirmer que les variants pompes Shopify (0,50/0,50/1,00 €) matchent les `lst_price` Odoo (Task 0) — pas d'écart facture au moment de la sync commande.

- [ ] **Step 4 : Commit final éventuel + récap**

```bash
git add -A && git commit -m "chore(pompes): QA + ajustements finaux" || echo "rien à committer"
```

Ne **PAS** push live tant que Yoann n'a pas dit « PUSH LIVE ».

---

## Self-Review (couverture spec)

- ✅ Formats 200/500/1000, prix 0,50/0,50/1,00 → Task 0/1/2.
- ✅ Une pompe par format, réutilisation Odoo → Task 0.
- ✅ `_pumps` source de vérité + lecture prix en direct → Task 2.
- ✅ Quantité alignée + 2e ligne panier → Task 5 (fiche), Task 7 (express).
- ✅ Case fiche produit → Task 3/4/5. Colonne commande express → Task 6/7.
- ✅ Cart drawer inchangé (non-tiered) → Task 8 Step 1.
- ✅ Risque itérations map (`_pumps` sans `sizes`) → vérifié : `findProductEntry` et `main-product.liquid:723` skippent les entrées sans `sizes`.
- ✅ Dégradation sans JS : `<label hidden>` reste masqué ; colonne pompe vide (cellule remplie par JS).
- ✅ Rupture pompe : `loadPumpProduct` retourne null si `available===false` → case non affichée.
