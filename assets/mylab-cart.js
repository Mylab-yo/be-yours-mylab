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
     BRIDGE — Be Yours <add-to-cart> → drawer auto-open
     Le custom element <add-to-cart> de Be Yours (utilisé
     par les card-product, donc boutique-testeurs, collections,
     etc.) dispatch 'ajaxProduct:added' mais pas 'cart:refresh'.
     Sans ce bridge, le drawer ne s'ouvre pas après un ajout
     depuis une miniature. Sur les pages parcours, on n'ouvre
     pas le drawer (l'user reste dans le flow de configuration).
     ------------------------------------------------------- */
  var SILENT_OPEN_REGEX = /\/pages\/(creons-ensemble-votre-marque|parcours-(dossier|etiquette|produits|recap))\/?$/i;
  document.addEventListener('ajaxProduct:added', function () {
    var silentOpen = SILENT_OPEN_REGEX.test(window.location.pathname);
    document.dispatchEvent(new CustomEvent('cart:refresh', { detail: { open: !silentOpen } }));
  });

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

  /* -------------------------------------------------------
     SORTIE « COMMANDER DES ÉCHANTILLONS » (panier bloqué)
     1er clic sur le lien → confirmation inline
     Confirm → retire les articles marque-création via
     /cart/update.js puis redirige vers la boutique testeurs.
     ------------------------------------------------------- */
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-ml-sample-trigger]');
    if (trigger) {
      e.preventDefault();
      var box = trigger.closest('.ml-sample-exit');
      if (!box) return;
      trigger.hidden = true;
      var confirmEl = box.querySelector('.ml-sample-exit__confirm');
      if (confirmEl) confirmEl.hidden = false;
      return;
    }

    var cancel = e.target.closest('[data-ml-sample-cancel]');
    if (cancel) {
      var boxC = cancel.closest('.ml-sample-exit');
      if (!boxC) return;
      var confC = boxC.querySelector('.ml-sample-exit__confirm');
      var linkC = boxC.querySelector('[data-ml-sample-trigger]');
      if (confC) confC.hidden = true;
      if (linkC) linkC.hidden = false;
      return;
    }

    var go = e.target.closest('[data-ml-sample-confirm]');
    if (go) {
      e.preventDefault();
      var boxG = go.closest('.ml-sample-exit');
      if (!boxG) return;
      var redirect = boxG.getAttribute('data-ml-redirect') || '/pages/boutique-testeurs';
      var keysAttr = boxG.getAttribute('data-ml-remove-keys') || '';
      var keys = keysAttr.split(',').filter(Boolean);
      var errEl = boxG.querySelector('.ml-sample-exit__error');
      if (errEl) errEl.hidden = true;

      if (keys.length === 0) { window.location.href = redirect; return; }

      go.setAttribute('aria-busy', 'true');
      go.disabled = true;

      var updates = {};
      keys.forEach(function (k) { updates[k] = 0; });

      fetch('/cart/update.js', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates: updates })
      }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        window.location.href = redirect;
      }).catch(function () {
        go.removeAttribute('aria-busy');
        go.disabled = false;
        if (errEl) errEl.hidden = false;
      });
      return;
    }
  });

})();
