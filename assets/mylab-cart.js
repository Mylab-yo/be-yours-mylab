'use strict';

/**
 * MyLab Shop — Surcouche prix dégressifs sur le mini-cart Be Yours
 * Chargé globalement via layout/theme.liquid.
 *
 * Stratégie : on laisse le mini-cart Be Yours fonctionner normalement
 * (gift wrapping, discount codes, shipping calc, notes, recommandations…)
 * et on remplace uniquement les prix affichés par nos tarifs HT dégressifs.
 */

(function () {

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
    return (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
  }

  /* -------------------------------------------------------
     OVERRIDE DES PRIX DANS LE MINI-CART BE YOURS
     On lit les <li> du mini-cart, fetch les produits,
     puis remplace le contenu des <price-money> et du subtotal.
     ------------------------------------------------------- */
  var overrideRunning = false;

  function overrideMiniCartPrices() {
    var miniCart = document.querySelector('mini-cart');
    if (!miniCart) return;

    // Trouver tous les items du panier
    var items = miniCart.querySelectorAll('cart-items li[data-handle]');
    if (!items.length) return;

    // Éviter les exécutions multiples simultanées
    if (overrideRunning) return;
    overrideRunning = true;

    // Collecter les handles uniques
    var handles = [];
    items.forEach(function (li) {
      var handle = li.dataset.handle;
      if (handle && handles.indexOf(handle) === -1) handles.push(handle);
    });

    // Fetch tous les produits
    var promises = handles.map(function (handle) {
      return getProductData(handle).catch(function () { return null; });
    });

    Promise.all(promises).then(function () {
      var newSubtotal = 0;
      var hasOverride = false;

      items.forEach(function (li) {
        var handle = li.dataset.handle;
        var quantity = parseInt(li.dataset.quantity) || 1;
        var product = productCache[handle];

        if (!product) return;

        var tierKey = detectTierKey(product.tags, product.title);
        if (!tierKey) return;

        var unitPrice = getUnitPrice(tierKey, quantity);
        if (!unitPrice) return;

        hasOverride = true;
        var lineTotal = unitPrice * quantity;
        newSubtotal += lineTotal;

        // Remplacer le prix unitaire affiché
        var priceMoneyEls = li.querySelectorAll('price-money bdi');
        if (priceMoneyEls.length > 0) {
          // Le premier est le prix unitaire (ou prix barré + prix sale)
          // On remplace le dernier <price-money> visible (le prix effectif)
          var lastPrice = priceMoneyEls[priceMoneyEls.length - 1];
          lastPrice.textContent = formatMoney(unitPrice) + ' HT';
        }

        // Si prix barré (sale), masquer l'ancien prix barré
        var strikeEl = li.querySelector('.price--on-sale s');
        if (strikeEl) strikeEl.style.display = 'none';

        // Ajouter info quantité × prix si pas déjà fait
        var descEl = li.querySelector('.product-description .product-content');
        if (descEl && !descEl.querySelector('.ml-cart-line-info')) {
          var infoEl = document.createElement('div');
          infoEl.className = 'ml-cart-line-info';
          infoEl.style.cssText = 'font-size:1.2rem;color:#888;margin-top:2px;';
          infoEl.textContent = quantity + ' × ' + formatMoney(unitPrice) + ' HT = ' + formatMoney(lineTotal) + ' HT';
          descEl.appendChild(infoEl);
        } else if (descEl) {
          var existing = descEl.querySelector('.ml-cart-line-info');
          if (existing) existing.textContent = quantity + ' × ' + formatMoney(unitPrice) + ' HT = ' + formatMoney(lineTotal) + ' HT';
        }
      });

      // Remplacer le sous-total
      if (hasOverride) {
        var subtotalEl = document.getElementById('mini-cart-subtotal');
        if (subtotalEl) {
          subtotalEl.textContent = formatMoney(newSubtotal) + ' HT';
        }
      }

      overrideRunning = false;
    }).catch(function () {
      overrideRunning = false;
    });
  }

  /* -------------------------------------------------------
     OBSERVER LE MINI-CART POUR RE-OVERRIDE APRÈS CHAQUE RENDER
     Be Yours remplace le innerHTML du mini-cart à chaque update.
     On observe les mutations pour réappliquer nos prix.
     ------------------------------------------------------- */
  function setupMiniCartObserver() {
    var miniCart = document.querySelector('mini-cart');
    if (!miniCart) return;

    var observer = new MutationObserver(function () {
      // Petit délai pour laisser Be Yours finir le render
      setTimeout(overrideMiniCartPrices, 100);
    });

    observer.observe(miniCart, { childList: true, subtree: true });

    // Override initial aussi
    setTimeout(overrideMiniCartPrices, 500);
  }

  /* -------------------------------------------------------
     OUVRIR LE MINI-CART BE YOURS (pour notre CTA custom)
     ------------------------------------------------------- */
  function openBeYoursCart() {
    // Méthode 1 : Ouvrir le <details> du cart-drawer
    var details = document.querySelector('cart-drawer > details');
    if (details) {
      details.open = true;
      // Be Yours charge le contenu lazily via fetch
      var miniCart = details.querySelector('mini-cart');
      if (miniCart && miniCart.dataset.url) {
        fetch(miniCart.dataset.url)
          .then(function (r) { return r.text(); })
          .then(function (html) {
            var parser = new DOMParser();
            var doc = parser.parseFromString(html, 'text/html');
            var newContent = doc.querySelector('.mini-cart__inner');
            var inner = miniCart.querySelector('.mini-cart__inner');
            if (newContent && inner) {
              inner.innerHTML = newContent.innerHTML;
            } else if (newContent) {
              miniCart.innerHTML = '<div class="mini-cart__inner">' + newContent.innerHTML + '</div>';
            }
            // Les prix seront overridés par le MutationObserver
          });
      }
      return;
    }

    // Fallback : click sur le summary du cart
    var summary = document.querySelector('cart-drawer > details > summary');
    if (summary) summary.click();
  }

  /* -------------------------------------------------------
     REFRESH APRÈS AJOUT AU PANIER (appelé par mylab-product.js)
     Fetch le mini-cart section HTML et injecte dans Be Yours
     ------------------------------------------------------- */
  function refreshCartAndOpen() {
    // Mettre à jour les bulles compteur
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

    // Ouvrir et rafraîchir le mini-cart Be Yours
    openBeYoursCart();
  }

  /* -------------------------------------------------------
     INIT
     ------------------------------------------------------- */
  function init() {
    setupMiniCartObserver();

    // Exposer globalement
    window.MylabCart = {
      open: refreshCartAndOpen,
      refresh: overrideMiniCartPrices
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
