/**
 * MY.LAB — Configurateur Commande Gros Volumes
 * assets/bulk-order-core.js
 *
 * Shared state, constants, helpers, navigation between steps.
 * Must be loaded FIRST — other modules depend on window.BulkOrder.
 */
(function () {
  'use strict';

  var config = window.BulkOrderConfig;
  if (!config) return;

  /* ══════════════════════════════════════════════
     SHARED NAMESPACE
     ══════════════════════════════════════════════ */
  window.BulkOrder = {
    config: config,

    /* ── Global state ── */
    state: {
      step: 1,
      formulas: [],
      selectedIds: {},
      formats: {},
      skipTakemoto: false,
      filterGamme: 'all',
      filterType: 'all',
      data: null
    },

    /* ── Bottle state ── */
    bottleState: {
      activeFormulaId: null,
      selections: {},
      selectedColors: {},
      filterMaterial: 'all',
      filterColor: 'all',
      filterEco: false,
      filterMoqCompat: true,
      filterSprayOnly: false,
      filterClosure: 'all',
      page: 1
    },

    /* ── Quantity state ── */
    qtyState: {},

    /* ── Bottles JSON data ── */
    bottlesData: null,

    /* ── Product images ── */
    productImages: {},

    /* ── Module registry (filled by each module) ── */
    modules: {},

    /* ── Constants ── */
    STEPS: [
      { num: 1, label: 'Formules' },
      { num: 2, label: 'Format' },
      { num: 3, label: 'Flacon' },
      { num: 4, label: 'Quantité' },
      { num: 5, label: 'Récap' }
    ],

    LABELS: ['Sans sulfate', 'Sans parabène', 'Sans silicone', 'Vegan', 'Sans cruauté'],

    SERUM_HUILE_PRICING: {
      serum:  { 250: 6.45, 500: 6.10 },
      huile:  { 250: 5.80, 500: 5.50 }
    },

    CLOSURE_COMPAT: {
      shampoing: ['pump', 'screw_cap', 'nozzle', 'twist_cap'],
      creme_coiffage: ['pump', 'flip_top', 'disc', 'twist_cap'],
      masque: ['pump', 'flip_top', 'screw_cap', 'disc', 'twist_cap'],
      spray: ['spray'],
      serum: ['dropper', 'pump', 'nozzle'],
      huile: ['dropper', 'pump', 'nozzle']
    },

    COLOR_LABELS: { clear: 'Transparent', amber: 'Ambré', blush: 'Rose poudré', butter_yellow: 'Jaune beurre', mist: 'Fumé', teal: 'Bleu-vert', red: 'Rouge', white: 'Blanc', black: 'Noir', frosted: 'Givré' },
    COLOR_DOTS: { clear: '#f0f0f0', amber: '#b5651d', blush: '#e8a0a0', butter_yellow: '#f5d67a', mist: '#c0c0c0', teal: '#008080', red: '#c0392b', white: '#ffffff', black: '#333333', frosted: '#d4e4f7' },
    COLOR_ORDER: ['clear', 'amber', 'blush', 'butter_yellow', 'mist', 'teal', 'red', 'white', 'black', 'frosted'],
    MATERIAL_LABELS: { PET: 'PET', rPET: 'rPET', PCR: 'PCR', biomass_PET: 'Bio PET', glass: 'Verre' },
    CLOSURE_FILTER_LABELS: { screw_cap: '\uD83D\uDD12 Bouchon \u00e0 vis', flip_top: '\uD83D\uDD04 Bouchon clapet', pump: '\uD83E\uDDF4 Pompe cr\u00e8me', spray: '\uD83D\uDCA7 Spray', dropper: '\uD83D\uDC8A Pipette', nozzle: '\uD83D\uDD87 Bec verseur', disc: '\u25CE Disc top', twist_cap: '\uD83D\uDD04 Twist cap' },
    CLOSURE_ORDER: ['screw_cap', 'pump', 'spray', 'flip_top', 'twist_cap', 'nozzle', 'disc', 'dropper'],
    CLOSURE_LABELS: { pump: 'Pompe', screw_cap: 'Bouchon vis', flip_top: 'Clapet', spray: 'Spray', dropper: 'Pipette', nozzle: 'Bec verseur', disc: 'Disc top', twist_cap: 'Twist cap' },

    BOTTLES_PER_PAGE: 30,
    N8N_WEBHOOK: 'https://n8n.startec-paris.com/webhook/bulk-order-quote',

    /* ── DOM refs ── */
    els: {},

    /* ══════════════════════════════════════════════
       HELPERS
       ══════════════════════════════════════════════ */
    esc: function (str) {
      var d = document.createElement('div');
      d.textContent = str;
      return d.innerHTML;
    },

    selectedCount: function () {
      return Object.keys(this.state.selectedIds).length;
    },

    fmtPrice: function (euros) {
      return euros.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '\u00a0\u20ac';
    },

    isSerumOrHuile: function (formula) {
      return formula.category === 'serum' || formula.category === 'huile' || formula.pricing_mode === 'units';
    },

    getSelectedFormulasWithFormat: function () {
      var self = this;
      return this.state.formulas.filter(function (f) {
        return self.state.selectedIds[f.id] && self.state.formats[f.id];
      });
    },

    bindFilterEvents: function (container, attr, cb) {
      if (!container._bulkBoundAttrs) container._bulkBoundAttrs = {};
      if (container._bulkBoundAttrs[attr]) return;
      container._bulkBoundAttrs[attr] = true;
      container.addEventListener('click', function (e) {
        var btn = e.target.closest('.bulk-chip');
        if (!btn) return;
        container.querySelectorAll('.bulk-chip').forEach(function (c) {
          c.classList.remove('bulk-chip--active');
        });
        btn.classList.add('bulk-chip--active');
        cb(btn.getAttribute(attr));
      });
    },

    allFormatsChosen: function () {
      var self = this;
      var selected = this.state.formulas.filter(function (f) { return !!self.state.selectedIds[f.id]; });
      return selected.length > 0 && selected.every(function (f) { return !!self.state.formats[f.id]; });
    },

    allMoqsMet: function () {
      var self = this;
      var formulas = this.getSelectedFormulasWithFormat();
      return formulas.every(function (f) {
        var qs = self.qtyState[f.id];
        if (!qs) return false;
        var calc = self.calculateOrder(f, self.state.formats[f.id], qs.kg, qs.tier);
        return calc && calc.moqMet;
      });
    },

    /* ══════════════════════════════════════════════
       ORDER CALCULATION (shared by quantity & summary)
       ══════════════════════════════════════════════ */
    calculateOrder: function (formula, formatMl, kg, tierKey) {
      var fmtKey = formatMl + 'ml';
      var pricing = formula.pricing && formula.pricing[tierKey] && formula.pricing[tierKey][fmtKey];

      if (!pricing && formula.pricing && formula.pricing[tierKey] && formula.pricing[tierKey]['200ml']) {
        var base = formula.pricing[tierKey]['200ml'];
        var calcFormule = Math.round((base.formule / 200) * formatMl * 100) / 100;
        pricing = {
          formule: calcFormule,
          remplissage: base.remplissage,
          packaging: base.packaging,
          etiquette: base.etiquette,
          total: Math.round((calcFormule + base.remplissage + base.packaging + base.etiquette) * 100) / 100
        };
      }
      if (!pricing) return null;

      var nbUnits = Math.ceil((kg * 1000) / formatMl);
      var bottleId = this.bottleState.selections[formula.id];
      var isCustomBottle = bottleId && bottleId !== 'standard';
      var needsPump = formatMl === 1000 && formula.category !== 'shampoing';

      var formuleTotal = pricing.formule * nbUnits;
      var remplissageTotal = pricing.remplissage * nbUnits;
      var packagingTotal = isCustomBottle ? 0 : pricing.packaging * nbUnits;
      var etiquetteTotal = pricing.etiquette * nbUnits;
      var pumpTotal = needsPump ? 0.45 * nbUnits : 0;

      var bottleUnitPrice = 0;
      var bottleMoq = 0;
      var bottleName = '';
      var nbSets = 0;
      var nbBottlesOrdered = 0;
      var bottleSurplus = 0;

      if (isCustomBottle && this.bottlesData) {
        var bObj = this.bottlesData.bottles.find(function (b) { return b.id === bottleId; });
        if (bObj) {
          bottleName = bObj.name;
          var pickedCol = this.bottleState.selectedColors && this.bottleState.selectedColors[bottleId];
          var displayCol = pickedCol || (bObj.available_colors && bObj.available_colors[0]) || bObj.color;
          if (displayCol) bottleName += ' — ' + (this.COLOR_LABELS[displayCol] || displayCol);
          bottleMoq = bObj.min_order_qty || 0;

          if (bottleMoq > 0) {
            nbSets = Math.ceil(nbUnits / bottleMoq);
            nbBottlesOrdered = nbSets * bottleMoq;
          } else {
            nbBottlesOrdered = nbUnits;
            nbSets = 1;
          }

          bottleSurplus = nbBottlesOrdered - nbUnits;

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
    },

    /* ══════════════════════════════════════════════
       STEPPER
       ══════════════════════════════════════════════ */
    renderStepper: function () {
      var elStepper = this.els.stepper;
      if (!elStepper) return;
      var self = this;
      var html = '';
      this.STEPS.forEach(function (s) {
        var cls = '';
        if (s.num < self.state.step) cls = 'bulk-stepper__item--done';
        else if (s.num === self.state.step) cls = 'bulk-stepper__item--active';
        var icon = s.num < self.state.step
          ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg>'
          : s.num;
        html += '<div class="bulk-stepper__item ' + cls + '">' +
          '<span class="bulk-stepper__circle">' + icon + '</span>' +
          '<span class="bulk-stepper__label">' + self.esc(s.label) + '</span>' +
          '</div>';
      });
      elStepper.innerHTML = html;
    },

    /* ══════════════════════════════════════════════
       STEP NAVIGATION
       ══════════════════════════════════════════════ */
    goToStep: function (n) {
      if (n < 1 || n > 5) return;
      var self = this;

      if (n === 2 && this.state.step === 1 && this.selectedCount() === 0) return;
      if (n === 3 && this.state.step === 2 && !this.allFormatsChosen()) return;
      if (n === 5 && this.state.step === 4 && !this.allMoqsMet()) return;

      this.state.step = n;
      document.querySelectorAll('.bulk-order__step').forEach(function (el) {
        el.style.display = parseInt(el.dataset.step) === n ? '' : 'none';
      });
      this.els.prev.disabled = n === 1;
      this.els.next.disabled = n === 5;
      this.els.selBar.classList.toggle('bulk-selection-bar--visible', n === 1 && this.selectedCount() > 0);

      /* Render step-specific content via modules */
      if (n === 2 && this.modules.formulas && this.modules.formulas.renderFormats) {
        this.modules.formulas.renderFormats();
      }
      if (n === 3 && this.modules.bottles) {
        if (this.modules.bottles.renderBottleTabs) this.modules.bottles.renderBottleTabs();
        if (this.modules.bottles.renderBottleGrid) this.modules.bottles.renderBottleGrid();
      }
      if (n === 4 && this.modules.quantity && this.modules.quantity.renderQuantity) {
        this.modules.quantity.renderQuantity();
      }
      if (n === 5 && this.modules.summary && this.modules.summary.renderSummary) {
        this.modules.summary.renderSummary();
      }

      this.renderStepper();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    /* ══════════════════════════════════════════════
       INIT — cache DOM refs, bind nav, load data
       ══════════════════════════════════════════════ */
    init: function () {
      var self = this;

      /* Cache DOM refs */
      this.els.stepper    = document.getElementById('bulk-stepper');
      this.els.grid       = document.getElementById('bulk-formulas-grid');
      this.els.empty      = document.getElementById('bulk-formulas-empty');
      this.els.filterGamme = document.getElementById('bulk-filter-gamme');
      this.els.filterType = document.getElementById('bulk-filter-type');
      this.els.selBar     = document.getElementById('bulk-selection-bar');
      this.els.selCount   = document.getElementById('bulk-selection-count');
      this.els.selChips   = document.getElementById('bulk-selection-chips');
      this.els.selNext    = document.getElementById('bulk-formulas-next');
      this.els.prev       = document.getElementById('bulk-prev');
      this.els.next       = document.getElementById('bulk-next');

      if (!this.els.grid || !this.els.stepper) return;

      /* Backward compat */
      window.bulkOrderState = this.state;

      /* Nav buttons */
      if (this.els.prev) {
        this.els.prev.addEventListener('click', function () {
          if (self.state.step === 4 && self.state.skipTakemoto) {
            self.goToStep(2);
          } else {
            self.goToStep(self.state.step - 1);
          }
        });
      }
      if (this.els.next) {
        this.els.next.addEventListener('click', function () {
          if (self.state.step === 2) {
            if (!self.allFormatsChosen()) return;
            var has5L = self.state.formulas.some(function (f) {
              return self.state.selectedIds[f.id] && self.state.formats[f.id] === 5000;
            });
            if (has5L) {
              self.goToStep(3);
            }
            return;
          }
          self.goToStep(self.state.step + 1);
        });
      }
      if (this.els.selNext) {
        this.els.selNext.addEventListener('click', function () {
          if (self.selectedCount() > 0) self.goToStep(2);
        });
      }

      /* Type filter */
      if (this.els.filterType) {
        this.bindFilterEvents(this.els.filterType, 'data-filter-type', function (val) {
          self.state.filterType = val;
          if (self.modules.formulas && self.modules.formulas.applyFilters) {
            self.modules.formulas.applyFilters();
          }
        });
      }

      /* Render initial stepper */
      this.renderStepper();

      /* Load data */
      Promise.all([
        fetch(config.formulasUrl).then(function (r) { if (!r.ok) throw new Error('Formulas HTTP ' + r.status); return r.json(); }),
        fetch(config.bottlesUrl).then(function (r) { if (!r.ok) throw new Error('Bottles HTTP ' + r.status); return r.json(); }),
        config.productImagesUrl ? fetch(config.productImagesUrl).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }) : Promise.resolve({})
      ])
      .then(function (results) {
        self.state.data = results[0];
        self.bottlesData = results[1];
        self.productImages = results[2] || {};

        /* Notify modules that data is ready */
        if (self.modules.formulas && self.modules.formulas.onDataReady) {
          self.modules.formulas.onDataReady();
        }
      })
      .catch(function (err) {
        console.error('BulkOrder: impossible de charger les données', err);
        if (self.els.grid) {
          self.els.grid.innerHTML = '<p style="text-align:center;color:#c00;padding:2rem;">Erreur de chargement des données. Veuillez rafraîchir la page.</p>';
        }
      });
    }
  };

  /* Init after all deferred modules have loaded.
     Deferred scripts execute before DOMContentLoaded,
     so all modules will have registered by the time this fires. */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      window.BulkOrder.init();
    });
  } else {
    /* DOM already parsed (e.g. script loaded late) */
    window.BulkOrder.init();
  }

})();
