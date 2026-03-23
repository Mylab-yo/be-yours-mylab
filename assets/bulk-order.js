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
    state.step = n;
    document.querySelectorAll('.bulk-order__step').forEach(function (el) {
      el.style.display = parseInt(el.dataset.step) === n ? '' : 'none';
    });
    elPrev.disabled = n === 1;
    elNext.disabled = n === 5;
    elSelBar.classList.toggle('bulk-selection-bar--visible', n === 1 && selectedCount() > 0);
    renderStepper();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (elPrev) elPrev.addEventListener('click', function () { goToStep(state.step - 1); });
  if (elNext) elNext.addEventListener('click', function () { goToStep(state.step + 1); });
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
