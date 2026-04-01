'use strict';

/**
 * MyLab Shop — Fiche produit B2B (Be Yours)
 * Contenance selector + paliers quantité + prix dynamique + CTA
 * Fonctionne sur page produit ET dans le quick view modal.
 * Dépend de ml-utils.js (MylabUtils)
 */

(function () {

  var U = window.MylabUtils;
  if (!U) { console.error('MyLab: ml-utils.js non chargé'); return; }

  /* -------------------------------------------------------
     HELPERS
     ------------------------------------------------------- */

  /** querySelector scopé au conteneur pricing (évite les collisions d'IDs en quick view) */
  function q(root, sel) { return root.querySelector(sel); }

  /**
   * Cache/montre les blocs natifs Be Yours (price, buy_buttons)
   * qui sont frères du bloc MyLab dans le même product__info-container.
   */
  function toggleNativeBlocks(root, show) {
    var infoContainer = root.closest('.product__info-container') || root.parentElement;
    if (!infoContainer) return;
    var selectors = [
      '[id^="price-"]:not([data-mylab-pricing] *)',
      '.product__tax',
      '.installment',
      '.volume-pricing-note'
    ];
    selectors.forEach(function (sel) {
      var el = infoContainer.querySelector(sel);
      if (el) el.style.display = show ? '' : 'none';
    });
    var buyBtns = infoContainer.querySelectorAll('.buy-buttons');
    buyBtns.forEach(function (bb) {
      if (!bb.closest('[data-mylab-pricing]') && !bb.closest('[data-mylab-fallback]')) {
        bb.style.display = show ? '' : 'none';
      }
    });
  }

  /* -------------------------------------------------------
     PALIERS — BOUTONS QUANTITÉ
     ------------------------------------------------------- */
  function renderQtyButtons(ctx) {
    var container = q(ctx.root, '#ml-qty-btns');
    if (!container) return;

    container.innerHTML = '';
    var basePrice = ctx.tiers[0].price;

    ctx.tiers.forEach(function (tier, index) {
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

      btn.addEventListener('click', function () { selectQty(ctx, this); });
      container.appendChild(btn);
    });

    return container;
  }

  function selectQty(ctx, btn) {
    var qty = parseInt(btn.dataset.qty);
    var unitPrice = parseInt(btn.dataset.price);

    ctx.root.querySelectorAll('.ml-qty-btn').forEach(function (b) {
      b.classList.remove('is-active');
      b.setAttribute('aria-pressed', 'false');
    });
    btn.classList.add('is-active');
    btn.setAttribute('aria-pressed', 'true');

    ctx.selectedQty = qty;
    updatePriceDisplay(ctx, qty, unitPrice);
    updatePalierTable(ctx, qty);
    updateCartButton(ctx, qty);
  }

  /* -------------------------------------------------------
     AFFICHAGE PRIX
     ------------------------------------------------------- */
  function updatePriceDisplay(ctx, qty, unitPrice) {
    var basePrice = ctx.tiers[0].price;
    var totalPrice = unitPrice * qty;
    var savings = (basePrice - unitPrice) * qty;

    var totalEl = q(ctx.root, '#ml-price-total');
    if (totalEl) {
      totalEl.classList.add('is-updating');
      setTimeout(function () {
        totalEl.textContent = U.formatPriceCompact(totalPrice);
        totalEl.classList.remove('is-updating');
      }, 120);
    }

    var unitEl = q(ctx.root, '#ml-price-unit');
    if (unitEl) unitEl.textContent = U.formatPrice(unitPrice);

    var savingsEl = q(ctx.root, '#ml-price-savings');
    var savingsText = q(ctx.root, '#ml-savings-text');
    if (savingsEl && savingsText) {
      if (savings > 0) {
        savingsText.textContent = 'Vous économisez ' + U.formatPrice(savings) + ' sur cette commande';
        savingsEl.classList.add('is-visible');
      } else {
        savingsEl.classList.remove('is-visible');
      }
    }
  }

  /* -------------------------------------------------------
     TABLE RÉCAP PALIERS
     ------------------------------------------------------- */
  function updatePalierTable(ctx, activeQty) {
    var tbody = q(ctx.root, '#ml-palier-body');
    if (!tbody) return;

    tbody.innerHTML = '';
    var basePrice = ctx.tiers[0].price;

    ctx.tiers.forEach(function (tier) {
      var discountPct = Math.round((1 - tier.price / basePrice) * 100);
      var isActive = tier.qty === activeQty;

      var tr = document.createElement('tr');
      if (isActive) tr.classList.add('is-active');

      var discountHtml = discountPct > 0
        ? '<span class="ml-discount-badge">-' + discountPct + '%</span>'
        : '<span class="ml-no-discount">—</span>';

      tr.innerHTML =
        '<td class="ml-palier-qty">' + tier.qty + ' unité' + (tier.qty > 1 ? 's' : '') + '</td>' +
        '<td class="ml-palier-price">' + U.formatPrice(tier.price) + '</td>' +
        '<td class="ml-palier-discount">' + discountHtml + '</td>';

      tbody.appendChild(tr);
    });
  }

  function updateCartButton(ctx, qty) {
    var pill = q(ctx.root, '#ml-cart-pill');
    if (pill) pill.textContent = qty + ' unité' + (qty > 1 ? 's' : '');
  }

  /* -------------------------------------------------------
     AJOUT AU PANIER
     ------------------------------------------------------- */
  function handleAddToCart(ctx) {
    var btn = q(ctx.root, '#ml-btn-cart');
    if (!btn || !ctx.variantId || !ctx.selectedQty) return;

    btn.classList.add('is-loading');
    btn.disabled = true;

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ items: [{ id: ctx.variantId, quantity: ctx.selectedQty }] })
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

      document.dispatchEvent(new CustomEvent('cart:refresh', { detail: { open: true } }));

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
     INIT — instancie un contexte par bloc [data-mylab-pricing]
     ------------------------------------------------------- */
  function initBlock(root) {
    var qtyContainer = q(root, '#ml-qty-btns');
    if (!qtyContainer) return;

    var handle = root.dataset.productHandle;
    if (!handle) {
      var pathParts = window.location.pathname.split('/products/');
      if (!pathParts[1]) return;
      handle = pathParts[1].split('?')[0].split('#')[0];
    }

    var ctx = {
      root: root,
      tiers: [],
      variantId: null,
      selectedQty: null
    };

    var cartBtn = q(root, '#ml-btn-cart');
    if (cartBtn && cartBtn.dataset.variantId) {
      ctx.variantId = parseInt(cartBtn.dataset.variantId);
    }
    if (cartBtn) {
      cartBtn.addEventListener('click', function () { handleAddToCart(ctx); });
    }

    Promise.all([
      U.loadProductMap(),
      fetch('/products/' + handle + '.js').then(function (r) { return r.json(); })
    ])
      .then(function (results) {
        var map = results[0];
        var product = results[1];
        var tierStr = U.findTiers(handle, map);
        var tiers = U.parseTierString(tierStr);

        if (!tiers || !tiers.length) {
          root.style.display = 'none';
          var fallback = root.parentElement && root.parentElement.querySelector('[data-mylab-fallback]');
          if (fallback) fallback.style.display = '';
          toggleNativeBlocks(root, true);
          return;
        }

        toggleNativeBlocks(root, false);
        ctx.tiers = tiers;

        if (!ctx.variantId && product.variants && product.variants.length > 0) {
          ctx.variantId = product.variants[0].id;
        }

        var container = renderQtyButtons(ctx);
        if (container) {
          var firstBtn = container.querySelector('.ml-qty-btn');
          if (firstBtn) selectQty(ctx, firstBtn);
        }
      })
      .catch(function (err) {
        console.error('MyLab: impossible de charger les données produit', err);
      });
  }

  function init() {
    var blocks = document.querySelectorAll('[data-mylab-pricing]');
    blocks.forEach(function (block) {
      if (block.dataset.mylabInit) return;
      block.dataset.mylabInit = '1';
      initBlock(block);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
