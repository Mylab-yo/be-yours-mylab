// Local replay of the patched ✅ Valider + 🧠 Matcher + ⚙️ Préparer
// against the HAIRDEX payload, with `prices` added (as a patched configurator
// would emit). Verifies the total Odoo order_lines sum to the same total as
// the configurateur (3859.60 €).
//
// No network calls — pure Node, no Odoo writes.

const fs = require('fs');
const path = require('path');

const exec = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'exec-75791-cowork.json'), 'utf8'));
const patchedWf = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'wf-cowork-devis-patched.json'), 'utf8'));

// ───────────── Reconstruct the HAIRDEX webhook body, but with `prices`
// blocks as a PATCHED configurator would emit (per
// `assets/bulk-data-formulas.json`, Gamme Nourrissante / Volume / HA Repulpe
// / Coloristeur — all shampoo 300ml at tier 50kg).
const originalValid = exec.data.resultData.runData['✅ Valider données entrantes'][0].data.main[0][0].json;

// pricing for shampoo 300ml at 50kg tier (from bulk-data-formulas.json — all
// four shampoos share identical pricing data; see formules.json).
const priceShampoo300_50kg = { formule: 3.9, remplissage: 0.6, packaging: 0.5, etiquette: 0.2 }; // total 5.20

const bottlePriceEstimateCentimes = 90; // tk-s-apin-300-pb-v35-cap → 0.90 €
const isCustom = true;
const nbUnits = 167;

function buildItem(produit, gamme) {
  // Mirror exactly what bulk-order-summary.js now emits.
  const grandTotalUnit =
    priceShampoo300_50kg.formule +
    priceShampoo300_50kg.remplissage +
    (isCustom ? 0 : priceShampoo300_50kg.packaging) +
    priceShampoo300_50kg.etiquette +
    (bottlePriceEstimateCentimes / 100);
  return {
    gamme: gamme,
    product: produit,
    format: '300ml',
    bottle: 'S-APIN-300 + PB-V35 CAP — Ambré',
    quantity_kg: 50,
    nb_units: nbUnits,
    unit_price: Math.round(grandTotalUnit * 100) / 100,
    total_ht: Math.round(grandTotalUnit * nbUnits * 100) / 100,
    tier: '50kg',
    moq: 1,
    qty_arrondie: nbUnits,
    qty_surplus: 0,
    cout_surplus: 0,
    prices: {
      is_serum_huile: false,
      is_custom_bottle: isCustom,
      formule_unit: priceShampoo300_50kg.formule,
      remplissage_unit: priceShampoo300_50kg.remplissage,
      packaging_unit: isCustom ? 0 : priceShampoo300_50kg.packaging,
      etiquette_unit: priceShampoo300_50kg.etiquette,
      pompe_unit: 0,
      flacon_unit: bottlePriceEstimateCentimes / 100,
      qty_flacons: nbUnits
    }
  };
}

// Standard MY.LAB bottle case — exercises packaging line
function buildItemStandard(produit, gamme, format, formulePrice, packagingPrice) {
  const grandTotalUnit = formulePrice + 0.6 + packagingPrice + 0.2; // no bottle no pump
  const nb = 250;
  return {
    gamme, product: produit, format: format,
    bottle: 'MY.LAB Standard',
    quantity_kg: 50, nb_units: nb,
    unit_price: Math.round(grandTotalUnit * 100) / 100,
    total_ht: Math.round(grandTotalUnit * nb * 100) / 100,
    tier: '50kg', moq: 0, qty_arrondie: nb, qty_surplus: 0, cout_surplus: 0,
    prices: {
      is_serum_huile: false, is_custom_bottle: false,
      formule_unit: formulePrice, remplissage_unit: 0.6, packaging_unit: packagingPrice,
      etiquette_unit: 0.2, pompe_unit: 0, flacon_unit: 0, qty_flacons: 0
    }
  };
}

// 1L crème custom (Takemoto) — exercises pompe + flacon
function buildItem1LWithPump(produit, gamme) {
  const formulePrice = 18; // crème 1000ml 50kg tier
  const remplissage = 0.6, packaging = 0, etiquette = 0.2, pompe = 0.45;
  const flacon_unit = 0; // skip — no cap pricing
  const grandTotalUnit = formulePrice + remplissage + packaging + etiquette + pompe + flacon_unit;
  const nb = 50;
  return {
    gamme, product: produit, format: '1000ml',
    bottle: 'CUSTOM-BOTTLE-1L — Frosted',
    quantity_kg: 50, nb_units: nb,
    unit_price: Math.round(grandTotalUnit * 100) / 100,
    total_ht: Math.round(grandTotalUnit * nb * 100) / 100,
    tier: '50kg', moq: 0, qty_arrondie: nb, qty_surplus: 0, cout_surplus: 0,
    prices: {
      is_serum_huile: false, is_custom_bottle: true,
      formule_unit: formulePrice, remplissage_unit: remplissage,
      packaging_unit: packaging, etiquette_unit: etiquette,
      pompe_unit: pompe, flacon_unit: flacon_unit, qty_flacons: nb
    }
  };
}

