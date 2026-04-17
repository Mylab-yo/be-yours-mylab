# Shopify Order → Odoo Sale Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Déployer un workflow n8n qui transforme chaque commande Shopify payée en `sale.order` Odoo confirmé, déclenchant automatiquement un `stock.picking` prêt à être traité avec le BL cartons.

**Architecture:** Webhook Shopify `orders/paid` → n8n (vérification HMAC + parsing) → Odoo XML-RPC (find/create partner, match products, create + confirm sale.order, create activity on picking) → log Google Sheet. Workflow développé via le n8n MCP Workflow SDK et déployé via `create_workflow_from_code`.

**Tech Stack:** n8n (Workflow SDK TypeScript), Odoo 18 XML-RPC (via JS `this.helpers.httpRequest()`), Shopify Admin webhooks + HMAC SHA256, Python 3.11+ (setup Odoo préalable).

**Spec :** [docs/superpowers/specs/2026-04-17-shopify-order-to-odoo-design.md](../specs/2026-04-17-shopify-order-to-odoo-design.md)

---

## File Structure

**Fichiers à créer :**

- `scripts/odoo/step06_ensure_fiscal_positions.py` — idempotent : crée les fiscal positions "Intracommunautaire" et "Export" si absentes dans Odoo
- `scripts/n8n/README.md` — guide d'utilisation des scripts n8n
- `scripts/n8n/shopify_order_workflow.md` — documentation du workflow (responsabilité de chaque node, payload type, logs)
- `docs/shopify-webhook-setup.md` — guide manuel pour Yoann (registration du webhook côté Shopify admin)

**Fichiers de code à créer pour le workflow n8n :**

Le workflow est déployé via l'outil MCP `mcp__claude_ai_n8n__create_workflow_from_code`, qui prend un blob de code TypeScript définissant tout le workflow (nodes + connexions). Pour la lisibilité et la diff-abilité git, on maintient **le corps JavaScript de chaque Code node dans des fichiers séparés** :

- `scripts/n8n/shopify_order_workflow/01_verify_hmac.js` — vérification signature Shopify + extraction payload
- `scripts/n8n/shopify_order_workflow/02_odoo_client.js` — helper inline Odoo XML-RPC (authenticate + execute_kw)
- `scripts/n8n/shopify_order_workflow/03_find_or_create_partner.js` — matching client par email + création
- `scripts/n8n/shopify_order_workflow/04_match_products.js` — SKU match + alias + line notes
- `scripts/n8n/shopify_order_workflow/05_create_sale_order.js` — création + confirmation sale.order
- `scripts/n8n/shopify_order_workflow/06_activity_on_picking.js` — création mail.activity sur le picking
- `scripts/n8n/shopify_order_workflow/07_log_row.js` — log ligne Google Sheet
- `scripts/n8n/shopify_order_workflow/workflow_definition.ts` — assemblage n8n SDK (imports les JS ci-dessus comme strings et définit nodes + connexions)
- `scripts/n8n/shopify_order_workflow/product_aliases.json` — dictionnaire alias partagé (copie du devis manuel)

**Responsabilités :**
- Les `.js` sont des snippets autonomes : reçoivent `$input` (payload n8n), retournent un output n8n item.
- Le `.ts` est l'unique point qui construit le workflow complet à partir des snippets et les envoie à n8n.
- Chaque `.js` est testable unitairement avec un payload de test injecté (Yoann peut coller le snippet dans un node n8n Code existant pour debug).

---

## Prérequis environnement

- [ ] **n8n MCP configuré** (normalement déjà ok — memory mentionne plusieurs workflows déployés via API)
- [ ] **Odoo credentials** : `.env.local` avec `ODOO_LOGIN`, `ODOO_URL`, `ODOO_DB`, `ODOO_API_KEY` (déjà setup dans le projet BL cartons)
- [ ] **Shopify admin access** : Yoann doit pouvoir créer un webhook dans Shopify (Settings → Notifications)
- [ ] **Google Sheets API access** : credentials n8n pour append row dans un sheet de log (si pas déjà setup)

---

## Task 1: Setup des fiscal positions Odoo

**Files:**
- Create: `scripts/odoo/step06_ensure_fiscal_positions.py`

- [ ] **Step 1: Écrire le script**

Créer `scripts/odoo/step06_ensure_fiscal_positions.py` :

