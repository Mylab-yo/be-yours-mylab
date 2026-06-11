// Node "Lire stocks Shopify et comparer" — mappe SKU->inventory_item_id, compare au stock Odoo.
// Secrets via $env. HTTP via this.helpers.httpRequest. Appels inventory_levels BATCHES (50 ids/req)
// + filtre location + retry 429 pour rester sous le rate limit Shopify (2 req/s).
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

// 1) Recuperer tous les produits Shopify (pagination via header Link)
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

// 3) Produits Odoo matches dans Shopify
const matched = [];
for (const odoo of odooProducts) {
  const s = skuMap[odoo.sku];
  if (s) matched.push({ odoo, inv: s.inventory_item_id });
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

// 5) Comparer
const updates = [];
for (const { odoo, inv } of matched) {
  const currentShopifyQty = levelByItem[String(inv)] ?? 0;
  if (currentShopifyQty !== odoo.odoo_qty) {
    updates.push({
      json: {
        sku: odoo.sku,
        name: odoo.name,
        inventory_item_id: inv,
        location_id: LOCATION_ID,
        odoo_qty: odoo.odoo_qty,
        shopify_qty: currentShopifyQty,
        diff: odoo.odoo_qty - currentShopifyQty,
      },
    });
  }
}

if (updates.length === 0) {
  return [{ json: { message: 'Aucune difference de stock', updates: 0 } }];
}

return updates;
