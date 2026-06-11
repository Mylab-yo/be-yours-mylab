// Node "Lire stocks Odoo" — lit qty_available de tous les produits stockables Odoo.
// Secrets via $env (ODOO_API_KEY). HTTP via this.helpers.httpRequest (fetch indispo dans le runner n8n).
const ODOO_URL = 'https://odoo.startec-paris.com';
const ODOO_DB = 'OdooYJ';
const ODOO_UID = 8;
const ODOO_API_KEY = $env.ODOO_API_KEY;

const result = await this.helpers.httpRequest({
  method: 'POST',
  url: ODOO_URL + '/jsonrpc',
  headers: { 'Content-Type': 'application/json' },
  body: {
    jsonrpc: '2.0', id: 1, method: 'call',
    params: {
      service: 'object', method: 'execute_kw',
      args: [ODOO_DB, ODOO_UID, ODOO_API_KEY, 'product.product', 'search_read',
        [[['is_storable', '=', true]]],
        { fields: ['id', 'default_code', 'name', 'qty_available', 'virtual_available'], limit: 500 }
      ]
    }
  },
  json: true
});

const products = (result && result.result) || [];

return products
  .filter(p => p.default_code)
  .map(p => ({ json: { sku: p.default_code, odoo_qty: Math.floor(p.qty_available), name: p.name } }));