```python
"""Ensure 'Intracommunautaire' and 'Export' fiscal positions exist in Odoo for company 3.

Idempotent: if they already exist, prints their ids and exits without changes.
"""
from scripts.odoo._client import search_read, create

COMPANY_ID = 3  # SARL STARTEC

POSITIONS = [
    {
        "name": "Intracommunautaire (0%)",
        "note": "Livraison intracommunautaire B2B avec numéro de TVA valide — exonération TVA art. 262 ter I du CGI",
        "auto_apply": False,
        "vat_required": True,
    },
    {
        "name": "Export (0%)",
        "note": "Export hors Union Européenne — exonération TVA art. 262 I du CGI",
        "auto_apply": False,
        "vat_required": False,
    },
]


def main():
    for fp in POSITIONS:
        existing = search_read(
            "account.fiscal.position",
            [("name", "=", fp["name"]), ("company_id", "=", COMPANY_ID)],
            ["id", "name"],
            limit=1,
        )
        if existing:
            print(f"Fiscal position '{fp['name']}' exists (id={existing[0]['id']}), skipping")
            continue
        new_id = create("account.fiscal.position", {
            "name": fp["name"],
            "note": fp["note"],
            "auto_apply": fp["auto_apply"],
            "vat_required": fp["vat_required"],
            "company_id": COMPANY_ID,
        })
        print(f"Created fiscal position '{fp['name']}' (id={new_id})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Exécuter**

```bash
cd d:/be-yours-mylab && python -m scripts.odoo.step06_ensure_fiscal_positions
```

Expected (premier passage) :
```
Created fiscal position 'Intracommunautaire (0%)' (id=XX)
Created fiscal position 'Export (0%)' (id=YY)
```

Noter les IDs retournés — ils seront utilisés dans le workflow n8n (tâche 10).

- [ ] **Step 3: Commit**

```bash
git add scripts/odoo/step06_ensure_fiscal_positions.py
git commit -m "Add script to ensure Intracommunautaire + Export fiscal positions"
```

---

## Task 2: [USER] Registration du webhook Shopify

**Files:**
- Create: `docs/shopify-webhook-setup.md`

- [ ] **Step 1: Écrire le guide de setup Shopify**

Créer `docs/shopify-webhook-setup.md` :

```markdown
# Shopify Webhook Setup — orders/paid → n8n

## Création du webhook

1. Ouvrir Shopify admin : https://mylab-shop-3.myshopify.com/admin
2. Settings (roue crantée en bas à gauche) → Notifications → scroll vers "Webhooks"
3. Cliquer "Create webhook"
4. Remplir :
   - **Event** : `Order payment` (équivalent `orders/paid`)
   - **Format** : `JSON`
   - **URL** : `https://n8n.startec-paris.com/webhook/mylab-shopify-order`
   - **API version** : la plus récente stable disponible
5. Enregistrer

## Récupération du HMAC secret

Après création du premier webhook de la boutique, Shopify affiche une section "Webhook signing secret" avec une valeur style `shpss_xxxxxxxxxxxxx`.

**Copier cette valeur** — elle servira à vérifier la signature HMAC SHA256 côté n8n.

## Stockage côté n8n

Dans n8n → Credentials → New credential → "Generic Credential Type" (ou custom) :
- Nom : `Shopify Webhook HMAC Secret`
- Field : `secret` = valeur du webhook signing secret Shopify

Ou, plus simple : stocker en variable d'environnement n8n (`SHOPIFY_WEBHOOK_SECRET` dans le docker-compose/env file sur le VPS), et y accéder via `$env.SHOPIFY_WEBHOOK_SECRET` dans les Code nodes.

## Test de base

Une fois le webhook créé, Shopify permet d'envoyer un test :
- Sur la ligne du webhook créé → "Send test notification"
- n8n doit recevoir un POST avec un payload d'exemple (une fausse commande).
- Vérifier dans les logs n8n que le workflow s'exécute et log correctement (même si il "skip" parce que la fake commande a un id étrange).
```

- [ ] **Step 2: Action manuelle de Yoann**

Yoann exécute les étapes ci-dessus. Il notera :
- URL exacte du webhook créé
- Webhook signing secret (value `shpss_...`)
- Qu'il préfère le stocker en credential n8n ou en variable d'environnement VPS

- [ ] **Step 3: Commit**

```bash
git add docs/shopify-webhook-setup.md
git commit -m "Add Shopify webhook setup guide"
```

---

## Task 3: Explorer le n8n SDK

**Files:** aucun (action d'exploration via MCP).

- [ ] **Step 1: Lire la référence SDK**

Appeler le tool MCP :
```
mcp__claude_ai_n8n__get_sdk_reference(sections=["guidelines", "design", "core"])
```

Noter :
- Syntaxe pour définir un workflow (nodes, connections)
- Format des Code nodes (jsCode comme string, ou function)
- Comment passer des données entre nodes

- [ ] **Step 2: Découvrir les nodes nécessaires**

```
mcp__claude_ai_n8n__search_nodes(queries=[
    "webhook",
    "code",
    "if",
    "http request",
    "google sheets"
])
```

Identifier les node IDs / types exacts (ex: `n8n-nodes-base.webhook`, `n8n-nodes-base.code`, etc.).

- [ ] **Step 3: Obtenir les types détaillés**

```
mcp__claude_ai_n8n__get_node_types(node_ids=[
    "<webhook type id>",
    "<code type id>",
    "<if type id>",
    "<http request type id>",
    "<google sheets append type id>"
])
```

Conserver les schémas en référence pour la tâche 10 (assemblage).

---

## Task 4: Code HMAC verify + payload extraction

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/01_verify_hmac.js`

