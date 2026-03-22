'use strict';

/**
 * ML Volume Pricing — Tarifs dégressifs MyLab
 * Lit les paliers depuis assets/ml-product-map.json (source de vérité unique).
 */

(function () {
  var PRODUCT_MAP = null;

  function loadProductMap() {
    if (PRODUCT_MAP) return Promise.resolve(PRODUCT_MAP);
    return fetch((window.MylabAssets && window.MylabAssets.productMapUrl) || '/assets/ml-product-map.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { PRODUCT_MAP = data; return data; });
  }

  function findTiers(handle, map) {
    /* Cherche directement par handle (clé = handle 200ml) */
    if (map[handle] && map[handle].tiers) {
      var sizes = map[handle].sizes || {};
      var sizeKeys = Object.keys(sizes);
      for (var i = 0; i < sizeKeys.length; i++) {
        if (sizes[sizeKeys[i]] === handle && map[handle].tiers[sizeKeys[i]]) {
          return map[handle].tiers[sizeKeys[i]];
        }
      }
      /* Fallback : première taille disponible */
      if (sizeKeys.length > 0) return map[handle].tiers[sizeKeys[0]];
    }
    /* Cherche dans les sizes de chaque entrée */
    var keys = Object.keys(map);
    for (var k = 0; k < keys.length; k++) {
      var entry = map[keys[k]];
      var entrySizes = entry.sizes || {};
      var eKeys = Object.keys(entrySizes);
      for (var s = 0; s < eKeys.length; s++) {
        if (entrySizes[eKeys[s]] === handle && entry.tiers && entry.tiers[eKeys[s]]) {
          return entry.tiers[eKeys[s]];
        }
      }
    }
    return null;
  }

  function parseTierString(str) {
    if (!str) return [];
    return str.split(',').map(function (t) {
      var p = t.split(':');
      return { qty: parseInt(p[0], 10), price: parseInt(p[1], 10) };
    });
  }

  /* -------------------------------------------------------
     RENDU DU TABLEAU
     ------------------------------------------------------- */
  function formatPrice(centimes) {
    return (centimes / 100).toFixed(2).replace('.', ',') + ' €';
  }

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
      var savingsHtml = '';
      if (savings > 0) {
        savingsHtml = '<span class="ml-savings">-' + savings + '%</span>';
      }

      var priceHtml = formatPrice(tier.price);
      if (i === tiers.length - 1) {
        priceHtml = '<span class="ml-price-best">' + formatPrice(tier.price) + '</span>';
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

    loadProductMap()
      .then(function (map) {
        var tierStr = findTiers(handle, map);
        var tiers = parseTierString(tierStr);
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
