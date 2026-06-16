// Patch the Cowork devis workflow to consume the new `prices` block emitted
// by the bulk-order configurateur. Fallback to legacy logic if absent so
// older clients (or other callers on /webhook/mylab-devis) keep working.
//
// Nodes patched:
//   ✅ Valider données entrantes  — passthrough `prices` field
//   🧠 Matcher produits           — use prices when present
//   ⚙️ Préparer le devis           — guard against optional sections

const fs = require('fs');
const path = require('path');

const SRC = path.resolve(__dirname, 'wf-cowork-devis.json');
const OUT = path.resolve(__dirname, 'wf-cowork-devis-patched.json');

const wf = JSON.parse(fs.readFileSync(SRC, 'utf8'));

// ───────────────────────────────────────────────────────────
// 1) ✅ Valider données entrantes : passthrough `prices`
// ───────────────────────────────────────────────────────────
const validNode = wf.nodes.find(n => n.name === '✅ Valider données entrantes');
const validJs = `const body = $input.first().json.body;
if (!body) throw new Error('Body vide');

const isGrosVolumes = !!body.items;
const hasLignes = !!body.lignes_commande;
if (!isGrosVolumes && !hasLignes) throw new Error('Ni items ni lignes_commande');

const c = body.client || {};
let client;
if (isGrosVolumes) {
  const nom = c.nom || c.company || ((c.firstname||'') + ' ' + (c.lastname||'')).trim() || 'Client inconnu';
  client = {
    nom: nom.trim(),
    email: (c.email || '').trim().toLowerCase(),
    telephone: (c.telephone || c.phone || '').trim(),
    portable: (c.portable || c.mobile || '').trim(),
    adresse: (c.adresse || c.address || '').trim(),
    ville: (c.ville || c.city || '').trim(),
    code_postal: (c.code_postal || c.zip || '').trim(),
    pays: (c.pays || 'FR').trim().toUpperCase(),
    entreprise: (c.entreprise || c.company || '').trim(),
    siret: (c.siret || '').trim()
  };
} else {
  client = {
    nom: (c.nom || 'Client inconnu').trim(),
    email: (c.email || '').trim().toLowerCase(),
    telephone: (c.telephone || '').trim(),
    portable: (c.portable || '').trim(),
    adresse: (c.adresse || '').trim(),
    ville: (c.ville || '').trim(),
    code_postal: (c.code_postal || '').trim(),
    pays: (c.pays || '').trim().toUpperCase(),
    entreprise: (c.entreprise || '').trim(),
    siret: (c.siret || '').trim()
  };
}

let lignes_commande;
if (isGrosVolumes) {
  lignes_commande = (body.items || []).map(i => ({
    produit: (i.product || i.produit || '').trim(),
    format: (i.format || '').trim(),
    quantite: parseFloat(i.nb_units || i.nb_unites || i.quantite || 0) || 0,
    prix_unitaire: parseFloat(i.unit_price || i.prix_unit || i.prix_unitaire || 0) || 0,
    gamme: (i.gamme || '').trim(),
    total_ht: parseFloat(i.total_ht || 0) || 0,
    bottle: (i.bottle || i.flacon || '').trim(),
    quantity_kg: parseFloat(i.quantity_kg || i.qty_kg || 0) || 0,
    tier: (i.tier || '').trim(),
    prices: i.prices || null,
    qty_arrondie: parseFloat(i.qty_arrondie || 0) || 0,
    qty_surplus: parseFloat(i.qty_surplus || 0) || 0,
    cout_surplus: parseFloat(i.cout_surplus || 0) || 0,
    moq: parseFloat(i.moq || 0) || 0
  }));
} else {
  lignes_commande = (body.lignes_commande || []).map(l => ({
    produit: (l.produit || '').trim(),
    format: (l.format || '').trim(),
    quantite: parseFloat(l.quantite || 0) || 0,
    prix_unitaire: parseFloat(l.prix_unitaire || 0) || 0,
    gamme: (l.gamme || '').trim(),
    total_ht: parseFloat(l.total_ht || 0) || 0,
    bottle: '',
    quantity_kg: 0,
    tier: '',
    prices: null,
    qty_arrondie: 0, qty_surplus: 0, cout_surplus: 0, moq: 0
  }));
}

return [{json: {
  is_gros_volumes: isGrosVolumes,
  client,
  lignes_commande,
  total_ht: parseFloat(body.total_ht) || 0,
  thread_id: body.thread_id || '',
  reponse_html: body.reponse_html || '<p>Bonjour,</p><p>Veuillez trouver ci-joint votre devis MY.LAB.</p><p>Cordialement,<br>L\\u0027\\u00e9quipe MY.LAB</p>',
  source: body.source || '',
  ref: body.ref || '',
  send_to_client: body.send_to_client === true || body.send_to_client === 'true' || false
}}];`;

