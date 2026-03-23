/**
 * MY.LAB — Bulk Order API (Cloudflare Worker / Vercel Edge Function)
 * ===================================================================
 * Option A : Crée un Draft Order Shopify à partir des données du devis.
 *
 * Déploiement Cloudflare Workers :
 *   npx wrangler deploy api/bulk-order-worker.js --name mylab-bulk-order
 *
 * Variables d'environnement requises :
 *   SHOPIFY_STORE_URL=mylab-shop-3.myshopify.com
 *   SHOPIFY_ACCESS_TOKEN=shpat_xxx (Admin API token avec write_draft_orders)
 *   NOTIFICATION_EMAIL=yoann@mylab-shop.com
 *   ALLOWED_ORIGIN=https://mylab-shop-3.myshopify.com
 *
 * Pour créer le token API Shopify :
 *   Admin > Paramètres > Applications > Développer des applications >
 *   Créer une application > Configurer les portées API Admin :
 *     - write_draft_orders
 *     - read_draft_orders
 *     - write_customers
 *     - read_customers
 */

// ── Rate limiting (in-memory, reset par instance) ──
const rateLimits = new Map();
const RATE_LIMIT = 5;       // max requêtes
const RATE_WINDOW = 3600000; // 1 heure en ms

function checkRateLimit(ip) {
  const now = Date.now();
  const entry = rateLimits.get(ip) || { count: 0, start: now };
  if (now - entry.start > RATE_WINDOW) {
    entry.count = 1;
    entry.start = now;
  } else {
    entry.count++;
  }
  rateLimits.set(ip);
  return entry.count <= RATE_LIMIT;
}

// ── Données formules pour recalcul serveur ──
// NOTE : En production, charger depuis un KV store ou une base de données.
// Ici on utilise les mêmes données que bulk-data-formulas.json.
const PRICING = {
  shampoing: {
    '50kg': { '200ml': 3.90, '500ml': 7.90, '1000ml': 14.50, '5000ml': 66.50 },
    '100_200kg': { '200ml': 3.60, '500ml': 7.30, '1000ml': 13.40, '5000ml': 61.40 }
  },
  masque: {
    '50kg': { '200ml': 5.70, '500ml': 12.10, '1000ml': 22.50, '5000ml': 106.50 },
    '100_200kg': { '200ml': 5.40, '500ml': 11.30, '1000ml': 21.40, '5000ml': 101.40 }
  },
  creme_coiffage: {
    '50kg': { '200ml': 5.10, '500ml': 10.60, '1000ml': 19.50, '5000ml': 91.50 },
    '100_200kg': { '200ml': 4.80, '500ml': 10.00, '1000ml': 18.40, '5000ml': 86.40 }
  }
};

function getServerPrice(category, tier, format) {
  const cat = PRICING[category] || PRICING.shampoing;
  const tierData = cat[tier] || cat['50kg'];
  return tierData[format] || null;
}

// ── Validation ──
function validatePayload(data) {
  const errors = [];

  if (!data.client) errors.push('Client manquant');
  if (!data.client?.email) errors.push('Email client manquant');
  if (!data.client?.firstname) errors.push('Prénom client manquant');
  if (!data.client?.lastname) errors.push('Nom client manquant');
  if (!data.client?.company) errors.push('Société manquante');

  if (!data.items || !Array.isArray(data.items) || data.items.length === 0) {
    errors.push('Aucun produit dans le devis');
  }

  if (data.items) {
    data.items.forEach((item, i) => {
      if (!item.product) errors.push(`Item ${i + 1}: produit manquant`);
      if (!item.format) errors.push(`Item ${i + 1}: format manquant`);
      if (!item.quantity_kg || item.quantity_kg < 50) errors.push(`Item ${i + 1}: quantité minimum 50kg`);
      if (!item.tier) errors.push(`Item ${i + 1}: tranche manquante`);
    });
  }

  return errors;
}

// ── Calcul serveur des prix (ne jamais faire confiance au frontend) ──
function recalculateItems(items) {
  return items.map(item => {
    const formatMl = parseInt(item.format);
    const formatKey = formatMl + 'ml';
    const kg = item.quantity_kg;
    const nbUnits = Math.ceil((kg * 1000) / formatMl);

    // Recalcul prix serveur
    const unitPrice = getServerPrice(item.category || 'shampoing', item.tier, formatKey);
    if (!unitPrice) {
      throw new Error(`Prix non trouvé pour ${item.category} ${item.tier} ${formatKey}`);
    }

    const totalHT = unitPrice * nbUnits;

    return {
      title: `${item.gamme} — ${item.product} — ${formatKey} — Gros Volume`,
      quantity: 1,
      price: totalHT.toFixed(2),
      properties: [
        { name: 'Gamme', value: item.gamme || '' },
        { name: 'Type', value: item.category || '' },
        { name: 'Format', value: formatKey },
        { name: 'Flacon', value: item.bottle || 'MY.LAB Standard' },
        { name: 'Quantité (kg)', value: String(kg) },
        { name: 'Nombre d\'unités', value: String(nbUnits) },
        { name: 'Prix unitaire HT', value: unitPrice.toFixed(2) + ' €' },
        { name: 'Tranche', value: item.tier === '100_200kg' ? '100-200 kg' : '50 kg' }
      ]
    };
  });
}