- [ ] **Step 1: Écrire le snippet JS**

Créer `scripts/n8n/shopify_order_workflow/01_verify_hmac.js` :

```javascript
// Node type: Code (Run Once for All Items)
// Input: webhook trigger output (body + headers)
// Output: { order } — the parsed Shopify order object
// Env: SHOPIFY_WEBHOOK_SECRET

const crypto = require('crypto');

// Grab the raw body string + Shopify HMAC header
const rawBody = $input.first().json.body !== undefined
  ? JSON.stringify($input.first().json.body)
  : $input.first().json; // depending on n8n webhook config, body may be root

const headers = $input.first().json.headers || {};
const hmacHeader = headers['x-shopify-hmac-sha256'];

if (!hmacHeader) {
  throw new Error('Missing X-Shopify-Hmac-Sha256 header');
}

const secret = $env.SHOPIFY_WEBHOOK_SECRET;
if (!secret) {
  throw new Error('SHOPIFY_WEBHOOK_SECRET env variable not set');
}

const computed = crypto
  .createHmac('sha256', secret)
  .update(rawBody, 'utf8')
  .digest('base64');

const valid = crypto.timingSafeEqual(
  Buffer.from(computed, 'base64'),
  Buffer.from(hmacHeader, 'base64')
);

if (!valid) {
  throw new Error(`HMAC verification failed (computed=${computed}, header=${hmacHeader})`);
}

// Parse the order body and return it as structured output
const order = typeof rawBody === 'string' ? JSON.parse(rawBody) : rawBody;

return [{ json: { order } }];
```

- [ ] **Step 2: Commit**

```bash
mkdir -p scripts/n8n/shopify_order_workflow
git add scripts/n8n/shopify_order_workflow/01_verify_hmac.js
git commit -m "Add HMAC verification + Shopify payload extraction snippet"
```

---

## Task 5: Helper Odoo XML-RPC (JS inline)

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/02_odoo_client.js`

- [ ] **Step 1: Écrire le helper**

Créer `scripts/n8n/shopify_order_workflow/02_odoo_client.js` :

```javascript
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
```

- [ ] **Step 2: Commit**

```bash
git add scripts/n8n/shopify_order_workflow/02_odoo_client.js
git commit -m "Add Odoo XML-RPC helper snippet for n8n Code nodes"
```

---

## Task 6: Find or create partner

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/03_find_or_create_partner.js`

- [ ] **Step 1: Écrire le snippet**

Créer `scripts/n8n/shopify_order_workflow/03_find_or_create_partner.js` :

```javascript
// Node type: Code (Run Once for All Items)
// Input: { order } from previous node
// Output: { order, partner_id, partner_created (bool), partner_notes: [...] }
// Dependencies: 02_odoo_client.js must be prepended

// ---- EU country codes for fiscal position detection ----
const EU_COUNTRIES = new Set([
  'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU',
  'IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE'
]);

// ---- Fiscal position IDs (from Task 1 output — to be hardcoded after initial deployment) ----
const FP_INTRACOM_ID = parseInt($env.ODOO_FP_INTRACOM_ID || '0', 10);
const FP_EXPORT_ID = parseInt($env.ODOO_FP_EXPORT_ID || '0', 10);

const { order } = $input.first().json;
const email = (order.customer?.email
  || order.billing_address?.email
  || order.shipping_address?.email
  || `shopify-order-${order.id}@placeholder.mylab-shop.com`
).toLowerCase();

const ship = order.shipping_address || order.billing_address || {};
const partner_notes = [];

// 1. Search existing partner
const existingIds = await odooExecute.call(this, 'res.partner', 'search',
  [[['email', '=ilike', email]]], { limit: 1 });

let partnerId;
let partnerCreated = false;

if (existingIds.length > 0) {
  partnerId = existingIds[0];
  // Compare Shopify shipping address to Odoo partner to flag differences
  const [odooPartner] = await odooExecute.call(this, 'res.partner', 'read',
    [[partnerId]], { fields: ['street', 'zip', 'city', 'country_id'] });
  const odooStreet = odooPartner.street || '';
  const shopStreet = ship.address1 || '';
  if (odooStreet && shopStreet && odooStreet.trim().toLowerCase() !== shopStreet.trim().toLowerCase()) {
    partner_notes.push(`ℹ Adresse livraison Shopify (${shopStreet}, ${ship.zip} ${ship.city}) diffère de l'adresse Odoo (${odooStreet}, ${odooPartner.zip} ${odooPartner.city})`);
  }
} else {
  // 2. Lookup country_id by ISO code
  const countryCode = (ship.country_code || 'FR').toUpperCase();
  const countryIds = await odooExecute.call(this, 'res.country', 'search',
    [[['code', '=', countryCode]]], { limit: 1 });
  const countryId = countryIds.length ? countryIds[0] : false;

  // 3. Fiscal position detection
  const vat = order.customer?.tax_exempt
    ? null
    : (order.billing_address?.company_vat_number || null);
  let fiscalPositionId = false;
  if (countryCode === 'FR') {
    fiscalPositionId = false; // default TVA 20%
  } else if (EU_COUNTRIES.has(countryCode) && vat) {
    fiscalPositionId = FP_INTRACOM_ID || false;
  } else {
    fiscalPositionId = FP_EXPORT_ID || false;
  }

  // 4. Build partner name
  const company = ship.company;
  const name = company
    ? company
    : `${ship.first_name || order.customer?.first_name || ''} ${ship.last_name || order.customer?.last_name || ''}`.trim() || email;

  const vals = {
    name,
    is_company: !!company,
    email,
    phone: ship.phone || order.customer?.phone || false,
    street: ship.address1 || false,
    street2: ship.address2 || false,
    zip: ship.zip || false,
    city: ship.city || false,
    country_id: countryId,
    property_account_position_id: fiscalPositionId,
    company_id: 3,
    customer_rank: 1,
  };
  if (vat) vals.vat = vat;

  partnerId = await odooExecute.call(this, 'res.partner', 'create', [vals]);
  partnerCreated = true;
}

