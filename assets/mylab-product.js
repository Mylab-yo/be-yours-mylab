'use strict';

/**
 * MyLab Shop — Fiche produit B2B (Be Yours)
 * Contenance selector + paliers quantité + prix dynamique + CTA
 */

(function () {

  /* -------------------------------------------------------
     GRILLES TARIFAIRES (centimes HT, prix unitaire)
     ------------------------------------------------------- */
  /* -------------------------------------------------------
     PRODUCT MAP — source de vérité unique
     Chargé depuis assets/ml-product-map.json
     ------------------------------------------------------- */
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
    /* Cherche directement par handle (clé = handle 200ml) */
    if (map[handle]) return { entry: map[handle], size: null };
    /* Cherche dans les sizes de chaque entrée */
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

  function detectTiers(handle, map) {
    var found = findProductEntry(handle, map);
    if (!found) return null;
    var entry = found.entry;
    var size = found.size;
    /* Si on a trouvé par la clé directe, déterminer la taille du produit courant */
    if (!size) {
      var sizeKeys = Object.keys(entry.sizes || {});
      for (var i = 0; i < sizeKeys.length; i++) {
        if (entry.sizes[sizeKeys[i]] === handle) { size = sizeKeys[i]; break; }
      }
      if (!size && sizeKeys.length > 0) size = sizeKeys[0];
    }
    var tierStr = entry.tiers ? entry.tiers[size] : null;
    if (!tierStr) return null;
    return parseTierString(tierStr);
  }

  /* -------------------------------------------------------
     STATE & HELPERS
     ------------------------------------------------------- */
  var state = {
    selectedQty: null,
    currentTiers: [],
    variantId: null
  };

  function formatMoney(cents) {
    return (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
  }

  function formatMoneyCompact(cents) {
    return (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  /* -------------------------------------------------------
     PALIERS — BOUTONS QUANTITÉ
     ------------------------------------------------------- */
  function renderQtyButtons(tiers) {
    var container = document.getElementById('ml-qty-btns');
    if (!container) return;

    container.innerHTML = '';
    var basePrice = tiers[0].price;

    tiers.forEach(function (tier, index) {
      var discountPct = Math.round((1 - tier.price / basePrice) * 100);
      var btn = document.createElement('button');
      btn.className = 'ml-qty-btn' + (index === 0 ? ' is-active' : '');
      btn.setAttribute('data-qty', tier.qty);
      btn.setAttribute('data-price', tier.price);
      btn.setAttribute('aria-pressed', index === 0 ? 'true' : 'false');

      var badgeHtml = discountPct > 0
        ? '<span class="ml-qty-btn__badge">-' + discountPct + '%</span>'
        : '';

      btn.innerHTML =
        '<span class="ml-qty-btn__num">' + tier.qty + '</span>' +
        '<span class="ml-qty-btn__label">unité' + (tier.qty > 1 ? 's' : '') + '</span>' +
        badgeHtml;

      btn.addEventListener('click', function () { selectQty(this); });
      container.appendChild(btn);
    });
  }

  function selectQty(btn) {
    var qty = parseInt(btn.dataset.qty);
    var unitPrice = parseInt(btn.dataset.price);

    document.querySelectorAll('.ml-qty-btn').forEach(function (b) {
      b.classList.remove('is-active');
      b.setAttribute('aria-pressed', 'false');
    });
    btn.classList.add('is-active');
    btn.setAttribute('aria-pressed', 'true');

    state.selectedQty = qty;
    updatePriceDisplay(qty, unitPrice);
    updatePalierTable(qty);
    updateCartButton(qty);
  }

  /* -------------------------------------------------------
     AFFICHAGE PRIX
     ------------------------------------------------------- */
  function updatePriceDisplay(qty, unitPrice) {
    var basePrice = state.currentTiers[0].price;
    var totalPrice = unitPrice * qty;
    var savings = (basePrice - unitPrice) * qty;

    var totalEl = document.getElementById('ml-price-total');
    if (totalEl) {
      totalEl.classList.add('is-updating');
      setTimeout(function () {
        totalEl.textContent = formatMoneyCompact(totalPrice);
        totalEl.classList.remove('is-updating');
      }, 120);
    }

    var unitEl = document.getElementById('ml-price-unit');
    if (unitEl) unitEl.textContent = formatMoney(unitPrice);

    var savingsEl = document.getElementById('ml-price-savings');
    var savingsText = document.getElementById('ml-savings-text');
    if (savingsEl && savingsText) {
      if (savings > 0) {
        savingsText.textContent = 'Vous économisez ' + formatMoney(savings) + ' sur cette commande';
        savingsEl.classList.add('is-visible');
      } else {
        savingsEl.classList.remove('is-visible');
      }
    }
  }

  /* -------------------------------------------------------
     TABLE RÉCAP PALIERS
     ------------------------------------------------------- */
  function updatePalierTable(activeQty) {
    var tbody = document.getElementById('ml-palier-body');
    if (!tbody) return;

    tbody.innerHTML = '';
    var basePrice = state.currentTiers[0].price;

    state.currentTiers.forEach(function (tier) {
      var unitPrice = tier.price;
      var discountPct = Math.round((1 - unitPrice / basePrice) * 100);
      var isActive = tier.qty === activeQty;

      var tr = document.createElement('tr');
      if (isActive) tr.classList.add('is-active');

      var discountHtml = discountPct > 0
        ? '<span class="ml-discount-badge">-' + discountPct + '%</span>'
        : '<span class="ml-no-discount">—</span>';

      tr.innerHTML =
        '<td class="ml-palier-qty">' + tier.qty + ' unité' + (tier.qty > 1 ? 's' : '') + '</td>' +
        '<td class="ml-palier-price">' + formatMoney(unitPrice) + '</td>' +
        '<td class="ml-palier-discount">' + discountHtml + '</td>';

      tbody.appendChild(tr);
    });
  }

  function updateCartButton(qty) {
    var pill = document.getElementById('ml-cart-pill');
    if (pill) pill.textContent = qty + ' unité' + (qty > 1 ? 's' : '');
  }

  /* -------------------------------------------------------
     AJOUT AU PANIER
     ------------------------------------------------------- */
  function handleAddToCart() {
    var btn = document.getElementById('ml-btn-cart');
    if (!btn || !state.variantId || !state.selectedQty) return;

    btn.classList.add('is-loading');
    btn.disabled = true;

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ items: [{ id: state.variantId, quantity: state.selectedQty }] })
    })
    .then(function (response) {
      if (!response.ok) throw new Error('Erreur ajout panier');
      return response.json();
    })
    .then(function () {
      btn.classList.remove('is-loading');
      btn.classList.add('is-success');
      var textEl = btn.querySelector('.ml-btn-cart__text');
      if (textEl) textEl.textContent = 'Ajouté !';

      // Ouvrir le panier MyLab custom
      if (window.MylabCart && window.MylabCart.open) {
        window.MylabCart.open();
      }

      setTimeout(function () {
        btn.classList.remove('is-success');
        btn.disabled = false;
        if (textEl) textEl.textContent = 'Ajouter au panier';
      }, 2000);
    })
    .catch(function (error) {
      console.error('MyLab Cart Error:', error);
      btn.classList.remove('is-loading');
      btn.disabled = false;
      btn.classList.add('is-error');
      setTimeout(function () { btn.classList.remove('is-error'); }, 2000);
    });
  }

  /* -------------------------------------------------------
     INIT
     ------------------------------------------------------- */
  function init() {
    var container = document.getElementById('ml-qty-btns');
    if (!container) return;

    var pathParts = window.location.pathname.split('/products/');
    if (!pathParts[1]) return;
    var handle = pathParts[1].split('?')[0].split('#')[0];

    // Variant ID depuis le bouton CTA ou le bouton contenance actif
    var cartBtn = document.getElementById('ml-btn-cart');
    var activeContBtn = document.querySelector('.ml-contenance-btn.is-active');

    if (activeContBtn && activeContBtn.dataset.variantId) {
      state.variantId = parseInt(activeContBtn.dataset.variantId);
    } else if (cartBtn && cartBtn.dataset.variantId) {
      state.variantId = parseInt(cartBtn.dataset.variantId);
    }

    if (cartBtn) {
      cartBtn.addEventListener('click', handleAddToCart);
    }

    Promise.all([
      loadProductMap(),
      fetch('/products/' + handle + '.js').then(function (r) { return r.json(); })
    ])
      .then(function (results) {
        var map = results[0];
        var product = results[1];
        var tiers = detectTiers(handle, map);

        if (!tiers || !tiers.length) {
          // Pas de paliers volume : masquer le bloc MyLab, afficher le formulaire natif
          var wrapper = document.querySelector('[data-mylab-pricing]');
          if (wrapper) wrapper.style.display = 'none';
          var fallback = document.querySelector('[data-mylab-fallback]');
          if (fallback) fallback.style.display = '';
          return;
        }

        state.currentTiers = tiers;

        // Si pas de variant ID depuis Liquid, utiliser le premier variant
        if (!state.variantId && product.variants && product.variants.length > 0) {
          state.variantId = product.variants[0].id;
        }

        renderQtyButtons(state.currentTiers);
        var firstBtn = container.querySelector('.ml-qty-btn');
        if (firstBtn) selectQty(firstBtn);
      })
      .catch(function (err) {
        console.error('MyLab: impossible de charger les données produit', err);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
