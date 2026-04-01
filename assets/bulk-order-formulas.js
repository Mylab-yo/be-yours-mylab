/**
 * MY.LAB — Configurateur Commande Gros Volumes
 * assets/bulk-order-formulas.js
 *
 * Step 1 (formula selection) + Step 2 (format selection).
 * Depends on: bulk-order-core.js (window.BulkOrder)
 */
(function () {
  'use strict';

  var B = window.BulkOrder;
  if (!B) return;

  /* ══════════════════════════════════════════════
     DOM REFS (step 2)
     ══════════════════════════════════════════════ */
  var elFormatList   = document.getElementById('bulk-format-list');
  var elTakemoto     = document.getElementById('bulk-format-takemoto');
  var el5lNotice     = document.getElementById('bulk-format-5l-notice');
  var elTakemotoYes  = document.getElementById('bulk-takemoto-yes');
  var elTakemotoNo   = document.getElementById('bulk-takemoto-no');

  /* ══════════════════════════════════════════════
     GAMME FILTER CHIPS
     ══════════════════════════════════════════════ */
  function renderGammeFilters() {
    if (!B.state.data || !B.els.filterGamme) return;
    var html = '<button type="button" class="bulk-chip bulk-chip--active" data-filter-gamme="all">Toutes</button>';
    B.state.data.gammes.forEach(function (g) {
      html += '<button type="button" class="bulk-chip bulk-chip--gamme" ' +
        'data-filter-gamme="' + B.esc(g.id) + '" ' +
        'style="--gamme-color:' + B.esc(g.color) + '">' +
        B.esc(g.label.replace('Gamme ', '')) +
        '</button>';
    });
    B.els.filterGamme.innerHTML = html;
    B.bindFilterEvents(B.els.filterGamme, 'data-filter-gamme', function (val) {
      B.state.filterGamme = val;
      applyFilters();
    });
  }

  /* ══════════════════════════════════════════════
     FORMULA CARDS
     ══════════════════════════════════════════════ */
  function renderFormulas() {
    if (!B.state.data) return;
    B.state.formulas = [];
    var html = '';

    B.state.data.gammes.forEach(function (gamme) {
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
          pricing_mode: f.pricing_mode || null,
          packaging_notes: f.packaging_notes
        };
        B.state.formulas.push(formula);

        var isSelected = !!B.state.selectedIds[f.id];
        var selClass = isSelected ? ' bulk-card--selected' : '';

        html += '<div class="bulk-card' + selClass + '" ' +
          'data-formula-id="' + B.esc(f.id) + '" ' +
          'data-gamme="' + B.esc(gamme.id) + '" ' +
          'data-category="' + B.esc(f.category) + '" ' +
          'style="--gamme-color:' + B.esc(gamme.color) + '">' +

          '<span class="bulk-card__check">' +
            (isSelected ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg>' : '') +
          '</span>' +

          '<div class="bulk-card__visual">' +
            (B.productImages[f.id] ?
              '<img class="bulk-card__product-img" src="' + B.productImages[f.id] + '" alt="' + B.esc(f.name) + '" loading="lazy">' :
              '<span class="bulk-card__color-dot"></span>') +
            '<span class="bulk-card__gamme-label">' + B.esc(gamme.label.replace('Gamme ', '')) + '</span>' +
          '</div>' +

          '<div class="bulk-card__name">' + B.esc(f.name) + '</div>' +

          '<span class="bulk-card__natural">' +
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' +
            f.natural_pct + '% naturel' +
          '</span>' +

          '<div class="bulk-card__actifs">' +
            f.actifs.map(function (a) { return '<span class="bulk-card__actif-tag">' + B.esc(a) + '</span>'; }).join('') +
          '</div>' +

          '<div class="bulk-card__labels">' +
            B.LABELS.map(function (l) { return '<span class="bulk-card__label">' + B.esc(l) + '</span>'; }).join('') +
          '</div>' +

          '</div>';
      });
    });

    B.els.grid.innerHTML = html;
    bindCardEvents();
  }

  function bindCardEvents() {
    B.els.grid.addEventListener('click', function (e) {
      var card = e.target.closest('.bulk-card');
      if (!card) return;
      var id = card.dataset.formulaId;
      if (B.state.selectedIds[id]) {
        delete B.state.selectedIds[id];
        card.classList.remove('bulk-card--selected');
        card.querySelector('.bulk-card__check').innerHTML = '';
      } else {
        B.state.selectedIds[id] = true;
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
    var cards = B.els.grid.querySelectorAll('.bulk-card');
    var visible = 0;
    cards.forEach(function (card) {
      var matchGamme = B.state.filterGamme === 'all' || card.dataset.gamme === B.state.filterGamme;
      var matchType = B.state.filterType === 'all' || card.dataset.category === B.state.filterType;
      if (matchGamme && matchType) {
        card.classList.remove('bulk-card--hidden');
        visible++;
      } else {
        card.classList.add('bulk-card--hidden');
      }
    });
    B.els.empty.style.display = visible === 0 ? '' : 'none';
  }

  /* ══════════════════════════════════════════════
     SELECTION BAR
     ══════════════════════════════════════════════ */
  function updateSelectionBar() {
    var count = B.selectedCount();
    B.els.selCount.textContent = count;
    B.els.selNext.disabled = count === 0;

    if (count > 0) {
      B.els.selBar.classList.add('bulk-selection-bar--visible');
    } else {
      B.els.selBar.classList.remove('bulk-selection-bar--visible');
    }

    var html = '';
    B.state.formulas.forEach(function (f) {
      if (!B.state.selectedIds[f.id]) return;
      var short = f.name.replace('Crème de Coiffage ', 'Crème ').replace('Shampoing-Gel Douche', 'Gel Douche');
      html += '<span class="bulk-selection-chip" data-remove-id="' + B.esc(f.id) + '">' +
        B.esc(short) +
        '<span class="bulk-selection-chip__x">×</span>' +
        '</span>';
    });
    B.els.selChips.innerHTML = html;
  }

  /* Remove chip click */
  document.addEventListener('click', function (e) {
    var chip = e.target.closest('.bulk-selection-chip');
    if (!chip) return;
    var id = chip.dataset.removeId;
    if (id && B.state.selectedIds[id]) {
      delete B.state.selectedIds[id];
      var card = B.els.grid.querySelector('[data-formula-id="' + id + '"]');
      if (card) {
        card.classList.remove('bulk-card--selected');
        card.querySelector('.bulk-card__check').innerHTML = '';
      }
      updateSelectionBar();
    }
  });

  /* ══════════════════════════════════════════════
     STEP 2 — FORMAT SELECTION
     ══════════════════════════════════════════════ */
  function getPackagingNote(format, category) {
    if (format === 5000) return 'Packaging à votre charge';
    if (format === 1000) return 'Packaging inclus : bouteille ambrée + bouchon blanc (pompe en option : +0,45\u00a0\u20ac/unité)';
    if (category === 'shampoing') return 'Packaging inclus : bouteille ambrée + bouchon noir';
    return 'Packaging inclus : bouteille ambrée + pompe noire';
  }

  function renderFormats() {
    if (!elFormatList || !B.state.data) return;

    var selected = B.state.formulas.filter(function (f) { return !!B.state.selectedIds[f.id]; });

    if (selected.length === 0) {
      elFormatList.innerHTML = '<p style="text-align:center;color:#888;padding:2rem;">Aucune formule sélectionnée. Retournez à l\'étape 1.</p>';
      return;
    }

    var html = '';
    selected.forEach(function (f) {
      var currentFormat = B.state.formats[f.id] || null;

      /* Sérum/Huile: auto-set 50ml */
      if (B.isSerumOrHuile(f)) {
        B.state.formats[f.id] = 50;
        html += '<div class="bulk-format-row" style="--gamme-color:' + B.esc(f.gammeColor) + '">' +
          '<div class="bulk-format-row__header">' +
            '<span class="bulk-format-row__dot"></span>' +
            '<span class="bulk-format-row__gamme">' + B.esc(f.gammeLabel.replace('Gamme ', '')) + '</span>' +
          '</div>' +
          '<div class="bulk-format-row__name">' + B.esc(f.name) + '</div>' +
          '<div class="bulk-format-row__formats">' +
            '<button type="button" class="bulk-format-pill bulk-format-pill--active" data-formula-id="' + B.esc(f.id) + '" data-format="50">50 ml</button>' +
          '</div>' +
          '<div class="bulk-format-row__price" style="color:#888;font-style:italic;">Format fixe 50 ml — Commande en unités (250 ou 500 u.)</div>' +
          '</div>';
        return;
      }

      var dynamicFormats = f.available_formats || [200, 500];

      html += '<div class="bulk-format-row" style="--gamme-color:' + B.esc(f.gammeColor) + '">' +
        '<div class="bulk-format-row__header">' +
          '<span class="bulk-format-row__dot"></span>' +
          '<span class="bulk-format-row__gamme">' + B.esc(f.gammeLabel.replace('Gamme ', '')) + '</span>' +
        '</div>' +
        '<div class="bulk-format-row__name">' + B.esc(f.name) + '</div>' +
        '<div class="bulk-format-row__formats">';

      dynamicFormats.forEach(function (fmt) {
        var label = fmt >= 1000 ? (fmt / 1000) + ' L' : fmt + ' ml';
        var isActive = currentFormat === fmt;
        html += '<button type="button" class="bulk-format-pill' + (isActive ? ' bulk-format-pill--active' : '') + '" ' +
          'data-formula-id="' + B.esc(f.id) + '" data-format="' + fmt + '">' +
          label +
          '</button>';
      });

      html += '</div>';

      /* Price indication */
      if (currentFormat && f.pricing) {
        var fmtKey = currentFormat + 'ml';
        var priceData = f.pricing['50kg'] && f.pricing['50kg'][fmtKey];

        if (!priceData && f.pricing['50kg'] && f.pricing['50kg']['200ml']) {
          var base = f.pricing['50kg']['200ml'];
          var calcFormule = Math.round((base.formule / 200) * currentFormat * 100) / 100;
          priceData = {
            formule: calcFormule,
            remplissage: base.remplissage,
            packaging: base.packaging,
            etiquette: base.etiquette,
            total: Math.round((calcFormule + base.remplissage + base.packaging + base.etiquette) * 100) / 100
          };
        }

        if (priceData) {
          html += '<div class="bulk-format-row__price">\u00c0 partir de <strong>' + B.fmtPrice(priceData.total) + ' HT/unit\u00e9</strong> (tranche 50 kg)</div>';
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
        B.state.formats[fid] = fmt;
        renderFormats();
      });
    });
  }

  function updateTakemotoVisibility() {
    if (!elTakemoto || !el5lNotice) return;

    var selected = B.state.formulas.filter(function (f) { return !!B.state.selectedIds[f.id]; });
    var has5L = false;
    var allHaveFormat = true;

    selected.forEach(function (f) {
      if (!B.state.formats[f.id]) allHaveFormat = false;
      if (B.state.formats[f.id] === 5000) has5L = true;
    });

    el5lNotice.style.display = has5L ? '' : 'none';

    if (allHaveFormat && !has5L && selected.length > 0) {
      elTakemoto.style.display = '';
    } else if (has5L) {
      elTakemoto.style.display = 'none';
      B.state.skipTakemoto = false;
    } else {
      elTakemoto.style.display = 'none';
    }
  }

  /* Takemoto buttons */
  if (elTakemotoYes) {
    elTakemotoYes.addEventListener('click', function () {
      B.state.skipTakemoto = false;
      B.goToStep(3);
    });
  }
  if (elTakemotoNo) {
    elTakemotoNo.addEventListener('click', function () {
      B.state.skipTakemoto = true;
      B.goToStep(4);
    });
  }

  /* ══════════════════════════════════════════════
     REGISTER MODULE
     ══════════════════════════════════════════════ */
  B.modules.formulas = {
    renderFormats: renderFormats,
    applyFilters: applyFilters,
    onDataReady: function () {
      renderGammeFilters();
      renderFormulas();
      updateSelectionBar();
    }
  };

})();
