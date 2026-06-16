const fs = require('fs');
const w = JSON.parse(fs.readFileSync('./docs/debug/wf-gestion-commandes.json', 'utf8'));
const node = w.nodes.find(x => x.name === 'Decrementer stock Odoo');

const newCode = `const data = $('Preparer donnees commande').first().json;
const stockItems = data.stock_items || [];
const ODOO_URL = data.odoo_url;
const ODOO_DB = data.odoo_db;
const ODOO_UID = data.odoo_uid;
const ODOO_API_KEY = data.odoo_api_key;
const LOCATION_ID = 28;

async function rpc(payload) {
  return await this.helpers.httpRequest({
    method: 'POST',
    url: ODOO_URL + '/jsonrpc',
    headers: { 'Content-Type': 'application/json' },
    body: payload,
    json: true,
  });
}

const results = [];
for (const item of stockItems) {
  const searchResult = await rpc.call(this, { jsonrpc: '2.0', id: 1, method: 'call', params: { service: 'object', method: 'execute_kw', args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, 'product.product', 'search_read', [[['default_code', '=', item.sku]]], {fields: ['id', 'name', 'qty_available'], limit: 1}] } });
  const products = searchResult.result || [];
  if (products.length === 0) { results.push({ sku: item.sku, status: 'SKU non trouve' }); continue; }
  const product = products[0];
  const newQty = Math.max(0, product.qty_available - item.quantity);

  const quantResult = await rpc.call(this, { jsonrpc: '2.0', id: 2, method: 'call', params: { service: 'object', method: 'execute_kw', args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, 'stock.quant', 'search_read', [[['product_id', '=', product.id], ['location_id', '=', LOCATION_ID]]], {fields: ['id', 'quantity', 'inventory_quantity'], limit: 1}] } });
  const quants = quantResult.result || [];

  if (quants.length > 0) {
    await rpc.call(this, { jsonrpc: '2.0', id: 3, method: 'call', params: { service: 'object', method: 'execute_kw', args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, 'stock.quant', 'write', [[quants[0].id], {inventory_quantity: newQty}]] } });
    await rpc.call(this, { jsonrpc: '2.0', id: 4, method: 'call', params: { service: 'object', method: 'execute_kw', args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, 'stock.quant', 'action_apply_inventory', [[quants[0].id]]] } });
  } else {
    const createResult = await rpc.call(this, { jsonrpc: '2.0', id: 5, method: 'call', params: { service: 'object', method: 'execute_kw', args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, 'stock.quant', 'create', [{product_id: product.id, location_id: LOCATION_ID, inventory_quantity: newQty}]] } });
    if (createResult.result) {
      await rpc.call(this, { jsonrpc: '2.0', id: 6, method: 'call', params: { service: 'object', method: 'execute_kw', args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, 'stock.quant', 'action_apply_inventory', [[createResult.result]]] } });
    }
  }
  results.push({ sku: item.sku, title: item.title, old: product.qty_available, new: newQty });
}

return [{ json: { stock_updates: results, count: results.length } }];`;

node.parameters.jsCode = newCode;

const allowedSettings = ['executionOrder','callerPolicy','errorWorkflow','saveDataErrorExecution','saveDataSuccessExecution','saveExecutionProgress','saveManualExecutions','executionTimeout','timezone'];
const cleanSettings = {};
for (const k of allowedSettings) if (w.settings && w.settings[k] !== undefined) cleanSettings[k] = w.settings[k];

const payload = { name: w.name, nodes: w.nodes, connections: w.connections, settings: cleanSettings };
fs.writeFileSync('./docs/debug/wf-gestion-commandes-patched.json', JSON.stringify(payload, null, 2));
console.log('payload written');
console.log('new code length:', newCode.length, 'old was:', /* approximative */);
