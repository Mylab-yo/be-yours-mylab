/**
 * MY.LAB — Configurateur Commande Gros Volumes
 * assets/bulk-order.js
 */
(function () {
  'use strict';

  var config = window.BulkOrderConfig;
  if (!config) return;

  /* ══════════════════════════════════════════════
     ÉTAT GLOBAL
     ══════════════════════════════════════════════ */
  window.bulkOrderState = {
    step: 1,
    formulas: [],       // { id, name, gammeId, gammeColor, category, ... }
    selectedIds: {},     // { formulaId: true }
    formats: {},         // { formulaId: 200|500|1000|5000 }
    skipTakemoto: false, // true if user chooses to keep standard packaging
    filterGamme: 'all',
    filterType: 'all',
    data: null           // données JSON chargées
  };
  var state = window.bulkOrderState;

  var STEPS = [
    { num: 1, label: 'Formules' },
    { num: 2, label: 'Format' },
    { num: 3, label: 'Flacon' },
    { num: 4, label: 'Quantité' },
    { num: 5, label: 'Récap' }
  ];

  var LABELS = ['Sans sulfate', 'Sans parabène', 'Sans silicone', 'Vegan', 'Sans cruauté'];

  /* ══════════════════════════════════════════════
     DOM REFS
     ══════════════════════════════════════════════ */
  var elStepper       = document.getElementById('bulk-stepper');
  var elGrid          = document.getElementById('bulk-formulas-grid');
  var elEmpty         = document.getElementById('bulk-formulas-empty');
  var elFilterGamme   = document.getElementById('bulk-filter-gamme');
  var elFilterType    = document.getElementById('bulk-filter-type');
  var elSelBar        = document.getElementById('bulk-selection-bar');
  var elSelCount      = document.getElementById('bulk-selection-count');
  var elSelChips      = document.getElementById('bulk-selection-chips');
  var elSelNext       = document.getElementById('bulk-formulas-next');
  var elPrev          = document.getElementById('bulk-prev');
  var elNext          = document.getElementById('bulk-next');

  if (!elGrid || !elStepper) return;

  /* ══════════════════════════════════════════════
     HELPERS
     ══════════════════════════════════════════════ */
  function esc(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function selectedCount() {
    return Object.keys(state.selectedIds).length;
  }

  /* ══════════════════════════════════════════════
     STEPPER
     ══════════════════════════════════════════════ */
  function renderStepper() {
    var html = '';
    STEPS.forEach(function (s) {
      var cls = '';
      if (s.num < state.step) cls = 'bulk-stepper__item--done';
      else if (s.num === state.step) cls = 'bulk-stepper__item--active';
      var icon = s.num < state.step
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg>'
        : s.num;
      html += '<div class="bulk-stepper__item ' + cls + '">' +
        '<span class="bulk-stepper__circle">' + icon + '</span>' +
        '<span class="bulk-stepper__label">' + esc(s.label) + '</span>' +
        '</div>';
    });
    elStepper.innerHTML = html;
  }

  /* ══════════════════════════════════════════════
     FILTERS — GAMME CHIPS
     ══════════════════════════════════════════════ */
  function renderGammeFilters() {
    if (!state.data || !elFilterGamme) return;
    var html = '<button type="button" class="bulk-chip bulk-chip--active" data-filter-gamme="all">Toutes</button>';
    state.data.gammes.forEach(function (g) {
      html += '<button type="button" class="bulk-chip bulk-chip--gamme" ' +
        'data-filter-gamme="' + esc(g.id) + '" ' +
        'style="--gamme-color:' + esc(g.color) + '">' +
        esc(g.label.replace('Gamme ', '')) +
        '</button>';
    });
    elFilterGamme.innerHTML = html;
    bindFilterEvents(elFilterGamme, 'data-filter-gamme', function (val) {
      state.filterGamme = val;
      applyFilters();
    });
  }

  function bindFilterEvents(container, attr, cb) {
    container.addEventListener('click', function (e) {
      var btn = e.target.closest('.bulk-chip');
      if (!btn) return;
      container.querySelectorAll('.bulk-chip').forEach(function (c) {
        c.classList.remove('bulk-chip--active');
      });
      btn.classList.add('bulk-chip--active');
      cb(btn.getAttribute(attr));
    });
  }

  /* ══════════════════════════════════════════════
     FORMULA CARDS
     ══════════════════════════════════════════════ */
  function renderFormulas() {
    if (!state.data) return;
    state.formulas = [];
    var html = '';

    state.data.gammes.forEach(function (gamme) {
      gamme.formulas.forEach(function (f) {
        var formula = {
          id: f.id,
          name: f.name,
          category: f.category,
          gammeId: gamme.id,
          gammeLabel: gamme.label,
          gammeColor: gamme.color,
          description: f.description,
          actifs: f.actifs,
          natural_pct: f.natural_pct,
          available_formats: f.available_formats,
          pricing: f.pricing,
          packaging_notes: f.packaging_notes
        };
        state.formulas.push(formula);

        var isSelected = !!state.selectedIds[f.id];
        var selClass = isSelected ? ' bulk-card--selected' : '';

        html += '<div class="bulk-card' + selClass + '" ' +
          'data-formula-id="' + esc(f.id) + '" ' +
          'data-gamme="' + esc(gamme.id) + '" ' +
          'data-category="' + esc(f.category) + '" ' +
          'style="--gamme-color:' + esc(gamme.color) + '">' +

          '<span class="bulk-card__check">' +
            (isSelected ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg>' : '') +
          '</span>' +

          '<div class="bulk-card__visual">' +
            '<span class="bulk-card__color-dot"></span>' +
            '<span class="bulk-card__gamme-label">' + esc(gamme.label.replace('Gamme ', '')) + '</span>' +
          '</div>' +

          '<div class="bulk-card__name">' + esc(f.name) + '</div>' +

          '<span class="bulk-card__natural">' +
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' +
            f.natural_pct + '% naturel' +
          '</span>' +

          '<div class="bulk-card__actifs">' +
            f.actifs.map(function (a) { return '<span class="bulk-card__actif-tag">' + esc(a) + '</span>'; }).join('') +
          '</div>' +

          '<div class="bulk-card__labels">' +
            LABELS.map(function (l) { return '<span class="bulk-card__label">' + esc(l) + '</span>'; }).join('') +
          '</div>' +

          '</div>';
      });
    });

    elGrid.innerHTML = html;
    bindCardEvents();
  }

  function bindCardEvents() {
    elGrid.addEventListener('click', function (e) {
      var card = e.target.closest('.bulk-card');
      if (!card) return;
      var id = card.dataset.formulaId;
      if (state.selectedIds[id]) {
        delete state.selectedIds[id];
        card.classList.remove('bulk-card--selected');
        card.querySelector('.bulk-card__check').innerHTML = '';
      } else {
        state.selectedIds[id] = true;
        card.classList.add('bulk-card--selected');
        card.querySelector('.bulk-card__check').innerHTML =
          '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg>';
      }
      updateSelectionBar();
    });
  }

  /* ══════════════════════════════════════════════
     FILTERS
     ══════════════════════════════════════════════ */
  function applyFilters() {
    var cards = elGrid.querySelectorAll('.bulk-card');
    var visible = 0;
    cards.forEach(function (card) {
      var matchGamme = state.filterGamme === 'all' || card.dataset.gamme === state.filterGamme;
      var matchType = state.filterType === 'all' || card.dataset.category === state.filterType;
      if (matchGamme && matchType) {
        card.classList.remove('bulk-card--hidden');
        visible++;
      } else {
        card.classList.add('bulk-card--hidden');
      }
    });
    elEmpty.style.display = visible === 0 ? '' : 'none';
  }

  /* ══════════════════════════════════════════════
     SELECTION BAR
     ══════════════════════════════════════════════ */
  function updateSelectionBar() {
    var count = selectedCount();
    elSelCount.textContent = count;
    elSelNext.disabled = count === 0;

    if (count > 0) {
      elSelBar.classList.add('bulk-selection-bar--visible');
    } else {
      elSelBar.classList.remove('bulk-selection-bar--visible');
    }

    /* Chips */
    var html = '';
    state.formulas.forEach(function (f) {
      if (!state.selectedIds[f.id]) return;
      var short = f.name.replace('Crème de Coiffage ', 'Crème ').replace('Shampoing-Gel Douche', 'Gel Douche');
      html += '<span class="bulk-selection-chip" data-remove-id="' + esc(f.id) + '">' +
        esc(short) +
        '<span class="bulk-selection-chip__x">×</span>' +
        '</span>';
    });
    elSelChips.innerHTML = html;
  }

  /* Remove chip click */
  document.addEventListener('click', function (e) {
    var chip = e.target.closest('.bulk-selection-chip');
    if (!chip) return;
    var id = chip.dataset.removeId;
    if (id && state.selectedIds[id]) {
      delete state.selectedIds[id];
      var card = elGrid.querySelector('[data-formula-id="' + id + '"]');
      if (card) {
        card.classList.remove('bulk-card--selected');
        card.querySelector('.bulk-card__check').innerHTML = '';
      }
      updateSelectionBar();
    }
  });

  /* ══════════════════════════════════════════════
     STEP NAVIGATION
     ══════════════════════════════════════════════ */
  function goToStep(n) {
    if (n < 1 || n > 5) return;

    /* Validate before advancing */
    if (n === 2 && state.step === 1 && selectedCount() === 0) return;
    if (n === 3 && state.step === 2 && !allFormatsChosen()) return;

    state.step = n;
    document.querySelectorAll('.bulk-order__step').forEach(function (el) {
      el.style.display = parseInt(el.dataset.step) === n ? '' : 'none';
    });
    elPrev.disabled = n === 1;
    elNext.disabled = n === 5;
    elSelBar.classList.toggle('bulk-selection-bar--visible', n === 1 && selectedCount() > 0);

    /* Render step-specific content */
    if (n === 2) renderFormats();

    renderStepper();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (elPrev) elPrev.addEventListener('click', function () {
    /* When going back from step 4, if Takemoto was skipped, go to step 2 */
    if (state.step === 4 && state.skipTakemoto) {
      goToStep(2);
    } else {
      goToStep(state.step - 1);
    }
  });
  if (elNext) elNext.addEventListener('click', function () {
    /* At step 2, if all formats chosen and no 5L, show Takemoto choice (handled by renderFormats) */
    if (state.step === 2) {
      if (!allFormatsChosen()) return;
      var has5L = state.formulas.some(function (f) { return state.selectedIds[f.id] && state.formats[f.id] === 5000; });
      if (has5L) {
        goToStep(3); /* Force Takemoto for 5L */
      }
      /* Otherwise, Takemoto choice buttons handle navigation */
      return;
    }
    goToStep(state.step + 1);
  });
  if (elSelNext) elSelNext.addEventListener('click', function () {
    if (selectedCount() > 0) goToStep(2);
  });

  /* Type filter events */
  if (elFilterType) {
    bindFilterEvents(elFilterType, 'data-filter-type', function (val) {
      state.filterType = val;
      applyFilters();
    });
  }

  /* ══════════════════════════════════════════════
     STEP 2 — FORMAT SELECTION
     ══════════════════════════════════════════════ */
  var elFormatList   = document.getElementById('bulk-format-list');
  var elTakemoto     = document.getElementById('bulk-format-takemoto');
  var el5lNotice     = document.getElementById('bulk-format-5l-notice');
  var elTakemotoYes  = document.getElementById('bulk-takemoto-yes');
  var elTakemotoNo   = document.getElementById('bulk-takemoto-no');

  function fmtPrice(euros) {
    return euros.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '\u00a0\u20ac';
  }

  function getPackagingNote(format, category) {
    if (format === 5000) return 'Packaging à votre charge';
    if (format === 1000) return 'Packaging inclus : bouteille ambrée + bouchon blanc (pompe en option : +0,45\u00a0\u20ac/unité)';
    if (category === 'shampoing') return 'Packaging inclus : bouteille ambrée + bouchon noir';
    return 'Packaging inclus : bouteille ambrée + pompe noire';
  }

  function renderFormats() {
    if (!elFormatList || !state.data) return;

    var selected = state.formulas.filter(function (f) { return !!state.selectedIds[f.id]; });

    if (selected.length === 0) {
      elFormatList.innerHTML = '<p style="text-align:center;color:#888;padding:2rem;">Aucune formule sélectionnée. Retournez à l\'étape 1.</p>';
      return;
    }

    var html = '';
    selected.forEach(function (f) {
      var currentFormat = state.formats[f.id] || null;

      html += '<div class="bulk-format-row" style="--gamme-color:' + esc(f.gammeColor) + '">' +
        '<div class="bulk-format-row__header">' +
          '<span class="bulk-format-row__dot"></span>' +
          '<span class="bulk-format-row__gamme">' + esc(f.gammeLabel.replace('Gamme ', '')) + '</span>' +
        '</div>' +
        '<div class="bulk-format-row__name">' + esc(f.name) + '</div>' +
        '<div class="bulk-format-row__formats">';

      f.available_formats.forEach(function (fmt) {
        var label = fmt >= 1000 ? (fmt / 1000) + ' L' : fmt + ' ml';
        var isActive = currentFormat === fmt;
        html += '<button type="button" class="bulk-format-pill' + (isActive ? ' bulk-format-pill--active' : '') + '" ' +
          'data-formula-id="' + esc(f.id) + '" data-format="' + fmt + '">' +
          label +
          '</button>';
      });

      html += '</div>';

      /* Price indication */
      if (currentFormat && f.pricing) {
        var fmtKey = currentFormat + 'ml';
        var priceData = f.pricing['50kg'] && f.pricing['50kg'][fmtKey];
        if (priceData) {
          html += '<div class="bulk-format-row__price">À partir de <strong>' + fmtPrice(priceData.total) + ' HT/unité</strong> (tranche 50 kg)</div>';
        }
        html += '<div class="bulk-format-row__packaging">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="1.5"><path d="M20 7H4a2 2 0 00-2 2v10a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z"/><path d="M16 3l-4 4-4-4"/></svg>' +
          '<span>' + getPackagingNote(currentFormat, f.category) + '</span>' +
          '</div>';
      }

      html += '</div>';
    });

    elFormatList.innerHTML = html;
    updateTakemotoVisibility();

    /* Bind format pill clicks */
    elFormatList.querySelectorAll('.bulk-format-pill').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var fid = btn.dataset.formulaId;
        var fmt = parseInt(btn.dataset.format, 10);
        state.formats[fid] = fmt;
        renderFormats();
      });
    });
  }

  function updateTakemotoVisibility() {
    if (!elTakemoto || !el5lNotice) return;

    var selected = state.formulas.filter(function (f) { return !!state.selectedIds[f.id]; });
    var has5L = false;
    var allHaveFormat = true;

    selected.forEach(function (f) {
      if (!state.formats[f.id]) allHaveFormat = false;
      if (state.formats[f.id] === 5000) has5L = true;
    });

    /* Show 5L notice */
    el5lNotice.style.display = has5L ? '' : 'none';

    /* Show Takemoto choice only when all formats chosen and no 5L */
    if (allHaveFormat && !has5L && selected.length > 0) {
      elTakemoto.style.display = '';
    } else if (has5L) {
      /* 5L forces Takemoto step — hide the optional choice */
      elTakemoto.style.display = 'none';
      state.skipTakemoto = false;
    } else {
      elTakemoto.style.display = 'none';
    }
  }

  function allFormatsChosen() {
    var selected = state.formulas.filter(function (f) { return !!state.selectedIds[f.id]; });
    return selected.length > 0 && selected.every(function (f) { return !!state.formats[f.id]; });
  }

  /* Takemoto buttons */
  if (elTakemotoYes) {
    elTakemotoYes.addEventListener('click', function () {
      state.skipTakemoto = false;
      goToStep(3);
    });
  }
  if (elTakemotoNo) {
    elTakemotoNo.addEventListener('click', function () {
      state.skipTakemoto = true;
      goToStep(4); /* Skip step 3 */
    });
  }

  /* ══════════════════════════════════════════════
     INIT
     ══════════════════════════════════════════════ */
  renderStepper();

  fetch(config.formulasUrl)
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (data) {
      state.data = data;
      renderGammeFilters();
      renderFormulas();
      updateSelectionBar();
    })
    .catch(function (err) {
      console.error('BulkOrder: impossible de charger les formules', err);
      elGrid.innerHTML = '<p style="text-align:center;color:#c00;padding:2rem;">Erreur de chargement des données. Veuillez rafraîchir la page.</p>';
    });

})();
