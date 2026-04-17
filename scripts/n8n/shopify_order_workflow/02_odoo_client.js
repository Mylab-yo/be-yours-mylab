// Node type: Code — shared helper, not a standalone node.
// This block of code is prepended to other Code nodes that need to talk to Odoo.
// Exposes: odooExecute(model, method, args, kwargs) -> Promise<any>

const ODOO_URL = $env.ODOO_URL || 'https://odoo.startec-paris.com';
const ODOO_DB = $env.ODOO_DB || 'OdooYJ';
const ODOO_LOGIN = $env.ODOO_LOGIN || 'yoann@mylab-shop.com';
const ODOO_API_KEY = $env.ODOO_API_KEY;

if (!ODOO_API_KEY) {
  throw new Error('ODOO_API_KEY env variable not set');
}

// XML-RPC body builder for Odoo
function xmlrpcBody(method, params) {
  const escape = (s) => String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  function encode(v) {
    if (v === null || v === undefined) return '<value><nil/></value>';
    if (typeof v === 'boolean') return `<value><boolean>${v ? 1 : 0}</boolean></value>`;
    if (Number.isInteger(v)) return `<value><int>${v}</int></value>`;
    if (typeof v === 'number') return `<value><double>${v}</double></value>`;
    if (typeof v === 'string') return `<value><string>${escape(v)}</string></value>`;
    if (Array.isArray(v)) {
      return `<value><array><data>${v.map(encode).join('')}</data></array></value>`;
    }
    if (typeof v === 'object') {
      const members = Object.entries(v)
        .map(([k, val]) => `<member><name>${escape(k)}</name>${encode(val)}</member>`)
        .join('');
      return `<value><struct>${members}</struct></value>`;
    }
    throw new Error(`Unsupported type: ${typeof v}`);
  }
  const paramsXml = params.map((p) => `<param>${encode(p)}</param>`).join('');
  return `<?xml version="1.0"?><methodCall><methodName>${method}</methodName><params>${paramsXml}</params></methodCall>`;
}

// Minimal XML-RPC response parser (handles success + fault)
function parseXmlrpcResponse(xml) {
  if (xml.includes('<fault>')) {
    const faultMatch = xml.match(/<string>([^<]+)<\/string>/);
    throw new Error(`Odoo fault: ${faultMatch ? faultMatch[1] : xml.slice(0, 500)}`);
  }
  // Very simple value extractor — works for int, string, array-of-ints, bool
  function extract(fragment) {
    const intMatch = fragment.match(/<int>(-?\d+)<\/int>/);
    if (intMatch) return parseInt(intMatch[1], 10);
    const boolMatch = fragment.match(/<boolean>([01])<\/boolean>/);
    if (boolMatch) return boolMatch[1] === '1';
    const strMatch = fragment.match(/<string>([^<]*)<\/string>/);
    if (strMatch) return strMatch[1];
    const arrMatch = fragment.match(/<array><data>([\s\S]*)<\/data><\/array>/);
    if (arrMatch) {
      const items = [...arrMatch[1].matchAll(/<value>([\s\S]*?)<\/value>/g)];
      return items.map((m) => extract(m[1]));
    }
    return null;
  }
  const valueMatch = xml.match(/<param><value>([\s\S]*?)<\/value><\/param>/);
  return valueMatch ? extract(valueMatch[1]) : null;
}

// Authenticate once and cache UID for this execution
let cachedUid = null;
async function odooAuthenticate() {
  if (cachedUid !== null) return cachedUid;
  const body = xmlrpcBody('authenticate', [ODOO_DB, ODOO_LOGIN, ODOO_API_KEY, {}]);
  const resp = await this.helpers.httpRequest({
    method: 'POST',
    url: `${ODOO_URL}/xmlrpc/2/common`,
    headers: { 'Content-Type': 'text/xml' },
    body,
    returnFullResponse: false,
  });
  const uid = parseXmlrpcResponse(resp);
  if (!uid) throw new Error('Odoo authentication failed');
  cachedUid = uid;
  return uid;
}

async function odooExecute(model, method, args, kwargs = {}) {
  const uid = await odooAuthenticate.call(this);
  const body = xmlrpcBody('execute_kw', [ODOO_DB, uid, ODOO_API_KEY, model, method, args, kwargs]);
  const resp = await this.helpers.httpRequest({
    method: 'POST',
    url: `${ODOO_URL}/xmlrpc/2/object`,
    headers: { 'Content-Type': 'text/xml' },
    body,
    returnFullResponse: false,
  });
  return parseXmlrpcResponse(resp);
}

// ATTENTION: this file is designed to be copy-pasted at the top of each Code node
// that interacts with Odoo. The odooExecute function uses "this" (the node context)
// to access helpers.httpRequest, so call it as odooExecute.call(this, ...).
