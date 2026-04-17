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
