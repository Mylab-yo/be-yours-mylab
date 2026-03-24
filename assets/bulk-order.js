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
  var productImages = {};  // { handle: imageUrl }

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
            (productImages[f.id] ?
              '<img class="bulk-card__product-img" src="' + productImages[f.id] + '" alt="' + esc(f.name) + '" loading="lazy">' :
              '<span class="bulk-card__color-dot"></span>') +
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
    if (n === 5 && state.step === 4 && !allMoqsMet()) return;

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
    if (n === 5) renderSummary();

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

  function allMoqsMet() {
    var formulas = getSelectedFormulasWithFormat();
    return formulas.every(function (f) {
      var qs = qtyState[f.id];
      if (!qs) return false;
      var calc = calculateOrder(f, state.formats[f.id], qs.kg, qs.tier);
      return calc && calc.moqMet;
    });
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
  var BOTTLES_PER_PAGE = 30;
  var bottleState = {
    activeFormulaId: null,
    selections: {},      // { formulaId: bottleId }
    filterMaterial: 'all',
    filterColor: 'all',
    filterEco: false,
    filterMoqCompat: true,  // show only MOQ-compatible by default
    page: 1
  };

  var CLOSURE_COMPAT = {
    shampoing: ['pump', 'screw_cap'],
    creme_coiffage: ['pump', 'dispensing_cap'],
    masque: ['pump', 'dispensing_cap', 'screw_cap'],
    spray: ['spray'],
    serum: ['dropper', 'pump'],
    huile: ['dropper', 'pump']
  };

  var COLOR_LABELS = { clear: 'Transparent', amber: 'Ambré', blush: 'Rose poudré', butter_yellow: 'Jaune beurre', mist: 'Fumé', teal: 'Bleu-vert', red: 'Rouge', white: 'Blanc', black: 'Noir', frosted: 'Givré' };
  var COLOR_DOTS = { clear: '#f0f0f0', amber: '#b5651d', blush: '#e8a0a0', butter_yellow: '#f5d67a', mist: '#c0c0c0', teal: '#008080', red: '#c0392b', white: '#ffffff', black: '#333333', frosted: '#d4e4f7' };
  var COLOR_ORDER = ['clear', 'amber', 'blush', 'butter_yellow', 'mist', 'teal', 'red', 'white', 'black', 'frosted'];
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

  var placeholderUrl = (config.placeholderUrl || '/assets/placeholder-bottle.svg');

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

    /* Calculate expected nb of bottles for MOQ compatibility check */
    var qs = qtyState[f.id] || { kg: 50, tier: '50kg' };
    var expectedUnits = Math.ceil((qs.kg * 1000) / format);

    /* Sort bottles: compatible first, then by price */
    var filteredBottles = bottlesData.bottles.filter(function (b) {
      return b.compatible_formats && b.compatible_formats.includes(format);
    }).sort(function (a, b2) {
      var aCompat = (!a.min_order_qty || expectedUnits >= a.min_order_qty) ? 0 : 1;
      var bCompat = (!b2.min_order_qty || expectedUnits >= b2.min_order_qty) ? 0 : 1;
      if (aCompat !== bCompat) return aCompat - bCompat;
      var aPrice = a.price_estimate || 99999;
      var bPrice = b2.price_estimate || 99999;
      return aPrice - bPrice;
    });

    /* Takemoto bottles — filter then paginate */
    var visibleBottles = [];
    filteredBottles.forEach(function (b) {
      var matMatch = bottleState.filterMaterial === 'all' || b.material === bottleState.filterMaterial;
      var colMatch = bottleState.filterColor === 'all' || b.color === bottleState.filterColor;
      var ecoMatch = !bottleState.filterEco || b.eco_label;
      var moqCompat = !b.min_order_qty || expectedUnits >= b.min_order_qty;
      var visible = matMatch && colMatch && ecoMatch;
      if (bottleState.filterMoqCompat && !moqCompat) visible = false;
      if (visible) visibleBottles.push({ bottle: b, moqCompat: moqCompat });
    });

    /* Pagination */
    var totalPages = Math.max(1, Math.ceil(visibleBottles.length / BOTTLES_PER_PAGE));
    if (bottleState.page > totalPages) bottleState.page = totalPages;
    var startIdx = (bottleState.page - 1) * BOTTLES_PER_PAGE;
    var pageBottles = visibleBottles.slice(startIdx, startIdx + BOTTLES_PER_PAGE);

    /* Render page of bottles */
    pageBottles.forEach(function (entry) {
      var b = entry.bottle;
      var moqCompat = entry.moqCompat;
      var isSelected = bottleState.selections[f.id] === b.id;

      var badges = '';
      if (moqCompat) {
        badges += '<span class="bulk-bottle__badge bulk-bottle__badge--compat">\u2713 Compatible</span>';
      } else {
        badges += '<span class="bulk-bottle__badge bulk-bottle__badge--moq-warn">\u26A0 Min. non atteint</span>';
      }
      if (b.eco_label) badges += '<span class="bulk-bottle__badge bulk-bottle__badge--eco">Éco</span>';

      var priceHtml = '';
      if (b.price_tiers && b.price_tiers.length > 0) {
        var lowestTier = b.price_tiers[b.price_tiers.length - 1];
        priceHtml = '<div class="bulk-bottle__price" tabindex="0">À partir de ' + fmtPrice(lowestTier.price) + '/u' +
          '<span class="bulk-bottle__tiers-tooltip">';
        b.price_tiers.forEach(function (t) {
          priceHtml += '<span>' + t.min_qty + (t.max_qty ? '–' + t.max_qty : '+') + ' u → ' + fmtPrice(t.price) + '</span>';
        });
        priceHtml += '</span></div>';
      } else if (b.price_estimate) {
        priceHtml = '<div class="bulk-bottle__price">' + fmtPrice(b.price_estimate / 100) + ' HT/unité</div>';
      } else {
        priceHtml = '<div class="bulk-bottle__price" style="color:#888;font-style:italic;">Prix sur demande</div>';
      }

      var moqHtml = '';
      if (b.min_order_qty) {
        var setTotal = b.price_estimate ? (b.price_estimate / 100) * b.min_order_qty : 0;
        moqHtml = '<div class="bulk-bottle__moq">Minimum : ' + b.min_order_qty + ' unités (1 set)' +
          (setTotal > 0 ? '<br>Set complet : ' + fmtPrice(setTotal) : '') + '</div>';
      }

      var linkHtml = b.takemoto_url
        ? '<a href="' + esc(b.takemoto_url) + '" target="_blank" rel="noopener" class="bulk-bottle__link" onclick="event.stopPropagation()">Voir sur Takemoto <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 17L17 7M17 7H7M17 7v10"/></svg></a>'
        : '';

      html += '<div class="bulk-bottle' + (isSelected ? ' bulk-bottle--selected' : '') + '" data-bottle-id="' + esc(b.id) + '" data-material="' + esc(b.material) + '" data-color="' + esc(b.color) + '" data-eco="' + b.eco_label + '">' +
        badges +
        '<div class="bulk-bottle__img" data-zoom-images="' + esc(JSON.stringify(b.images_all || [b.image_url_600 || b.image_url_external || ''])) + '">' +
          (b.image_url_600 ? '<img src="' + esc(b.image_url_600) + '" alt="' + esc(b.name) + '" loading="lazy" class="bulk-bottle__img--loading" onload="this.classList.remove(\'bulk-bottle__img--loading\');this.classList.add(\'bulk-bottle__img--loaded\')" onerror="this.src=\'' + placeholderUrl + '\'">' :
           b.image_url_external ? '<img src="' + esc(b.image_url_external) + '" alt="' + esc(b.name) + '" loading="lazy" class="bulk-bottle__img--loading" onload="this.classList.remove(\'bulk-bottle__img--loading\');this.classList.add(\'bulk-bottle__img--loaded\')" onerror="this.src=\'' + placeholderUrl + '\'">' :
           '<img src="' + placeholderUrl + '" alt="Placeholder" class="bulk-bottle__img--loaded">') +
        '</div>' +
        '<div class="bulk-bottle__body">' +
        '<div class="bulk-bottle__name">' + esc(b.name) + '</div>' +
        '<div class="bulk-bottle__meta">' +
          '<span class="bulk-bottle__tag">' + (MATERIAL_LABELS[b.material] || b.material) + '</span>' +
          '<span class="bulk-bottle__tag">' + (CLOSURE_LABELS[b.closure_type] || b.closure_type) + '</span>' +
          '<span class="bulk-bottle__tag">' + (COLOR_LABELS[b.color] || b.color) + '</span>' +
          (b.eco_label ? '<span class="bulk-bottle__tag bulk-bottle__tag--eco">Éco</span>' : '') +
        '</div>' +
        priceHtml +
        moqHtml +
        linkHtml +
        '</div></div>';

      visibleCount++;
    });

    /* Pagination controls */
    if (totalPages > 1) {
      html += '<div class="bulk-bottles__pagination">' +
        '<button type="button" class="bulk-bottles__page-btn" data-page-dir="prev"' + (bottleState.page <= 1 ? ' disabled' : '') + '>' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg> Précédent</button>' +
        '<span class="bulk-bottles__page-info">Page ' + bottleState.page + ' sur ' + totalPages + '</span>' +
        '<button type="button" class="bulk-bottles__page-btn" data-page-dir="next"' + (bottleState.page >= totalPages ? ' disabled' : '') + '>' +
        'Suivant <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></button>' +
        '</div>';
    }

    elBottlesGrid.innerHTML = html;
    elBottlesEmpty.style.display = visibleBottles.length === 0 ? '' : 'none';

    /* Bind pagination */
    elBottlesGrid.querySelectorAll('.bulk-bottles__page-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (btn.dataset.pageDir === 'prev' && bottleState.page > 1) bottleState.page--;
        if (btn.dataset.pageDir === 'next' && bottleState.page < totalPages) bottleState.page++;
        renderBottleGrid();
        var gridTop = elBottlesGrid.getBoundingClientRect().top + window.scrollY - 100;
        window.scrollTo({ top: gridTop, behavior: 'smooth' });
      });
    });

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
    COLOR_ORDER.forEach(function (c) {
      if (!colors[c]) return;
      var dot = COLOR_DOTS[c] || '#ccc';
      var border = c === 'clear' || c === 'white' ? 'border:1px solid #ccc;' : '';
      colHtml += '<button type="button" class="bulk-chip' + (bottleState.filterColor === c ? ' bulk-chip--active' : '') + '" data-filter-color="' + c + '">' +
        '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:' + dot + ';' + border + 'margin-right:6px;vertical-align:middle;"></span>' +
        (COLOR_LABELS[c] || c) + '</button>';
    });
    elBottlesColFilter.innerHTML = colHtml;

    /* Bind filter events */
    bindFilterEvents(elBottlesMatFilter, 'data-filter-material', function (val) {
      bottleState.filterMaterial = val;
      bottleState.page = 1;
      renderBottleGrid();
    });
    bindFilterEvents(elBottlesColFilter, 'data-filter-color', function (val) {
      bottleState.filterColor = val;
      bottleState.page = 1;
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
      bottleState.page = 1;
      renderBottleGrid();
    });
  }

  /* MOQ compatibility filter */
  var elBottlesMoqFilter = document.getElementById('bulk-bottles-moq-filter');
  if (elBottlesMoqFilter) {
    elBottlesMoqFilter.addEventListener('change', function () {
      bottleState.filterMoqCompat = elBottlesMoqFilter.checked;
      bottleState.page = 1;
      renderBottleGrid();
    });
  }

  /* ══════════════════════════════════════════════
     IMAGE ZOOM MODAL
     ══════════════════════════════════════════════ */
  var modalOverlay = null;
  var modalImages = [];
  var modalIndex = 0;

  function createModal() {
    if (modalOverlay) return;
    modalOverlay = document.createElement('div');
    modalOverlay.className = 'bulk-modal-overlay';
    modalOverlay.setAttribute('role', 'dialog');
    modalOverlay.setAttribute('aria-label', 'Image agrandie');
    modalOverlay.setAttribute('aria-modal', 'true');
    modalOverlay.innerHTML =
      '<div class="bulk-modal__content">' +
        '<button class="bulk-modal__close" aria-label="Fermer">&times;</button>' +
        '<button class="bulk-modal__nav bulk-modal__nav--prev" aria-label="Précédent"><svg width="14" height="14" viewBox="0 0 8 14" fill="none"><path d="M7 1L1 7l6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button>' +
        '<img class="bulk-modal__img" src="" alt="">' +
        '<button class="bulk-modal__nav bulk-modal__nav--next" aria-label="Suivant"><svg width="14" height="14" viewBox="0 0 8 14" fill="none"><path d="M1 1l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button>' +
        '<div class="bulk-modal__dots"></div>' +
      '</div>';
    document.body.appendChild(modalOverlay);

    modalOverlay.querySelector('.bulk-modal__close').addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', function (e) { if (e.target === modalOverlay) closeModal(); });
    modalOverlay.querySelector('.bulk-modal__nav--prev').addEventListener('click', function () { showModalImage(modalIndex - 1); });
    modalOverlay.querySelector('.bulk-modal__nav--next').addEventListener('click', function () { showModalImage(modalIndex + 1); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeModal(); });
  }

  function openModal(images, startIndex) {
    createModal();
    modalImages = images.filter(function (u) { return u && u.length > 0; });
    if (modalImages.length === 0) return;
    modalIndex = startIndex || 0;
    showModalImage(modalIndex);
    modalOverlay.classList.add('bulk-modal-overlay--open');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (!modalOverlay) return;
    modalOverlay.classList.remove('bulk-modal-overlay--open');
    document.body.style.overflow = '';
  }

  function showModalImage(idx) {
    if (idx < 0 || idx >= modalImages.length) return;
    modalIndex = idx;
    modalOverlay.querySelector('.bulk-modal__img').src = modalImages[idx];
    var navPrev = modalOverlay.querySelector('.bulk-modal__nav--prev');
    var navNext = modalOverlay.querySelector('.bulk-modal__nav--next');
    navPrev.style.display = modalImages.length > 1 ? '' : 'none';
    navNext.style.display = modalImages.length > 1 ? '' : 'none';
    navPrev.disabled = idx === 0;
    navNext.disabled = idx === modalImages.length - 1;

    /* Dots */
    var dotsHtml = '';
    if (modalImages.length > 1) {
      for (var i = 0; i < modalImages.length; i++) {
        dotsHtml += '<button class="bulk-modal__dot' + (i === idx ? ' bulk-modal__dot--active' : '') + '" data-dot="' + i + '"></button>';
      }
    }
    var dotsEl = modalOverlay.querySelector('.bulk-modal__dots');
    dotsEl.innerHTML = dotsHtml;
    dotsEl.querySelectorAll('.bulk-modal__dot').forEach(function (d) {
      d.addEventListener('click', function () { showModalImage(parseInt(d.dataset.dot)); });
    });
  }

  /* Bind image clicks for zoom */
  document.addEventListener('click', function (e) {
    var imgWrap = e.target.closest('.bulk-bottle__img[data-zoom-images]');
    if (!imgWrap || e.target.closest('.bulk-bottle__body') || e.target.closest('a')) return;
    try {
      var images = JSON.parse(imgWrap.dataset.zoomImages);
      if (images && images.length > 0 && images[0]) {
        e.stopPropagation();
        openModal(images, 0);
      }
    } catch (err) {}
  });

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

    /* Production costs (based on nbUnits = actual product units) */
    var formuleTotal = pricing.formule * nbUnits;
    var remplissageTotal = pricing.remplissage * nbUnits;
    var packagingTotal = isCustomBottle ? 0 : pricing.packaging * nbUnits;
    var etiquetteTotal = pricing.etiquette * nbUnits;
    var pumpTotal = needsPump ? 0.45 * nbUnits : 0;

    /* Bottle / Takemoto costs */
    var bottleUnitPrice = 0;
    var bottleMoq = 0;
    var bottleName = '';
    var nbSets = 0;
    var nbBottlesOrdered = 0; /* actual bottles ordered (rounded to sets) */
    var bottleSurplus = 0;

    if (isCustomBottle && bottlesData) {
      var bObj = bottlesData.bottles.find(function (b) { return b.id === bottleId; });
      if (bObj) {
        bottleName = bObj.name;
        bottleMoq = bObj.min_order_qty || 0;

        /* Round up to full sets */
        if (bottleMoq > 0) {
          nbSets = Math.ceil(nbUnits / bottleMoq);
          nbBottlesOrdered = nbSets * bottleMoq;
        } else {
          nbBottlesOrdered = nbUnits;
          nbSets = 1;
        }

        bottleSurplus = nbBottlesOrdered - nbUnits;

        /* Apply tier pricing based on actual bottles ordered */
        if (bObj.price_tiers && bObj.price_tiers.length > 0) {
          bottleUnitPrice = bObj.price_tiers[0].price;
          for (var ti = 0; ti < bObj.price_tiers.length; ti++) {
            if (nbBottlesOrdered >= bObj.price_tiers[ti].min_qty) {
              bottleUnitPrice = bObj.price_tiers[ti].price;
            }
          }
        } else if (bObj.price_estimate) {
          bottleUnitPrice = bObj.price_estimate / 100;
        }
      }
    }

    var bottleTotal = bottleUnitPrice * nbBottlesOrdered;
    var moqMet = !isCustomBottle || bottleMoq === 0 || nbUnits >= bottleMoq;
    var moqMinKg = bottleMoq > 0 ? Math.ceil((bottleMoq * formatMl) / 1000) : 0;
    var setPrice = bottleUnitPrice * bottleMoq;

    var productionTotal = formuleTotal + remplissageTotal + packagingTotal + etiquetteTotal + pumpTotal;
    var grandTotal = productionTotal + bottleTotal;

    return {
      nbUnits: nbUnits,
      pricing: pricing,
      formuleTotal: formuleTotal,
      remplissageTotal: remplissageTotal,
      packagingTotal: packagingTotal,
      etiquetteTotal: etiquetteTotal,
      pumpTotal: pumpTotal,
      needsPump: needsPump,
      productionTotal: productionTotal,
      bottleUnitPrice: bottleUnitPrice,
      bottleTotal: bottleTotal,
      bottleName: bottleName,
      bottleMoq: bottleMoq,
      nbSets: nbSets,
      nbBottlesOrdered: nbBottlesOrdered,
      bottleSurplus: bottleSurplus,
      setPrice: setPrice,
      moqMet: moqMet,
      moqMinKg: moqMinKg,
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

        /* MOQ status */
        if (calc.isCustomBottle && calc.bottleMoq > 0) {
          if (!calc.moqMet) {
            /* CAS 2: MOQ not met */
            html += '<div class="bulk-qty-moq-warning">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e65100" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>' +
              '<div><strong>Quantit\u00e9 insuffisante pour ce flacon</strong>' +
              '<p>Votre commande : <strong>' + calc.nbUnits + ' flacons</strong><br>' +
              'Minimum requis : <strong>' + calc.bottleMoq + ' flacons</strong> (1 set Takemoto)<br>' +
              '\u2192 Augmentez \u00e0 au moins <strong>' + calc.moqMinKg + ' kg</strong> pour atteindre le minimum.</p></div>' +
              '</div>';
          } else if (calc.moqMet && calc.bottleSurplus > 0) {
            /* CAS 3: MOQ met but not exact multiple */
            html += '<div class="bulk-qty-moq-info">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1565c0" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>' +
              '<div>Takemoto livre par sets de <strong>' + calc.bottleMoq + '</strong>. ' +
              'Vous commanderez <strong>' + calc.nbSets + ' set' + (calc.nbSets > 1 ? 's' : '') + '</strong> ' +
              'soit <strong>' + calc.nbBottlesOrdered + ' flacons</strong>. ' +
              'Surplus de ' + calc.bottleSurplus + ' flacon' + (calc.bottleSurplus > 1 ? 's' : '') + '.</div>' +
              '</div>';
          } else {
            /* CAS 1: Perfect match */
            html += '<div class="bulk-qty-moq-ok">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2.5"><path d="M5 12l5 5L19 7"/></svg>' +
              'Votre commande de ' + calc.nbUnits + ' flacons respecte le minimum de ' + calc.bottleMoq + ' unit\u00e9s.' +
              '</div>';
          }
        }

        /* Price breakdown — Production MY.LAB */
        html += '<div class="bulk-qty-table-wrap"><table class="bulk-qty-table">' +
          '<thead><tr><th>Composant</th><th>Prix unitaire</th><th>Quantité</th><th>Sous-total</th></tr></thead>' +
          '<tbody>' +
          '<tr><td colspan="4" class="bulk-qty-section-label">Production MY.LAB</td></tr>' +
          '<tr><td>Formule</td><td>' + fmtPrice(calc.pricing.formule) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.formuleTotal) + '</td></tr>' +
          '<tr><td>Remplissage</td><td>' + fmtPrice(calc.pricing.remplissage) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.remplissageTotal) + '</td></tr>';

        html += '<tr><td>Étiquette</td><td>' + fmtPrice(calc.pricing.etiquette) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.etiquetteTotal) + '</td></tr>';

        if (calc.needsPump) {
          html += '<tr><td>Pompe (option 1L)</td><td>' + fmtPrice(0.45) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.pumpTotal) + '</td></tr>';
        }

        /* Packaging section */
        html += '<tr><td colspan="4" class="bulk-qty-section-label">Packaging</td></tr>';
        if (calc.isCustomBottle && calc.bottleUnitPrice > 0) {
          html += '<tr><td>Flacon ' + esc(calc.bottleName) + '</td><td>' + fmtPrice(calc.bottleUnitPrice) + '</td><td>' + calc.nbBottlesOrdered + '*</td><td>' + fmtPrice(calc.bottleTotal) + '</td></tr>';
        } else if (calc.isCustomBottle && calc.bottleUnitPrice === 0) {
          html += '<tr><td>Flacon ' + esc(calc.bottleName) + '</td><td colspan="3" style="color:#888;font-style:italic;">Prix sur demande</td></tr>';
        } else {
          html += '<tr><td>Packaging MY.LAB Standard</td><td>' + fmtPrice(calc.pricing.packaging) + '</td><td>' + calc.nbUnits + '</td><td>' + fmtPrice(calc.packagingTotal) + '</td></tr>';
        }

        html += '<tr class="bulk-qty-row--total"><td colspan="3">Total HT</td><td>' + fmtPrice(calc.grandTotal) + '</td></tr>' +
          '</tbody></table>';

        /* Note about sets */
        if (calc.isCustomBottle && calc.bottleMoq > 0 && calc.nbBottlesOrdered > calc.nbUnits) {
          html += '<p class="bulk-qty-set-note">* Flacons livr\u00e9s par sets de ' + calc.bottleMoq + ' (' + calc.nbSets + ' set' + (calc.nbSets > 1 ? 's' : '') + ' command\u00e9' + (calc.nbSets > 1 ? 's' : '') + ')</p>';
        }
        html += '</div>';
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
     STEP 5 — SUMMARY & QUOTE
     ══════════════════════════════════════════════ */
  var elSummaryRef   = document.getElementById('bulk-summary-ref');
  var elSummaryDate  = document.getElementById('bulk-summary-date');
  var elSummaryBody  = document.getElementById('bulk-summary-body');
  var elSummaryFoot  = document.getElementById('bulk-summary-foot');
  var elSummaryForm  = document.getElementById('bulk-summary-form');
  var elBtnPdf       = document.getElementById('bulk-btn-pdf');
  var elBtnSend      = document.getElementById('bulk-btn-send');
  var elSummaryOk    = document.getElementById('bulk-summary-success');

  function genRef() {
    var d = new Date();
    var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
    var rand = Math.floor(1000 + Math.random() * 9000);
    return 'MYLAB-GV-' + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + '-' + rand;
  }

  function renderSummary() {
    if (!elSummaryBody || !elSummaryFoot) return;
    var formulas = getSelectedFormulasWithFormat();
    var now = new Date();
    var dateStr = now.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });

    if (elSummaryRef) elSummaryRef.textContent = 'Réf. : ' + genRef();
    if (elSummaryDate) elSummaryDate.textContent = 'Date : ' + dateStr;

    var bodyHtml = '';
    var totalHT = 0;
    var totalUnits = 0;

    formulas.forEach(function (f) {
      var format = state.formats[f.id];
      var fmtLabel = format >= 1000 ? (format / 1000) + ' L' : format + ' ml';
      var qs = qtyState[f.id] || { kg: 50, tier: '50kg' };
      var calc = calculateOrder(f, format, qs.kg, qs.tier);
      if (!calc) return;

      var bottleId = bottleState.selections[f.id] || 'standard';
      var bottleName = 'MY.LAB Standard';
      if (bottleId !== 'standard' && bottlesData) {
        var bObj = bottlesData.bottles.find(function (b) { return b.id === bottleId; });
        if (bObj) bottleName = bObj.name;
      }

      totalHT += calc.grandTotal;
      totalUnits += calc.nbUnits;

      bodyHtml += '<tr>' +
        '<td><span class="bulk-summary__gamme-dot" style="background:' + esc(f.gammeColor) + '"></span>' + esc(f.gammeLabel.replace('Gamme ', '')) + '</td>' +
        '<td>' + esc(f.name) + '</td>' +
        '<td>' + fmtLabel + '</td>' +
        '<td>' + esc(bottleName) + '</td>' +
        '<td>' + qs.kg + ' kg</td>' +
        '<td>' + calc.nbUnits + '</td>' +
        '<td>' + fmtPrice(calc.grandTotal / calc.nbUnits) + '</td>' +
        '<td>' + fmtPrice(calc.grandTotal) + '</td>' +
        '</tr>';
    });

    elSummaryBody.innerHTML = bodyHtml;

    var tva = totalHT * 0.20;
    var ttc = totalHT + tva;

    elSummaryFoot.innerHTML =
      '<tr class="bulk-summary__row--subtotal"><td colspan="7">Sous-total HT</td><td>' + fmtPrice(totalHT) + '</td></tr>' +
      '<tr class="bulk-summary__row--tva"><td colspan="7">TVA (20%)</td><td>' + fmtPrice(tva) + '</td></tr>' +
      '<tr class="bulk-summary__row--total"><td colspan="7">Total TTC</td><td>' + fmtPrice(ttc) + '</td></tr>';
  }

  function collectFormData() {
    return {
      firstname: document.getElementById('bulk-client-firstname').value.trim(),
      lastname: document.getElementById('bulk-client-lastname').value.trim(),
      company: document.getElementById('bulk-client-company').value.trim(),
      email: document.getElementById('bulk-client-email').value.trim(),
      phone: document.getElementById('bulk-client-phone').value.trim(),
      city: document.getElementById('bulk-client-city').value.trim(),
      notes: document.getElementById('bulk-client-notes').value.trim()
    };
  }

  function buildQuotePayload() {
    var client = collectFormData();
    var formulas = getSelectedFormulasWithFormat();
    var items = [];
    var totalHT = 0;

    formulas.forEach(function (f) {
      var format = state.formats[f.id];
      var qs = qtyState[f.id] || { kg: 50, tier: '50kg' };
      var calc = calculateOrder(f, format, qs.kg, qs.tier);
      if (!calc) return;

      var bottleId = bottleState.selections[f.id] || 'standard';
      var bottleName = 'MY.LAB Standard';
      if (bottleId !== 'standard' && bottlesData) {
        var bObj = bottlesData.bottles.find(function (b) { return b.id === bottleId; });
        if (bObj) bottleName = bObj.name;
      }

      totalHT += calc.grandTotal;

      items.push({
        gamme: f.gammeLabel,
        product: f.name,
        format: format + 'ml',
        bottle: bottleName,
        quantity_kg: qs.kg,
        nb_units: calc.nbUnits,
        unit_price: Math.round(calc.grandTotal / calc.nbUnits * 100) / 100,
        total_ht: Math.round(calc.grandTotal * 100) / 100,
        tier: qs.tier
      });
    });

    return {
      ref: elSummaryRef ? elSummaryRef.textContent.replace('Réf. : ', '') : genRef(),
      date: new Date().toISOString(),
      client: client,
      items: items,
      total_ht: Math.round(totalHT * 100) / 100,
      tva: Math.round(totalHT * 0.20 * 100) / 100,
      total_ttc: Math.round(totalHT * 1.20 * 100) / 100,
      source: 'Shopify — Commande Gros Volumes'
    };
  }

  /* PDF generation (lazy load html2pdf) */
  function generatePDF() {
    var summaryEl = document.getElementById('bulk-summary');
    if (!summaryEl) return;

    /* Hide buttons and form for PDF */
    var actions = summaryEl.querySelector('.bulk-summary__actions');
    var formWrap = summaryEl.querySelector('.bulk-summary__form-wrap');
    if (actions) actions.style.display = 'none';
    if (formWrap) formWrap.style.display = 'none';

    var script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
    script.onload = function () {
      var ref = elSummaryRef ? elSummaryRef.textContent.replace('Réf. : ', '') : 'devis';
      html2pdf().set({
        margin: [10, 10, 10, 10],
        filename: ref + '.pdf',
        image: { type: 'jpeg', quality: 0.95 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' }
      }).from(summaryEl).save().then(function () {
        if (actions) actions.style.display = '';
        if (formWrap) formWrap.style.display = '';
      });
    };
    document.head.appendChild(script);
  }

  /* Send quote via webhook */
  function sendQuote() {
    var client = collectFormData();
    if (!client.firstname || !client.lastname || !client.company || !client.email) {
      alert('Veuillez remplir tous les champs obligatoires (Prénom, Nom, Société, Email).');
      return;
    }

    var payload = buildQuotePayload();
    elBtnSend.disabled = true;
    elBtnSend.textContent = 'Envoi en cours...';

    /* Send to Shopify contact form as fallback */
    var formData = new FormData();
    formData.append('form_type', 'contact');
    formData.append('utf8', '✓');
    formData.append('contact[email]', client.email);
    formData.append('contact[Prenom]', client.firstname);
    formData.append('contact[Nom]', client.lastname);
    formData.append('contact[Societe]', client.company);
    formData.append('contact[Telephone]', client.phone);
    formData.append('contact[Ville]', client.city);
    formData.append('contact[Notes]', client.notes);
    formData.append('contact[Formulaire]', 'Devis Gros Volumes');
    formData.append('contact[Devis]', JSON.stringify(payload.items));
    formData.append('contact[Total_HT]', payload.total_ht + ' EUR');
    formData.append('contact[Reference]', payload.ref);

    fetch('/contact#contact_form', {
      method: 'POST',
      body: formData
    })
    .then(function () {
      /* Also send to n8n if configured */
      if (config.webhookUrl) {
        fetch(config.webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          keepalive: true
        }).catch(function () {});
      }

      elSummaryForm.style.display = 'none';
      document.querySelector('.bulk-summary__actions').style.display = 'none';
      document.querySelector('.bulk-summary__conditions').style.display = 'none';
      elSummaryOk.style.display = '';
      window.scrollTo({ top: elSummaryOk.offsetTop - 100, behavior: 'smooth' });
    })
    .catch(function () {
      elBtnSend.disabled = false;
      elBtnSend.textContent = 'Envoyer le devis par email';
      alert('Erreur lors de l\'envoi. Veuillez réessayer ou nous contacter directement.');
    });
  }

  /* Bind buttons */
  if (elBtnPdf) elBtnPdf.addEventListener('click', generatePDF);
  if (elBtnSend) elBtnSend.addEventListener('click', sendQuote);

  /* ══════════════════════════════════════════════
     INIT
     ══════════════════════════════════════════════ */
  renderStepper();

  Promise.all([
    fetch(config.formulasUrl).then(function (r) { if (!r.ok) throw new Error('Formulas HTTP ' + r.status); return r.json(); }),
    fetch(config.bottlesUrl).then(function (r) { if (!r.ok) throw new Error('Bottles HTTP ' + r.status); return r.json(); }),
    config.productImagesUrl ? fetch(config.productImagesUrl).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }) : Promise.resolve({})
  ])
    .then(function (results) {
      state.data = results[0];
      bottlesData = results[1];
      productImages = results[2] || {};
      renderGammeFilters();
      renderFormulas();
      updateSelectionBar();
    })
    .catch(function (err) {
      console.error('BulkOrder: impossible de charger les données', err);
      if (elGrid) elGrid.innerHTML = '<p style="text-align:center;color:#c00;padding:2rem;">Erreur de chargement des données. Veuillez rafraîchir la page.</p>';
    });

})();
