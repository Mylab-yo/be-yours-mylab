'use strict';

/**
 * MyLab Shop — Fiche produit B2B (Be Yours)
 * Contenance selector + paliers quantité + prix dynamique + CTA
 */

(function () {

  /* -------------------------------------------------------
     GRILLES TARIFAIRES (centimes HT, prix unitaire)
     ------------------------------------------------------- */
  var TIERS = {
    /* ---- SHAMPOINGS ---- */
    shampoing_200: [
      { qty: 6, price: 700 }, { qty: 12, price: 665 },
      { qty: 24, price: 630 }, { qty: 48, price: 560 }, { qty: 96, price: 500 }
    ],
    shampoing_500: [
      { qty: 6, price: 1490 }, { qty: 12, price: 1340 },
      { qty: 24, price: 1265 }, { qty: 48, price: 1190 }, { qty: 96, price: 1065 }
    ],
    shampoing_1000: [
      { qty: 1, price: 2490 }, { qty: 3, price: 2365 },
      { qty: 6, price: 2100 }, { qty: 12, price: 1865 }
    ],

    /* ---- MASQUES ---- */
    masque_200: [
      { qty: 6, price: 950 }, { qty: 12, price: 900 },
      { qty: 24, price: 855 }, { qty: 48, price: 760 }, { qty: 96, price: 680 }
    ],
    masque_400: [
      { qty: 6, price: 1690 }, { qty: 12, price: 1590 },
      { qty: 24, price: 1520 }, { qty: 48, price: 1350 }, { qty: 96, price: 1210 }
    ],
    masque_1000: [
      { qty: 1, price: 3290 }, { qty: 3, price: 3125 },
      { qty: 6, price: 2790 }, { qty: 12, price: 2465 }
    ],

    /* ---- CRÈMES SANS RINÇAGE ---- */
    creme_200: [
      { qty: 6, price: 850 }, { qty: 12, price: 805 },
      { qty: 24, price: 765 }, { qty: 48, price: 680 }, { qty: 96, price: 610 }
    ],
    creme_400: [
      { qty: 6, price: 1690 }, { qty: 12, price: 1590 },
      { qty: 24, price: 1520 }, { qty: 48, price: 1350 }, { qty: 96, price: 1210 }
    ],
    creme_1000: [
      { qty: 1, price: 3290 }, { qty: 3, price: 3125 },
      { qty: 6, price: 2790 }, { qty: 12, price: 2465 }
    ],

    /* ---- DÉJAUNISSEUR / COLORISTEUR ---- */
    dejaunisseur_shampoing_200: [
      { qty: 6, price: 750 }, { qty: 12, price: 710 },
      { qty: 24, price: 675 }, { qty: 48, price: 600 }, { qty: 96, price: 540 }
    ],
    dejaunisseur_masque_200: [
      { qty: 6, price: 960 }, { qty: 12, price: 910 },
      { qty: 24, price: 860 }, { qty: 48, price: 765 }, { qty: 96, price: 690 }
    ],
    dejaunisseur_shampoing_1000: [
      { qty: 1, price: 2890 }, { qty: 3, price: 2745 },
      { qty: 6, price: 2450 }, { qty: 12, price: 2160 }
    ],
    dejaunisseur_masque_1000: [
      { qty: 1, price: 3490 }, { qty: 3, price: 3315 },
      { qty: 6, price: 2965 }, { qty: 12, price: 2615 }
    ],

    /* ---- MASQUE RÉPARATEUR SPRAY ---- */
    spray_reparateur_200: [
      { qty: 6, price: 990 }, { qty: 12, price: 940 },
      { qty: 24, price: 890 }, { qty: 48, price: 790 }, { qty: 96, price: 710 }
    ],

    /* ---- SÉRUM 50ml ---- */
    serum_50: [
      { qty: 6, price: 850 }, { qty: 12, price: 805 },
      { qty: 24, price: 765 }, { qty: 48, price: 680 }, { qty: 96, price: 610 }
    ],

    /* ---- HUILE 50ml ---- */
    huile_50: [
      { qty: 6, price: 950 }, { qty: 12, price: 900 },
      { qty: 24, price: 850 }, { qty: 48, price: 760 }, { qty: 96, price: 680 }
    ],

    /* ---- CIRES 50ml ---- */
    cire_50: [
      { qty: 6, price: 690 }, { qty: 12, price: 660 },
      { qty: 24, price: 630 }, { qty: 48, price: 600 }
    ],

    /* ---- HOMME : MASQUE INTENSE 500ml ---- */
    homme_masque_500: [
      { qty: 6, price: 1990 }, { qty: 12, price: 1790 },
      { qty: 24, price: 1690 }, { qty: 48, price: 1590 }, { qty: 96, price: 1430 }
    ]
  };

  /* -------------------------------------------------------
     DÉTECTION DU TYPE DE GRILLE (tags + titre)
     ------------------------------------------------------- */
  function detectTierKey(productData) {
    var tags = (productData.tags || []).map(function (t) { return t.toLowerCase().trim(); });
    var title = (productData.title || '').toLowerCase();
    var allTags = tags.join(' ');

    // Format
    var format = '';
    tags.forEach(function (tag) {
      if (tag === '1000ml' || tag === '1l') format = '1000';
      else if (tag === '500ml' && !format) format = '500';
      else if (tag === '400ml' && !format) format = '400';
      else if (tag === '200ml' && !format) format = '200';
      else if (tag === '50ml' && !format) format = '50';
    });
    if (!format) {
      if (title.includes('1000') || title.includes('1l')) format = '1000';
      else if (title.includes('500')) format = '500';
      else if (title.includes('400')) format = '400';
      else if (title.includes('200')) format = '200';
      else if (title.includes('50ml')) format = '50';
    }

    // Type
    var type = '';
    if (allTags.includes('shampoing') || title.includes('shampoing') || title.includes('shampooing')) {
      type = 'shampoing';
    } else if ((allTags.includes('spray') || title.includes('spray')) && (allTags.includes('masque') || title.includes('masque'))) {
      type = 'spray_reparateur';
    } else if (allTags.includes('masque') || title.includes('masque')) {
      type = 'masque';
    } else if (allTags.includes('creme') || allTags.includes('crème') || title.includes('crème') || title.includes('creme')) {
      type = 'creme';
    } else if (allTags.includes('serum') || allTags.includes('sérum') || title.includes('sérum') || title.includes('serum')) {
      type = 'serum';
    } else if (allTags.includes('huile') || title.includes('huile') || title.includes('bain miraculeux')) {
      type = 'huile';
    } else if (allTags.includes('cire') || title.includes('cire')) {
      type = 'cire';
    }

    // Gamme spéciale
    var gamme = '';
    if (allTags.includes('dejauniss') || allTags.includes('colorist') || title.includes('déjauniss') || title.includes('dejauniss') || title.includes('colorist')) {
      gamme = 'dejaunisseur';
    } else if (allTags.includes('homme') || allTags.includes('herborist') || title.includes('herborist')) {
      gamme = 'homme';
    }

    // Construire la clé
    if (gamme === 'dejaunisseur') {
      var key = 'dejaunisseur_' + type + '_' + format;
      if (TIERS[key]) return key;
    }
    if (gamme === 'homme') {
      var key2 = 'homme_' + type + '_' + format;
      if (TIERS[key2]) return key2;
    }
    if (type === 'spray_reparateur') {
      return 'spray_reparateur_200';
    }

    var baseKey = type + '_' + format;
    if (TIERS[baseKey]) return baseKey;

    // Fallback 50ml
    if (!format && (type === 'serum' || type === 'huile' || type === 'cire')) {
      var key3 = type + '_50';
      if (TIERS[key3]) return key3;
    }

    return null;
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

      // Mettre à jour le panier Be Yours
      refreshBeYoursCart();

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

  function refreshBeYoursCart() {
    fetch('/cart.js', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        // Mettre à jour les bulles compteur
        document.querySelectorAll('.cart-count-bubble span[aria-hidden="true"]').forEach(function (el) {
          el.textContent = cart.item_count;
        });
        document.querySelectorAll('.cart-count-bubble').forEach(function (el) {
          el.style.display = cart.item_count > 0 ? '' : 'none';
        });

        // Essayer d'ouvrir le mini-cart Be Yours
        var miniCart = document.querySelector('mini-cart');
        if (miniCart && typeof miniCart.open === 'function') {
          miniCart.open();
        } else {
          var cartDrawer = document.querySelector('cart-drawer');
          if (cartDrawer && typeof cartDrawer.open === 'function') {
            cartDrawer.open();
          }
        }
      })
      .catch(function () {});
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

    fetch('/products/' + handle + '.js')
      .then(function (r) { return r.json(); })
      .then(function (product) {
        var tierKey = detectTierKey(product);
        if (!tierKey || !TIERS[tierKey]) {
          // Masquer le bloc MyLab si pas de grille
          var wrapper = document.querySelector('[data-mylab-pricing]');
          if (wrapper) wrapper.style.display = 'none';
          return;
        }

        state.currentTiers = TIERS[tierKey];

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
