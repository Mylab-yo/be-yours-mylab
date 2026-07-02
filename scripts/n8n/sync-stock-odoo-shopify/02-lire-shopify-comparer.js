// Node "Lire stocks Shopify et comparer" — mappe SKU->inventory_item_id, compare au stock Odoo.
// Testeurs : miroir du stock du produit classique parent (ils sont a 0 en propre dans Odoo).
// MIROIR EXACT : Shopify reflete Odoo a l'identique, 0 inclus (negatifs clamp a 0). Sûr depuis
// le backorder LIVE (a 0 : policy=continue -> "sur commande" ; deny/testeur -> "prevenez-moi").
// Voir sync_stock_from_odoo.py qui partage cette logique + memoire project_rupture_backorder.
// Secrets via $env. HTTP via this.helpers.httpRequest. inventory_levels en BATCHES (50 ids/req) + retry 429.
const SHOPIFY_TOKEN = $env.SHOPIFY_ACCESS_TOKEN;
const SHOPIFY_STORE = 'mylab-shop-3';
const LOCATION_ID = 107265032526;
const BASE = 'https://' + SHOPIFY_STORE + '.myshopify.com/admin/api/2024-01';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const doReq = (opts) => this.helpers.httpRequest(opts);

async function shopify(opts) {
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      return await doReq(opts);
    } catch (err) {
      const code = String(err.httpCode || err.statusCode || (err.response && err.response.status) || '');
      if (code === '429' && attempt < 3) { await sleep(800 * (attempt + 1)); continue; }
      throw err;
    }
  }
}

const odooProducts = $input.all().map((i) => i.json);

// SKU -> produit Odoo (pour resoudre le parent des testeurs)
const odooBySku = {};
for (const p of odooProducts) odooBySku[p.sku] = p;

// Mapping testeur -> produit classique parent.
// Match : tokens du testeur inclus dans ceux du classique (apres retrait 'coloristeur' + contenance),
// on prefere la contenance 200ml (sinon 50ml pour huile/serum-barbe).
const CONT = /-(\d+)-ml$/;
const PREF = [200, 50, 100, 250, 400, 500, 1000];
const classics = {};
for (const sku of Object.keys(odooBySku)) {
  const m = sku.match(CONT);
  if (m) {
    const core = new Set(sku.replace(CONT, '').split('-').filter((t) => t !== 'coloristeur'));
    classics[sku] = { core, size: parseInt(m[1], 10) };
  }
}
function parentOf(sku) {
  if (!sku.endsWith('-testeur')) return null;
  const tt = sku.slice(0, -('-testeur'.length)).split('-');
  let best = null, bestScore = null;
  for (const cs of Object.keys(classics)) {
    const { core, size } = classics[cs];
    if (!tt.every((t) => core.has(t))) continue;
    const prefIdx = PREF.indexOf(size) === -1 ? 99 : PREF.indexOf(size);
    const score = (core.size - tt.length) * 100 + prefIdx;
    if (bestScore === null || score < bestScore) { bestScore = score; best = cs; }
  }
  return best;
}

// 1) Tous les produits Shopify (pagination via header Link)
let allProducts = [];
let url = BASE + '/products.json?limit=250&fields=id,title,variants';
while (url) {
  const resp = await shopify({
    method: 'GET', url,
    headers: { 'X-Shopify-Access-Token': SHOPIFY_TOKEN },
    json: true, returnFullResponse: true,
  });
  const data = resp.body || {};
  if (data.products) allProducts.push(...data.products);
  const linkHeader = (resp.headers && (resp.headers.link || resp.headers.Link)) || '';
  const nextMatch = linkHeader.match(/<([^>]+)>;\s*rel="next"/);
  url = nextMatch ? nextMatch[1] : null;
  await sleep(300);
}

// 2) Mapping SKU -> inventory_item_id
const skuMap = {};
for (const p of allProducts) {
  for (const v of (p.variants || [])) {
    if (v.sku) skuMap[v.sku] = { inventory_item_id: v.inventory_item_id, variant_id: v.id, title: p.title };
  }
}

// 3) Produits Odoo matches + qty effective (testeur = stock du parent)
const matched = [];
for (const odoo of odooProducts) {
  const s = skuMap[odoo.sku];
  if (!s) continue;
  const parent = parentOf(odoo.sku);
  const eff = (parent && odooBySku[parent]) ? odooBySku[parent].odoo_qty : odoo.odoo_qty;
  matched.push({ sku: odoo.sku, name: odoo.name, inv: s.inventory_item_id, eff });
}

// 4) Stock Shopify actuel — BATCH de 50 inventory_item_ids, filtre location
const levelByItem = {};
for (let i = 0; i < matched.length; i += 50) {
  const batchIds = matched.slice(i, i + 50).map((m) => m.inv);
  const lvlData = await shopify({
    method: 'GET',
    url: BASE + '/inventory_levels.json?location_ids=' + LOCATION_ID + '&inventory_item_ids=' + batchIds.join(','),
    headers: { 'X-Shopify-Access-Token': SHOPIFY_TOKEN },
    json: true,
  });
  for (const l of (lvlData.inventory_levels || [])) {
    if (l.location_id === LOCATION_ID) levelByItem[String(l.inventory_item_id)] = l.available ?? 0;
  }
  await sleep(400);
}

// 5) Comparer — MIROIR EXACT : Shopify = Odoo (0 inclus), negatifs clamp a 0.
// Plus de filtre >0 : a 0 le backorder (continue) ou le prevenez-moi (deny) prend le relais.
const updates = [];
for (const m of matched) {
  const target = Math.max(0, m.eff);
  const currentShopifyQty = levelByItem[String(m.inv)] ?? 0;
  if (currentShopifyQty !== target) {
    updates.push({
      json: {
        sku: m.sku,
        name: m.name,
        inventory_item_id: m.inv,
        location_id: LOCATION_ID,
        odoo_qty: target,
        shopify_qty: currentShopifyQty,
        diff: target - currentShopifyQty,
      },
    });
  }
}

if (updates.length === 0) {
  return [{ json: { message: 'Aucune difference de stock', updates: 0 } }];
}

return updates;
