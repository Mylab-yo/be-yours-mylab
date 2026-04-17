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

// Depth-aware XML-RPC response parser — handles nested arrays + structs, tolerates whitespace
function parseXmlrpcResponse(xml) {
  if (xml.includes('<fault>')) {
    const faultMatch = xml.match(/<string>([\s\S]*?)<\/string>/);
    throw new Error(`Odoo fault: ${faultMatch ? faultMatch[1] : xml.slice(0, 500)}`);
  }
  const m = xml.match(/<params>\s*<param>\s*<value>([\s\S]*)<\/value>\s*<\/param>\s*<\/params>/);
  if (!m) return null;
  return parseValue(m[1].trim());
}

function parseValue(frag) {
  frag = frag.trim();
  if (frag.startsWith('<nil/>')) return null;
  const m = frag.match(/^<(int|i4|boolean|string|double|array|struct|dateTime\.iso8601|base64)>([\s\S]*)<\/\1>$/);
  if (!m) return frag; // implicit string
  const tag = m[1];
  const inner = m[2];
  if (tag === 'int' || tag === 'i4') return parseInt(inner, 10);
  if (tag === 'boolean') return inner === '1';
  if (tag === 'string') return inner;
  if (tag === 'double') return parseFloat(inner);
  if (tag === 'dateTime.iso8601') return inner;
  if (tag === 'base64') return inner;
  if (tag === 'array') {
    const dataMatch = inner.match(/<data>([\s\S]*)<\/data>/);
    if (!dataMatch) return [];
    return splitValues(dataMatch[1]).map(parseValue);
  }
  if (tag === 'struct') {
    const result = {};
    let rest = inner;
    while (true) {
      const mem = rest.match(/^\s*<member>\s*<name>([^<]+)<\/name>\s*<value>([\s\S]*)/);
      if (!mem) break;
      const nameStr = mem[1];
      const after = mem[2];
      const endIdx = findMatchingValueEnd(after);
      if (endIdx < 0) break;
      result[nameStr] = parseValue(after.slice(0, endIdx));
      const afterVal = after.slice(endIdx);
      const memEnd = afterVal.match(/<\/value>\s*<\/member>/);
      if (!memEnd) break;
      rest = afterVal.slice(memEnd.index + memEnd[0].length);
    }
    return result;
  }
  return null;
}

// Split <data> content into top-level <value>...</value> fragments (depth-aware)
function splitValues(data) {
  const out = [];
  let i = 0;
  while (i < data.length) {
    const start = data.indexOf('<value>', i);
    if (start < 0) break;
    const end = findMatchingValueEnd(data.slice(start + 7));
    if (end < 0) break;
    out.push(data.slice(start + 7, start + 7 + end).trim());
    i = start + 7 + end + '</value>'.length;
  }
  return out;
}

// Given a string starting just AFTER <value>, return index of matching </value>
function findMatchingValueEnd(s) {
  let depth = 1;
  let i = 0;
  while (i < s.length && depth > 0) {
    const openIdx = s.indexOf('<value>', i);
    const closeIdx = s.indexOf('</value>', i);
    if (closeIdx < 0) return -1;
    if (openIdx >= 0 && openIdx < closeIdx) {
      depth++;
      i = openIdx + 7;
    } else {
      depth--;
      if (depth === 0) return closeIdx;
      i = closeIdx + 8;
    }
  }
  return -1;
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
  if (!uid) throw new Error(`Odoo authentication failed (resp=${String(resp).slice(0, 300)})`);
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

// ATTENTION: this file is designed to be prepended to each Code node
// that interacts with Odoo. odooExecute uses "this" (the node context) for
// helpers.httpRequest, so call it as odooExecute.call(this, ...).
