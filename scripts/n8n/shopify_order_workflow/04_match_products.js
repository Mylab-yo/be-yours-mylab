// Node type: Code (Run Once for All Items)
// Input: { order, partner_id, ... }
// Output: { order, partner_id, order_lines, has_unmatched (bool), unmatched_log: [...] }
// Dependencies: 02_odoo_client.js prepended
// External data: PRODUCT_ALIASES dict inlined below (keep in sync with product_aliases.json)

const PRODUCT_ALIASES = {
  "brillance": "protecteur/protectrice de couleur",
  "blond polaire": "dejaunisseur platine",
  "platine": "dejaunisseur platine",
  "blond cuivré": "coloristeur cuivre",
  "cuivré": "coloristeur cuivre",
  "spray volume": "spray texturisant",
  "spray détox": "spray texturisant",
  "1 litre": "1000ml",
  "1l": "1000ml"
};

const SHIPPING_PRODUCT_ID = 2413; // Frais de livraison DPD

const input = $input.first().json;
const order = input.order;
const partner_id = input.partner_id;
const partner_notes = input.partner_notes || [];

const order_lines = [];
const unmatched_log = [];

// --- Helper: match one product line ---
async function matchOneProduct(sku, title) {
  // 1. Exact SKU match on product.product.default_code
  if (sku) {
    const ids = await odooExecute.call(this, 'product.product', 'search',
      [[['default_code', '=', sku]]], { limit: 1 });
    if (ids.length) return ids[0];
  }
  // 2. Alias lookup on title (normalized lowercase)
  const titleLower = (title || '').toLowerCase();
  for (const [alias, target] of Object.entries(PRODUCT_ALIASES)) {
    if (titleLower.includes(alias)) {
      const ids = await odooExecute.call(this, 'product.product', 'search',
        [[['name', '=ilike', `%${target}%`]]], { limit: 1 });
      if (ids.length) return ids[0];
    }
  }
  // 3. Fuzzy by title ilike
  if (title) {
    const ids = await odooExecute.call(this, 'product.product', 'search',
      [[['name', '=ilike', `%${title}%`]]], { limit: 1 });
    if (ids.length) return ids[0];
  }
  return null;
}

// --- Process each Shopify line_item ---
for (const item of order.line_items || []) {
  const productId = await matchOneProduct.call(this, item.sku, item.title);
  if (productId) {
    order_lines.push([0, 0, {
      product_id: productId,
      product_uom_qty: item.quantity,
      price_unit: parseFloat(item.price),  // Shopify source of truth
    }]);
  } else {
    const note = `⚠ NON MATCHÉ — SKU: ${item.sku || 'N/A'} — ${item.title} × ${item.quantity} @ ${item.price} €`;
    order_lines.push([0, 0, {
      display_type: 'line_note',
      name: note,
      product_uom_qty: 0,
      price_unit: 0,
    }]);
    unmatched_log.push({ sku: item.sku, title: item.title, qty: item.quantity, price: item.price });
  }
}

// --- Shipping line ---
const shippingLine = (order.shipping_lines || [])[0];
if (shippingLine && parseFloat(shippingLine.price) > 0) {
  order_lines.push([0, 0, {
    product_id: SHIPPING_PRODUCT_ID,
    product_uom_qty: 1,
    price_unit: parseFloat(shippingLine.price),
    name: `Frais de livraison — ${shippingLine.title || 'DPD'}`,
  }]);
}

const has_unmatched = unmatched_log.length > 0;

return [{
  json: {
    order,
    partner_id,
    partner_notes,
    order_lines,
    has_unmatched,
    unmatched_log,
  },
}];