return [{ json: { order, partner_id: partnerId, partner_created: partnerCreated, partner_notes } }];
```

- [ ] **Step 2: Commit**

```bash
git add scripts/n8n/shopify_order_workflow/03_find_or_create_partner.js
git commit -m "Add partner matching + creation with fiscal position detection"
```

---

## Task 7: Match products + build order lines

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/04_match_products.js`
- Create: `scripts/n8n/shopify_order_workflow/product_aliases.json`

- [ ] **Step 1: Créer le fichier d'alias**

Créer `scripts/n8n/shopify_order_workflow/product_aliases.json` (copie du dictionnaire du devis manuel, à adapter au besoin) :

```json
{
  "brillance": "protecteur/protectrice de couleur",
  "blond polaire": "dejaunisseur platine",
  "platine": "dejaunisseur platine",
  "blond cuivré": "coloristeur cuivre",
  "cuivré": "coloristeur cuivre",
  "spray volume": "spray texturisant",
  "spray détox": "spray texturisant",
  "1 litre": "1000ml",
  "1l": "1000ml"
}
```

- [ ] **Step 2: Écrire le snippet matching**

Créer `scripts/n8n/shopify_order_workflow/04_match_products.js` :

```javascript
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
```

- [ ] **Step 3: Commit**

```bash
git add scripts/n8n/shopify_order_workflow/04_match_products.js scripts/n8n/shopify_order_workflow/product_aliases.json
git commit -m "Add product matching snippet with alias fallback + shipping line"
```

---

## Task 8: Create sale.order + optional confirm

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/05_create_sale_order.js`

- [ ] **Step 1: Écrire le snippet**

Créer `scripts/n8n/shopify_order_workflow/05_create_sale_order.js` :

```javascript
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
```

- [ ] **Step 2: Commit**

```bash
git add scripts/n8n/shopify_order_workflow/05_create_sale_order.js
git commit -m "Add sale.order creation + conditional confirmation"
```

---

## Task 9: Create mail.activity on picking

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/06_activity_on_picking.js`

- [ ] **Step 1: Écrire le snippet**

Créer `scripts/n8n/shopify_order_workflow/06_activity_on_picking.js` :

```javascript
// Node type: Code (Run Once for All Items)
// Only runs if picking_id is present (confirmed sale.order)
// Input: previous output
// Output: same + activity_id

const input = $input.first().json;
const { picking_id, shopify_order_number, customer_email, order_number } = input;

if (!picking_id) {
  // Pass-through: no activity to create (draft case)
  return [{ json: { ...input, activity_id: null } }];
}

const pickingModelId = (await odooExecute.call(this, 'ir.model', 'search',
  [[['model', '=', 'stock.picking']]], { limit: 1 }))[0];

const activityTypeIds = await odooExecute.call(this, 'mail.activity.type', 'search',
  [[['category', '=', 'default']]], { limit: 1 });
const activityTypeId = activityTypeIds.length ? activityTypeIds[0] : false;

const activityId = await odooExecute.call(this, 'mail.activity', 'create', [{
  res_model_id: pickingModelId,
  res_id: picking_id,
  activity_type_id: activityTypeId,
  summary: `Répartir en cartons et imprimer BL — Shopify #${shopify_order_number}`,
  note: `Commande Shopify #${shopify_order_number} — ${customer_email || 'email manquant'} — sale.order ${order_number}.<br>Cliquer "Répartir en cartons" puis imprimer "Bon de livraison MyLab".`,
  user_id: 8,
}]);

return [{ json: { ...input, activity_id: activityId } }];
```

- [ ] **Step 2: Commit**

```bash
git add scripts/n8n/shopify_order_workflow/06_activity_on_picking.js
git commit -m "Add mail.activity on picking creation"
```

---

## Task 10: Log row to Google Sheet

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/07_log_row.js`

