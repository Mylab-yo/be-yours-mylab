"""
Create n8n workflow: MY.LAB — Shopify Orders/Cancelled → Odoo SO Cancel
Run once to create the workflow (active=False). Yoann activates manually via UI.
"""
import urllib.request
import json
from pathlib import Path

N8N_KEY = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local").read_text(encoding="utf-8").splitlines()[39].strip()
N8N_BASE = "https://n8n.startec-paris.com"

# ── Node 1: Webhook ──────────────────────────────────────────────────────────
webhook_node = {
    "id": "webhook-order-cancelled",
    "name": "Webhook Shopify Order Cancelled",
    "type": "n8n-nodes-base.webhook",
    "typeVersion": 1,
    "position": [240, 300],
    "parameters": {
        "path": "shopify-order-cancelled",
        "httpMethod": "POST",
        "responseMode": "onReceived",
        "options": {"rawBody": True},
    },
}

# ── Node 2: Extract Order (mirrors Xj8T "Verify HMAC" — HMAC bypass) ─────────
extract_node = {
    "id": "extract-order",
    "name": "Extract Order",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [460, 300],
    "parameters": {
        "jsCode": r"""const input = $input.first().json;
// Shopify sends body under .body when rawBody is enabled, otherwise flat
const order = (input.body && typeof input.body === 'object' && input.body.id)
  ? input.body
  : input;
if (!order || !order.id) {
  throw new Error('Invalid Shopify payload - missing order.id. Keys: ' + Object.keys(input).join(', '));
}
return [{ json: { order } }];"""
    },
}