const body = {
  ref: 'TEST-MYLAB-GV-PATCHED',
  client: { firstname: 'Test', lastname: 'Patch', company: 'TEST', email: 'test@example.invalid', phone: '', city: '' },
  items: [
    buildItem('Shampoing Nourrissant', 'Gamme Nourrissante'),
    buildItem('Shampoing Volume', 'Gamme Volume'),
    buildItem('Shampoing HA Repulpe', 'Gamme HA Repulpe'),
    buildItem('Shampoing Déjaunisseur', 'Gamme Coloristeur'),
    buildItemStandard('Masque Nourrissant', 'Gamme Nourrissante', '500ml', 10.5, 0.8),
    buildItem1LWithPump('Crème de Coiffage Nourrissante', 'Gamme Nourrissante')
  ],
  total_ht: 0,
  tva: 0,
  total_ttc: 0,
  send_to_client: false,
  source: 'TEST-LOCAL'
};
body.total_ht = body.items.reduce((s, i) => s + i.total_ht, 0);
body.tva = +(body.total_ht * 0.2).toFixed(2);
body.total_ttc = +(body.total_ht * 1.2).toFixed(2);

console.log('=== PAYLOAD (configurateur patché) ===');
console.log('Total HT envoyé:', body.total_ht.toFixed(2), '€');
console.log('Per item unit_price:', body.items[0].unit_price, '€');
console.log('Per item total_ht:', body.items[0].total_ht, '€');

// ───────────── Simulate ✅ Valider node ─────────────
function makeNode(name, wf) {
  const n = wf.nodes.find(x => x.name === name);
  if (!n) throw new Error('Node not found: ' + name);
  return n;
}

// Build a $-style accessor map keyed on node name.
const ctx = {};
function $$(name) {
  return { item: { json: ctx[name] } };
}

// 1) ✅ Valider
const validJs = makeNode('✅ Valider données entrantes', patchedWf).parameters.jsCode;
const validFn = new Function('$input', '$', '$json', validJs);
const validOut = validFn({ first: () => ({ json: { body } }) }, null, null);
ctx['✅ Valider données entrantes'] = validOut[0].json;
console.log('\\n=== Valider OUT ===');
console.log('  is_gros_volumes:', ctx['✅ Valider données entrantes'].is_gros_volumes);
console.log('  lignes_commande count:', ctx['✅ Valider données entrantes'].lignes_commande.length);
console.log('  first ligne prices:', JSON.stringify(ctx['✅ Valider données entrantes'].lignes_commande[0].prices));

// 2) Simulate 🔗 Extraire partner_id (passes through with partner_id)
ctx['🔗 Extraire partner_id'] = Object.assign(
  { partner_id: 99999, search_method: 'test' },
  ctx['✅ Valider données entrantes']
);

// 3) Stub 📦 Chercher catalogue produits with the actual products fetched
// during exec 75791 — they have all the Formule/Remplissage/Étiquette/Flacon.
ctx['📦 Chercher catalogue produits'] = exec.data.resultData.runData['📦 Chercher catalogue produits'][0].data.main[0][0].json;
console.log('\\n  Catalogue products:', ctx['📦 Chercher catalogue produits'].result.length);

// 4) 🧠 Matcher produits
const matcherJs = makeNode('🧠 Matcher produits', patchedWf).parameters.jsCode;
const matcherFn = new Function('$', matcherJs);
const matcherOut = matcherFn($$);
ctx['🧠 Matcher produits'] = matcherOut[0].json;

console.log('\\n=== Matcher OUT — first item ===');
const first = ctx['🧠 Matcher produits'].matched_lines[0];
console.log(JSON.stringify({
  formule: first.formule,
  remplissage: first.remplissage,
  etiquette: first.etiquette,
  flacon: first.flacon
}, null, 2));

// 5) ⚙️ Préparer le devis — emit the [0,0,{}] order_lines
const prepJs = makeNode('⚙️ Préparer le devis', patchedWf).parameters.jsCode;
const prepFn = new Function('$', prepJs);
const prepOut = prepFn($$);
const orderLines = prepOut[0].json.order_lines;

console.log('\\n=== Préparer OUT — order_lines count ===', orderLines.length);

let totalOdoo = 0;
const lineSummary = [];
orderLines.forEach(([_,__,line]) => {
  if (line.display_type === 'line_section') {
    lineSummary.push('  ── SECTION : ' + line.name + ' ──');
  } else {
    const total = (line.product_uom_qty || 0) * (line.price_unit || 0);
    totalOdoo += total;
    lineSummary.push('  ' + line.name.padEnd(50) + ' qty=' + String(line.product_uom_qty).padStart(5) + ' × ' + String(line.price_unit).padStart(7) + ' € = ' + total.toFixed(2) + ' €');
  }
});
lineSummary.forEach(l => console.log(l));

console.log('\\n=== VERDICT ===');
console.log('Total Odoo lignes  :', totalOdoo.toFixed(2), '€');
console.log('Total HT configurateur :', body.total_ht.toFixed(2), '€');
const delta = Math.abs(totalOdoo - body.total_ht);
console.log('Écart absolu       :', delta.toFixed(2), '€  →', delta < 0.05 ? '✅ MATCH (within rounding)' : '❌ MISMATCH');
