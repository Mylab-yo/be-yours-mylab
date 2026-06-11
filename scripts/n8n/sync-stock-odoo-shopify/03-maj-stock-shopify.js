// Node "MAJ stock Shopify" (mode runOnceForEachItem) — pousse odoo_qty vers Shopify inventory_levels/set.
// Secret via $env. HTTP via this.helpers.httpRequest (throw sur 4xx -> capture en success:false).
const item = $input.item.json;

if (item.message) return { json: item }; // Pas de MAJ necessaire

const SHOPIFY_TOKEN = $env.SHOPIFY_ACCESS_TOKEN;
const SHOPIFY_STORE = 'mylab-shop-3';

try {
  const data = await this.helpers.httpRequest({
    method: 'POST',
    url: 'https://' + SHOPIFY_STORE + '.myshopify.com/admin/api/2024-01/inventory_levels/set.json',
    headers: { 'X-Shopify-Access-Token': SHOPIFY_TOKEN, 'Content-Type': 'application/json' },
    body: {
      location_id: item.location_id,
      inventory_item_id: item.inventory_item_id,
      available: item.odoo_qty,
    },
    json: true,
  });
  return {
    json: {
      success: !data.errors,
      sku: item.sku,
      name: item.name,
      old_qty: item.shopify_qty,
      new_qty: item.odoo_qty,
      error: data.errors || null,
    },
  };
} catch (e) {
  return { json: { success: false, sku: item.sku, error: e.message } };
}
