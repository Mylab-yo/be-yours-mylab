// Creer le devis dans Odoo (avec attachement fichier si mode upload)
const ODOO_URL = 'https://odoo.startec-paris.com';
const ODOO_DB = 'OdooYJ';
const ODOO_UID = 8;
const ODOO_KEY = 'e6d35b4261b948664841075e8fffc3510c8db437';
const COMPANY_ID = 3;
const PRICELIST_ID = 3;

const helpers = this.helpers;
const input = $input.first().json;

if (input.error) {
  return [{ json: input }];
}

const { email, client_name, products, raw_demande } = input;

async function odoo(model, method, args, kwargs) {
  const resp = await helpers.httpRequest({
    method: 'POST',
    url: ODOO_URL + '/jsonrpc',
    headers: { 'Content-Type': 'application/json' },
    body: {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'call',
      params: {
        service: 'object',
        method: 'execute_kw',
        args: [ODOO_DB, ODOO_UID, ODOO_KEY, model, method, args],
        kwargs: kwargs || {}
      }
    }
  });
  if (resp.error) throw new Error(JSON.stringify(resp.error));
  return resp.result;
}

const PRODUCT_ALIASES = {
  'shampoing brillance 200ml': 'shampoing protecteur de couleur 200ml',
  'shampoing brillance 500ml': 'shampoing protecteur de couleur 500ml',
  'shampoing brillance 1000ml': 'shampoing protecteur de couleur 1000ml',
  'creme brillance 200ml': 'creme protectrice de couleur 200ml',
  'masque brillance 200ml': 'masque protecteur de couleur 200ml',
  'masque brillance 400ml': 'masque protecteur de couleur 400ml',
  'masque brillance 1000ml': 'masque protecteur de couleur 1000ml',
  'shampoing blond polaire 200ml': 'shampoing dejaunisseur platine 200ml',
  'shampoing blond polaire 1000ml': 'shampoing dejaunisseur platine 1000ml',
  'masque blond polaire 200ml': 'masque dejaunisseur platine 200ml',
  'masque blond polaire 1000ml': 'masque dejaunisseur platine 1000ml',
  'masque blond cuivre 200ml': 'masque coloristeur cuivre 200ml',
  'masque blond cuivre 1000ml': 'masque coloristeur cuivre intense 1000ml',
  'shampoing blond cuivre 200ml': 'shampoing coloristeur cuivre 200ml',
  'shampoing blond cuivre 1000ml': 'shampoing coloristeur cuivre 1000ml',
  'spray volume 200ml': 'spray texturisant 200ml',
  'spray detox 200ml': 'spray texturisant 200ml',
  'spray volume detox 200ml': 'spray texturisant 200ml',
  'huile bain miraculeux 50ml': 'bain miraculeux 50ml',
  'shampoing blond ble 200ml': 'shampoing coloristeur blond soleil 200ml',
  'shampoing blond ble 1000ml': 'shampoing coloristeur blond soleil 1000ml',
  'masque blond ble 200ml': 'masque coloristeur blond soleil 200ml',
  'masque blond ble 1000ml': 'masque coloristeur blond soleil 1000ml',
  'shampoing roucou 200ml': 'shampoing coloristeur cuivre 200ml',
  'shampoing roucou 1000ml': 'shampoing coloristeur cuivre 1000ml',
  'masque roucou 200ml': 'masque coloristeur cuivre intense 200ml',
  'masque roucou 1000ml': 'masque coloristeur cuivre intense 1000ml',
  'masque tulipe noire 200ml': 'masque coloristeur tulipe noire 200ml',
  'masque tulipe noire 1000ml': 'masque coloristeur tulipe noire 1000ml',
  'spray masque reparateur sans rincage 200ml': 'masque reparateur sans rincage 200ml',
};

// 1. Chercher ou creer le client
let partnerId;
let partnerName = client_name || email || 'Client sans nom';

if (email) {
  const existing = await odoo('res.partner', 'search_read',
    [[['email', '=', email]]],
    { fields: ['id', 'name'], limit: 1 }
  );
  if (existing.length > 0) {
    partnerId = existing[0].id;
    partnerName = existing[0].name;
  }
}

if (!partnerId) {
  partnerId = await odoo('res.partner', 'create', [{
    name: partnerName,
    email: email || false,
    company_type: 'company',
    customer_rank: 1,
    company_id: COMPANY_ID
  }]);
}

// Validation email partner
const partnerFull = await odoo('res.partner', 'read', [[partnerId]], { fields: ['email', 'name'] });
const partnerEmail = partnerFull[0].email;
const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
if (!partnerEmail || !emailRegex.test(partnerEmail)) {
  return [{ json: {
    error: 'Email partner manquant ou invalide',
    error_code: 'PARTNER_EMAIL_MISSING',
    partner_id: partnerId,
    partner_name: partnerFull[0].name,
    partner_email: partnerEmail || null,
    details: "Le devis n'a pas ete cree : l'email du client dans Odoo est manquant ou invalide. Corrige-le dans Odoo puis resoumets le formulaire.",
    raw_demande: raw_demande || null
  }}];
}

// 2. Matcher les produits dans Odoo
const orderLines = [];
const matched = [];
const unmatched = [];