validNode.parameters.jsCode = validJs;

// ───────────────────────────────────────────────────────────
// 2) 🧠 Matcher produits : nouveau chemin via `prices`
// ───────────────────────────────────────────────────────────
const matchNode = wf.nodes.find(n => n.name === '🧠 Matcher produits');
// Preserve legacy MOQ table + CATALOGUE from the existing node so the
// fallback path (line.prices absent) keeps the previous behaviour.
const legacyJs = matchNode.parameters.jsCode;
// We rewrite the GV branch entirely. Pull the legacy classique path verbatim
// from the existing code (lines 'if (!isGV)' .. 'else { ── FORMAT GROS VOLUMES ──').
// To keep the patch simple we just append a wrapper that delegates to the new
// path when prices are present and reuses the legacy code as a fallback
// otherwise. We keep the same return shape so '⚙️ Préparer le devis' is
// largely unchanged.

const matchJs = `const products = $('📦 Chercher catalogue produits').item.json.result || [];
const data = $('🔗 Extraire partner_id').item.json;
const lines = data.lignes_commande;
const isGV = data.is_gros_volumes;

function findProduct(name) {
  const upper = (name || '').toUpperCase().trim();
  if (!upper) return null;
  let match = products.find(p => (p.name || '').trim().toUpperCase() === upper);
  if (match) return { ...match, match_method: 'exact' };
  const lineWords = upper.split(/\\s+/).filter(w => w.length > 2);
  let best = null, bestScore = 0;
  for (const p of products) {
    const pWords = (p.name || '').toUpperCase().split(/\\s+/).filter(w => w.length > 2);
    const common = lineWords.filter(lw => pWords.some(pw => pw === lw || pw.includes(lw) || lw.includes(pw)));
    const score = common.length / Math.max(lineWords.length, 1);
    if (score > bestScore) { bestScore = score; best = p; }
  }
  if (best && bestScore >= 0.7) return { ...best, match_method: 'approché (' + Math.round(bestScore*100) + '%)' };
  return null;
}

function round2(n) { return Math.round((Number(n) || 0) * 100) / 100; }

const matchedLines = [];
const toCreate = [];

if (!isGV) {
  // ── FORMAT CLASSIQUE (inchangé) ──
  for (const line of lines) {
    const fullName = (line.produit + ' ' + line.format).trim();
    const match = findProduct(fullName);
    if (match) {
      matchedLines.push({product_id: match.id, name: fullName, product_uom_qty: line.quantite, price_unit: line.prix_unitaire, match_method: match.match_method});
    } else {
      matchedLines.push({product_id: null, name: fullName, product_uom_qty: line.quantite, price_unit: line.prix_unitaire, match_method: 'à créer'});
      toCreate.push({name: fullName, price_unit: line.prix_unitaire, gamme: line.gamme, format: line.format});
    }
  }
} else {
  // ── FORMAT GROS VOLUMES ──
  // Ensure les produits génériques existent (remplissage / étiquette).
  const remplissageMatch = findProduct('Remplissage MY.LAB');
  const etiquetteMatch = findProduct('Étiquette MY.LAB');
  const remplissageId = remplissageMatch ? remplissageMatch.id : null;
  const etiquetteId = etiquetteMatch ? etiquetteMatch.id : null;
  if (!remplissageId) toCreate.push({name: 'Remplissage MY.LAB', price_unit: 0.60, gamme: '', format: '', is_generic: true});
  if (!etiquetteId) toCreate.push({name: 'Étiquette MY.LAB', price_unit: 0.20, gamme: '', format: '', is_generic: true});

  for (const line of lines) {
    const nbUnits = line.quantite;
    const prices = line.prices;

    // ── PATH NOUVEAU : la configurateur a transmis le détail ──
    if (prices && typeof prices === 'object') {
      const isSH = !!prices.is_serum_huile;
      const formuleName = isSH ? line.produit : ('Formule ' + line.produit + ' ' + line.format);

      const formuleUnit = round2(prices.formule_unit);
      const formuleMatch = findProduct(formuleName);
      if (!formuleMatch) toCreate.push({name: formuleName, price_unit: formuleUnit, gamme: line.gamme, format: line.format});

      const out = {
        _type: 'gros_volume',
        formule: {
          product_id: formuleMatch ? formuleMatch.id : null,
          name: formuleName, qty: nbUnits, price: formuleUnit,
          match_method: formuleMatch ? formuleMatch.match_method : 'à créer'
        }
      };

      if (!isSH && (prices.remplissage_unit || 0) > 0) {
        out.remplissage = {
          product_id: remplissageId,
          name: 'Remplissage MY.LAB', qty: nbUnits, price: round2(prices.remplissage_unit),
          match_method: remplissageMatch ? remplissageMatch.match_method : 'à créer'
        };
      }
      if (!isSH && (prices.etiquette_unit || 0) > 0) {
        out.etiquette = {
          product_id: etiquetteId,
          name: 'Étiquette MY.LAB', qty: nbUnits, price: round2(prices.etiquette_unit),
          match_method: etiquetteMatch ? etiquetteMatch.match_method : 'à créer'
        };
      }
      if (!isSH && (prices.pompe_unit || 0) > 0) {
        // Produit Odoo générique id=2578 (Pompe 1L MY.LAB)
        out.pompe = {
          product_id: 2578,
          name: 'Pompe 1L MY.LAB', qty: nbUnits, price: round2(prices.pompe_unit),
          match_method: 'générique'
        };
      }
      if (!isSH && (prices.packaging_unit || 0) > 0 && !prices.is_custom_bottle) {
        // Produit Odoo générique id=2577 (Packaging MY.LAB Standard)
        out.packaging = {
          product_id: 2577,
          name: 'Packaging MY.LAB Standard — ' + line.format, qty: nbUnits, price: round2(prices.packaging_unit),
          match_method: 'générique'
        };
      }

      // Flacon : seulement pour Takemoto custom (is_custom_bottle) avec qty arrondie.
      if (!isSH && prices.is_custom_bottle && line.bottle && (prices.flacon_unit || 0) > 0) {
        const flaconName = 'Flacon ' + line.bottle;
        const qtyFlacons = prices.qty_flacons || nbUnits;
        const flaconMatch = findProduct(flaconName);
        const moqNote = qtyFlacons > nbUnits ? '* Flacons livrés par sets (MOQ ' + (line.moq || 0) + ')' : '';
        if (!flaconMatch) toCreate.push({name: flaconName, price_unit: round2(prices.flacon_unit), gamme: '', format: ''});
        out.flacon = {
          product_id: flaconMatch ? flaconMatch.id : null,
          name: flaconName, qty: qtyFlacons, price: round2(prices.flacon_unit),
          moq: line.moq || 0,
          moq_note: moqNote,
          match_method: flaconMatch ? flaconMatch.match_method : 'à créer'
        };
      }

      matchedLines.push(out);
      continue;
    }

    // ── PATH LEGACY (prices absent) : fallback à l'ancienne logique ──
    // (conservé pour rétro-compatibilité — supprimer une fois sûr que toutes
    // les clients web sont sur la nouvelle version JS)
    const CATALOGUE = {
      shampoing: { '200ml': 2.60, '500ml': 4.50, '1000ml': 8.00 },
      masque:    { '200ml': 3.60, '500ml': 6.20, '1000ml': 11.00 },
      creme:     { '200ml': 3.20, '500ml': 5.50, '1000ml': 9.50 }
    };
    function getPrixFormule(produit, format) {
      const p = (produit || '').toLowerCase();
      const f = (format || '').toLowerCase();
      if (p.includes('shampoing')) return CATALOGUE.shampoing[f] || 0;
      if (p.includes('masque')) return CATALOGUE.masque[f] || 0;
      if (p.includes('creme') || p.includes('crème')) return CATALOGUE.creme[f] || 0;
      return 0;
    }
    const unitPrice = line.prix_unitaire;
    const prixFormuleCatalogue = getPrixFormule(line.produit, line.format);
    const flaconName = 'Flacon ' + line.bottle;
    let prixFlaconUnit = 0;
    if (prixFormuleCatalogue > 0) {
      prixFlaconUnit = +(unitPrice - prixFormuleCatalogue - 0.60 - 0.20).toFixed(4);
      if (prixFlaconUnit < 0) prixFlaconUnit = 0;
    }
    const formuleName = 'Formule ' + line.produit + ' ' + line.format;
    const formuleMatch = findProduct(formuleName);
    if (!formuleMatch) toCreate.push({name: formuleName, price_unit: prixFormuleCatalogue, gamme: line.gamme, format: line.format});
    let flaconMatch = null;
    if (line.bottle) {
      flaconMatch = findProduct(flaconName);
      if (!flaconMatch) toCreate.push({name: flaconName, price_unit: prixFlaconUnit, gamme: '', format: ''});
    }
    matchedLines.push({
      _type: 'gros_volume',
      formule: { product_id: formuleMatch ? formuleMatch.id : null, name: formuleName, qty: nbUnits, price: prixFormuleCatalogue, match_method: formuleMatch ? formuleMatch.match_method : 'à créer' },
      remplissage: { product_id: remplissageId, name: 'Remplissage MY.LAB', qty: nbUnits, price: 0.60, match_method: remplissageMatch ? remplissageMatch.match_method : 'à créer' },
      etiquette: { product_id: etiquetteId, name: 'Étiquette MY.LAB', qty: nbUnits, price: 0.20, match_method: etiquetteMatch ? etiquetteMatch.match_method : 'à créer' },
      flacon: line.bottle ? { product_id: flaconMatch ? flaconMatch.id : null, name: flaconName, qty: nbUnits, price: prixFlaconUnit, moq: 0, moq_note: '', match_method: flaconMatch ? flaconMatch.match_method : 'à créer' } : null
    });
  }
}

const create_payload = toCreate.map(p => ({
  name: p.name,
  type: 'service',
  sale_ok: true,
  purchase_ok: false,
  list_price: p.price_unit,
  description_sale: p.gamme ? 'Gamme ' + p.gamme + ' · ' + (p.format || '') : (p.format || ''),
  uom_id: 1,
  uom_po_id: 1
}));

let productMatches;
if (!isGV) {
  productMatches = matchedLines.map(l => l.name + ': ' + l.match_method);
} else {
  productMatches = [];
  for (const item of matchedLines) {
    if (item._type !== 'gros_volume') continue;
    productMatches.push(item.formule.name + ': ' + item.formule.match_method);
    if (item.remplissage) productMatches.push(item.remplissage.name + ': ' + item.remplissage.match_method);
    if (item.etiquette) productMatches.push(item.etiquette.name + ': ' + item.etiquette.match_method);
    if (item.pompe) productMatches.push(item.pompe.name + ': ' + item.pompe.match_method);
    if (item.packaging) productMatches.push(item.packaging.name + ': ' + item.packaging.match_method);
    if (item.flacon) productMatches.push(item.flacon.name + ': ' + item.flacon.match_method);
  }
}

return [{json: {
  partner_id: data.partner_id,
  matched_lines: matchedLines,
  to_create: toCreate,
  has_missing: toCreate.length > 0,
  create_payload: create_payload,
  is_gros_volumes: isGV,
  search_method: data.search_method,
  client_email: data.client.email,
  thread_id: data.thread_id,
  reponse_html: data.reponse_html,
  ref: data.ref || ''
}}];`;

