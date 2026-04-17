// Node type: Code (Run Once for All Items)
// Formats the final log payload for the Google Sheets node
// Output: row to append

const input = $input.first().json;

const row = {
  timestamp: new Date().toISOString(),
  shopify_order_number: input.shopify_order_number || '',
  customer_email: input.customer_email || '',
  odoo_sale_order: input.order_number || '',
  odoo_sale_order_id: input.sale_order_id || '',
  status: input.status || '',
  picking_id: input.picking_id || '',
  unmatched_count: (input.unmatched_log || []).length,
  unmatched_details: (input.unmatched_log || [])
    .map((u) => `${u.sku || 'N/A'}:${u.title}`)
    .join(' | '),
};

return [{ json: row }];
