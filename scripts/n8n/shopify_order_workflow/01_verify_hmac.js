// Node type: Code (Run Once for All Items)
// Input: webhook trigger output (body + headers)
// Output: { order } — the parsed Shopify order object
//
// NOTE: HMAC verification is currently BYPASSED — the Shopify raw body
// cannot be reproduced reliably from $input.first().json.body (JSON.stringify
// produces different bytes than what Shopify signed). Security relies on the
// webhook URL not being publicly known. To fix properly, access the raw body
// via $input.first().binary.data once rawBody:true is reliable in this n8n
// version, or verify HMAC outside n8n (e.g. nginx).

const input = $input.first().json;

// Shopify sends the order object directly as the request body when the webhook
// is configured with format=JSON. Depending on n8n webhook config, it may be
// at the root (input) or under input.body.
const order = input.body && typeof input.body === 'object' && input.body.id
  ? input.body
  : input;

if (!order || !order.id) {
  throw new Error(`Invalid Shopify payload — missing order.id. Keys: ${Object.keys(input).join(', ')}`);
}

return [{ json: { order } }];
