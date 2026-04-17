// Node type: Code (Run Once for All Items)
// Input: { order, partner_id, order_lines, has_unmatched, partner_notes, unmatched_log }
// Output: { sale_order_id, order_number, picking_id (if confirmed), status, unmatched_log }
// Dependencies: 02_odoo_client.js prepended

const COMPANY_ID = 3;
const PRICELIST_ID = 3;

const input = $input.first().json;
const order = input.order;
const partner_id = input.partner_id;
const order_lines = input.order_lines;
const has_unmatched = input.has_unmatched;
const partner_notes = input.partner_notes || [];
const unmatched_log = input.unmatched_log || [];

// --- Idempotence: check if already processed ---
const existingSOs = await odooExecute.call(this, 'sale.order', 'search_read',
  [[['client_order_ref', '=', String(order.id)], ['company_id', '=', COMPANY_ID]]],
  { fields: ['id', 'state', 'name'], limit: 1 });

if (existingSOs.length > 0) {
  const so = existingSOs[0];
  return [{
    json: {
      sale_order_id: so.id,
      order_number: so.name,
      status: 'already_processed',
      unmatched_log,
      message: `Order ${order.id} already processed as ${so.name} (state=${so.state})`,
    },
  }];
}

// --- Build sale.order vals ---
const vals = {
  partner_id,
  partner_invoice_id: partner_id,
  partner_shipping_id: partner_id,
  client_order_ref: String(order.id),
  origin: `Shopify #${order.order_number || order.number || order.id}`,
  company_id: COMPANY_ID,
  pricelist_id: PRICELIST_ID,
  order_line: order_lines,
};

// note: client-provided note from Shopify
if (order.note) {
  vals.note = order.note;
}

const saleOrderId = await odooExecute.call(this, 'sale.order', 'create', [vals]);

// --- Post any partner notes in chatter ---
if (partner_notes.length > 0) {
  const body = `<ul>${partner_notes.map((n) => `<li>${n}</li>`).join('')}</ul>`;
  await odooExecute.call(this, 'sale.order', 'message_post',
    [[saleOrderId]], { body, message_type: 'comment' });
}

let pickingId = null;
let status;

if (has_unmatched) {
  // --- Leave as draft + create mail.activity to fix products ---
  const activityTypeIds = await odooExecute.call(this, 'mail.activity.type', 'search',
    [[['category', '=', 'default']]], { limit: 1 });
  const activityTypeId = activityTypeIds.length ? activityTypeIds[0] : false;
  const modelId = (await odooExecute.call(this, 'ir.model', 'search',
    [[['model', '=', 'sale.order']]], { limit: 1 }))[0];
  await odooExecute.call(this, 'mail.activity', 'create', [{
    res_model_id: modelId,
    res_id: saleOrderId,
    activity_type_id: activityTypeId,
    summary: `⚠ Corriger produits non matchés (${unmatched_log.length})`,
    note: unmatched_log.map((u) => `• SKU ${u.sku || 'N/A'} — ${u.title} × ${u.qty}`).join('<br>'),
    user_id: 8,  // Yoann
  }]);
  status = 'draft_unmatched';
} else {
  // --- Confirm + retrieve picking ---
  await odooExecute.call(this, 'sale.order', 'action_confirm', [[saleOrderId]]);
  const soData = await odooExecute.call(this, 'sale.order', 'read',
    [[saleOrderId]], { fields: ['picking_ids', 'name'] });
  const pickingIds = soData[0].picking_ids || [];
  pickingId = pickingIds.length ? pickingIds[0] : null;
  status = 'confirmed';
}

const soName = (await odooExecute.call(this, 'sale.order', 'read',
  [[saleOrderId]], { fields: ['name'] }))[0].name;

return [{
  json: {
    sale_order_id: saleOrderId,
    order_number: soName,
    picking_id: pickingId,
    status,
    unmatched_log,
    shopify_order_number: order.order_number || order.number || order.id,
    customer_email: order.customer?.email,
  },
}];
