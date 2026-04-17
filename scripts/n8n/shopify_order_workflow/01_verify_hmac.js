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
