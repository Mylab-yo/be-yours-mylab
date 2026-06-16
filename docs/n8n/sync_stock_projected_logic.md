# Sync Stock Odoo→Shopify — Projected Stock Logic

**Designed**: 2026-05-20
**Status**: Design complete, NOT yet pushed (awaiting controller approval)
**Reference**: Stock MRP Odoo plan, Task 8

---

## Workflow Identity

| Field | Value |
|-------|-------|
| Workflow ID | `1AUxe9M9d9cNKz6W` |
| Name | Sync Stock Odoo → Shopify |
| Folder | Yo (`Z2t5yT17QDhgf2XO`) |
| Schedule | Every 5 hours (`scheduleTrigger`, interval=hours, hoursInterval=5) |
| Active | true |

---

## Goal of the Patch

Currently the workflow pushes **physical stock** (`qty_available` from `product.product`) directly to Shopify. This ignores bulk concentrate, packaging (flacons, bouchons) sitting in the warehouse that could be turned into finished products.

The patch replaces the pushed quantity with a **projected stock**:

```
stock_projete = qty_fini + floor(min(potential_from_bulk, potential_from_flacon, potential_from_bouchon))
```

Where:
- `qty_fini` = physical finished-product stock (current `qty_available`)
- `potential_from_bulk` = `(bulk_kg_available * mix_ratio) / poids_par_bouteille`
- `potential_from_flacon` = available stock of the matching flacon SKU
- `potential_from_bouchon` = available stock of the matching bouchon SKU

BOM data comes from `x_mylab_bom_summary` (custom field on `product.template`, Odoo id=12857), JSON string populated for 78 finished products.

---

## Current Workflow Structure (5 nodes)

```
[Schedule Trigger]          "Toutes les 5 heures"
        ↓
[Code] Lire stocks Odoo     id=0a182915 — reads product.product, returns {sku, odoo_qty, name}
        ↓
[Code] Lire stocks Shopify et comparer   id=305219f8 — fetches Shopify variants, compares qty
        ↓
[Code] MAJ stock Shopify    id=ed607151 — sets inventory_levels/set.json for each diff
```

Note: the `connections` JSON in n8n still uses key `"Toutes les 5 minutes"` (stale name from when
the trigger was previously set to 5 minutes) — the actual trigger fires every 5 hours.
The patch must preserve this stale key to avoid breaking the connection.

---

## Patch Design

### New data flow (6 nodes)

```
[Schedule Trigger]
        ↓
[Code] Lire stocks Odoo + BOM          ← MODIFIED (replaces "Lire stocks Odoo")
        ↓
[Code] Preload Bulk + Packaging stocks ← NEW node (inserted between Odoo fetch and Shopify compare)
        ↓
[Code] Calculer stock projeté          ← NEW node (projects stock per finished product)
        ↓
[Code] Lire stocks Shopify et comparer ← MODIFIED (use stock_projete instead of odoo_qty)
        ↓
[Code] MAJ stock Shopify               ← MODIFIED (send stock_projete as available qty)
```

---

## Constants

### MIX — ratio of bulk concentrate used per bottle size per family

```javascript
const MIX = {
  shampoings:    { "200": 0.77, "500": 0.07, "1000": 0.16 },
  masques:       { "200": 0.80, "400": 0.03, "1000": 0.17 },
  serums_huiles: { "50":  1.0  },
};
```

`MIX[family][contenance]` is the fraction of the total bulk-per-bottle that corresponds to this
contenance within its family. This accounts for the fact that bulk concentrate is shared across
sizes (e.g. for shampoings, 77% of batches go to 200ml, 7% to 500ml, 16% to 1000ml).

### POIDS_PAR_BOUTEILLE — kg of concentrate per filled bottle

```javascript
const POIDS_PAR_BOUTEILLE = {
  "50":   0.05,
  "200":  0.2,
  "400":  0.4,
  "500":  0.5,
  "1000": 1.0,
};
```

If `summary.bulk_kg` is provided in the BOM JSON and the contenance key is missing here,
`summary.bulk_kg` is used as fallback (default 0.2).

---

## Node Code: Modified "Lire stocks Odoo + BOM"

Replaces the existing `Lire stocks Odoo` node. Adds:
- `x_mylab_bom_summary` field from `product.template` (via `product_tmpl_id` join)
- Falls back to `fetch()` replacement with `this.helpers.httpRequest()` per project convention

