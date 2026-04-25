/**
 * ML Forfait Gate — Auto-ajout du forfait d'impression annuel Appstle
 *
 * Règle métier (confirmée 2026-04-23) :
 *   - Étiquette standard (logo noir MY.LAB)          → Forfait d'impression noire
 *   - Modèles 99€ et sur-mesure 390€                 → Forfait d'impression couleur
 *   - Client déjà abonné (tag `abo-impression-*`)    → skip
 *
 * Config attendue dans window.MylabForfaitGate (injectée par theme.liquid) :
 *   customerTags      : string[]
 *   noireHandles      : string[]  (handles de produits qui déclenchent la noire)
 *   couleurHandles    : string[]  (handles de produits qui déclenchent la couleur)
 *   forfaitNoire      : { handle, variantId, sellingPlanId }
 *   forfaitCouleur    : { handle, variantId, sellingPlanId }
 */
(function () {
  'use strict';

  var cfg = window.MylabForfaitGate;
  if (!cfg) return;

  var isProcessing = false;
  var isGateAction = false;

  function has(tag) { return (cfg.customerTags || []).indexOf(tag) >= 0; }
  function inList(list, handle) { return (list || []).indexOf(handle) >= 0; }

  function checkCart() {
    if (isProcessing) return Promise.resolve();
    isProcessing = true;

    return fetch('/cart.js')
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        var hasNoireLabel = false;
        var hasCouleurLabel = false;
        var hasForfaitNoire = false;
        var hasForfaitCouleur = false;

        cart.items.forEach(function (item) {
          if (item.handle === cfg.forfaitNoire.handle) hasForfaitNoire = true;
          if (item.handle === cfg.forfaitCouleur.handle) hasForfaitCouleur = true;
          if (inList(cfg.noireHandles, item.handle)) hasNoireLabel = true;
          if (inList(cfg.couleurHandles, item.handle)) hasCouleurLabel = true;
        });

        var needNoire   = hasNoireLabel   && !hasForfaitNoire   && !has('abo-impression-noire');
        var needCouleur = hasCouleurLabel && !hasForfaitCouleur && !has('abo-impression-couleur');

        // Couleur wins si les 2 sont déclenchés (une étiquette couleur couvre aussi le besoin noir)
        if (needCouleur) return addForfait(cfg.forfaitCouleur);
        if (needNoire)   return addForfait(cfg.forfaitNoire);
      })
      .catch(function (err) { console.error('MylabForfaitGate:', err); })
      .finally(function () { isProcessing = false; });
  }

  function addForfait(f) {
    isGateAction = true;
    return fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: [{
          id: f.variantId,
          quantity: 1,
          selling_plan: f.sellingPlanId
        }]
      })
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (e) { throw new Error(e.description || 'Forfait add failed'); });
      return r.json();
    }).then(function () {
      // Sur les pages parcours "Créons ensemble votre marque" (legacy + multi-pages),
      // on ne doit pas ouvrir automatiquement le drawer — l'user reste dans le flow
      // de configuration.
      var silentOpen = /\/pages\/(creons-ensemble-votre-marque|parcours-(dossier|etiquette|produits|recap))\/?$/i.test(window.location.pathname);
      document.dispatchEvent(new CustomEvent('cart:refresh'));
      document.dispatchEvent(new CustomEvent('mylab:cart:refresh', { detail: { open: !silentOpen } }));
    }).finally(function () {
      isGateAction = false;
    });
  }

  // Intercept fetch on cart mutation URLs (same pattern que ml-dossier-gate)
  var origFetch = window.fetch;
  window.fetch = function (url, opts) {
    var result = origFetch.apply(this, arguments);
    var urlStr = typeof url === 'string' ? url : (url && url.url) || '';
    if (!isGateAction && /\/cart\/(add|change|update)(\.js)?/.test(urlStr)) {
      result.then(function () {
        setTimeout(checkCart, 350);
      }, function () { /* swallow, original caller still sees rejection */ });
    }
    return result;
  };

  document.addEventListener('cart:refresh', function () { setTimeout(checkCart, 450); });
  document.addEventListener('mylab:cart:refresh', function () { setTimeout(checkCart, 450); });

  // Initial check if a label is already in cart at page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(checkCart, 300); });
  } else {
    setTimeout(checkCart, 300);
  }
})();