# ── Node 3: Odoo Search + Cancel ─────────────────────────────────────────────
odoo_cancel_code = r"""const ODOO_URL = $env.ODOO_URL || 'https://odoo.startec-paris.com';
const ODOO_DB = $env.ODOO_DB || 'OdooYJ';
const ODOO_UID = 8;
const ODOO_API_KEY = $env.ODOO_API_KEY || 'e6d35b4261b948664841075e8fffc3510c8db437';
const COMPANY_ID = 3;

/* ── XML-RPC helpers (same pattern as Xj8T5a7aO8drZk5v) ── */
function xmlrpcBody(method, params) {
  const escape = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  function encode(v) {
    if (v === null || v === undefined) return '<value><nil/></value>';
    if (typeof v === 'boolean') return '<value><boolean>' + (v ? 1 : 0) + '</boolean></value>';
    if (Number.isInteger(v)) return '<value><int>' + v + '</int></value>';
    if (typeof v === 'number') return '<value><double>' + v + '</double></value>';
    if (typeof v === 'string') return '<value><string>' + escape(v) + '</string></value>';
    if (Array.isArray(v)) return '<value><array><data>' + v.map(encode).join('') + '</data></array></value>';
    if (typeof v === 'object') {
      const members = Object.entries(v).map(([k, val]) => '<member><name>' + escape(k) + '</name>' + encode(val) + '</member>').join('');
      return '<value><struct>' + members + '</struct></value>';
    }
    throw new Error('Unsupported type: ' + typeof v);
  }
  const paramsXml = params.map((p) => '<param>' + encode(p) + '</param>').join('');
  return '<?xml version="1.0"?><methodCall><methodName>' + method + '</methodName><params>' + paramsXml + '</params></methodCall>';
}

function parseXmlrpcResponse(xml) {
  if (xml.includes('<fault>')) {
    const faultMatch = xml.match(/<string>([\s\S]*?)<\/string>/);
    throw new Error('Odoo fault: ' + (faultMatch ? faultMatch[1] : xml.slice(0, 500)));
  }
  const m = xml.match(/<params>\s*<param>\s*<value>([\s\S]*)<\/value>\s*<\/param>\s*<\/params>/);
  if (!m) return null;
  return parseValue(m[1].trim());
}

function parseValue(frag) {
  frag = frag.trim();
  if (frag.startsWith('<nil/>')) return null;
  const m = frag.match(/^<(int|i4|boolean|string|double|array|struct|dateTime\.iso8601|base64)>([\s\S]*)<\/\1>$/);
  if (!m) return frag;
  const tag = m[1], inner = m[2];
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
    while (rest.trim()) {
      const mem = rest.match(/^\s*<member>\s*<name>([^<]+)<\/name>\s*<value>([\s\S]*)/);
      if (!mem) break;
      const nameStr = mem[1];
      const after = mem[2];
      const closeTag = after.indexOf('<\/value>');
      if (closeTag === -1) break;
      const valueInner = after.slice(0, closeTag);
      result[nameStr] = parseValue(valueInner);
      rest = after.slice(closeTag + 8);
      const memClose = rest.indexOf('<\/member>');
      if (memClose !== -1) rest = rest.slice(memClose + 9);
    }
    return result;
  }
  return frag;
}

function splitValues(data) {
  const results = [];
  let i = 0;
  while (i < data.length) {
    const start = data.indexOf('<value>', i);
    if (start === -1) break;
    let depth = 1, pos = start + 7;
    while (pos < data.length && depth > 0) {
      if (data.startsWith('<value>', pos)) { depth++; pos += 7; }
      else if (data.startsWith('<\/value>', pos)) { depth--; if (depth > 0) pos += 8; }
      else pos++;
    }
    results.push(data.slice(start + 7, pos));
    i = pos + 8;
  }
  return results;
}

async function odooExecute(model, method, args, kwargs) {
  const body = xmlrpcBody('execute_kw', [ODOO_DB, ODOO_UID, ODOO_API_KEY, model, method, args, kwargs || {}]);
  const resp = await this.helpers.httpRequest({
    method: 'POST',
    url: ODOO_URL + '/xmlrpc/2/object',
    headers: { 'Content-Type': 'text/xml' },
    body: body,
    json: false,
  });
  return parseXmlrpcResponse(resp);
}

/* ── Main logic ── */
const input = $input.first().json;
const order = input.order || input;

// client_order_ref = String(order.id) — same convention as workflow Xj8T5a7aO8drZk5v (orders/paid)
const shopifyOrderId = String(order.id);
const shopifyOrderName = order.name || ('#' + (order.order_number || order.id));

const sos = await odooExecute.call(this, 'sale.order', 'search_read',
  [[['client_order_ref', '=', shopifyOrderId], ['company_id', '=', COMPANY_ID]]],
  { fields: ['id', 'name', 'state', 'partner_id'], limit: 1 });

if (!sos || sos.length === 0) {
  return [{ json: {
    result: 'no_match',
    shopify_order_id: shopifyOrderId,
    shopify_order_name: shopifyOrderName,
    note: 'Aucune SO Odoo trouvée avec ce client_order_ref'
  }}];
}

const so = sos[0];
const partnerName = Array.isArray(so.partner_id) ? so.partner_id[1] : (so.partner_id || 'inconnu');

if (so.state === 'cancel') {
  return [{ json: {
    result: 'already_cancelled',
    so_id: so.id,
    so_name: so.name,
    shopify_order_id: shopifyOrderId,
    shopify_order_name: shopifyOrderName,
    partner: partnerName,
    state: so.state
  }}];
}

if (so.state === 'done') {
  return [{ json: {
    result: 'skipped_done',
    so_id: so.id,
    so_name: so.name,
    shopify_order_id: shopifyOrderId,
    shopify_order_name: shopifyOrderName,
    partner: partnerName,
    state: so.state,
    note: 'SO en état done — impossible d\'annuler automatiquement, action manuelle requise'
  }}];
}

// Cancel the SO — releases all stock reservations
await odooExecute.call(this, 'sale.order', 'action_cancel', [[so.id]]);

return [{ json: {
  result: 'cancelled',
  so_id: so.id,
  so_name: so.name,
  shopify_order_id: shopifyOrderId,
  shopify_order_name: shopifyOrderName,
  partner: partnerName
}}];"""

odoo_cancel_node = {
    "id": "odoo-cancel-so",
    "name": "Odoo Cancel SO",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [680, 300],
    "parameters": {"jsCode": odoo_cancel_code},
}

# ── Full workflow payload ─────────────────────────────────────────────────────
workflow = {
    "name": "MY.LAB — Shopify Orders/Cancelled → Odoo SO Cancel",
    "nodes": [webhook_node, extract_node, odoo_cancel_node],
    "connections": {
        "Webhook Shopify Order Cancelled": {
            "main": [[{"node": "Extract Order", "type": "main", "index": 0}]]
        },
        "Extract Order": {
            "main": [[{"node": "Odoo Cancel SO", "type": "main", "index": 0}]]
        },
    },
    "settings": {"executionOrder": "v1"},
}

body = json.dumps(workflow, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(
    f"{N8N_BASE}/api/v1/workflows",
    data=body,
    headers={
        "X-N8N-API-KEY": N8N_KEY,
        "Content-Type": "application/json; charset=utf-8",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print("SUCCESS")
    print("ID:", result.get("id"))
    print("Name:", result.get("name"))
    print("Active:", result.get("active"))
    print("Nodes:", [n.get("name") for n in result.get("nodes", [])])
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode("utf-8", errors="replace")[:3000])