- [ ] **Step 1: Écrire le snippet**

Créer `scripts/n8n/shopify_order_workflow/07_log_row.js` :

```javascript
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
```

**Note**: le node suivant sera un "Google Sheets: Append Row" n8n standard qui reçoit ce JSON et append dans un sheet dédié (spreadsheet ID + worksheet name à configurer par Yoann).

- [ ] **Step 2: Commit**

```bash
git add scripts/n8n/shopify_order_workflow/07_log_row.js
git commit -m "Add log row formatter for Google Sheets append"
```

---

## Task 11: Assemble the workflow (n8n SDK)

**Files:**
- Create: `scripts/n8n/shopify_order_workflow/workflow_definition.ts`

- [ ] **Step 1: Lire les 7 snippets `.js` comme strings**

Le workflow TypeScript doit embarquer tous les snippets comme `jsCode` sur des nodes Code. Structure attendue (pseudocode) :

```typescript
import * as fs from 'fs';
import * as path from 'path';

const dir = __dirname; // or path to shopify_order_workflow/

const hmacCode = fs.readFileSync(path.join(dir, '01_verify_hmac.js'), 'utf-8');
const odooClient = fs.readFileSync(path.join(dir, '02_odoo_client.js'), 'utf-8');
const partnerCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '03_find_or_create_partner.js'), 'utf-8');
const productsCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '04_match_products.js'), 'utf-8');
const saleOrderCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '05_create_sale_order.js'), 'utf-8');
const activityCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '06_activity_on_picking.js'), 'utf-8');
const logCode = fs.readFileSync(path.join(dir, '07_log_row.js'), 'utf-8');
```

- [ ] **Step 2: Écrire le workflow SDK**

Créer `scripts/n8n/shopify_order_workflow/workflow_definition.ts` :

```typescript
// n8n Workflow SDK definition for MY.LAB - Shopify → Commande Odoo
// Deployed via mcp__claude_ai_n8n__create_workflow_from_code

import * as fs from 'fs';
import * as path from 'path';

const dir = path.join(__dirname);

const hmacCode = fs.readFileSync(path.join(dir, '01_verify_hmac.js'), 'utf-8');
const odooClient = fs.readFileSync(path.join(dir, '02_odoo_client.js'), 'utf-8');
const partnerCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '03_find_or_create_partner.js'), 'utf-8');
const productsCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '04_match_products.js'), 'utf-8');
const saleOrderCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '05_create_sale_order.js'), 'utf-8');
const activityCode = odooClient + '\n\n' + fs.readFileSync(path.join(dir, '06_activity_on_picking.js'), 'utf-8');
const logCode = fs.readFileSync(path.join(dir, '07_log_row.js'), 'utf-8');

export const workflow = {
  name: 'MY.LAB - Shopify → Commande Odoo',
  nodes: [
    {
      id: 'webhook',
      name: 'Webhook Shopify',
      type: 'n8n-nodes-base.webhook',
      typeVersion: 2,
      position: [240, 300],
      webhookId: 'mylab-shopify-order',
      parameters: {
        path: 'mylab-shopify-order',
        httpMethod: 'POST',
        responseMode: 'onReceived',
        options: { rawBody: true },
      },
    },
    {
      id: 'verify_hmac',
      name: 'Verify HMAC',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [460, 300],
      parameters: { language: 'javaScript', jsCode: hmacCode },
    },
    {
      id: 'partner',
      name: 'Find/Create Partner',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [680, 300],
      parameters: { language: 'javaScript', jsCode: partnerCode },
    },
    {
      id: 'products',
      name: 'Match Products',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [900, 300],
      parameters: { language: 'javaScript', jsCode: productsCode },
    },
    {
      id: 'sale_order',
      name: 'Create Sale Order',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [1120, 300],
      parameters: { language: 'javaScript', jsCode: saleOrderCode },
    },
    {
      id: 'activity',
      name: 'Activity on Picking',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [1340, 300],
      parameters: { language: 'javaScript', jsCode: activityCode },
    },
    {
      id: 'format_log',
      name: 'Format Log Row',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [1560, 300],
      parameters: { language: 'javaScript', jsCode: logCode },
    },
    // Google Sheets Append node — user configures credentials + spreadsheet manually
    {
      id: 'log_sheet',
      name: 'Append Log Sheet',
      type: 'n8n-nodes-base.googleSheets',
      typeVersion: 4,
      position: [1780, 300],
      parameters: {
        operation: 'append',
        resource: 'sheet',
        // Placeholder: Yoann fills in spreadsheetId + sheetName after deployment
        spreadsheetId: '={{ $env.MYLAB_LOG_SHEET_ID }}',
        sheetName: 'Shopify Orders Log',
        options: {},
      },
    },
  ],
  connections: {
    'Webhook Shopify': { main: [[{ node: 'Verify HMAC', type: 'main', index: 0 }]] },
    'Verify HMAC': { main: [[{ node: 'Find/Create Partner', type: 'main', index: 0 }]] },
    'Find/Create Partner': { main: [[{ node: 'Match Products', type: 'main', index: 0 }]] },
    'Match Products': { main: [[{ node: 'Create Sale Order', type: 'main', index: 0 }]] },
    'Create Sale Order': { main: [[{ node: 'Activity on Picking', type: 'main', index: 0 }]] },
    'Activity on Picking': { main: [[{ node: 'Format Log Row', type: 'main', index: 0 }]] },
    'Format Log Row': { main: [[{ node: 'Append Log Sheet', type: 'main', index: 0 }]] },
  },
  settings: {
    executionOrder: 'v1',
    saveExecutionProgress: true,
    saveDataSuccessExecution: 'all',
    saveDataErrorExecution: 'all',
  },
};
```

