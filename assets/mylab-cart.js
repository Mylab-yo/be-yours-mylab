'use strict';

/**
 * MyLab Shop — Gestion des selects de paliers dans le mini-cart et la page panier.
 * Les prix HT et les dropdowns sont rendus côté serveur (Liquid).
 * Ce script gère uniquement :
 *  1. Le changement de quantité via les <select class="ml-qty-select">
 *  2. L'API window.MylabCart pour l'intégration avec mylab-product.js
 */

(function () {

  /* -------------------------------------------------------
     SELECT CHANGE → appelle updateQuantity de Be Yours
     Délégation d'événement sur document pour couvrir
     les éléments re-rendus par AJAX (section rendering).
     ------------------------------------------------------- */
  document.addEventListener('change', function (e) {
    var select = e.target;
    if (!select.classList.contains('ml-qty-select')) return;

    var index = select.dataset.index;
    var quantity = parseInt(select.value, 10);

    // Chercher le <cart-items> parent (mini-cart ou page panier)
    var cartItems = select.closest('cart-items');
    if (cartItems && typeof cartItems.updateQuantity === 'function') {
      cartItems.updateQuantity(index, quantity);
    }
  });

  /* -------------------------------------------------------
     OUVRIR LE CART DRAWER (Be Yours natif)
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
    // Mettre à jour le badge
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

    // Recharger le contenu du mini-cart via section rendering
    var miniCart = document.getElementById('mini-cart');
    if (miniCart) {
      var sectionId = miniCart.closest('.shopify-section')?.id?.replace('shopify-section-', '') || 'mini-cart';
      fetch('/?section_id=' + sectionId)
        .then(function (r) { return r.text(); })
        .then(function (html) {
          var doc = new DOMParser().parseFromString(html, 'text/html');
          var section = doc.querySelector('.shopify-section');
          if (section) {
            miniCart.closest('.shopify-section').innerHTML = section.innerHTML;
          }
        });
    }

    openBeYoursCart();
  }

  /* -------------------------------------------------------
     API GLOBALE
     ------------------------------------------------------- */
  window.MylabCart = {
    open: refreshCartAndOpen,
    refresh: function () {
      // Recharger le mini-cart sans ouvrir
      var miniCart = document.getElementById('mini-cart');
      if (miniCart) {
        var sectionId = miniCart.closest('.shopify-section')?.id?.replace('shopify-section-', '') || 'mini-cart';
        fetch('/?section_id=' + sectionId)
          .then(function (r) { return r.text(); })
          .then(function (html) {
            var doc = new DOMParser().parseFromString(html, 'text/html');
            var section = doc.querySelector('.shopify-section');
            if (section) {
              miniCart.closest('.shopify-section').innerHTML = section.innerHTML;
            }
          });
      }
    }
  };

})();
