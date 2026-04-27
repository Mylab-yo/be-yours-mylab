/**
 * MY.LAB — Cache de sélection du configurateur gros volume
 * assets/bulk-order-cache.js
 *
 * Persiste les choix utilisateur (formules, formats, flacons, couleurs,
 * quantités) dans localStorage pour qu'un visiteur qui ferme la page et
 * revient retrouve son projet à l'identique. La donnée catalogue
 * (formulas/bottles/images) n'est PAS cachée — toujours rechargée fraîche
 * depuis le CDN.
 *
 * Cycle de vie :
 *   - Restaure dès que window.BulkOrder existe (avant init)
 *   - Auto-save sur chaque goToStep + à beforeunload (filet de secours)
 *   - Clear quand l'événement 'bulk-order:submitted' est dispatché par
 *     bulk-order-summary.js après envoi réussi du devis
 *   - Expire automatiquement après 14 jours
 */
(function () {
  'use strict';

  var KEY = 'mylab.bulkOrder.v1';
  var TTL_MS = 14 * 24 * 60 * 60 * 1000; // 14 jours

  function safeParse(raw) {
    try { return JSON.parse(raw); } catch (_) { return null; }
  }

  function save() {
    var bo = window.BulkOrder;
    if (!bo) return;
    try {
      var snapshot = {
        version: 1,
        savedAt: Date.now(),
        // BulkOrder.state — sélections principales
        selectedIds:   bo.state ? bo.state.selectedIds : {},
        formats:       bo.state ? bo.state.formats : {},
        skipTakemoto:  bo.state ? !!bo.state.skipTakemoto : false,
        step:          bo.state ? bo.state.step : 1,
        // BulkOrder.bottleState — choix flacons
        bottleSelections: bo.bottleState ? bo.bottleState.selections : {},
        bottleColors:     bo.bottleState ? bo.bottleState.selectedColors : {},
        // BulkOrder.qtyState — quantités
        qtyState: bo.qtyState || {}
      };
      localStorage.setItem(KEY, JSON.stringify(snapshot));
    } catch (_) {
      // Quota dépassé ou localStorage désactivé — on encaisse silencieusement
    }
  }

  function restore() {
    var raw;
    try { raw = localStorage.getItem(KEY); } catch (_) { return null; }
    if (!raw) return null;
    var parsed = safeParse(raw);
    if (!parsed || parsed.version !== 1) return null;
    if (typeof parsed.savedAt !== 'number' || Date.now() - parsed.savedAt > TTL_MS) {
      try { localStorage.removeItem(KEY); } catch (_) {}
      return null;
    }
    return parsed;
  }

  function clear() {
    try { localStorage.removeItem(KEY); } catch (_) {}
  }

  function applyTo(bo, snap) {
    if (!bo || !snap) return;
    if (bo.state) {
      if (snap.selectedIds) bo.state.selectedIds = snap.selectedIds;
      if (snap.formats)     bo.state.formats     = snap.formats;
      if (typeof snap.skipTakemoto === 'boolean') bo.state.skipTakemoto = snap.skipTakemoto;
    }
    if (bo.bottleState) {
      if (snap.bottleSelections) bo.bottleState.selections      = snap.bottleSelections;
      if (snap.bottleColors)     bo.bottleState.selectedColors  = snap.bottleColors;
    }
    if (snap.qtyState) bo.qtyState = snap.qtyState;
  }

  // Reprendre l'utilisateur à l'étape la plus avancée encore valide compte
  // tenu de ses sélections — évite de le ramener à 1 quand il avait fini.
  function pickResumeStep(bo, requested) {
    if (!bo) return 1;
    var maxStep = 1;
    var hasFormulas = bo.selectedCount && bo.selectedCount() > 0;
    var hasFormats = bo.allFormatsChosen && bo.allFormatsChosen();
    var hasMoq     = bo.allMoqsMet && bo.allMoqsMet();
    if (hasFormulas) maxStep = 2;
    if (hasFormats)  maxStep = bo.state && bo.state.skipTakemoto ? 4 : 3;
    if (hasMoq)      maxStep = 5;
    var target = Math.min(requested || 1, maxStep);
    return Math.max(1, target);
  }

  function patchBulkOrder() {
    var bo = window.BulkOrder;
    if (!bo) { setTimeout(patchBulkOrder, 30); return; }

    var snap = restore();

    // Restaurer immédiatement les objets d'état — modules de rendu liront
    // ces valeurs dès qu'ils s'exécuteront.
    if (snap) applyTo(bo, snap);

    // Auto-save sur chaque transition d'étape
    if (typeof bo.goToStep === 'function' && !bo._cacheGoToWrapped) {
      var origGoTo = bo.goToStep;
      bo.goToStep = function () {
        var result = origGoTo.apply(this, arguments);
        save();
        return result;
      };
      bo._cacheGoToWrapped = true;
    }

    // Au moment où la donnée catalogue est prête, rejouer la dernière étape
    // valide pour que l'utilisateur reprenne là où il était.
    if (snap && snap.step && snap.step > 1 && bo.modules) {
      var formulasMod = bo.modules.formulas;
      if (formulasMod && typeof formulasMod.onDataReady === 'function' && !formulasMod._cacheOnDataReadyWrapped) {
        var origOnReady = formulasMod.onDataReady;
        formulasMod.onDataReady = function () {
          var result = origOnReady.apply(this, arguments);
          var target = pickResumeStep(bo, snap.step);
          if (target > 1) {
            // Laisse le rendu initial finir avant de naviguer
            setTimeout(function () { bo.goToStep(target); }, 0);
          }
          return result;
        };
        formulasMod.onDataReady._cacheOnDataReadyWrapped = true;
      }
    }

    // Expose pour debug et clear manuel
    bo.cache = { save: save, restore: restore, clear: clear };
  }

  // bulk-order-cache.js est défer comme les autres modules → core a déjà
  // créé window.BulkOrder au moment où ce script s'exécute, mais ses modules
  // peuvent ne pas tous être enregistrés. patchBulkOrder retry jusqu'à
  // disposer du namespace.
  patchBulkOrder();

  // Filet de secours : sauver avant fermeture / refresh
  window.addEventListener('beforeunload', save);

  // Vidé après envoi réussi du devis (event dispatché par bulk-order-summary.js)
  document.addEventListener('bulk-order:submitted', clear);
})();
