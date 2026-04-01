/**
 * MY.LAB — Configurateur Commande Gros Volumes
 * assets/bulk-order-quantity.js
 *
 * Step 4 — Quantity selection and pricing calculation.
 * Depends on: bulk-order-core.js (window.BulkOrder)
 */
(function () {
  'use strict';

  var B = window.BulkOrder;
  if (!B) return;

  /* ══════════════════════════════════════════════
     DOM REFS
     ══════════════════════════════════════════════ */
  var elQtyList    = document.getElementById('bulk-quantity-list');
  var elGrandValue = document.getElementById('bulk-quantity-grand-value');
  var elGrandUnits = document.getElementById('bulk-quantity-grand-units');

  /* ══════════════════════════════════════════════
     RENDER QUANTITY STEP
     ══════════════════════════════════════════════ */
  function renderQuantity() {
    if (!elQtyList) return;
    var formulas = B.getSelectedFormulasWithFormat();
    if (formulas.length === 0) { elQtyList.innerHTML = ''; return; }

    var html = '';
    formulas.forEach(function (f) {
      var format = B.state.formats[f.id];
      var fmtLabel = format >= 1000 ? (format / 1000) + ' L' : format + ' ml';
      var bottleId = B.bottleState.selections[f.id] || 'standard';
      var bottleName = bottleId === 'standard' ? 'MY.LAB Standard' : '';
      if (bottleId !== 'standard' && B.bottlesData) {
        var bObj = B.bottlesData.bottles.find(function (b) { return b.id === bottleId; });
        if (bObj) bottleName = bObj.name;
      }

      /* ── Serum / Huile: unit-based pricing (50ml fixed) ── */
      if (B.isSerumOrHuile(f)) {
        var pricingKey = f.category;
        var shPricing = B.SERUM_HUILE_PRICING[pricingKey] || {};
        if (!B.qtyState[f.id]) B.qtyState[f.id] = { units: 250, tier: '250u' };
        var qsu = B.qtyState[f.id];
        var unitPrice = shPricing[qsu.units] || 0;
        var totalHT = unitPrice * qsu.units;

        html += '<div class="bulk-qty-block" style="--gamme-color:' + B.esc(f.gammeColor) + '">' +
          '<div class="bulk-qty-block__header">' +
            '<span class="bulk-qty-block__dot" style="background:' + B.esc(f.gammeColor) + '"></span>' +
            '<span class="bulk-qty-block__label">' + B.esc(f.name) + '</span>' +
            '<span class="bulk-qty-block__detail">50 ml</span>' +
          '</div>' +
          '<div class="bulk-qty-tiers">' +
            '<button type="button" class="bulk-qty-tier' + (qsu.units === 250 ? ' bulk-qty-tier--active' : '') + '" data-formula-qty="' + B.esc(f.id) + '" data-tier="250u">250 unités <span class="bulk-qty-tier__price">' + B.fmtPrice(shPricing[250] || 0) + '/u</span></button>' +
            '<button type="button" class="bulk-qty-tier' + (qsu.units === 500 ? ' bulk-qty-tier--active' : '') + '" data-formula-qty="' + B.esc(f.id) + '" data-tier="500u">500 unités <span class="bulk-qty-tier__price">' + B.fmtPrice(shPricing[500] || 0) + '/u</span></button>' +
          '</div>' +
          '<table class="bulk-qty-table"><thead><tr><th>Composant</th><th>Prix unitaire</th><th>Quantité</th><th>Sous-total</th></tr></thead><tbody>' +
          '<tr><td>' + B.esc(f.name) + '</td><td>' + B.fmtPrice(unitPrice) + '</td><td>' + qsu.units + '</td><td>' + B.fmtPrice(totalHT) + '</td></tr>' +
          '<tr class="bulk-qty-row--total"><td colspan="3">Total HT</td><td>' + B.fmtPrice(totalHT) + '</td></tr>' +
          '</tbody></table>' +
          '<p class="bulk-qty-set-note">Prix tout compris : formule, conditionnement, \u00e9tiquette et flacon 50 ml.</p>' +
          '</div>';
        return;
      }

      /* ── Standard kg-based pricing ── */
      if (!B.qtyState[f.id]) B.qtyState[f.id] = { kg: 50, tier: '50kg' };
      var qs = B.qtyState[f.id];

      if (qs.tier === '100_200kg') qs.kg = 100;
      else qs.kg = 50;

      var calc = B.calculateOrder(f, format, qs.kg, qs.tier);
      var tierLabel50 = '50 litres minimum';
      var tierLabel100 = '100 litres';

      var price50 = '';
      var calcFor50 = B.calculateOrder(f, format, 50, '50kg');
      if (calcFor50) price50 = '<span class="bulk-qty-tier__price">' + B.fmtPrice(calcFor50.pricing.total) + '/u</span>';
      var price100 = '';
      if (f.pricing && f.pricing['100_200kg'] && f.pricing['100_200kg'][format + 'ml']) {
        price100 = '<span class="bulk-qty-tier__price">' + B.fmtPrice(f.pricing['100_200kg'][format + 'ml'].total) + '/u</span>';
      }

      html += '<div class="bulk-qty-block" style="--gamme-color:' + B.esc(f.gammeColor) + '">' +

        '<div class="bulk-qty-block__header">' +
          '<span class="bulk-qty-block__dot" style="background:' + B.esc(f.gammeColor) + '"></span>' +
          '<span class="bulk-qty-block__label">' + B.esc(f.name) + '</span>' +
          '<span class="bulk-qty-block__detail">' + fmtLabel + ' · ' + B.esc(bottleName) + '</span>' +
        '</div>' +

        '<div class="bulk-qty-tiers">' +
          '<button type="button" class="bulk-qty-tier' + (qs.tier === '50kg' ? ' bulk-qty-tier--active' : '') + '" data-formula-qty="' + B.esc(f.id) + '" data-tier="50kg">' +
            tierLabel50 + price50 +
          '</button>' +
          '<button type="button" class="bulk-qty-tier' + (qs.tier === '100_200kg' ? ' bulk-qty-tier--active' : '') + '" data-formula-qty="' + B.esc(f.id) + '" data-tier="100_200kg">' +
            tierLabel100 + price100 +
          '</button>' +
        '</div>';

      if (calc) {
        html += '<div class="bulk-qty-calc">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2"><path d="M5 12l5 5L19 7"/></svg>' +
          qs.kg + ' kg = <strong>' + calc.nbUnits + ' flacons</strong> de ' + fmtLabel +
          '</div>';

        /* MOQ status */
        if (calc.isCustomBottle && calc.bottleMoq > 0) {
          if (!calc.moqMet) {
            html += '<div class="bulk-qty-moq-warning">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e65100" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>' +
              '<div><strong>Quantit\u00e9 insuffisante pour ce flacon</strong>' +
              '<p>Votre commande : <strong>' + calc.nbUnits + ' flacons</strong><br>' +
              'Minimum requis : <strong>' + calc.bottleMoq + ' flacons</strong> (1 set Takemoto)<br>' +
              '\u2192 Augmentez \u00e0 au moins <strong>' + calc.moqMinKg + ' kg</strong> pour atteindre le minimum.</p></div>' +
              '</div>';
          } else if (calc.moqMet && calc.bottleSurplus > 0) {
            html += '<div class="bulk-qty-moq-info">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1565c0" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>' +
              '<div>Takemoto livre par sets de <strong>' + calc.bottleMoq + '</strong>. ' +
              'Vous commanderez <strong>' + calc.nbSets + ' set' + (calc.nbSets > 1 ? 's' : '') + '</strong> ' +
              'soit <strong>' + calc.nbBottlesOrdered + ' flacons</strong>. ' +
              'Surplus de ' + calc.bottleSurplus + ' flacon' + (calc.bottleSurplus > 1 ? 's' : '') + '.</div>' +
              '</div>';
          } else {
            html += '<div class="bulk-qty-moq-ok">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2.5"><path d="M5 12l5 5L19 7"/></svg>' +
              'Votre commande de ' + calc.nbUnits + ' flacons respecte le minimum de ' + calc.bottleMoq + ' unit\u00e9s.' +
              '</div>';
          }
        }

        /* Price breakdown */
        html += '<div class="bulk-qty-table-wrap"><table class="bulk-qty-table">' +
          '<thead><tr><th>Composant</th><th>Prix unitaire</th><th>Quantité</th><th>Sous-total</th></tr></thead>' +
          '<tbody>' +
          '<tr><td colspan="4" class="bulk-qty-section-label">Production MY.LAB</td></tr>' +
          '<tr><td>Formule</td><td>' + B.fmtPrice(calc.pricing.formule) + '</td><td>' + calc.nbUnits + '</td><td>' + B.fmtPrice(calc.formuleTotal) + '</td></tr>' +
          '<tr><td>Remplissage</td><td>' + B.fmtPrice(calc.pricing.remplissage) + '</td><td>' + calc.nbUnits + '</td><td>' + B.fmtPrice(calc.remplissageTotal) + '</td></tr>';

        html += '<tr><td>Étiquette</td><td>' + B.fmtPrice(calc.pricing.etiquette) + '</td><td>' + calc.nbUnits + '</td><td>' + B.fmtPrice(calc.etiquetteTotal) + '</td></tr>';

        if (calc.needsPump) {
          html += '<tr><td>Pompe (option 1L)</td><td>' + B.fmtPrice(0.45) + '</td><td>' + calc.nbUnits + '</td><td>' + B.fmtPrice(calc.pumpTotal) + '</td></tr>';
        }

        html += '<tr><td colspan="4" class="bulk-qty-section-label">Packaging</td></tr>';
        if (calc.isCustomBottle && calc.bottleUnitPrice > 0) {
          var bottleCostCommande = calc.bottleUnitPrice * calc.nbUnits;
          html += '<tr><td>Flacon ' + B.esc(calc.bottleName) + '</td><td>' + B.fmtPrice(calc.bottleUnitPrice) + '</td><td>' + calc.nbUnits + '</td><td>' + B.fmtPrice(bottleCostCommande) + '</td></tr>';
          if (calc.bottleSurplus > 0) {
            var coutSurplus = calc.bottleUnitPrice * calc.bottleSurplus;
            html += '<tr style="color:#888;font-style:italic;"><td>Surplus MOQ flacons</td><td>' + B.fmtPrice(calc.bottleUnitPrice) + '</td><td>' + calc.bottleSurplus + '*</td><td>' + B.fmtPrice(coutSurplus) + '</td></tr>';
          }
        } else if (calc.isCustomBottle && calc.bottleUnitPrice === 0) {
          html += '<tr><td>Flacon ' + B.esc(calc.bottleName) + '</td><td colspan="3" style="color:#888;font-style:italic;">Prix sur demande</td></tr>';
        } else {
          html += '<tr><td>Packaging MY.LAB Standard</td><td>' + B.fmtPrice(calc.pricing.packaging) + '</td><td>' + calc.nbUnits + '</td><td>' + B.fmtPrice(calc.packagingTotal) + '</td></tr>';
        }

        html += '<tr class="bulk-qty-row--total"><td colspan="3">Total HT</td><td>' + B.fmtPrice(calc.grandTotal) + '</td></tr>' +
          '</tbody></table>';

        if (calc.isCustomBottle && calc.bottleMoq > 0 && calc.bottleSurplus > 0) {
          html += '<p class="bulk-qty-set-note">* Flacons livr\u00e9s par sets de ' + calc.bottleMoq + '. Vous commanderez ' + calc.nbSets + ' set' + (calc.nbSets > 1 ? 's' : '') + ' soit ' + calc.nbBottlesOrdered + ' flacons. Surplus : ' + calc.bottleSurplus + ' flacon' + (calc.bottleSurplus > 1 ? 's' : '') + '.</p>';
        }
        html += '</div>';
      }

      html += '</div>';
    });

    elQtyList.innerHTML = html;
    updateGrandTotal();
    bindQtyEvents();
  }

  /* ══════════════════════════════════════════════
     GRAND TOTAL
     ══════════════════════════════════════════════ */
  function updateGrandTotal() {
    var formulas = B.getSelectedFormulasWithFormat();
    var total = 0;
    var totalUnits = 0;

    formulas.forEach(function (f) {
      var qs = B.qtyState[f.id];
      if (!qs) return;
      var calc = B.calculateOrder(f, B.state.formats[f.id], qs.kg, qs.tier);
      if (calc) {
        total += calc.grandTotal;
        totalUnits += calc.nbUnits;
      }
    });

    if (elGrandValue) elGrandValue.textContent = B.fmtPrice(total) + ' HT';
    if (elGrandUnits) elGrandUnits.textContent = totalUnits + ' flacons au total';
  }

  /* ══════════════════════════════════════════════
     TIER BUTTON EVENTS
     ══════════════════════════════════════════════ */
  function bindQtyEvents() {
    elQtyList.querySelectorAll('.bulk-qty-tier').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var fid = btn.dataset.formulaQty;
        var tier = btn.dataset.tier;

        if (tier === '250u' || tier === '500u') {
          var units = parseInt(tier, 10);
          B.qtyState[fid] = { units: units, tier: tier };
        } else {
          if (!B.qtyState[fid]) B.qtyState[fid] = { kg: 50, tier: '50kg' };
          B.qtyState[fid].tier = tier;
          B.qtyState[fid].kg = tier === '100_200kg' ? 100 : 50;
        }
        renderQuantity();
      });
    });
  }

  /* ══════════════════════════════════════════════
     REGISTER MODULE
     ══════════════════════════════════════════════ */
  B.modules.quantity = {
    renderQuantity: renderQuantity
  };

})();