- [ ] **Step 3: Commit**

```bash
git add scripts/n8n/shopify_order_workflow/workflow_definition.ts
git commit -m "Assemble n8n workflow definition with all Code nodes"
```

---

## Task 12: Validate the workflow

**Files:** aucun (appel MCP).

- [ ] **Step 1: Appeler validate_workflow**

Avec le contenu de `workflow_definition.ts` (résolu en string après lecture des 7 snippets), appeler :

```
mcp__claude_ai_n8n__validate_workflow(code=<workflow code as string>)
```

- [ ] **Step 2: Corriger les erreurs**

Si le validator retourne des erreurs (nodes mal typés, connexions invalides, etc.) :
- Modifier `workflow_definition.ts` ou les snippets `.js` concernés
- Re-commit
- Re-valider

Répéter jusqu'à ce que `validate_workflow` retourne OK.

- [ ] **Step 3: Commit fixes si besoin**

```bash
git add scripts/n8n/shopify_order_workflow/
git commit -m "Fix validation errors on Shopify workflow"
```

---

## Task 13: Deploy the workflow to n8n

**Files:** aucun (appel MCP).

- [ ] **Step 1: Appeler create_workflow_from_code**

```
mcp__claude_ai_n8n__create_workflow_from_code(
    code=<workflow code as string>,
    description="Transforme chaque commande Shopify payée en sale.order Odoo confirmé, déclenchant la création automatique d'un stock.picking prêt pour expédition avec BL cartons."
)
```

- [ ] **Step 2: Noter l'ID du workflow créé**

Le tool retourne un `workflow_id`. Le noter dans la memory pour référence future.

