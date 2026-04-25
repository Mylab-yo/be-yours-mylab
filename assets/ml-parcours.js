/**
 * ml-parcours.js — État partagé du parcours multi-pages MY.LAB
 * - Lit /cart.js au load et reconstruit l'état des étapes
 * - Sync le stepper et le récap drawer
 * - Gère auto-add du dossier au démarrage
 * - Gère la sortie « Quitter le parcours »
 */
(function () {
  'use strict';

  const CONFIG = {
    paths: {
      landing: '/pages/creons-ensemble-votre-marque',
      dossier: '/pages/parcours-dossier',
      etiquette: '/pages/parcours-etiquette',
      produits: '/pages/parcours-produits',
      recap: '/pages/parcours-recap'
    },
    handles: {
      dossier: 'creation-du-dossier-cosmetologique',
      forfaitStandard: 'forfait-dimpression-standard',
      forfaitCouleur: 'forfait-dimpression'
    },
    collections: {
      etiquettes: 'modeles-detiquettes',
      produits: 'boutique-adherents'
    }
  };

  // Determine current page from window.location
  function currentStep() {
    const p = window.location.pathname.replace(/\/$/, '');
    if (p === CONFIG.paths.landing) return 'landing';
    if (p === CONFIG.paths.dossier) return 'dossier';
    if (p === CONFIG.paths.etiquette) return 'etiquette';
    if (p === CONFIG.paths.produits) return 'produits';
    if (p === CONFIG.paths.recap) return 'recap';
    return null;
  }

  // Read cart and build state
  async function readState() {
    const res = await fetch('/cart.js', { credentials: 'same-origin' });
    if (!res.ok) throw new Error('cart fetch failed: ' + res.status);
    const cart = await res.json();
    const items = cart.items || [];
    return {
      cart,
      hasDossier: items.some(it => it.handle === CONFIG.handles.dossier),
      hasEtiquette: items.some(it => isEtiquette(it)),
      hasProduits: items.some(it => isProduit(it)),
      hasForfait: items.some(it =>
        it.handle === CONFIG.handles.forfaitStandard ||
        it.handle === CONFIG.handles.forfaitCouleur
      ),
      total: items.reduce((sum, it) => sum + it.line_price, 0)
    };
  }

  // Format cents → "12,34 €"
  function fmt(cents) {
    return (cents / 100).toFixed(2).replace('.', ',') + ' €';
  }

  function isEtiquette(item) {
    const etiquetteHandles = window.MylabParcours?.etiquetteHandles || [];
    return etiquetteHandles.includes(item.handle);
  }

  function isProduit(item) {
    const produitHandles = window.MylabParcours?.produitHandles || [];
    return produitHandles.includes(item.handle);
  }

  // Sync the stepper UI
  function syncStepper(state) {
    const cur = currentStep();
    const stepOrder = ['dossier', 'etiquette', 'produits', 'recap'];
    const validated = {
      dossier: state.hasDossier,
      etiquette: state.hasEtiquette,
      produits: state.hasProduits,
      recap: false
    };
    document.querySelectorAll('.ml-parcours__step').forEach((el, i) => {
      const name = stepOrder[i];
      el.classList.remove('is-done', 'is-current', 'is-locked');
      if (name === cur) {
        el.classList.add('is-current');
      } else if (validated[name]) {
        el.classList.add('is-done');
      } else {
        el.classList.add('is-locked');
      }
    });
    document.querySelectorAll('.ml-parcours__step-line').forEach((line, i) => {
      const before = stepOrder[i];
      line.classList.toggle('is-filled', validated[before]);
    });
  }

  // Sync the recap drawer content. Builds lines via createElement to avoid
  // injecting cart-sourced strings through innerHTML.
  function syncRecap(state) {
    const root = document.querySelector('[data-ml-parcours-recap]');
    if (!root) return;

    const items = state.cart.items || [];
    const dossierItem = items.find(it => it.handle === CONFIG.handles.dossier);
    const etiquetteItems = items.filter(it => isEtiquette(it));
    const produitItems = items.filter(it => isProduit(it));
    const sumPrice = arr => arr.reduce((sum, it) => sum + it.line_price, 0);

    const lines = [
      { name: 'Dossier cosmétologique', done: state.hasDossier, value: dossierItem ? fmt(dossierItem.line_price) : '—' },
      { name: 'Étiquette & impression', done: state.hasEtiquette, value: etiquetteItems.length ? fmt(sumPrice(etiquetteItems)) : '—' },
      { name: 'Produits sélectionnés', done: state.hasProduits, value: produitItems.length ? fmt(sumPrice(produitItems)) : '—' }
    ];

    const linesEl = root.querySelector('[data-ml-recap-lines]');
    if (linesEl) {
      linesEl.textContent = '';
      lines.forEach(l => {
        const row = document.createElement('div');
        row.className = 'ml-parcours__recap-line ' + (l.done ? 'is-done' : 'is-pending');
        const icon = document.createElement('span');
        icon.className = 'ml-parcours__recap-line-icon';
        icon.textContent = l.done ? '✓' : '·';
        const label = document.createElement('span');
        label.className = 'ml-parcours__recap-line-label';
        label.textContent = l.name;
        const value = document.createElement('span');
        value.className = 'ml-parcours__recap-line-value';
        value.textContent = l.value;
        row.append(icon, label, value);
        linesEl.appendChild(row);
      });
    }

    const totalEl = root.querySelector('[data-ml-recap-total]');
    if (totalEl) totalEl.textContent = fmt(state.total);
  }

  // Toast feedback. Used for confirmations (e.g. exit failures); the start CTA
  // redirects too fast to render a toast on the source page.
  function showToast(msg) {
    let t = document.querySelector('.ml-parcours__toast');
    if (!t) {
      t = document.createElement('div');
      t.className = 'ml-parcours__toast';
      t.setAttribute('role', 'status');
      t.setAttribute('aria-live', 'polite');
      const icon = document.createElement('span');
      icon.className = 'ml-parcours__toast-icon';
      icon.textContent = '✓';
      const message = document.createElement('span');
      message.className = 'ml-parcours__toast-message';
      t.append(icon, message);
      document.body.appendChild(t);
    }
    t.querySelector('.ml-parcours__toast-message').textContent = msg;
    t.classList.add('is-visible');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('is-visible'), 2400);
  }

  // Recap drawer toggle
  function bindRecapToggle() {
    const drawer = document.querySelector('[data-ml-parcours-recap]');
    if (!drawer) return;
    document.querySelectorAll('[data-ml-recap-toggle]').forEach(btn => {
      btn.addEventListener('click', () => {
        const open = drawer.classList.toggle('is-open');
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        const label = btn.querySelector('[data-ml-recap-toggle-label]');
        if (label) label.textContent = open ? 'Masquer mon projet' : 'Voir mon projet en cours';
      });
    });
  }

  // Stepper navigation
  function bindStepperNav() {
    document.querySelectorAll('.ml-parcours__step[data-go]').forEach(el => {
      el.addEventListener('click', e => {
        e.preventDefault();
        const target = el.dataset.go;
        if (CONFIG.paths[target]) {
          window.location.href = CONFIG.paths[target];
        }
      });
    });
  }

  // « Démarrer mon projet » CTA — auto-add dossier then redirect
  function bindStartCta() {
    document.querySelectorAll('[data-ml-start-parcours]').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.preventDefault();
        btn.disabled = true;
        try {
          const state = await readState();
          if (!state.hasDossier && window.MylabParcours?.dossierVariantId) {
            const res = await fetch('/cart/add.js', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({
                items: [{ id: window.MylabParcours.dossierVariantId, quantity: 1 }]
              })
            });
            if (!res.ok) throw new Error('cart add failed: ' + res.status);
          }
          window.location.href = CONFIG.paths.dossier;
        } catch (err) {
          console.error('[ml-parcours] start error', err);
          showToast('Erreur lors du démarrage. Réessayez.');
          btn.disabled = false;
        }
      });
    });
  }

  // « Quitter le parcours » — remove dossier + etiquette + forfait, keep produits
  function bindExitParcours() {
    document.querySelectorAll('[data-ml-exit-parcours]').forEach(link => {
      link.addEventListener('click', async e => {
        e.preventDefault();
        const ok = window.confirm(
          'Voulez-vous abandonner votre projet ?\n\n' +
          'Le dossier cosmétologique (389,90 €), l\'étiquette et le forfait d\'impression seront retirés du panier. ' +
          'Les produits ajoutés à l\'étape 03 restent dans votre panier.'
        );
        if (!ok) return;
        try {
          const state = await readState();
          const items = state.cart.items || [];
          const toRemove = items.filter(it =>
            it.handle === CONFIG.handles.dossier ||
            it.handle === CONFIG.handles.forfaitStandard ||
            it.handle === CONFIG.handles.forfaitCouleur ||
            isEtiquette(it)
          );
          for (const it of toRemove) {
            const res = await fetch('/cart/change.js', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({ id: it.key, quantity: 0 })
            });
            if (!res.ok) throw new Error('cart change failed: ' + res.status);
          }
          window.location.href = '/';
        } catch (err) {
          console.error('[ml-parcours] exit error', err);
          showToast('Erreur lors du retrait. Réessayez.');
        }
      });
    });
  }

  // Init — guarded against double-binding if init() runs twice
  let initialized = false;
  async function init() {
    if (initialized) return;
    initialized = true;
    document.body.classList.add('is-parcours');
    try {
      const state = await readState();
      syncStepper(state);
      syncRecap(state);
    } catch (err) {
      console.error('[ml-parcours] init readState failed', err);
    }
    bindRecapToggle();
    bindStepperNav();
    bindStartCta();
    bindExitParcours();

    // Listen to cart updates (debounced 200ms to coalesce bursts)
    let refreshTimer = null;
    document.addEventListener('cart:refresh', () => {
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(async () => {
        try {
          const s = await readState();
          syncStepper(s);
          syncRecap(s);
        } catch (err) {
          console.error('[ml-parcours] cart:refresh sync failed', err);
        }
      }, 200);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
