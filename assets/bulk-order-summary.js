/**
 * MY.LAB — Configurateur Commande Gros Volumes
 * assets/bulk-order-summary.js
 *
 * Step 5 — Order summary + webhook submission.
 * Depends on: bulk-order-core.js (window.BulkOrder)
 */
(function () {
  'use strict';

  var B = window.BulkOrder;
  if (!B) return;

  /* ══════════════════════════════════════════════
     DOM REFS
     ══════════════════════════════════════════════ */
  var elSummaryRef   = document.getElementById('bulk-summary-ref');
  var elSummaryDate  = document.getElementById('bulk-summary-date');
  var elSummaryBody  = document.getElementById('bulk-summary-body');
  var elSummaryFoot  = document.getElementById('bulk-summary-foot');
  var elSummaryForm  = document.getElementById('bulk-summary-form');
  var elBtnSend      = document.getElementById('bulk-btn-send');
  var elSummaryOk    = document.getElementById('bulk-summary-success');

  /* ══════════════════════════════════════════════
     HELPERS
     ══════════════════════════════════════════════ */
  function genRef() {
    var d = new Date();
    var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
    var rand = Math.floor(1000 + Math.random() * 9000);
    return 'MYLAB-GV-' + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + '-' + rand;
  }

  /* ══════════════════════════════════════════════
     RENDER SUMMARY
     ══════════════════════════════════════════════ */
  function renderSummary() {
    if (!elSummaryBody || !elSummaryFoot) return;
    var formulas = B.getSelectedFormulasWithFormat();
    var now = new Date();
    var dateStr = now.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });

    if (elSummaryRef) elSummaryRef.textContent = 'Réf. : ' + genRef();
    if (elSummaryDate) elSummaryDate.textContent = 'Date : ' + dateStr;

    var bodyHtml = '';
    var totalHT = 0;
    var totalUnits = 0;

    formulas.forEach(function (f) {
      var format = B.state.formats[f.id];
      var fmtLabel = format >= 1000 ? (format / 1000) + ' L' : format + ' ml';

      /* Serum / Huile: unit-based summary */
      if (B.isSerumOrHuile(f)) {
        var qsu = B.qtyState[f.id] || { units: 250, tier: '250u' };
        var shPrice = (B.SERUM_HUILE_PRICING[f.category] || {})[qsu.units] || 0;
        var shTotal = shPrice * qsu.units;
        totalHT += shTotal;
        totalUnits += qsu.units;
        bodyHtml += '<tr>' +
          '<td><span class="bulk-summary__gamme-dot" style="background:' + B.esc(f.gammeColor) + '"></span>' + B.esc(f.gammeLabel.replace('Gamme ', '')) + '</td>' +
          '<td>' + B.esc(f.name) + '</td>' +
          '<td>50 ml</td>' +
          '<td>Inclus</td>' +
          '<td>—</td>' +
          '<td>' + qsu.units + '</td>' +
          '<td>' + B.fmtPrice(shPrice) + '</td>' +
          '<td>' + B.fmtPrice(shTotal) + '</td>' +
          '</tr>';
        return;
      }

      var qs = B.qtyState[f.id] || { kg: 50, tier: '50kg' };
      var calc = B.calculateOrder(f, format, qs.kg, qs.tier);
      if (!calc) return;

      var bottleId = B.bottleState.selections[f.id] || 'standard';
      var bottleName = 'MY.LAB Standard';
      if (bottleId !== 'standard' && B.bottlesData) {
        var bObj = B.bottlesData.bottles.find(function (b) { return b.id === bottleId; });
        if (bObj) {
          bottleName = bObj.name;
          var pickedColor = B.bottleState.selectedColors && B.bottleState.selectedColors[bottleId];
          var displayColor = pickedColor || (bObj.available_colors && bObj.available_colors[0]) || bObj.color;
          if (displayColor) bottleName += ' — ' + (B.COLOR_LABELS[displayColor] || displayColor);
        }
      }

      totalHT += calc.grandTotal;
      totalUnits += calc.nbUnits;

      bodyHtml += '<tr>' +
        '<td><span class="bulk-summary__gamme-dot" style="background:' + B.esc(f.gammeColor) + '"></span>' + B.esc(f.gammeLabel.replace('Gamme ', '')) + '</td>' +
        '<td>' + B.esc(f.name) + '</td>' +
        '<td>' + fmtLabel + '</td>' +
        '<td>' + B.esc(bottleName) + '</td>' +
        '<td>' + qs.kg + ' kg</td>' +
        '<td>' + calc.nbUnits + '</td>' +
        '<td>' + B.fmtPrice(calc.grandTotal / calc.nbUnits) + '</td>' +
        '<td>' + B.fmtPrice(calc.grandTotal) + '</td>' +
        '</tr>';

      if (calc.isCustomBottle && calc.bottleSurplus > 0 && calc.bottleUnitPrice > 0) {
        var surplusCost = calc.bottleUnitPrice * calc.bottleSurplus;
        bodyHtml += '<tr style="color:#888;font-style:italic;font-size:0.9em;">' +
          '<td colspan="4">Surplus MOQ flacons (' + calc.bottleSurplus + ' x ' + B.fmtPrice(calc.bottleUnitPrice) + ')</td>' +
          '<td colspan="2">Sets : ' + calc.nbSets + ' x ' + calc.bottleMoq + '</td>' +
          '<td></td>' +
          '<td>' + B.fmtPrice(surplusCost) + '</td>' +
          '</tr>';
      }
    });

    elSummaryBody.innerHTML = bodyHtml;

    var tva = totalHT * 0.20;
    var ttc = totalHT + tva;

    elSummaryFoot.innerHTML =
      '<tr class="bulk-summary__row--subtotal"><td colspan="7">Sous-total HT</td><td>' + B.fmtPrice(totalHT) + '</td></tr>' +
      '<tr class="bulk-summary__row--tva"><td colspan="7">TVA (20%)</td><td>' + B.fmtPrice(tva) + '</td></tr>' +
      '<tr class="bulk-summary__row--total"><td colspan="7">Total TTC</td><td>' + B.fmtPrice(ttc) + '</td></tr>';
  }

  /* ══════════════════════════════════════════════
     FORM DATA & PAYLOAD
     ══════════════════════════════════════════════ */
  function collectFormData() {
    return {
      firstname: document.getElementById('bulk-client-firstname').value.trim(),
      lastname: document.getElementById('bulk-client-lastname').value.trim(),
      company: document.getElementById('bulk-client-company').value.trim(),
      email: document.getElementById('bulk-client-email').value.trim(),
      phone: document.getElementById('bulk-client-phone').value.trim(),
      city: document.getElementById('bulk-client-city').value.trim(),
      notes: document.getElementById('bulk-client-notes').value.trim()
    };
  }

  function buildQuotePayload() {
    var client = collectFormData();
    var formulas = B.getSelectedFormulasWithFormat();
    var items = [];
    var totalHT = 0;

    formulas.forEach(function (f) {
      var format = B.state.formats[f.id];

      if (B.isSerumOrHuile(f)) {
        var qsu = B.qtyState[f.id] || { units: 250, tier: '250u' };
        var shPrice = (B.SERUM_HUILE_PRICING[f.category] || {})[qsu.units] || 0;
        var shTotal = shPrice * qsu.units;
        totalHT += shTotal;
        items.push({
          gamme: f.gammeLabel,
          product: f.name,
          format: '50ml',
          bottle: 'Inclus',
          quantity_kg: null,
          nb_units: qsu.units,
          unit_price: shPrice,
          total_ht: Math.round(shTotal * 100) / 100,
          tier: qsu.tier,
          pricing_mode: 'units',
          moq: 0, qty_arrondie: qsu.units, qty_surplus: 0, cout_surplus: 0
        });
        return;
      }

      var qs = B.qtyState[f.id] || { kg: 50, tier: '50kg' };
      var calc = B.calculateOrder(f, format, qs.kg, qs.tier);
      if (!calc) return;

      var bottleId = B.bottleState.selections[f.id] || 'standard';
      var bottleName = 'MY.LAB Standard';
      if (bottleId !== 'standard' && B.bottlesData) {
        var bObj = B.bottlesData.bottles.find(function (b) { return b.id === bottleId; });
        if (bObj) {
          bottleName = bObj.name;
          var pickedColor = B.bottleState.selectedColors && B.bottleState.selectedColors[bottleId];
          var displayColor = pickedColor || (bObj.available_colors && bObj.available_colors[0]) || bObj.color;
          if (displayColor) bottleName += ' — ' + (B.COLOR_LABELS[displayColor] || displayColor);
        }
      }

      totalHT += calc.grandTotal;

      items.push({
        gamme: f.gammeLabel,
        product: f.name,
        format: format + 'ml',
        bottle: bottleName,
        quantity_kg: qs.kg,
        nb_units: calc.nbUnits,
        unit_price: Math.round(calc.grandTotal / calc.nbUnits * 100) / 100,
        total_ht: Math.round(calc.grandTotal * 100) / 100,
        tier: qs.tier,
        moq: calc.bottleMoq,
        qty_arrondie: calc.nbBottlesOrdered,
        qty_surplus: calc.bottleSurplus,
        cout_surplus: Math.round(calc.bottleUnitPrice * calc.bottleSurplus * 100) / 100
      });
    });

    return {
      ref: elSummaryRef ? elSummaryRef.textContent.replace('Réf. : ', '') : genRef(),
      date: new Date().toISOString(),
      client: client,
      items: items,
      total_ht: Math.round(totalHT * 100) / 100,
      tva: Math.round(totalHT * 0.20 * 100) / 100,
      total_ttc: Math.round(totalHT * 1.20 * 100) / 100,
      source: 'Shopify — Commande Gros Volumes'
    };
  }

  function buildN8nPayload(sendToClient) {
    var raw = buildQuotePayload();
    return {
      ref: raw.ref,
      date: new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }),
      client: raw.client,
      lignes: raw.items.map(function (it) {
        return {
          gamme: it.gamme,
          produit: it.product,
          format: it.format,
          flacon: it.bottle,
          qty_kg: it.quantity_kg,
          nb_unites: it.nb_units,
          prix_unit: it.unit_price,
          total_ht: it.total_ht,
          moq: it.moq,
          qty_arrondie: it.qty_arrondie,
          qty_surplus: it.qty_surplus,
          cout_surplus: it.cout_surplus
        };
      }),
      sous_total_ht: raw.total_ht,
      tva: raw.tva,
      total_ttc: raw.total_ttc,
      send_to_client: sendToClient
    };
  }

  /* ══════════════════════════════════════════════
     STATUS HELPER
     ══════════════════════════════════════════════ */
  function showBtnStatus(btn, msg, color, isError) {
    var el = btn.parentElement.querySelector('.bulk-summary__btn-status');
    if (!el) {
      el = document.createElement('div');
      el.className = 'bulk-summary__btn-status';
      el.style.cssText = 'font-size:1.1rem;margin-top:0.6rem;';
      btn.parentElement.appendChild(el);
    }
    el.style.color = color;
    el.textContent = msg;
    if (!isError) setTimeout(function () { el.textContent = ''; }, 8000);
  }

  /* ══════════════════════════════════════════════
     SEND QUOTE
     ══════════════════════════════════════════════ */
  function sendQuote() {
    var client = collectFormData();

    var emailEl = document.getElementById('bulk-client-email');
    if (!client.email) {
      if (emailEl) { emailEl.style.border = '2px solid #c0392b'; }
      showBtnStatus(elBtnSend, 'Email requis', '#c0392b', true);
      return;
    }
    if (emailEl) emailEl.style.border = '';

    if (!client.firstname || !client.lastname || !client.company) {
      showBtnStatus(elBtnSend, 'Veuillez remplir Prénom, Nom et Société', '#c0392b', true);
      return;
    }

    elBtnSend.disabled = true;
    var origText = elBtnSend.innerHTML;
    elBtnSend.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="10"/></svg> Envoi en cours...';

    var payload = buildN8nPayload(true);

    fetch(B.N8N_WEBHOOK, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    })
    .then(function (text) {
      // Webhook n8n peut renvoyer 200 + body vide (Respond to Webhook pas configuré)
      var data = {};
      if (text) { try { data = JSON.parse(text); } catch (_) {} }
      return data;
    })
    .then(function (data) {
      elSummaryForm.style.display = 'none';
      document.querySelector('.bulk-summary__actions').style.display = 'none';
      document.querySelector('.bulk-summary__conditions').style.display = 'none';
      elSummaryOk.style.display = '';
      elSummaryOk.querySelector('p').textContent = 'Devis envoyé à ' + client.email + ' et à notre équipe. Nous vous recontacterons dans les 48h.';
      window.scrollTo({ top: elSummaryOk.offsetTop - 100, behavior: 'smooth' });
    })
    .catch(function (err) {
      console.error('Send error:', err);
      elBtnSend.disabled = false;
      elBtnSend.innerHTML = origText;
      showBtnStatus(elBtnSend, "Erreur d'envoi, veuillez réessayer", '#c0392b', true);
    });
  }

  /* Bind send button */
  if (elBtnSend) elBtnSend.addEventListener('click', sendQuote);

  /* ══════════════════════════════════════════════
     REGISTER MODULE
     ══════════════════════════════════════════════ */
  B.modules.summary = {
    renderSummary: renderSummary
  };

})();
