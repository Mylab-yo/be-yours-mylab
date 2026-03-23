/**
 * ML Dossier Gate — Auto-ajout du dossier cosmétologique
 *
 * Quand un client non-taggé "dossier-valide" ajoute un produit de la
 * collection boutique-adherents au panier, le dossier cosmétologique
 * est automatiquement ajouté. Il ne peut pas être retiré tant qu'un
 * produit pro reste dans le panier.
 *
 * Config attendue dans window.MylabDossierGate (injectée par Liquid) :
 *   isProCustomer  : bool
 *   dossierHandle  : string
 *   proHandles     : { [handle]: true }
 */
(function () {
  'use strict';

  var config = window.MylabDossierGate;
  if (!config || config.isProCustomer) return;

  var dossierVariantId = null;
  var isProcessing = false;
  var isGateAction = false;

  /* ── Charger le variant ID du dossier ── */
  function loadDossierVariant() {
    return fetch('/products/' + config.dossierHandle + '.js')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (product) {
        dossierVariantId = product.variants[0].id;
      });
  }

  /* ── Vérifier le panier et agir ── */
  function checkCart() {
    if (isProcessing || !dossierVariantId) return;
    isProcessing = true;

    fetch('/cart.js')
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        var hasProProduct = false;
        var hasDossier = false;
        var dossierKey = null;

        var dossierQty = 0;

        cart.items.forEach(function (item) {
          if (config.proHandles[item.handle]) {
            hasProProduct = true;
          }
          if (item.handle === config.dossierHandle) {
            hasDossier = true;
            dossierKey = item.key;
            dossierQty = item.quantity;
          }
        });

        /* Dossier en double → forcer la quantité à 1 */
        if (hasDossier && dossierQty > 1 && dossierKey) {
          isGateAction = true;
          return fetch('/cart/change.js', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: dossierKey, quantity: 1 })
          }).then(function () {
            isGateAction = false;
            document.dispatchEvent(new CustomEvent('cart:refresh'));
          });
        }

        /* Produit pro dans le panier mais pas de dossier → ajouter */
        if (hasProProduct && !hasDossier) {
          isGateAction = true;
          return fetch('/cart/add.js', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              items: [{ id: dossierVariantId, quantity: 1 }]
            })
          }).then(function () {
            isGateAction = false;
            document.dispatchEvent(new CustomEvent('cart:refresh'));
          });
        }

        /* Le dossier peut être acheté seul — pas d'auto-retrait */
      })
      .catch(function (err) {
        console.error('MylabDossierGate:', err);
      })
      .finally(function () {
        isProcessing = false;
        isGateAction = false;
      });
  }

  /* ── Intercepter les modifications panier ── */
  var originalFetch = window.fetch;
  window.fetch = function () {
    var url = arguments[0];
    if (
      !isGateAction &&
      typeof url === 'string' &&
      (url.indexOf('/cart/add') !== -1 ||
       url.indexOf('/cart/change') !== -1 ||
       url.indexOf('/cart/update') !== -1)
    ) {
      var args = arguments;
      return originalFetch.apply(this, args).then(function (response) {
        setTimeout(checkCart, 400);
        return response;
      });
    }
    return originalFetch.apply(this, arguments);
  };

  /* ── Init ── */
  loadDossierVariant().then(function () {
    checkCart();
  });
})();