```javascript
const ODOO_URL = 'https://odoo.startec-paris.com';
const ODOO_DB  = 'OdooYJ';
const ODOO_UID = 8;
const ODOO_API_KEY = 'e6d35b4261b948664841075e8fffc3510c8db437';

// Helper: JSON-RPC call to Odoo
async function odooCall(model, method, args, kwargs) {
  const body = JSON.stringify({
    jsonrpc: '2.0', id: 1, method: 'call',
    params: { service: 'object', method: 'execute_kw',
      args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, model, method, args, kwargs || {}] }
  });
  const resp = await this.helpers.httpRequest({
    method: 'POST',
    url: ODOO_URL + '/jsonrpc',
    headers: { 'Content-Type': 'application/json' },
    body: body,
    json: false
  });
  const parsed = JSON.parse(resp);
  if (parsed.error) throw new Error(JSON.stringify(parsed.error));
  return parsed.result;
}

// 1. Read all storable product variants with SKU and physical stock
const products = await odooCall.call(this, 'product.product', 'search_read',
  [[['is_storable', '=', true]]],
  { fields: ['id', 'default_code', 'name', 'qty_available', 'product_tmpl_id'], limit: 500 }
);

// 2. Read x_mylab_bom_summary from product.template for all template IDs
const tmplIds = [...new Set(products.map(p => p.product_tmpl_id[0]))];
const templates = await odooCall.call(this, 'product.template', 'search_read',
  [[['id', 'in', tmplIds]]],
  { fields: ['id', 'x_mylab_bom_summary'], limit: 500 }
);
const tmplMap = {};
for (const t of templates) tmplMap[t.id] = t.x_mylab_bom_summary || null;

// 3. Return finished products with BOM summary attached
return products
  .filter(p => p.default_code)
  .map(p => ({
    json: {
      sku:               p.default_code,
      odoo_qty:          Math.floor(p.qty_available),
      name:              p.name,
      product_tmpl_id:   p.product_tmpl_id[0],
      x_mylab_bom_summary: tmplMap[p.product_tmpl_id[0]] || null,
    }
  }));
```

---

## Node Code: NEW "Preload Bulk + Packaging Stocks"

Fetches ALL bulk and packaging SKU stocks in two batched Odoo calls (not one per product).

```javascript
const ODOO_URL = 'https://odoo.startec-paris.com';
const ODOO_DB  = 'OdooYJ';
const ODOO_UID = 8;
const ODOO_API_KEY = 'e6d35b4261b948664841075e8fffc3510c8db437';

async function odooCall(model, method, args, kwargs) {
  const body = JSON.stringify({
    jsonrpc: '2.0', id: 1, method: 'call',
    params: { service: 'object', method: 'execute_kw',
      args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, model, method, args, kwargs || {}] }
  });
  const resp = await this.helpers.httpRequest({
    method: 'POST',
    url: ODOO_URL + '/jsonrpc',
    headers: { 'Content-Type': 'application/json' },
    body: body,
    json: false
  });
  const parsed = JSON.parse(resp);
  if (parsed.error) throw new Error(JSON.stringify(parsed.error));
  return parsed.result;
}

const items = $input.all();

// Collect all unique bulk + packaging SKUs referenced in BOM summaries
const bulkSkus = new Set();
const packagingSkus = new Set();
for (const item of items) {
  const raw = item.json.x_mylab_bom_summary;
  if (!raw) continue;
  try {
    const s = JSON.parse(raw);
    if (s.bulk_sku)   bulkSkus.add(s.bulk_sku);
    if (s.flacon_sku) packagingSkus.add(s.flacon_sku);
    if (s.bouchon_sku) packagingSkus.add(s.bouchon_sku);
  } catch {}
}

// Fetch bulk stocks (product.product by default_code, storable)
const bulkStocksRaw = bulkSkus.size > 0
  ? await odooCall.call(this, 'product.product', 'search_read',
      [[['default_code', 'in', [...bulkSkus]], ['is_storable', '=', true]]],
      { fields: ['default_code', 'qty_available'], limit: 200 })
  : [];

// Fetch packaging stocks
const packagingStocksRaw = packagingSkus.size > 0
  ? await odooCall.call(this, 'product.product', 'search_read',
      [[['default_code', 'in', [...packagingSkus]], ['is_storable', '=', true]]],
      { fields: ['default_code', 'qty_available'], limit: 500 })
  : [];

const bulk_stocks     = {};
const packaging_stocks = {};
for (const p of bulkStocksRaw)     bulk_stocks[p.default_code]     = p.qty_available;
for (const p of packagingStocksRaw) packaging_stocks[p.default_code] = p.qty_available;

// Forward all items with maps attached
return items.map(item => ({
  json: {
    ...item.json,
    bulk_stocks,
    packaging_stocks,
  }
}));
```

---

## Node Code: NEW "Calculer stock projeté"

Computes `stock_projete` per finished product using the preloaded maps.

