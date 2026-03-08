'use strict';

/**
 * MyLab Shop — Panier custom avec prix dégressifs (Be Yours)
 * Chargé globalement via layout/theme.liquid.
 * Recalcule les prix HT depuis les paliers hardcodés.
 */

(function () {

  /* -------------------------------------------------------
     GRILLES TARIFAIRES (centimes HT, prix unitaire)
     Même données que mylab-product.js — source unique à terme.
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
     DÉTECTION TIER KEY (identique à mylab-product.js)
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
     CACHE PRODUIT — on fetch les tags par handle
     ------------------------------------------------------- */
  var productCache = {};

  function getProductData(handle) {
    if (productCache[handle]) {
      return Promise.resolve(productCache[handle]);
    }
    return fetch('/products/' + handle + '.js')
      .then(function (r) { return r.json(); })
      .then(function (product) {
        productCache[handle] = product;
        return product;
      });
  }

  /* -------------------------------------------------------
     CALCUL PRIX UNITAIRE DEPUIS LES TIERS
     ------------------------------------------------------- */
  function getUnitPriceFromTiers(tierKey, quantity) {
    var tiers = TIERS[tierKey];
    if (!tiers) return null;

    var unitPrice = tiers[0].price;
    for (var i = 0; i < tiers.length; i++) {
      if (quantity >= tiers[i].qty) unitPrice = tiers[i].price;
    }
    return unitPrice;
  }

  /* -------------------------------------------------------
     HELPERS
     ------------------------------------------------------- */
  function formatMoney(cents) {
    return (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
  }

  /* -------------------------------------------------------
     RENDU DU PANIER
     ------------------------------------------------------- */
  function renderCart(cart, tierMap) {
    var itemsContainer = document.getElementById('ml-drawer-items');
    var emptyEl = document.getElementById('ml-drawer-empty');
    var footerEl = document.getElementById('ml-drawer-footer');
    var subtotalEl = document.getElementById('ml-drawer-subtotal');
    var countEl = document.getElementById('ml-drawer-count');

    if (!itemsContainer) return;

    if (countEl) countEl.textContent = cart.item_count;

    if (cart.item_count === 0) {
      itemsContainer.innerHTML = '';
      if (emptyEl) emptyEl.style.display = 'flex';
      if (footerEl) footerEl.style.display = 'none';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';
    if (footerEl) footerEl.style.display = 'block';

    // Calculer le sous-total avec les vrais prix remisés
    var calculatedTotal = 0;
    var itemsHtml = '';

    cart.items.forEach(function (item) {
      var tierKey = tierMap[item.product_id] || null;
      var unitPrice = tierKey ? getUnitPriceFromTiers(tierKey, item.quantity) : null;
      var linePrice = unitPrice ? unitPrice * item.quantity : item.line_price;
      var displayUnitPrice = unitPrice || item.price;

      calculatedTotal += linePrice;

      var imgHtml = item.image
        ? '<img src="' + item.image + '" alt="' + item.product_title + '" loading="lazy">'
        : '<div class="ml-cart-item__img-placeholder"></div>';

      var variantHtml = (item.variant_title && item.variant_title !== 'Default Title')
        ? '<div class="ml-cart-item__variant">' + item.variant_title + '</div>'
        : '';

      itemsHtml +=
        '<div class="ml-cart-item" data-key="' + item.key + '">' +
          '<div class="ml-cart-item__img">' + imgHtml + '</div>' +
          '<div class="ml-cart-item__details">' +
            '<div class="ml-cart-item__name">' + item.product_title + '</div>' +
            variantHtml +
            '<div class="ml-cart-item__price-row">' +
              '<span class="ml-cart-item__qty">' + item.quantity + ' × ' + formatMoney(displayUnitPrice) + ' HT</span>' +
              '<span class="ml-cart-item__price">' + formatMoney(linePrice) + ' HT</span>' +
            '</div>' +
            '<button class="ml-cart-item__remove" data-key="' + item.key + '" aria-label="Supprimer">' +
              '<svg width="10" height="10" viewBox="0 0 14 14" fill="none">' +
                '<path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' +
              '</svg>' +
              ' Supprimer' +
            '</button>' +
          '</div>' +
        '</div>';
    });

    if (subtotalEl) subtotalEl.textContent = formatMoney(calculatedTotal) + ' HT';
    itemsContainer.innerHTML = itemsHtml;

    // Listeners suppression
    itemsContainer.querySelectorAll('.ml-cart-item__remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        updateCartItem(btn.dataset.key, 0);
      });
    });
  }

  function updateCartItem(key, quantity) {
    fetch('/cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ id: key, quantity: quantity })
    })
    .then(function (r) { return r.json(); })
    .then(function (cart) {
      fetchAndRenderCart();
      updateCartCount(cart.item_count);
    })
    .catch(function (err) { console.error('MyLab Cart Update Error:', err); });
  }

  /* -------------------------------------------------------
     FETCH CART + RÉSOLUTION DES TIERS PAR PRODUIT
     ------------------------------------------------------- */
  function fetchAndRenderCart() {
    return fetch('/cart.js', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        updateCartCount(cart.item_count);

        if (cart.item_count === 0) {
          renderCart(cart, {});
          return;
        }

        // Récupérer les données produit pour chaque article (pour détection des tiers)
        var handles = [];
        var handleToProductId = {};
        cart.items.forEach(function (item) {
          if (item.handle && handles.indexOf(item.handle) === -1) {
            handles.push(item.handle);
            handleToProductId[item.handle] = item.product_id;
          }
        });

        var promises = handles.map(function (handle) {
          return getProductData(handle).then(function (product) {
            return { handle: handle, product: product };
          }).catch(function () {
            return { handle: handle, product: null };
          });
        });

        return Promise.all(promises).then(function (results) {
          var tierMap = {};
          results.forEach(function (r) {
            if (r.product) {
              var tierKey = detectTierKey(r.product.tags, r.product.title);
              var productId = handleToProductId[r.handle] || r.product.id;
              tierMap[productId] = tierKey;
            }
          });
          renderCart(cart, tierMap);
        });
      })
      .catch(function (err) { console.error('MyLab Fetch Cart Error:', err); });
  }

  /* -------------------------------------------------------
     CART COUNT
     ------------------------------------------------------- */
  function updateCartCount(count) {
    // Mettre à jour la bulle Be Yours
    document.querySelectorAll('.cart-count-bubble span[aria-hidden="true"]').forEach(function (el) {
      el.textContent = count;
    });
    document.querySelectorAll('.cart-count-bubble').forEach(function (el) {
      el.style.display = count > 0 ? '' : 'none';
    });
    // Mettre à jour notre compteur
    var drawerCount = document.getElementById('ml-drawer-count');
    if (drawerCount) drawerCount.textContent = count;
  }

  /* -------------------------------------------------------
     DRAWER OPEN / CLOSE
     ------------------------------------------------------- */
  function openDrawer() {
    var drawer = document.getElementById('ml-cart-drawer');
    var overlay = document.getElementById('ml-drawer-overlay');
    if (drawer) {
      drawer.classList.add('is-open');
      drawer.setAttribute('aria-hidden', 'false');
    }
    if (overlay) {
      overlay.classList.add('is-visible');
      overlay.setAttribute('aria-hidden', 'false');
    }
    document.body.classList.add('ml-drawer-open');
  }

  function closeDrawer() {
    var drawer = document.getElementById('ml-cart-drawer');
    var overlay = document.getElementById('ml-drawer-overlay');
    if (drawer) {
      drawer.classList.remove('is-open');
      drawer.setAttribute('aria-hidden', 'true');
    }
    if (overlay) {
      overlay.classList.remove('is-visible');
      overlay.setAttribute('aria-hidden', 'true');
    }
    document.body.classList.remove('ml-drawer-open');
  }

  /* -------------------------------------------------------
     INTERCEPTER LE PANIER BE YOURS
     On remplace le comportement du click sur l'icône panier
     pour ouvrir notre drawer custom à la place.
     ------------------------------------------------------- */
  function interceptCartIcon() {
    // Intercepter le <details> du cart-drawer Be Yours
    var cartDrawerDetails = document.querySelector('cart-drawer > details');
    if (cartDrawerDetails) {
      var summary = cartDrawerDetails.querySelector('summary');
      if (summary) {
        summary.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          // Empêcher le <details> de s'ouvrir
          if (cartDrawerDetails.open) {
            cartDrawerDetails.removeAttribute('open');
          }
          fetchAndRenderCart().then(openDrawer);
        }, true);
      }
    }

    // Intercepter aussi les liens directs vers /cart (header mobile, etc.)
    document.querySelectorAll('a[href="/cart"]').forEach(function (link) {
      // Ne pas intercepter le lien "Voir le panier complet" dans notre drawer
      if (link.classList.contains('ml-btn-cart-page')) return;
      link.addEventListener('click', function (e) {
        // Seulement si le drawer est activé
        if (document.getElementById('ml-cart-drawer')) {
          e.preventDefault();
          fetchAndRenderCart().then(openDrawer);
        }
      });
    });
  }

  /* -------------------------------------------------------
     INIT
     ------------------------------------------------------- */
  function init() {
    // Bouton fermer
    var closeBtn = document.getElementById('ml-drawer-close');
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

    // Overlay ferme le drawer
    var overlay = document.getElementById('ml-drawer-overlay');
    if (overlay) overlay.addEventListener('click', closeDrawer);

    // Escape ferme le drawer
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDrawer();
    });

    // Intercepter l'icône panier Be Yours
    interceptCartIcon();

    // Charger le panier initial
    fetchAndRenderCart();

    // Exposer globalement
    window.MylabCart = {
      open: function () { fetchAndRenderCart().then(openDrawer); },
      close: closeDrawer,
      refresh: fetchAndRenderCart
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