matchNode.parameters.jsCode = matchJs;

// ───────────────────────────────────────────────────────────
// 3) ⚙️ Préparer le devis : guards sur remplissage/étiquette optionnels
// ───────────────────────────────────────────────────────────
const prepNode = wf.nodes.find(n => n.name === '⚙️ Préparer le devis');
const prepJs = `const matchData = $('🧠 Matcher produits').item.json;
const matchedLines = matchData.matched_lines;
const isGV = matchData.is_gros_volumes;

let createdVariants = [];
try { createdVariants = $('🔍 Chercher variants créées').item.json.result || []; } catch(e) {}

function resolveId(productId, productName) {
  if (productId) return productId;
  if (createdVariants.length > 0) {
    const v = createdVariants.find(v => (v.name || '').toUpperCase().trim() === (productName || '').toUpperCase().trim());
    if (v) return v.id;
  }
  return null;
}

const orderLines = [];

if (!isGV) {
  for (const line of matchedLines) {
    const pid = resolveId(line.product_id, line.name);
    const ld = {name: line.name, product_uom_qty: line.product_uom_qty, price_unit: line.price_unit, product_uom: 1, tax_id: [[6, 0, [116]]]};
    if (pid) ld.product_id = pid;
    orderLines.push([0, 0, ld]);
  }
} else {
  for (const item of matchedLines) {
    if (item._type !== 'gros_volume') continue;

    orderLines.push([0, 0, {display_type: 'line_section', name: 'PRODUCTION MY.LAB'}]);

    const fId = resolveId(item.formule.product_id, item.formule.name);
    const fLine = {name: item.formule.name, product_uom_qty: item.formule.qty, price_unit: item.formule.price, product_uom: 1, tax_id: [[6, 0, [116]]]};
    if (fId) fLine.product_id = fId;
    orderLines.push([0, 0, fLine]);

    if (item.remplissage) {
      const rId = resolveId(item.remplissage.product_id, item.remplissage.name);
      const rLine = {name: item.remplissage.name, product_uom_qty: item.remplissage.qty, price_unit: item.remplissage.price, product_uom: 1, tax_id: [[6, 0, [116]]]};
      if (rId) rLine.product_id = rId;
      orderLines.push([0, 0, rLine]);
    }

    if (item.etiquette) {
      const eId = resolveId(item.etiquette.product_id, item.etiquette.name);
      const eLine = {name: item.etiquette.name, product_uom_qty: item.etiquette.qty, price_unit: item.etiquette.price, product_uom: 1, tax_id: [[6, 0, [116]]]};
      if (eId) eLine.product_id = eId;
      orderLines.push([0, 0, eLine]);
    }

    if (item.pompe) {
      const pId = resolveId(item.pompe.product_id, item.pompe.name);
      const pLine = {name: item.pompe.name, product_uom_qty: item.pompe.qty, price_unit: item.pompe.price, product_uom: 1, tax_id: [[6, 0, [116]]]};
      if (pId) pLine.product_id = pId;
      orderLines.push([0, 0, pLine]);
    }

    if (item.packaging || item.flacon) {
      orderLines.push([0, 0, {display_type: 'line_section', name: 'PACKAGING'}]);
    }
    if (item.packaging) {
      const kId = resolveId(item.packaging.product_id, item.packaging.name);
      const kLine = {name: item.packaging.name, product_uom_qty: item.packaging.qty, price_unit: item.packaging.price, product_uom: 1, tax_id: [[6, 0, [116]]]};
      if (kId) kLine.product_id = kId;
      orderLines.push([0, 0, kLine]);
    }
    if (item.flacon) {
      const bId = resolveId(item.flacon.product_id, item.flacon.name);
      const bName = item.flacon.moq_note ? (item.flacon.name + '\\n' + item.flacon.moq_note) : item.flacon.name;
      const bLine = {name: bName, product_uom_qty: item.flacon.qty, price_unit: item.flacon.price, product_uom: 1, tax_id: [[6, 0, [116]]]};
      if (bId) bLine.product_id = bId;
      orderLines.push([0, 0, bLine]);
    }
  }
}

const note = matchData.ref
  ? 'Devis généré automatiquement par MY.LAB Cowork — Réf: ' + matchData.ref
  : 'Devis généré automatiquement par MY.LAB Cowork';

let productMatches;
if (!isGV) {
  productMatches = matchedLines.map(l => l.name + ': ' + l.match_method);
} else {
  productMatches = [];
  for (const item of matchedLines) {
    if (item._type !== 'gros_volume') continue;
    productMatches.push(item.formule.name + ': ' + item.formule.match_method);
    if (item.remplissage) productMatches.push(item.remplissage.name + ': ' + item.remplissage.match_method);
    if (item.etiquette) productMatches.push(item.etiquette.name + ': ' + item.etiquette.match_method);
    if (item.pompe) productMatches.push(item.pompe.name + ': ' + item.pompe.match_method);
    if (item.packaging) productMatches.push(item.packaging.name + ': ' + item.packaging.match_method);
    if (item.flacon) productMatches.push(item.flacon.name + ': ' + item.flacon.match_method);
  }
}

return [{json: {
  partner_id: matchData.partner_id,
  order_lines: orderLines,
  note: note,
  client_email: matchData.client_email,
  thread_id: matchData.thread_id,
  reponse_html: matchData.reponse_html,
  client_search_method: matchData.search_method,
  product_matches: productMatches
}}];`;

prepNode.parameters.jsCode = prepJs;

// ───────────────────────────────────────────────────────────
// Build PUT payload (only fields the n8n API accepts).
// ───────────────────────────────────────────────────────────
const allowedSettings = ['executionOrder', 'callerPolicy', 'errorWorkflow', 'saveDataErrorExecution', 'saveDataSuccessExecution', 'saveExecutionProgress', 'saveManualExecutions', 'executionTimeout', 'timezone'];
const cleanSettings = {};
for (const k of allowedSettings) if (wf.settings && wf.settings[k] !== undefined) cleanSettings[k] = wf.settings[k];

const payload = {
  name: wf.name,
  nodes: wf.nodes,
  connections: wf.connections,
  settings: cleanSettings
};

fs.writeFileSync(OUT, JSON.stringify(payload, null, 2));
console.log('Patched workflow written to', OUT);
console.log('  Valider jsCode chars:', validJs.length);
console.log('  Matcher jsCode chars:', matchJs.length);
console.log('  Préparer jsCode chars:', prepJs.length);
