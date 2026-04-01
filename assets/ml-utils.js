'use strict';

/**
 * MylabUtils — Utilitaires partagés MyLab Shop
 * Utilisé par : mylab-product.js, ml-volume-pricing.js, ml-quick-order
 */
(function () {
  var PRODUCT_MAP = null;

  function loadProductMap() {
    if (PRODUCT_MAP) return Promise.resolve(PRODUCT_MAP);
    var mapUrl = (window.MylabAssets && window.MylabAssets.productMapUrl) || '/assets/ml-product-map.json';
    return fetch(mapUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) { PRODUCT_MAP = data; return data; });
  }

  function parseTierString(str) {
    if (!str) return [];
    return str.split(',').map(function (t) {
      var p = t.split(':');
      return { qty: parseInt(p[0], 10), price: parseInt(p[1], 10) };
    });
  }

  function findProductEntry(handle, map) {
    if (map[handle]) return { entry: map[handle], size: null };
    var keys = Object.keys(map);
    for (var i = 0; i < keys.length; i++) {
      var entry = map[keys[i]];
      var sizes = entry.sizes || {};
      var sizeKeys = Object.keys(sizes);
      for (var s = 0; s < sizeKeys.length; s++) {
        if (sizes[sizeKeys[s]] === handle) {
          return { entry: entry, size: sizeKeys[s] };
        }
      }
    }
    return null;
  }

  function findTiers(handle, map) {
    var found = findProductEntry(handle, map);
    if (!found) return null;
    var entry = found.entry;
    var size = found.size;
    if (!size) {
      var sizeKeys = Object.keys(entry.sizes || {});
      for (var i = 0; i < sizeKeys.length; i++) {
        if (entry.sizes[sizeKeys[i]] === handle) { size = sizeKeys[i]; break; }
      }
      if (!size && sizeKeys.length > 0) size = sizeKeys[0];
    }
    var tierStr = entry.tiers ? entry.tiers[size] : null;
    return tierStr || null;
  }

  function formatPrice(centimes) {
    return (centimes / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' \u20ac';
  }

  function formatPriceCompact(centimes) {
    return (centimes / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  /** Formatte centimes en "X,XX" (sans symbole €) — utilisé par la commande express */
  function formatPriceRaw(centimes) {
    var e = Math.floor(centimes / 100);
    var c = centimes % 100;
    return e.toLocaleString('fr-FR') + ',' + (c < 10 ? '0' : '') + c;
  }

  window.MylabUtils = {
    loadProductMap: loadProductMap,
    parseTierString: parseTierString,
    findProductEntry: findProductEntry,
    findTiers: findTiers,
    formatPrice: formatPrice,
    formatPriceCompact: formatPriceCompact,
    formatPriceRaw: formatPriceRaw
  };
})();
