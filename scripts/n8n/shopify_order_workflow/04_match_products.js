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

// --- Detect "TTC-as-HT" case: orders from wc_migration (legacy WP) reach
// Shopify with total_tax=0 even on French customers. The webhook's
// item.price is what the customer actually paid (TTC), not HT. If we push
// these prices to Odoo as HT and let Odoo add 20% VAT on top, the invoice
// total exceeds what the client paid (double-VAT effect).
// Fix: divide each Shopify price by (1 + tax_rate) so Odoo + VAT lands back
// on the original Shopify total.
const ship = order.shipping_address || order.billing_address || {};
const shipCountryCode = (ship.country_code || '').toUpperCase();
const customerTaxExempt = !!(order.customer && order.customer.tax_exempt);
const shopifyTotalTax = parseFloat(order.total_tax || '0');
const isWcMigration = (order.source_name || '') === 'wc_migration';
const priceIsActuallyTtc = (
  !customerTaxExempt &&
  shipCountryCode === 'FR' &&
  shopifyTotalTax === 0 &&
  isWcMigration
);
const TVA_DIVISOR = priceIsActuallyTtc ? 1.20 : 1.0;
if (priceIsActuallyTtc) {
  partner_notes.push(`⚠ Commande WP-migration sans TVA Shopify (total_tax=0). Prix divisés par 1.20 pour reconstituer le HT — total facture = total Shopify.`);
}

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
    // --- Discount: Shopify can emit per-line discount_allocations (one entry per
    // promo applied). Sum them, convert to a % of the line gross amount, and feed
    // Odoo's sale.order.line.discount (which Odoo applies before VAT).
    const grossLine = parseFloat(item.price) * (item.quantity || 0);
    let discountSum = 0;
    for (const da of (item.discount_allocations || [])) {
      discountSum += parseFloat(da.amount || 0);
    }
    const discountPct = (grossLine > 0 && discountSum > 0)
      ? Math.round((discountSum / grossLine) * 10000) / 100   // 2-decimal %
      : 0;
    const lineVals = {
      product_id: productId,
      product_uom_qty: item.quantity,
      price_unit: parseFloat(item.price) / TVA_DIVISOR,  // Shopify source of truth (÷ TVA if TTC)
    };
    if (discountPct > 0) {
      lineVals.discount = discountPct;
    }
    order_lines.push([0, 0, lineVals]);
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
// Shipping discounts (e.g. free-shipping promo codes) arrive as
// discount_allocations on the shipping_line, same as product lines.
// Without them, Odoo invoices the gross shipping price even when the
// customer paid 0 (discounted_price is the net the customer actually paid).
const shippingLine = (order.shipping_lines || [])[0];
if (shippingLine && parseFloat(shippingLine.price) > 0) {
  const shipGross = parseFloat(shippingLine.price);
  let shipDiscountSum = 0;
  for (const da of (shippingLine.discount_allocations || [])) {
    shipDiscountSum += parseFloat(da.amount || 0);
  }
  const shipDiscountPct = (shipDiscountSum > 0)
    ? Math.round((shipDiscountSum / shipGross) * 10000) / 100   // 2-decimal %
    : 0;
  const shipVals = {
    product_id: SHIPPING_PRODUCT_ID,
    product_uom_qty: 1,
    price_unit: shipGross / TVA_DIVISOR,
    name: `Frais de livraison — ${shippingLine.title || 'DPD'}`,
  };
  if (shipDiscountPct > 0) {
    shipVals.discount = shipDiscountPct;
  }
  order_lines.push([0, 0, shipVals]);
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