for (const p of products) {
  if (p.search_name === 'INCONNU') {
    unmatched.push({ demande: p.display_name, raison: 'Produit non reconnu par IA' });
    continue;
  }

  const searchName = PRODUCT_ALIASES[p.search_name] || p.search_name;

  let found = await odoo('product.product', 'search_read',
    [[['name', '=', searchName], ['sale_ok', '=', true]]],
    { fields: ['id', 'name', 'list_price', 'default_code'], limit: 1 }
  );

  if (found.length === 0) {
    found = await odoo('product.product', 'search_read',
      [[['name', 'ilike', searchName], ['sale_ok', '=', true]]],
      { fields: ['id', 'name', 'list_price', 'default_code'], limit: 3 }
    );
  }

  if (found.length === 0 && searchName.match(/\d+ml$/)) {
    const baseName = searchName.replace(/\s*\d+ml$/, '');
    found = await odoo('product.product', 'search_read',
      [[['name', 'ilike', baseName], ['sale_ok', '=', true]]],
      { fields: ['id', 'name', 'list_price', 'default_code'], limit: 5 }
    );
  }

  if (found.length > 0) {
    const prod = found[0];
    orderLines.push([0, 0, {
      product_id: prod.id,
      product_uom_qty: p.quantity
    }]);
    matched.push({
      name: prod.name,
      odoo_id: prod.id,
      sku: prod.default_code || '',
      quantity: p.quantity,
      prix_unitaire: prod.list_price
    });
  } else {
    unmatched.push({
      demande: p.display_name,
      search: p.search_name,
      raison: 'Non trouve dans Odoo'
    });
  }
}

// 3. Creer le devis
let result = {
  success: false,
  devis: null,
  devis_id: null,
  devis_url: null,
  client: partnerName,
  partner_id: partnerId,
  matched,
  unmatched,
  nb_produits: matched.length,
  nb_non_trouves: unmatched.length,
  montant_total: null
};

// 3b. Detecter la position fiscale automatiquement
let fiscalPositionId = false;
try {
  const fp = await odoo('account.fiscal.position', 'get_fiscal_position', [[partnerId]]);
  if (fp) fiscalPositionId = fp;
} catch(e) {
  try {
    const partner = await odoo('res.partner', 'read', [[partnerId]], { fields: ['country_id', 'vat'] });
    const countryId = partner[0].country_id ? partner[0].country_id[0] : false;
    const hasVat = !!partner[0].vat;
    if (countryId) {
      const fps = await odoo('account.fiscal.position', 'search_read',
        [[['auto_apply', '=', true]]],
        { fields: ['id', 'country_id', 'country_group_id', 'vat_required'], order: 'sequence' }
      );
      const groups = await odoo('res.country.group', 'search_read',
        [[['country_ids', 'in', [countryId]]]],
        { fields: ['id'] }
      );
      const groupIds = groups.map(g => g.id);
      for (const fp of fps) {
        const fpCountry = fp.country_id ? fp.country_id[0] : false;
        const fpGroup = fp.country_group_id ? fp.country_group_id[0] : false;
        if (fp.vat_required && !hasVat) continue;
        if (fpCountry && fpCountry === countryId) { fiscalPositionId = fp.id; break; }
        if (fpGroup && groupIds.includes(fpGroup)) { fiscalPositionId = fp.id; break; }
      }
    }
  } catch(e2) {}
}

if (orderLines.length > 0) {
  const orderId = await odoo('sale.order', 'create', [{
    partner_id: partnerId,
    pricelist_id: PRICELIST_ID,
    company_id: COMPANY_ID,
    order_line: orderLines,
    fiscal_position_id: fiscalPositionId || false,
  }]);

  const order = await odoo('sale.order', 'read', [[orderId]],
    { fields: ['name', 'amount_total', 'amount_untaxed'] }
  );

  result.success = true;
  result.devis = order[0].name;
  result.devis_id = orderId;
  result.devis_url = ODOO_URL + '/web#id=' + orderId + '&model=sale.order&view_type=form';
  result.montant_total = order[0].amount_total;
  result.montant_ht = order[0].amount_untaxed;
}

// 4. Attachement Odoo (mode fichier uniquement)
if (input.file_base64 && result.success && result.devis_id) {
  try {
    const attachmentName = input.file_name || `commande-${result.devis}.${input.file_mime === 'application/pdf' ? 'pdf' : 'jpg'}`;
    const attachmentId = await odoo('ir.attachment', 'create', [{
      name: attachmentName,
      type: 'binary',
      datas: input.file_base64,
      mimetype: input.file_mime,
      res_model: 'sale.order',
      res_id: result.devis_id,
      company_id: COMPANY_ID
    }]);

    await odoo('sale.order', 'message_post', [[result.devis_id]], {
      body: `<p>Devis genere automatiquement depuis un document uploade via le formulaire devis manuel.</p><p><b>Fichier source :</b> ${attachmentName}</p>`,
      attachment_ids: [attachmentId],
      message_type: 'comment',
      subtype_xmlid: 'mail.mt_note'
    });

    result.file_attached = true;
    result.attachment_id = attachmentId;
  } catch (e) {
    result.file_attached = false;
    result.attachment_error = String(e.message || e);
  }
} else if (input.file_base64) {
  result.file_attached = false;
}

result.source = input.source || (input.file_base64 ? 'file' : 'text');

// Cas special : 0 produit extrait + fichier present → exposer raw_ocr pour le front
if (input.file_base64 && matched.length === 0 && input.raw_ocr) {
  result.raw_ocr = input.raw_ocr;
}

return [{ json: result }];
