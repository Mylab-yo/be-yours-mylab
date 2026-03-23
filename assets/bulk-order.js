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
    if (n === 3) { renderBottleTabs(); renderBottleGrid(); }
    if (n === 4) renderQuantity();

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
     STEP 3 — BOTTLE SELECTION
     ══════════════════════════════════════════════ */
  var elBottlesTabs     = document.getElementById('bulk-bottles-tabs');
  var elBottlesGrid     = document.getElementById('bulk-bottles-grid');
  var elBottlesEmpty    = document.getElementById('bulk-bottles-empty');
  var elBottlesRecap    = document.getElementById('bulk-bottles-recap-list');
  var elBottlesMatFilter = document.getElementById('bulk-bottles-filter-material');
  var elBottlesColFilter = document.getElementById('bulk-bottles-filter-color');
  var elBottlesEcoFilter = document.getElementById('bulk-bottles-eco-filter');

  var bottlesData = null;
  var bottleState = {
    activeFormulaId: null,
    selections: {},      // { formulaId: bottleId }
    filterMaterial: 'all',
    filterColor: 'all',
    filterEco: false
  };

  var CLOSURE_COMPAT = {
    shampoing: ['pump', 'screw_cap'],
    creme_coiffage: ['pump', 'dispensing_cap'],
    masque: ['pump', 'dispensing_cap', 'screw_cap'],
    spray: ['spray'],
    serum: ['dropper', 'pump'],
    huile: ['dropper', 'pump']
  };

  var COLOR_LABELS = { amber: 'Ambré', clear: 'Transparent', white: 'Blanc', black: 'Noir', frosted: 'Givré' };
  var MATERIAL_LABELS = { PET: 'PET', rPET: 'rPET', PCR: 'PCR', biomass_PET: 'Bio PET', glass: 'Verre' };
  var CLOSURE_LABELS = { pump: 'Pompe', screw_cap: 'Bouchon vis', dispensing_cap: 'Clapet', spray: 'Spray', dropper: 'Pipette' };

  function getSelectedFormulasWithFormat() {
    return state.formulas.filter(function (f) {
      return state.selectedIds[f.id] && state.formats[f.id];
    });
  }

  function renderBottleTabs() {
    if (!elBottlesTabs) return;
    var formulas = getSelectedFormulasWithFormat();
    if (formulas.length === 0) return;

    if (!bottleState.activeFormulaId || !state.selectedIds[bottleState.activeFormulaId]) {
      bottleState.activeFormulaId = formulas[0].id;
    }

    var html = '';
    formulas.forEach(function (f) {
      var isActive = f.id === bottleState.activeFormulaId;
      var hasBottle = !!bottleState.selections[f.id];
      var fmtLabel = state.formats[f.id] >= 1000 ? (state.formats[f.id] / 1000) + 'L' : state.formats[f.id] + 'ml';
      html += '<button type="button" class="bulk-bottles__tab' + (isActive ? ' bulk-bottles__tab--active' : '') + '" data-tab-formula="' + esc(f.id) + '">' +
        esc(f.name) + ' — ' + fmtLabel +
        (hasBottle ? ' <span class="bulk-bottles__tab-check">✓</span>' : '') +
        '</button>';
    });
    elBottlesTabs.innerHTML = html;

    elBottlesTabs.querySelectorAll('.bulk-bottles__tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        bottleState.activeFormulaId = btn.dataset.tabFormula;
        renderBottleTabs();
        renderBottleGrid();
      });
    });
  }

  function renderBottleGrid() {
    if (!elBottlesGrid || !bottlesData) return;
    var f = state.formulas.find(function (x) { return x.id === bottleState.activeFormulaId; });
    if (!f) return;

    var format = state.formats[f.id];
    var category = f.category;
    var compatClosures = CLOSURE_COMPAT[category] || [];

    /* Build material + color filter chips */
    renderBottleFilterChips(format, compatClosures);

    var html = '';
    var visibleCount = 0;

    /* Standard MY.LAB option first (for ≤1000ml) */
    if (format <= 1000) {
      var stdSelected = bottleState.selections[f.id] === 'standard';
      html += '<div class="bulk-bottle bulk-bottle--standard' + (stdSelected ? ' bulk-bottle--selected' : '') + '" data-bottle-id="standard">' +
        '<span class="bulk-bottle__badge bulk-bottle__badge--included">Inclus</span>' +
        '<div class="bulk-bottle__img"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="1.5"><path d="M20 7H4a2 2 0 00-2 2v10a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z"/><path d="M16 3l-4 4-4-4"/></svg></div>' +
        '<div class="bulk-bottle__name">Packaging MY.LAB Standard</div>' +
        '<div class="bulk-bottle__meta"><span class="bulk-bottle__tag">Bouteille ambrée</span><span class="bulk-bottle__tag">' + (category === 'shampoing' ? 'Bouchon noir' : 'Pompe noire') + '</span></div>' +
        '<div class="bulk-bottle__price bulk-bottle__price--free">Inclus dans le prix</div>' +
        '</div>';
      visibleCount++;
    }

    /* Takemoto bottles filtered by compatibility */
    bottlesData.bottles.forEach(function (b) {
      if (!b.compatible_formats.includes(format)) return;
      var closureMatch = compatClosures.length === 0 || compatClosures.indexOf(b.closure_type) !== -1;

      /* Apply filters */
      var matMatch = bottleState.filterMaterial === 'all' || b.material === bottleState.filterMaterial;
      var colMatch = bottleState.filterColor === 'all' || b.color === bottleState.filterColor;
      var ecoMatch = !bottleState.filterEco || b.eco_label;
      var visible = matMatch && colMatch && ecoMatch;

      var isSelected = bottleState.selections[f.id] === b.id;
      var badges = '';
      if (b.eco_label) badges += '<span class="bulk-bottle__badge bulk-bottle__badge--eco">Éco</span>';
      if (closureMatch && !b.eco_label) badges += '<span class="bulk-bottle__badge bulk-bottle__badge--recommended">Recommandé</span>';

      var priceHtml = b.price_estimate
        ? '<div class="bulk-bottle__price">' + fmtPrice(b.price_estimate / 100) + ' HT/unité</div>'
        : '<div class="bulk-bottle__price" style="color:#888;">Prix sur demande</div>';

      var linkHtml = b.takemoto_url
        ? '<a href="' + esc(b.takemoto_url) + '" target="_blank" rel="noopener" class="bulk-bottle__link" onclick="event.stopPropagation()">Voir sur Takemoto <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 17L17 7M17 7H7M17 7v10"/></svg></a>'
        : '';

      html += '<div class="bulk-bottle' + (isSelected ? ' bulk-bottle--selected' : '') + (visible ? '' : ' bulk-bottle--hidden') + '" data-bottle-id="' + esc(b.id) + '" data-material="' + esc(b.material) + '" data-color="' + esc(b.color) + '" data-eco="' + b.eco_label + '">' +
        badges +
        '<div class="bulk-bottle__img">' +
          (b.image_url ? '<img src="' + esc(b.image_url) + '" alt="' + esc(b.name) + '">' : '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M3 7h18l-2 13H5L3 7z"/><path d="M8 7V5a4 4 0 018 0v2"/></svg>') +
        '</div>' +
        '<div class="bulk-bottle__name">' + esc(b.name) + '</div>' +
        '<div class="bulk-bottle__meta">' +
          '<span class="bulk-bottle__tag">' + (MATERIAL_LABELS[b.material] || b.material) + '</span>' +
          '<span class="bulk-bottle__tag">' + (CLOSURE_LABELS[b.closure_type] || b.closure_type) + '</span>' +
          '<span class="bulk-bottle__tag">' + (COLOR_LABELS[b.color] || b.color) + '</span>' +
          (b.eco_label ? '<span class="bulk-bottle__tag bulk-bottle__tag--eco">Éco</span>' : '') +
        '</div>' +
        priceHtml +
        linkHtml +
        '</div>';

      if (visible) visibleCount++;
    });

    elBottlesGrid.innerHTML = html;
    elBottlesEmpty.style.display = visibleCount === 0 ? '' : 'none';

    /* Bind click */
    elBottlesGrid.querySelectorAll('.bulk-bottle').forEach(function (card) {
      card.addEventListener('click', function () {
        var bid = card.dataset.bottleId;
        bottleState.selections[bottleState.activeFormulaId] = bid;
        renderBottleGrid();
        renderBottleTabs();
        renderBottleRecap();
      });
    });

    renderBottleRecap();
  }

  function renderBottleFilterChips(format, compatClosures) {
    if (!bottlesData || !elBottlesMatFilter || !elBottlesColFilter) return;

    var materials = {};
    var colors = {};
    bottlesData.bottles.forEach(function (b) {
      if (!b.compatible_formats.includes(format)) return;
      materials[b.material] = true;
      colors[b.color] = true;
    });

    var matHtml = '<button type="button" class="bulk-chip' + (bottleState.filterMaterial === 'all' ? ' bulk-chip--active' : '') + '" data-filter-material="all">Tous</button>';
    Object.keys(materials).forEach(function (m) {
      matHtml += '<button type="button" class="bulk-chip' + (bottleState.filterMaterial === m ? ' bulk-chip--active' : '') + '" data-filter-material="' + m + '">' + (MATERIAL_LABELS[m] || m) + '</button>';
    });
    elBottlesMatFilter.innerHTML = matHtml;

    var colHtml = '<button type="button" class="bulk-chip' + (bottleState.filterColor === 'all' ? ' bulk-chip--active' : '') + '" data-filter-color="all">Toutes</button>';
    Object.keys(colors).forEach(function (c) {
      colHtml += '<button type="button" class="bulk-chip' + (bottleState.filterColor === c ? ' bulk-chip--active' : '') + '" data-filter-color="' + c + '">' + (COLOR_LABELS[c] || c) + '</button>';
    });
    elBottlesColFilter.innerHTML = colHtml;

    /* Bind filter events */
    bindFilterEvents(elBottlesMatFilter, 'data-filter-material', function (val) {
      bottleState.filterMaterial = val;
      renderBottleGrid();
    });
    bindFilterEvents(elBottlesColFilter, 'data-filter-color', function (val) {
      bottleState.filterColor = val;
      renderBottleGrid();
    });
  }

  function renderBottleRecap() {
    if (!elBottlesRecap) return;
    var formulas = getSelectedFormulasWithFormat();
    var html = '';
    formulas.forEach(function (f) {
      var bid = bottleState.selections[f.id];
      var bottleName = '';
      if (bid === 'standard') {
        bottleName = 'MY.LAB Standard';
      } else if (bid && bottlesData) {
        var b = bottlesData.bottles.find(function (x) { return x.id === bid; });
        if (b) bottleName = b.name;
      }
      var icon = bid
        ? '<svg class="bulk-bottles__recap-check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2.5"><path d="M5 12l5 5L19 7"/></svg>'
        : '<svg class="bulk-bottles__recap-pending" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="2"><circle cx="12" cy="12" r="8"/></svg>';
      var fmtLabel = state.formats[f.id] >= 1000 ? (state.formats[f.id] / 1000) + 'L' : state.formats[f.id] + 'ml';
      html += '<div class="bulk-bottles__recap-item">' + icon +
        '<div><span class="bulk-bottles__recap-formula">' + esc(f.name) + ' — ' + fmtLabel + '</span>' +
        (bottleName ? '<br><span class="bulk-bottles__recap-bottle">' + esc(bottleName) + '</span>' : '<br><span class="bulk-bottles__recap-bottle" style="color:#c0392b;">À choisir</span>') +
        '</div></div>';
    });
    elBottlesRecap.innerHTML = html;
  }

  /* Eco filter */
  if (elBottlesEcoFilter) {
    elBottlesEcoFilter.addEventListener('change', function () {
      bottleState.filterEco = elBottlesEcoFilter.checked;
      renderBottleGrid();
    });
  }

  /* ══════════════════════════════════════════════
     STEP 4 — QUANTITY & PRICING
     ══════════════════════════════════════════════ */
  var elQtyList       = document.getElementById('bulk-quantity-list');
  var elGrandValue    = document.getElementById('bulk-quantity-grand-value');
  var elGrandUnits    = document.getElementById('bulk-quantity-grand-units');

  var qtyState = {};  // { formulaId: { kg: 50, tier: '50kg' } }

  function calculateOrder(formula, formatMl, kg, tierKey) {
    var fmtKey = formatMl + 'ml';
    var pricing = formula.pricing && formula.pricing[tierKey] && formula.pricing[tierKey][fmtKey];
    if (!pricing) return null;

    var nbUnits = Math.ceil((kg * 1000) / formatMl);
    var bottleId = bottleState.selections[formula.id];
    var isCustomBottle = bottleId && bottleId !== 'standard';
    var needsPump = formatMl === 1000 && formula.category !== 'shampoing';

    var formuleTotal = pricing.formule * nbUnits;
    var remplissageTotal = pricing.remplissage * nbUnits;
    var packagingTotal = isCustomBottle ? 0 : pricing.packaging * nbUnits;
    var etiquetteTotal = pricing.etiquette * nbUnits;
    var pumpTotal = needsPump ? 0.45 * nbUnits : 0;

    var bottleUnitPrice = 0;
    if (isCustomBottle && bottlesData) {
      var bObj = bottlesData.bottles.find(function (b) { return b.id === bottleId; });
      if (bObj && bObj.price_estimate) bottleUnitPrice = bObj.price_estimate / 100;
    }
    var bottleTotal = bottleUnitPrice * nbUnits;

    var grandTotal = formuleTotal + remplissageTotal + packagingTotal + etiquetteTotal + pumpTotal + bottleTotal;

    return {
      nbUnits: nbUnits,
      pricing: pricing,
      formuleTotal: formuleTotal,
      remplissageTotal: remplissageTotal,
      packagingTotal: packagingTotal,
      etiquetteTotal: etiquetteTotal,
      pumpTotal: pumpTotal,
      needsPump: needsPump,
      bottleUnitPrice: bottleUnitPrice,
      bottleTotal: bottleTotal,
      isCustomBottle: isCustomBottle,
      grandTotal: grandTotal
    };
  }

  function renderQuantity() {
    if (!elQtyList) return;
    var formulas = getSelectedFormulasWithFormat();
    if (formulas.length === 0) { elQtyList.innerHTML = ''; return; }

    var html = '';
    formulas.forEach(function (f) {
      var format = state.formats[f.id];
      var fmtLabel = format >= 1000 ? (format / 1000) + ' L' : format + ' ml';
      var bottleId = bottleState.selections[f.id] || 'standard';
      var bottleName = bottleId === 'standard' ? 'MY.LAB Standard' : '';
      if (bottleId !== 'standard' && bottlesData) {
        var bObj = bottlesData.bottles.find(function (b) { return b.id === bottleId; });
        if (bObj) bottleName = bObj.name;
      }

      if (!qtyState[f.id]) qtyState[f.id] = { kg: 50, tier: '50kg' };
      var qs = qtyState[f.id];

      /* Auto-detect tier */
      if (qs.kg >= 100) qs.tier = '100_200kg';
      else qs.tier = '50kg';

      var calc = calculateOrder(f, format, qs.kg, qs.tier);
      var tierLabel50 = '50 litres minimum';
      var tierLabel100 = '100 à 200 litres';

      html += '<div class="bulk-qty-block" style="--gamme-color:' + esc(f.gammeColor) + '">' +

        /* Header */
        '<div class="bulk-qty-block__header">' +
          '<span class="bulk-qty-block__dot" style="background:' + esc(f.gammeColor) + '"></span>' +
          '<span class="bulk-qty-block__label">' + esc(f.name) + '</span>' +
          '<span class="bulk-qty-block__detail">' + fmtLabel + ' · ' + esc(bottleName) + '</span>' +
        '</div>' +

        /* Tier selector */
        '<div class="bulk-qty-tiers">' +
          '<button type="button" class="bulk-qty-tier' + (qs.tier === '50kg' ? ' bulk-qty-tier--active' : '') + '" data-formula-qty="' + esc(f.id) + '" data-tier="50kg">' +
            tierLabel50 +
            (calc ? '<span class="bulk-qty-tier__price">' + fmtPrice(calc.pricing.total) + '/u</span>' : '') +
          '</button>' +
          '<button type="button" class="bulk-qty-tier' + (qs.tier === '100_200kg' ? ' bulk-qty-tier--active' : '') + '" data-formula-qty="' + esc(f.id) + '" data-tier="100_200kg">' +
            tierLabel100 +
            (f.pricing && f.pricing['100_200kg'] && f.pricing['100_200kg'][format + 'ml'] ? '<span class="bulk-qty-tier__price">' + fmtPrice(f.pricing['100_200kg'][format + 'ml'].total) + '/u</span>' : '') +
          '</button>' +
        '</div>' +

        /* Input */
        '<div class="bulk-qty-input-row">' +
          '<label>Quantité</label>' +
          '<input type="number" class="bulk-qty-input" data-formula-input="' + esc(f.id) + '" value="' + qs.kg + '" min="50" step="10">' +
          '<span class="bulk-qty-unit">kg</span>' +
        '</div>';

      if (calc) {
        html += '<div class="bulk-qty-calc">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2"><path d="M5 12l5 5L19 7"/></svg>' +
          qs.kg + ' kg = <strong>' + calc.nbUnits + ' flacons</strong> de ' + fmtLabel +
          '</div>';

        /* Price breakdown */
        html += '<div class="bulk-qty-table-wrap"><table class="bulk-qty-table">' +
          '<thead><tr><th>Composant</th><th>Prix unitaire</th><th>Quantité</th><th>Sous-total</th></tr></thead>' +
          '<tbody>' +
          '<tr><td>Formule</td><td>' + fmtPrice(calc.pricing.formule) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.formuleTotal) + '</td></tr>' +
          '<tr><td>Remplissage</td><td>' + fmtPrice(calc.pricing.remplissage) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.remplissageTotal) + '</td></tr>';

        if (calc.isCustomBottle && calc.bottleUnitPrice > 0) {
          html += '<tr><td>Flacon Takemoto</td><td>' + fmtPrice(calc.bottleUnitPrice) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.bottleTotal) + '</td></tr>';
        } else if (!calc.isCustomBottle) {
          html += '<tr><td>Packaging</td><td>' + fmtPrice(calc.pricing.packaging) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.packagingTotal) + '</td></tr>';
        }

        html += '<tr><td>Étiquette</td><td>' + fmtPrice(calc.pricing.etiquette) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.etiquetteTotal) + '</td></tr>';

        if (calc.needsPump) {
          html += '<tr><td>Pompe (option 1L)</td><td>' + fmtPrice(0.45) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.pumpTotal) + '</td></tr>';
        }

        html += '<tr class="bulk-qty-row--total"><td colspan="3">Total HT</td><td>' + fmtPrice(calc.grandTotal) + '</td></tr>' +
          '</tbody></table></div>';
      }

      html += '</div>';
    });

    elQtyList.innerHTML = html;
    updateGrandTotal();
    bindQtyEvents();
  }

  function updateGrandTotal() {
    var formulas = getSelectedFormulasWithFormat();
    var total = 0;
    var totalUnits = 0;

    formulas.forEach(function (f) {
      var qs = qtyState[f.id];
      if (!qs) return;
      var calc = calculateOrder(f, state.formats[f.id], qs.kg, qs.tier);
      if (calc) {
        total += calc.grandTotal;
        totalUnits += calc.nbUnits;
      }
    });

    if (elGrandValue) elGrandValue.textContent = fmtPrice(total) + ' HT';
    if (elGrandUnits) elGrandUnits.textContent = totalUnits + ' flacons au total';
  }

  function bindQtyEvents() {
    /* Tier buttons */
    elQtyList.querySelectorAll('.bulk-qty-tier').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var fid = btn.dataset.formulaQty;
        var tier = btn.dataset.tier;
        if (!qtyState[fid]) qtyState[fid] = { kg: 50, tier: '50kg' };
        qtyState[fid].tier = tier;
        if (tier === '100_200kg' && qtyState[fid].kg < 100) qtyState[fid].kg = 100;
        renderQuantity();
      });
    });

    /* Qty inputs */
    elQtyList.querySelectorAll('.bulk-qty-input').forEach(function (input) {
      input.addEventListener('input', function () {
        var fid = input.dataset.formulaInput;
        var val = parseInt(input.value, 10);
        if (isNaN(val) || val < 0) val = 0;
        if (!qtyState[fid]) qtyState[fid] = { kg: 50, tier: '50kg' };
        qtyState[fid].kg = val;
        if (val >= 100) qtyState[fid].tier = '100_200kg';
        else qtyState[fid].tier = '50kg';
        renderQuantity();
      });
    });
  }

  /* ══════════════════════════════════════════════
     INIT
     ══════════════════════════════════════════════ */
  renderStepper();

  Promise.all([
    fetch(config.formulasUrl).then(function (r) { if (!r.ok) throw new Error('Formulas HTTP ' + r.status); return r.json(); }),
    fetch(config.bottlesUrl).then(function (r) { if (!r.ok) throw new Error('Bottles HTTP ' + r.status); return r.json(); })
  ])
    .then(function (results) {
      state.data = results[0];
      bottlesData = results[1];
      renderGammeFilters();
      renderFormulas();
      updateSelectionBar();
    })
    .catch(function (err) {
      console.error('BulkOrder: impossible de charger les données', err);
      if (elGrid) elGrid.innerHTML = '<p style="text-align:center;color:#c00;padding:2rem;">Erreur de chargement des données. Veuillez rafraîchir la page.</p>';
    });

})();