// ── Création Draft Order Shopify ──
async function createDraftOrder(env, payload, lineItems) {
  const shopUrl = `https://${env.SHOPIFY_STORE_URL}/admin/api/2024-01/draft_orders.json`;

  const totalHT = lineItems.reduce((sum, item) => sum + parseFloat(item.price), 0);
  const acompte50 = (totalHT * 0.50).toFixed(2);

  const draftOrder = {
    draft_order: {
      line_items: lineItems,
      customer: {
        email: payload.client.email,
        first_name: payload.client.firstname,
        last_name: payload.client.lastname,
        phone: payload.client.phone || '',
        default_address: {
          company: payload.client.company,
          city: payload.client.city || ''
        }
      },
      note: `Commande Gros Volume — Devis N°${payload.ref || 'N/A'}\n` +
            `Société : ${payload.client.company}\n` +
            `Total HT : ${totalHT.toFixed(2)} €\n` +
            `Acompte 50% : ${acompte50} €\n` +
            (payload.client.notes ? `Notes : ${payload.client.notes}` : ''),
      tags: 'gros-volume, devis-en-ligne',
      tax_exempt: false,
      shipping_line: {
        title: 'Transport à la charge du client',
        price: '0.00'
      }
    }
  };

  const resp = await fetch(shopUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': env.SHOPIFY_ACCESS_TOKEN
    },
    body: JSON.stringify(draftOrder)
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Shopify API error ${resp.status}: ${errText}`);
  }

  const result = await resp.json();
  return result.draft_order;
}

// ── Notification email (via Shopify Draft Order invoice) ──
async function sendInvoice(env, draftOrderId) {
  const url = `https://${env.SHOPIFY_STORE_URL}/admin/api/2024-01/draft_orders/${draftOrderId}/send_invoice.json`;

  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': env.SHOPIFY_ACCESS_TOKEN
    },
    body: JSON.stringify({
      draft_order_invoice: {
        to: env.NOTIFICATION_EMAIL,
        subject: 'Nouveau devis Gros Volume MY.LAB',
        custom_message: 'Un nouveau devis gros volume a été créé depuis le site.'
      }
    })
  });

  return resp.ok;
}

// ── Handler principal ──
async function handleRequest(request, env) {
  const origin = env.ALLOWED_ORIGIN || 'https://mylab-shop-3.myshopify.com';

  // CORS
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400'
      }
    });
  }

  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Rate limit
  const ip = request.headers.get('CF-Connecting-IP') || request.headers.get('X-Forwarded-For') || 'unknown';
  if (!checkRateLimit(ip)) {
    return new Response(JSON.stringify({ error: 'Trop de requêtes. Réessayez dans 1 heure.' }), {
      status: 429,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': origin
      }
    });
  }

  try {
    const payload = await request.json();

    // Validation
    const errors = validatePayload(payload);
    if (errors.length > 0) {
      return new Response(JSON.stringify({ error: 'Validation échouée', details: errors }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': origin }
      });
    }

    // Recalcul serveur des prix
    const lineItems = recalculateItems(payload.items);

    // Création Draft Order
    const draftOrder = await createDraftOrder(env, payload, lineItems);

    // Envoyer notification
    await sendInvoice(env, draftOrder.id).catch(() => {});

    return new Response(JSON.stringify({
      success: true,
      draft_order_id: draftOrder.id,
      invoice_url: draftOrder.invoice_url,
      total_ht: lineItems.reduce((s, i) => s + parseFloat(i.price), 0).toFixed(2)
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': origin }
    });

  } catch (err) {
    console.error('Bulk order error:', err);
    return new Response(JSON.stringify({ error: 'Erreur serveur', message: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': origin }
    });
  }
}

// ── Export Cloudflare Workers ──
export default {
  async fetch(request, env) {
    return handleRequest(request, env);
  }
};

// ── Export Vercel / Netlify (alternative) ──
// Pour Vercel : renommer en api/bulk-order.js
// export default async function handler(req, res) {
//   const env = process.env;
//   // adapter request/response pour Node.js
// }
