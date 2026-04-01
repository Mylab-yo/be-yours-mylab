'use strict';

/**
 * ML Volume Pricing — Tarifs dégressifs MyLab
 * Lit les paliers depuis ml-product-map.json via MylabUtils.
 * Dépend de ml-utils.js
 */

(function () {
  var U = window.MylabUtils;
  if (!U) { console.error('ML Volume Pricing: ml-utils.js non chargé'); return; }

  /* -------------------------------------------------------
     RENDU DU TABLEAU
     ------------------------------------------------------- */
  function renderTable(container, tiers) {
    if (!tiers || tiers.length === 0) {
      container.style.display = 'none';
      return;
    }

    var basePrice = tiers[0].price;

    var html = '<div class="ml-volume-heading">Tarifs dégressifs HT</div>';
    html += '<table class="ml-volume-table">';
    html += '<thead><tr><th>Quantité</th><th>Prix unitaire HT</th><th>Économie</th></tr></thead>';
    html += '<tbody>';

    tiers.forEach(function (tier, i) {
      var savings = Math.round((1 - tier.price / basePrice) * 100);
      var savingsHtml = savings > 0
        ? '<span class="ml-savings">-' + savings + '%</span>'
        : '';

      var priceHtml = U.formatPrice(tier.price);
      if (i === tiers.length - 1) {
        priceHtml = '<span class="ml-price-best">' + U.formatPrice(tier.price) + '</span>';
      }

      var qtyLabel = tier.qty === 1 ? 'À l\'unité' : 'x' + tier.qty;

      html += '<tr>';
      html += '<td>' + qtyLabel + '</td>';
      html += '<td>' + priceHtml + '</td>';
      html += '<td>' + savingsHtml + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table>';
    html += '<p class="ml-volume-note">Prix HT par unité · Minimum de commande : ' + tiers[0].qty + ' unités</p>';

    container.innerHTML = html;
  }

  /* -------------------------------------------------------
     INIT
     ------------------------------------------------------- */
  function init() {
    var containers = document.querySelectorAll('[data-ml-volume-pricing]');
    if (!containers.length) return;

    var handle = window.location.pathname.split('/products/')[1];
    if (!handle) return;
    handle = handle.split('?')[0].split('#')[0];

    U.loadProductMap()
      .then(function (map) {
        var tierStr = U.findTiers(handle, map);
        var tiers = U.parseTierString(tierStr);
        containers.forEach(function (container) {
          if (tiers.length) {
            renderTable(container, tiers);
          } else {
            container.style.display = 'none';
          }
        });
      })
      .catch(function () {
        containers.forEach(function (c) { c.style.display = 'none'; });
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