- [ ] **Step 3: Publier le workflow (l'activer)**

```
mcp__claude_ai_n8n__publish_workflow(workflow_id=<id from step 2>)
```

- [ ] **Step 4: Commit marquant le déploiement**

```bash
git commit --allow-empty -m "Deploy MY.LAB Shopify -> Commande Odoo workflow to n8n"
```

---

## Task 14: [USER] Test avec fake payload

**Files:** aucun (test manuel dans n8n UI ou via Shopify admin).

- [ ] **Step 1: Configurer les variables d'environnement n8n**

Sur le VPS (ou n8n cloud), ajouter les env vars :
- `SHOPIFY_WEBHOOK_SECRET` : le secret récupéré en Task 2
- `ODOO_URL`, `ODOO_DB`, `ODOO_LOGIN`, `ODOO_API_KEY` : credentials Odoo (déjà dispo)
- `ODOO_FP_INTRACOM_ID`, `ODOO_FP_EXPORT_ID` : IDs fiscal positions de la Task 1
- `MYLAB_LOG_SHEET_ID` : ID du Google Sheet de log (créer un sheet vide avec headers pour commencer)

Redémarrer n8n pour qu'il recharge les env vars.

- [ ] **Step 2: Lancer "Send test notification" dans Shopify admin**

Settings → Notifications → Webhooks → lign du webhook créé → bouton "Send test notification".

Shopify envoie un faux payload `orders/paid` avec une commande d'exemple.

- [ ] **Step 3: Vérifier l'exécution dans n8n**

n8n → Executions → dernière exécution du workflow "MY.LAB - Shopify → Commande Odoo".

Attendu :
- Le node "Verify HMAC" passe sans erreur (signature valide puisque Shopify a signé le test).
- Le node "Find/Create Partner" trouve ou crée un partenaire test.
- Le node "Match Products" liste tous les produits en "non matchés" (normal, ce sont des produits fake).
- Le node "Create Sale Order" crée un devis en BROUILLON avec uniquement des lignes notes rouges.
- L'activité "Corriger produits non matchés" est créée sur le sale.order.
- La ligne de log apparaît dans le Google Sheet.

- [ ] **Step 4: Si erreur**

Ouvrir l'exécution n8n, identifier le node qui a planté, lire le message d'erreur. Cas typiques :
- HMAC fail → vérifier `SHOPIFY_WEBHOOK_SECRET`
- Odoo auth fail → vérifier `ODOO_LOGIN` et `ODOO_API_KEY`
- Fiscal position missing → vérifier IDs en env vars

- [ ] **Step 5: Nettoyer**

Supprimer le sale.order de test dans Odoo (il est en brouillon, unlink sans souci).

---

## Task 15: [USER] Test live avec vraie commande Shopify

**Files:** aucun.

- [ ] **Step 1: Passer une commande test sur mylab-shop-3.myshopify.com**

Idéalement utiliser une variante avec SKU réel, quantité faible, et payer avec une vraie carte / Shopify Bogus Gateway si dispo. Objectif : déclencher `orders/paid` avec un vrai payload bien formé.

- [ ] **Step 2: Vérifier le flow complet**

- Dans n8n : execution réussie, tous les nodes verts
- Dans Odoo : sale.order confirmé (pas brouillon), avec lignes produits matchés + frais livraison + prix cohérents avec Shopify
- Dans Odoo : picking créé automatiquement (visible sous Inventaire → Transferts)
- Dans Odoo : mail.activity sur le picking (cloche d'activité en haut à droite)
- Dans Google Sheet : ligne log ajoutée

- [ ] **Step 3: Tester le flow "non matché"**

Temporairement changer le SKU d'un produit Shopify (ou créer un produit test avec SKU qui n'existe pas dans Odoo), re-commander. Vérifier :
- sale.order en BROUILLON
- Ligne note rouge visible dans le devis Odoo
- Activité "Corriger produits non matchés" assignée à Yoann

- [ ] **Step 4: Rétablir le SKU Shopify à sa valeur normale**

Important pour ne pas perturber le catalogue en production.

- [ ] **Step 5: Commit marquant la validation**

```bash
git commit --allow-empty -m "Manual E2E test: Shopify order -> Odoo workflow validated live"
```

---

## Task 16: Documentation + memory update

**Files:**
- Create: `scripts/n8n/README.md`
- Create: `scripts/n8n/shopify_order_workflow.md`
- Modify: `CLAUDE.md` (ajouter section)
- Create: `C:/Users/startec/.claude/projects/d--be-yours-mylab/memory/project_shopify_odoo_workflow.md`
- Modify: `C:/Users/startec/.claude/projects/d--be-yours-mylab/memory/MEMORY.md`

- [ ] **Step 1: `scripts/n8n/README.md`**

```markdown
# Scripts n8n MyLab

Source des workflows n8n développés via le MCP Workflow SDK.

## Structure

- `shopify_order_workflow/` — workflow `MY.LAB - Shopify → Commande Odoo`

Chaque sous-dossier contient :
- Les snippets JavaScript des Code nodes (`01_...js`, `02_...js`, etc.)
- Un `workflow_definition.ts` qui assemble le tout via le n8n SDK
- Un fichier `.md` documentant le workflow (input/output, env vars)

## Déploiement

Via MCP :
1. `mcp__claude_ai_n8n__validate_workflow(code=<contenu ts résolu>)`
2. `mcp__claude_ai_n8n__create_workflow_from_code(code=<code>, description=...)`
3. `mcp__claude_ai_n8n__publish_workflow(workflow_id=...)`

Les env vars nécessaires côté n8n (VPS) sont documentées dans le `.md` de chaque workflow.
```

- [ ] **Step 2: `scripts/n8n/shopify_order_workflow.md`**

```markdown
# MY.LAB - Shopify → Commande Odoo

## Trigger
Webhook POST `https://n8n.startec-paris.com/webhook/mylab-shopify-order`
Registered dans Shopify admin : event `Order payment`.

## Env vars requises
- `SHOPIFY_WEBHOOK_SECRET` : secret HMAC Shopify
- `ODOO_URL`, `ODOO_DB`, `ODOO_LOGIN`, `ODOO_API_KEY` : credentials Odoo
- `ODOO_FP_INTRACOM_ID`, `ODOO_FP_EXPORT_ID` : IDs fiscal positions Odoo
- `MYLAB_LOG_SHEET_ID` : ID Google Sheet pour logs

## Flow (nodes)
1. Webhook — reçoit le POST Shopify
2. Verify HMAC — valide la signature
3. Find/Create Partner — matching email → res.partner
4. Match Products — SKU + alias + ligne notes si non matché
5. Create Sale Order — idempotence + création + action_confirm conditionnel
6. Activity on Picking — crée mail.activity sur le picking
7. Format Log Row — prépare la ligne de log
8. Append Log Sheet — ajoute au Google Sheet

## Idempotence
Search sale.order par `client_order_ref = shopify_order_id` avant création.

## Spec complet
`docs/superpowers/specs/2026-04-17-shopify-order-to-odoo-design.md`
```

- [ ] **Step 3: Modifier `CLAUDE.md`**

Ajouter après la section "Odoo customizations" :

```markdown
## n8n workflows

Source des workflows n8n dans `scripts/n8n/`. Workflows déployés via le MCP n8n (`mcp__claude_ai_n8n__create_workflow_from_code`). Voir `scripts/n8n/README.md` pour le pattern de développement.

Workflows actifs :
- `MY.LAB - Shopify → Commande Odoo` : webhook Shopify → création sale.order + picking Odoo
- `MY.LAB - Devis Manuel (Formulaire)` : formulaire web → devis Odoo (hors repo)
- `MY.LAB - Email → Devis Odoo (Auto)` : Gmail → devis Odoo (hors repo)
```

- [ ] **Step 4: Créer la memory projet**

Créer `C:/Users/startec/.claude/projects/d--be-yours-mylab/memory/project_shopify_odoo_workflow.md` :

```markdown
---
name: Workflow Shopify → Odoo (commandes auto)
description: Workflow n8n qui crée automatiquement un sale.order Odoo confirmé depuis chaque commande Shopify payée
type: project
---

## Architecture
- Webhook Shopify `orders/paid` → n8n `MY.LAB - Shopify → Commande Odoo` → Odoo sale.order + picking
- ID workflow n8n : (à noter après déploiement)

## Source
- `scripts/n8n/shopify_order_workflow/` dans le repo be-yours-mylab
- Spec : `docs/superpowers/specs/2026-04-17-shopify-order-to-odoo-design.md`
- Plan : `docs/superpowers/plans/2026-04-17-shopify-order-to-odoo.md`

## Fiscal positions Odoo associées
- "Intracommunautaire (0%)" : id XXX
- "Export (0%)" : id YYY

## Points techniques
- Idempotence via `sale.order.client_order_ref` = Shopify order id
- Prix forcés depuis Shopify (pricelist Odoo id=3 référencée mais pas appliquée)
- Produit "Frais de livraison DPD" id=2413 utilisé systématiquement
- Confirmation automatique sauf si produits non matchés (devis reste brouillon)
- mail.activity créée sur le picking assignée à UID 8 (Yoann)

**Why:** Éliminer la saisie manuelle des commandes Shopify dans Odoo pour que Yoann n'ait qu'à cliquer "Répartir en cartons" + imprimer le BL.

**How to apply:** Pour modifier le comportement, éditer les snippets `.js` dans `scripts/n8n/shopify_order_workflow/`, reconstruire le workflow via `workflow_definition.ts`, re-déployer via `mcp__claude_ai_n8n__update_workflow`.
```

- [ ] **Step 5: Ajouter entrée dans MEMORY.md**

Ajouter au tableau topics :
```
| project_shopify_odoo_workflow.md | Workflow n8n Shopify -> Odoo sale.order auto, source dans scripts/n8n/ | 2026-04-17 |
```

- [ ] **Step 6: Commit**

```bash
git add scripts/n8n/README.md scripts/n8n/shopify_order_workflow.md CLAUDE.md
git commit -m "Document Shopify -> Odoo n8n workflow in README, CLAUDE.md, memory"
```

---

## Self-review

**Couverture du spec :**
- Webhook orders/paid + HMAC → Tasks 2 + 4 ✓
- Parsing payload → Task 4 ✓
- Idempotence → Task 8 (check dans `05_create_sale_order.js`) ✓
- Find/create partner avec fiscal position auto → Task 6 ✓ (dépend des IDs de Task 1)
- Match products + alias + ligne notes → Task 7 ✓
- Frais livraison via produit 2413 → Task 7 ✓
- Prix forcés depuis Shopify → Task 7 ✓
- Création sale.order + conditional confirm → Task 8 ✓
- mail.activity sur sale.order (draft) ET sur picking (confirmé) → Tasks 8 + 9 ✓
- Logging Google Sheet → Tasks 10 + 11 ✓
- Sécurité HMAC → Task 4 ✓
- Tests (fake + live) → Tasks 14 + 15 ✓
- Fiscal positions preexistence → Task 1 ✓
- Chatter note si adresse diffère → Task 6 (partner_notes accumulés + Task 8 message_post) ✓

**Scan placeholders :** aucun TBD, TODO, "handle edge cases" abstrait. Toutes les tâches ont du code inline.

**Cohérence des types :**
- `order_lines` format : toujours `[[0, 0, {...}]]` côté Task 7/8 ✓
- `partner_id` typé integer partout ✓
- `has_unmatched` bool propagé de Task 7 à Task 8 ✓
- `pickings_id` retourné par Task 8 consommé par Task 9 ✓
- noms d'env vars cohérents : `ODOO_LOGIN`, `ODOO_API_KEY`, `SHOPIFY_WEBHOOK_SECRET`, `ODOO_FP_INTRACOM_ID`, `ODOO_FP_EXPORT_ID`, `MYLAB_LOG_SHEET_ID` ✓

**Risques non couverts dans le spec mais gérés dans le plan :**
- Task 14 explicite la config des env vars n8n (pas dans le spec mais nécessaire)
- Task 15 teste explicitement le cas "produit non matché"
