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
     REFRESH APRÈS AJOUT (appelé par mylab-product.js)
     Utilise l'event cart:refresh écouté par CartDrawer (global.js)
     qui gère le fetch des sections, la MAJ du DOM et l'ouverture.
     ------------------------------------------------------- */
  function refreshCartAndOpen() {
    document.dispatchEvent(new CustomEvent('cart:refresh', { detail: { open: true } }));
  }

  /* -------------------------------------------------------
     API GLOBALE
     ------------------------------------------------------- */
  window.MylabCart = {
    open: refreshCartAndOpen,
    refresh: function () {
      // Recharger le mini-cart sans ouvrir
      document.dispatchEvent(new CustomEvent('cart:refresh', { detail: { open: false } }));
    }
  };

})();
