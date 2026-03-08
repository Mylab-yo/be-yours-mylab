'use strict';

/**
 * MyLab Shop — Surcouche prix dégressifs sur le mini-cart Be Yours
 * Chargé globalement via layout/theme.liquid.
 *
 * Stratégie : on laisse le mini-cart Be Yours fonctionner normalement
 * et on remplace les prix + contrôles quantité par nos tarifs HT dégressifs.
 */

(function () {

  var DEBUG = true;
  console.log('[MyLab Cart] v2025-03-08b loaded');
  function log() {
    if (DEBUG) console.log.apply(console, ['[MyLab Cart]'].concat(Array.prototype.slice.call(arguments)));
  }

  /* -------------------------------------------------------
     GRILLES TARIFAIRES (centimes HT, prix unitaire)
     ------------------------------------------------------- */
  var TIERS = {
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
    spray_reparateur_200: [
      { qty: 6, price: 990 }, { qty: 12, price: 940 },
      { qty: 24, price: 890 }, { qty: 48, price: 790 }, { qty: 96, price: 710 }
    ],
    serum_50: [
      { qty: 6, price: 850 }, { qty: 12, price: 805 },
      { qty: 24, price: 765 }, { qty: 48, price: 680 }, { qty: 96, price: 610 }
    ],
    huile_50: [
      { qty: 6, price: 950 }, { qty: 12, price: 900 },
      { qty: 24, price: 850 }, { qty: 48, price: 760 }, { qty: 96, price: 680 }
    ],
    cire_50: [
      { qty: 6, price: 690 }, { qty: 12, price: 660 },
      { qty: 24, price: 630 }, { qty: 48, price: 600 }
    ],
    homme_masque_500: [
      { qty: 6, price: 1990 }, { qty: 12, price: 1790 },
      { qty: 24, price: 1690 }, { qty: 48, price: 1590 }, { qty: 96, price: 1430 }
    ]
  };

  /* -------------------------------------------------------
     DÉTECTION TIER KEY
     ------------------------------------------------------- */
  function detectTierKey(tags, title) {
    tags = (tags || []).map(function (t) { return t.toLowerCase().trim(); });
    title = (title || '').toLowerCase();
    var allTags = tags.join(' ');

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

    var gamme = '';
    if (allTags.includes('dejauniss') || allTags.includes('colorist') || title.includes('déjauniss') || title.includes('dejauniss') || title.includes('colorist')) {
      gamme = 'dejaunisseur';
    } else if (allTags.includes('homme') || allTags.includes('herborist') || title.includes('herborist')) {
      gamme = 'homme';
    }

    if (gamme === 'dejaunisseur') {
      var key = 'dejaunisseur_' + type + '_' + format;
      if (TIERS[key]) return key;
    }
    if (gamme === 'homme') {
      var key2 = 'homme_' + type + '_' + format;
      if (TIERS[key2]) return key2;
    }
    if (type === 'spray_reparateur') return 'spray_reparateur_200';

    var baseKey = type + '_' + format;
    if (TIERS[baseKey]) return baseKey;

    if (!format && (type === 'serum' || type === 'huile' || type === 'cire')) {
      var key3 = type + '_50';
      if (TIERS[key3]) return key3;
    }
    return null;
  }

  /* -------------------------------------------------------
     CACHE PRODUIT
     ------------------------------------------------------- */
  var productCache = {};

  function getProductData(handle) {
    if (productCache[handle]) return Promise.resolve(productCache[handle]);
    return fetch('/products/' + handle + '.js')
      .then(function (r) { return r.json(); })
      .then(function (product) { productCache[handle] = product; return product; });
  }

  /* -------------------------------------------------------
     CALCUL PRIX UNITAIRE
     ------------------------------------------------------- */
  function getUnitPrice(tierKey, quantity) {
    var tiers = TIERS[tierKey];
    if (!tiers) return null;
    var price = tiers[0].price;
    for (var i = 0; i < tiers.length; i++) {
      if (quantity >= tiers[i].qty) price = tiers[i].price;
    }
    return price;
  }

  function formatMoney(cents) {
    return (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' \u20ac';
  }

  /* -------------------------------------------------------
     DROPDOWN PALIER — remplace le +/- natif par un <select>
     ------------------------------------------------------- */
  function replaceQtyWithDropdown(li, qtyRow, tierKey, currentQty) {
    if (qtyRow.querySelector('.ml-qty-select')) return;

    var tiers = TIERS[tierKey];
    if (!tiers) return;

    var nativeInput = li.querySelector('input.quantity__input');
    if (!nativeInput) {
      log('No native input found in li', li);
      return;
    }
    var lineIndex = nativeInput.dataset.index;
    var variantId = nativeInput.dataset.quantityVariantId;

    var removeEl = li.querySelector('cart-remove-button');
    var removeIndex = removeEl ? removeEl.dataset.index : lineIndex;

    // Masquer tout le bloc natif quantité
    var nativeBlock = qtyRow.querySelector('dt');
    if (nativeBlock) nativeBlock.style.display = 'none';

    // Wrapper
    var wrapper = document.createElement('div');
    wrapper.className = 'ml-qty-wrapper';

    // <select>
    var select = document.createElement('select');
    select.className = 'ml-qty-select';
    select.name = 'updates[]';
    select.dataset.index = lineIndex;
    if (variantId) select.dataset.quantityVariantId = variantId;

    tiers.forEach(function (tier) {
      var opt = document.createElement('option');
      opt.value = tier.qty;
      opt.textContent = tier.qty + ' u. \u2014 ' + formatMoney(tier.price) + '/u';
      if (tier.qty === currentQty) opt.selected = true;
      select.appendChild(opt);
    });

    // Si qty actuelle hors palier, ajouter en premier
    var matched = tiers.some(function (t) { return t.qty === currentQty; });
    if (!matched && currentQty > 0) {
      var extra = document.createElement('option');
      extra.value = currentQty;
      extra.textContent = currentQty + ' u.';
      extra.selected = true;
      select.insertBefore(extra, select.firstChild);
    }

    // Quand le select change, appeler updateQuantity de Be Yours
    select.addEventListener('change', function () {
      log('Dropdown changed to', select.value);
      var cartItems = li.closest('cart-items');
      if (cartItems && typeof cartItems.updateQuantity === 'function') {
        cartItems.updateQuantity(lineIndex, parseInt(select.value));
      }
    });

    wrapper.appendChild(select);

    // Insérer le wrapper (juste le dropdown, sans Supprimer)
    var priceEl = qtyRow.querySelector('.ml-cart-line-price');
    if (priceEl) {
      qtyRow.insertBefore(wrapper, priceEl);
    } else {
      qtyRow.appendChild(wrapper);
    }

    // Lien Supprimer — placé dans le bloc prix (à droite, sous le total)
    var rightBlock = qtyRow.querySelector('.ml-cart-line-price');
    if (!rightBlock) {
      rightBlock = document.createElement('div');
      rightBlock.className = 'ml-cart-line-price';
      qtyRow.appendChild(rightBlock);
    }
    if (!rightBlock.querySelector('.ml-qty-remove')) {
      var removeLink = document.createElement('a');
      removeLink.className = 'ml-qty-remove';
      removeLink.textContent = 'Supprimer';
      removeLink.href = '#';
      removeLink.addEventListener('click', function (e) {
        e.preventDefault();
        var cartItems = li.closest('cart-items');
        if (cartItems && typeof cartItems.updateQuantity === 'function') {
          cartItems.updateQuantity(removeIndex, 0);
        }
      });
      rightBlock.appendChild(removeLink);
    }

    log('Dropdown injected for', tierKey, 'qty=', currentQty);
  }

  /* -------------------------------------------------------
     OVERRIDE DES PRIX + DROPDOWN
     ------------------------------------------------------- */
  var isApplying = false;

  function overrideMiniCartPrices() {
    var miniCart = document.getElementById('mini-cart');
    if (!miniCart) {
      log('mini-cart element not found');
      return;
    }

    var items = miniCart.querySelectorAll('cart-items li[data-handle]');
    log('Found', items.length, 'cart items');
    if (!items.length) return;

    // Collecter les handles
    var handles = [];
    items.forEach(function (li) {
      var h = li.dataset.handle;
      if (h && handles.indexOf(h) === -1) handles.push(h);
    });

    log('Fetching product data for', handles);

    Promise.all(handles.map(function (h) {
      return getProductData(h).catch(function (err) {
        log('Error fetching', h, err);
        return null;
      });
    })).then(function () {
      log('All products fetched, applying overrides');
      applyOverrides(miniCart, items);
      // Reconnecter l'observer sous-total (l'élément a pu être recréé par innerHTML)
      subtotalObserver = null;
      setupSubtotalObserver();
    });
  }

  function applyOverrides(miniCart, items) {
    isApplying = true;

    // Ajouter la classe .ml-active sur <mini-cart> dès le premier override.
    // Elle persiste même quand Be Yours remplace le innerHTML,
    // ce qui masque les éléments natifs via CSS (pas de flash).
    miniCart.classList.add('ml-active');

    var newSubtotal = 0;
    var hasOverride = false;

    items.forEach(function (li) {
      var handle = li.dataset.handle;
      var quantity = parseInt(li.dataset.quantity) || 1;
      var product = productCache[handle];

      if (!product) {
        log('No product data for', handle);
        return;
      }

      var tierKey = detectTierKey(product.tags, product.title);
      log('Product:', product.title, '→ tierKey:', tierKey, 'qty:', quantity);
      if (!tierKey) return;

      var unitPrice = getUnitPrice(tierKey, quantity);
      if (!unitPrice) return;

      hasOverride = true;
      var lineTotal = unitPrice * quantity;
      newSubtotal += lineTotal;

      // Les éléments natifs sont déjà masqués par CSS (.ml-active)
      // On injecte juste nos éléments custom

      // Remplacer le +/- par un dropdown + injecter prix
      var qtyRow = li.querySelector('.product-quantity');
      if (qtyRow) {
        replaceQtyWithDropdown(li, qtyRow, tierKey, quantity);

        // Prix aligné à droite (colonne : montant + Supprimer)
        var mlPrice = qtyRow.querySelector('.ml-cart-line-price');
        if (!mlPrice) {
          mlPrice = document.createElement('div');
          mlPrice.className = 'ml-cart-line-price';
          qtyRow.appendChild(mlPrice);
        }
        // Mettre le montant dans un sous-conteneur pour ne pas écraser le lien Supprimer
        var amountRow = mlPrice.querySelector('.ml-cart-line-price__row');
        if (!amountRow) {
          amountRow = document.createElement('div');
          amountRow.className = 'ml-cart-line-price__row';
          mlPrice.insertBefore(amountRow, mlPrice.firstChild);
        }
        amountRow.innerHTML =
          '<span class="ml-cart-line-price__amount">' + formatMoney(lineTotal) + '</span>' +
          '<span class="ml-cart-line-price__ht">HT</span>';
      } else {
        log('No .product-quantity found in li');
      }

      // Masquer le message d'erreur quantité natif Be Yours
      var errEl = li.querySelector('.cart-item__error');
      if (errEl) errEl.style.display = 'none';
    });

    // Sous-total HT
    if (hasOverride) {
      lastHtSubtotal = formatMoney(newSubtotal) + ' <span class="ml-cart-ht-label">HT</span>';
      writeSubtotal();
    }

    // Libérer le flag après stabilisation DOM
    setTimeout(function () { isApplying = false; }, 300);
  }

  /* -------------------------------------------------------
     SOUS-TOTAL PERSISTENT — Observer dédié
     Stocke le dernier sous-total HT et le réapplique
     instantanément si Be Yours le réécrit.
     ------------------------------------------------------- */
  var lastHtSubtotal = null;
  var subtotalObserver = null;
  var isWritingSubtotal = false;

  function writeSubtotal() {
    if (!lastHtSubtotal) return;
    isWritingSubtotal = true;
    document.querySelectorAll('#mini-cart-subtotal').forEach(function (el) {
      el.innerHTML = lastHtSubtotal;
    });
    // Fallback : .subtotal .value.price
    document.querySelectorAll('#mini-cart .subtotal .value.price, #cart .subtotal .value.price').forEach(function (el) {
      if (el.id !== 'mini-cart-subtotal') el.innerHTML = lastHtSubtotal;
    });
    log('Subtotal written:', lastHtSubtotal.replace(/<[^>]+>/g, ''));
    // Petit délai pour laisser le MutationObserver ignorer notre propre écriture
    setTimeout(function () { isWritingSubtotal = false; }, 50);
  }

  function setupSubtotalObserver() {
    if (subtotalObserver) return; // déjà en place
    var el = document.getElementById('mini-cart-subtotal');
    if (!el) return;

    subtotalObserver = new MutationObserver(function () {
      if (isWritingSubtotal || !lastHtSubtotal) return;
      // Be Yours a réécrit le sous-total → on le corrige immédiatement
      log('Subtotal observer: Be Yours overwrote subtotal, re-applying HT');
      writeSubtotal();
    });
    subtotalObserver.observe(el, { childList: true, characterData: true, subtree: true });
    log('Subtotal MutationObserver started');
  }

  /* -------------------------------------------------------
     HOOKS — plusieurs mécanismes pour garantir l'exécution
     ------------------------------------------------------- */

  // 1. MutationObserver sur #mini-cart
  var mutationTimer = null;

  function setupObserver() {
    var target = document.getElementById('mini-cart');
    if (!target) {
      log('mini-cart not in DOM yet, retrying in 1s...');
      setTimeout(setupObserver, 1000);
      return;
    }

    var obs = new MutationObserver(function (mutations) {
      if (isApplying) return;

      // Ne réagir qu'aux gros changements (innerHTML replacement), pas aux micro-mutations
      var dominated = mutations.some(function (m) {
        return m.type === 'childList' && m.addedNodes.length > 2;
      });
      if (!dominated) return;

      clearTimeout(mutationTimer);
      mutationTimer = setTimeout(function () {
        log('MutationObserver triggered');
        overrideMiniCartPrices();
      }, 400);
    });

    obs.observe(target, { childList: true, subtree: true });
    log('MutationObserver started on #mini-cart');
  }

  // 2. Monkey-patch MiniCart.renderContents (le plus fiable)
  function patchMiniCart() {
    var mc = document.querySelector('mini-cart');
    if (!mc) {
      log('mini-cart element not found for patching');
      return;
    }

    // Patch renderContents si la méthode existe sur le prototype
    var proto = Object.getPrototypeOf(mc);
    if (proto && proto.renderContents) {
      var original = proto.renderContents;
      proto.renderContents = function (parsedState) {
        log('renderContents intercepted');
        original.call(this, parsedState);
        // Laisser le DOM se mettre à jour, puis override
        setTimeout(overrideMiniCartPrices, 500);
      };
      log('MiniCart.renderContents patched');
    } else {
      log('renderContents not found on prototype, will rely on observer');
    }

    // Patch handleIntersection (chargement initial lazy)
    if (proto && proto.handleIntersection) {
      var origIntersect = proto.handleIntersection;
      proto.handleIntersection = function (entries, observer) {
        log('handleIntersection intercepted');
        origIntersect.call(this, entries, observer);
        // Le fetch + innerHTML se fait dans le .then, donner du temps
        setTimeout(overrideMiniCartPrices, 1000);
      };
      log('MiniCart.handleIntersection patched');
    }
  }

  // 3. Écouter les événements Be Yours
  function listenEvents() {
    document.addEventListener('cartdrawer:opened', function () {
      log('cartdrawer:opened event');
      setTimeout(overrideMiniCartPrices, 500);
    });

    document.addEventListener('cart:updated', function () {
      log('cart:updated event');
      setTimeout(overrideMiniCartPrices, 500);
    });
  }

  /* -------------------------------------------------------
     OUVRIR LE MINI-CART
     ------------------------------------------------------- */
  function openBeYoursCart() {
    var drawer = document.querySelector('cart-drawer');
    if (!drawer) return;

    if (typeof drawer.openMenuDrawer === 'function') {
      drawer.openMenuDrawer();
      return;
    }

    var summary = drawer.querySelector('details > summary');
    if (summary) summary.click();
  }

  /* -------------------------------------------------------
     REFRESH APRÈS AJOUT (appelé par mylab-product.js)
     ------------------------------------------------------- */
  function refreshCartAndOpen() {
    fetch('/cart.js', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        document.querySelectorAll('.cart-count-bubble span[aria-hidden="true"]').forEach(function (el) {
          el.textContent = cart.item_count;
        });
        document.querySelectorAll('.cart-count-bubble').forEach(function (el) {
          el.style.display = cart.item_count > 0 ? '' : 'none';
        });
      });

    // Recharger le contenu du mini-cart
    var miniCart = document.getElementById('mini-cart');
    if (miniCart) {
      var url = miniCart.dataset.url || '/?section_id=mini-cart';
      fetch(url)
        .then(function (r) { return r.text(); })
        .then(function (html) {
          var doc = new DOMParser().parseFromString(html, 'text/html');
          var section = doc.querySelector('.shopify-section');
          if (section) {
            miniCart.innerHTML = section.innerHTML;
            log('Mini-cart content reloaded');
            // L'observer + patch se chargeront de l'override
            setTimeout(overrideMiniCartPrices, 500);
          }
        });
    }

    openBeYoursCart();
  }

  /* -------------------------------------------------------
     INIT
     ------------------------------------------------------- */
  function init() {
    log('Initializing...');

    setupObserver();
    patchMiniCart();
    listenEvents();
    setupSubtotalObserver();

    // Override initial au cas où le cart est déjà chargé
    setTimeout(overrideMiniCartPrices, 1500);

    window.MylabCart = {
      open: refreshCartAndOpen,
      refresh: overrideMiniCartPrices
    };

    log('Ready. window.MylabCart exposed.');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