```javascript
const MIX = {
  shampoings:    { "200": 0.77, "500": 0.07, "1000": 0.16 },
  masques:       { "200": 0.80, "400": 0.03, "1000": 0.17 },
  serums_huiles: { "50":  1.0  },
};

const POIDS_PAR_BOUTEILLE = {
  "50":   0.05,
  "200":  0.2,
  "400":  0.4,
  "500":  0.5,
  "1000": 1.0,
};

return $input.all().map(item => {
  const data = item.json;
  const fini = data.odoo_qty || 0;

  const summaryRaw = data.x_mylab_bom_summary;
  if (!summaryRaw) {
    // No BOM: physical stock only
    return { json: { ...data, stock_projete: fini, projection_source: 'physical_only' } };
  }

  let summary;
  try { summary = JSON.parse(summaryRaw); }
  catch {
    return { json: { ...data, stock_projete: fini, projection_source: 'bom_parse_error' } };
  }

  const bulkKg  = (data.bulk_stocks  || {})[summary.bulk_sku]   || 0;
  const flacon  = (data.packaging_stocks || {})[summary.flacon_sku]  || 0;
  const bouchon = (data.packaging_stocks || {})[summary.bouchon_sku] || 0;

  const mix   = (MIX[summary.family] || {})[summary.contenance] || 0;
  const poids = POIDS_PAR_BOUTEILLE[summary.contenance] || summary.bulk_kg || 0.2;

  const potentielBulk = mix > 0 && poids > 0 ? (bulkKg * mix) / poids : 0;
  const potentiel     = Math.floor(Math.min(potentielBulk, flacon, bouchon));

  const stock_projete = fini + potentiel;

  return {
    json: {
      ...data,
      stock_projete,
      projection_source: 'computed',
      debug: { bulkKg, flacon, bouchon, mix, poids, potentielBulk, potentiel }
    }
  };
});
```

---

## Modified "Lire stocks Shopify et comparer"

**Change**: Replace `odoo.odoo_qty` with `odoo.stock_projete` in two places.

Before:
```javascript
if (currentShopifyQty !== odoo.odoo_qty) {
    updates.push({
      json: {
        ...
        odoo_qty: odoo.odoo_qty,
```

After:
```javascript
if (currentShopifyQty !== odoo.stock_projete) {
    updates.push({
      json: {
        ...
        odoo_qty: odoo.stock_projete,   // stock_projete pushed as the authoritative qty
```

Note: `odoo_qty` field name is kept for backward compat with the MAJ node that reads `item.odoo_qty`.

---

## Modified "MAJ stock Shopify"

**No code change needed** — this node already uses `item.odoo_qty` which the previous node now
populates with `stock_projete`.

---

## Connection Map After Patch

```json
{
  "Toutes les 5 minutes": {
    "main": [[{ "node": "Lire stocks Odoo + BOM", "type": "main", "index": 0 }]]
  },
  "Lire stocks Odoo + BOM": {
    "main": [[{ "node": "Preload Bulk + Packaging Stocks", "type": "main", "index": 0 }]]
  },
  "Preload Bulk + Packaging Stocks": {
    "main": [[{ "node": "Calculer stock projete", "type": "main", "index": 0 }]]
  },
  "Calculer stock projete": {
    "main": [[{ "node": "Lire stocks Shopify et comparer", "type": "main", "index": 0 }]]
  },
  "Lire stocks Shopify et comparer": {
    "main": [[{ "node": "MAJ stock Shopify", "type": "main", "index": 0 }]]
  }
}
```

---

## Key Caveats

1. **`fetch()` → `this.helpers.httpRequest()`**: All Odoo calls in the patched nodes use
   `this.helpers.httpRequest()` per project convention. The existing Shopify nodes still use
   `fetch()` (they already work — do not touch them during this patch).

2. **Stale connection key**: The n8n `connections` object still uses `"Toutes les 5 minutes"` as
   the trigger node key (the node was renamed but the key wasn't updated). The patch preserves
   this stale key to avoid breaking the wiring.

3. **`x_mylab_bom_summary` format**: The field stores a JSON string. Expected keys:
   `bulk_sku`, `bulk_kg`, `flacon_sku`, `bouchon_sku`, `family`, `contenance`.
   If the field is null or unparseable, `stock_projete` falls back to physical stock.

4. **No change to Shopify token or location_id** — both remain as-is.

5. **Run mode**: The MAJ node runs with "Run Once For Each Item" — no change needed.

---

## Dry-Run Test Plan

After push, execute the workflow manually and check output of "Calculer stock projete" for ~5
products. Verify:
- Products without `x_mylab_bom_summary` → `projection_source: "physical_only"`, `stock_projete = odoo_qty`
- Products with valid BOM → `projection_source: "computed"`, `debug` fields visible
- `stock_projete >= odoo_qty` (never negative projection)
- Shopify update payload uses `stock_projete` as `available`

---

## Files

| File | Purpose |
|------|---------|
| `docs/debug/backup_1AUxe9M9d9cNKz6W_2026-05-20.json` | Pre-patch workflow backup (gitignored) |
| `docs/n8n/sync_stock_projected_logic.md` | This file — patch design |
| `assets/mylab-product.js` | Client-side volume pricing (not affected) |
| `scripts/odoo/` | Odoo XML-RPC scripts (x_mylab_bom_summary populated separately) |
