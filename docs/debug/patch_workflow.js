const fs = require('fs');
const w = JSON.parse(fs.readFileSync('./docs/debug/wf-shopify-odoo.json', 'utf8'));

const n = w.nodes.find(x => x.name === 'Create Sale Order');
const oldVals = `const vals = { partner_id, partner_invoice_id: partner_id, partner_shipping_id: partner_id, client_order_ref: String(order.id), origin: \`Shopify #\${order.order_number || order.number || order.id}\`, company_id: COMPANY_ID, pricelist_id: PRICELIST_ID, order_line: order_lines };`;
const newVals = `const vals = { partner_id, partner_invoice_id: partner_id, partner_shipping_id: partner_id, client_order_ref: String(order.id), origin: \`Shopify #\${order.order_number || order.number || order.id}\`, company_id: COMPANY_ID, pricelist_id: PRICELIST_ID, sale_order_template_id: false, order_line: order_lines };`;

if (!n.parameters.jsCode.includes(oldVals)) {
  console.error('ERROR: anchor not found verbatim');
  process.exit(1);
}
if (n.parameters.jsCode.includes('sale_order_template_id')) {
  console.error('ALREADY PATCHED');
  process.exit(1);
}
n.parameters.jsCode = n.parameters.jsCode.replace(oldVals, newVals);
console.log('PATCH OK. Diff context:');
const idx = n.parameters.jsCode.indexOf('sale_order_template_id');
console.log(n.parameters.jsCode.slice(idx-50, idx+80));

// Build the update payload (n8n API requires: name, nodes, connections, settings)
const payload = {
  name: w.name,
  nodes: w.nodes,
  connections: w.connections,
  settings: w.settings || {}
};
fs.writeFileSync('./docs/debug/wf-shopify-odoo-patched.json', JSON.stringify(payload, null, 2));
console.log('payload written: docs/debug/wf-shopify-odoo-patched.json');
