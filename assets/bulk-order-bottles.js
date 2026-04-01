/**
 * MY.LAB — Configurateur Commande Gros Volumes
 * assets/bulk-order-bottles.js
 *
 * Step 3 — Bottle selection with filters, pagination, image zoom.
 * Depends on: bulk-order-core.js (window.BulkOrder)
 */
(function () {
  'use strict';

  var B = window.BulkOrder;
  if (!B) return;

  /* ══════════════════════════════════════════════
     DOM REFS
     ══════════════════════════════════════════════ */
  var elBottlesTabs       = document.getElementById('bulk-bottles-tabs');
  var elBottlesGrid       = document.getElementById('bulk-bottles-grid');
  var elBottlesEmpty      = document.getElementById('bulk-bottles-empty');
  var elBottlesRecap      = document.getElementById('bulk-bottles-recap-list');
  var elBottlesMatFilter  = document.getElementById('bulk-bottles-filter-material');
  var elBottlesColFilter  = document.getElementById('bulk-bottles-filter-color');
  var elBottlesClosureFilter = document.getElementById('bulk-bottles-filter-closure');
  var elBottlesEcoFilter  = document.getElementById('bulk-bottles-eco-filter');
  var elBottlesSprayFilter = document.getElementById('bulk-bottles-spray-filter');
  var elBottlesMoqFilter  = document.getElementById('bulk-bottles-moq-filter');

  var placeholderUrl = (B.config.placeholderUrl || '/assets/placeholder-bottle.svg');

  /* ══════════════════════════════════════════════
     BOTTLE TABS
     ══════════════════════════════════════════════ */
  function renderBottleTabs() {
    if (!elBottlesTabs) return;
    var formulas = B.getSelectedFormulasWithFormat();
    if (formulas.length === 0) return;

    if (!B.bottleState.activeFormulaId || !B.state.selectedIds[B.bottleState.activeFormulaId]) {
      B.bottleState.activeFormulaId = formulas[0].id;
    }

    var html = '';
    formulas.forEach(function (f) {
      var isActive = f.id === B.bottleState.activeFormulaId;
      var hasBottle = !!B.bottleState.selections[f.id];
      var fmtLabel = B.state.formats[f.id] >= 1000 ? (B.state.formats[f.id] / 1000) + 'L' : B.state.formats[f.id] + 'ml';
      html += '<button type="button" class="bulk-bottles__tab' + (isActive ? ' bulk-bottles__tab--active' : '') + '" data-tab-formula="' + B.esc(f.id) + '">' +
        B.esc(f.name) + ' — ' + fmtLabel +
        (hasBottle ? ' <span class="bulk-bottles__tab-check">✓</span>' : '') +
        '</button>';
    });
    elBottlesTabs.innerHTML = html;

    elBottlesTabs.querySelectorAll('.bulk-bottles__tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        B.bottleState.activeFormulaId = btn.dataset.tabFormula;
        B.bottleState.page = 1;
        B.bottleState.filterSprayOnly = false;
        B.bottleState.filterClosure = 'all';
        if (elBottlesSprayFilter) elBottlesSprayFilter.checked = false;
        renderBottleTabs();
        renderBottleGrid();
      });
    });
  }

  /* ══════════════════════════════════════════════
     BOTTLE GRID
     ══════════════════════════════════════════════ */
  function renderBottleGrid() {
    if (!elBottlesGrid || !B.bottlesData) return;
    var f = B.state.formulas.find(function (x) { return x.id === B.bottleState.activeFormulaId; });
    if (!f) return;

    var format = B.state.formats[f.id];
    var category = f.category;
    var compatClosures = B.CLOSURE_COMPAT[category] || [];

    renderBottleFilterChips(format, compatClosures);

    var html = '';
    var visibleCount = 0;

    /* Standard MY.LAB option first (for <=1000ml) */
    if (format <= 1000) {
      var stdSelected = B.bottleState.selections[f.id] === 'standard';
      html += '<div class="bulk-bottle bulk-bottle--standard' + (stdSelected ? ' bulk-bottle--selected' : '') + '" data-bottle-id="standard">' +
        '<span class="bulk-bottle__badge bulk-bottle__badge--included">Inclus</span>' +
        '<div class="bulk-bottle__img"><img src="https://cdn.shopify.com/s/files/1/0924/1922/7982/files/flacon-rpet-alex-200-ml.webp" alt="Flacon MY.LAB Standard" loading="lazy" class="bulk-bottle__img--loaded"></div>' +
        '<div class="bulk-bottle__name">Packaging MY.LAB Standard</div>' +
        '<div class="bulk-bottle__meta"><span class="bulk-bottle__tag">Bouteille ambrée</span><span class="bulk-bottle__tag">' + (category === 'shampoing' ? 'Bouchon noir' : 'Pompe noire') + '</span></div>' +
        '<div class="bulk-bottle__price bulk-bottle__price--free">Inclus dans le prix</div>' +
        '</div>';
      visibleCount++;
    }

    /* Expected units for MOQ check */
    var qs = B.qtyState[f.id] || { kg: 50, tier: '50kg' };
    var expectedUnits = Math.ceil((qs.kg * 1000) / format);

    /* Sort bottles */
    var filteredBottles = B.bottlesData.bottles.filter(function (b) {
      return b.compatible_formats && b.compatible_formats.includes(format);
    }).sort(function (a, b2) {
      var aCompat = (!a.min_order_qty || expectedUnits >= a.min_order_qty) ? 0 : 1;
      var bCompat = (!b2.min_order_qty || expectedUnits >= b2.min_order_qty) ? 0 : 1;
      if (aCompat !== bCompat) return aCompat - bCompat;
      var aPrice = a.price_estimate || 99999;
      var bPrice = b2.price_estimate || 99999;
      return aPrice - bPrice;
    });

    /* Filter by product type + material + color + closure + eco + moq */
    var productFilter = category === 'creme_coiffage' ? 'creme' : category;
    if (category === 'spray') productFilter = 'shampoing-spray';
    var visibleBottles = [];
    filteredBottles.forEach(function (b) {
      var prods = b.compatible_products || [];

      var prodMatch = false;
      if (category === 'spray') {
        prodMatch = prods.indexOf('spray') !== -1;
      } else if (category === 'shampoing') {
        prodMatch = prods.indexOf('shampoing') !== -1;
      } else {
        prodMatch = prods.indexOf(productFilter) !== -1;
      }
      if (!prodMatch) return;

      var matMatch = B.bottleState.filterMaterial === 'all' || b.material === B.bottleState.filterMaterial;
      var colMatch = B.bottleState.filterColor === 'all' || b.color === B.bottleState.filterColor;
      var closureMatch = B.bottleState.filterClosure === 'all' || b.closure_type === B.bottleState.filterClosure;
      var ecoMatch = !B.bottleState.filterEco || b.eco_label;
      var moqCompat = !b.min_order_qty || expectedUnits >= b.min_order_qty;
      var visible = matMatch && colMatch && closureMatch && ecoMatch;
      if (B.bottleState.filterMoqCompat && !moqCompat) visible = false;
      if (visible) visibleBottles.push({ bottle: b, moqCompat: moqCompat });
    });

    /* Pagination */
    var totalPages = Math.max(1, Math.ceil(visibleBottles.length / B.BOTTLES_PER_PAGE));
    if (B.bottleState.page > totalPages) B.bottleState.page = totalPages;
    var startIdx = (B.bottleState.page - 1) * B.BOTTLES_PER_PAGE;
    var pageBottles = visibleBottles.slice(startIdx, startIdx + B.BOTTLES_PER_PAGE);

    /* Render page */
    pageBottles.forEach(function (entry) {
      var b = entry.bottle;
      var moqCompat = entry.moqCompat;
      var isSelected = B.bottleState.selections[f.id] === b.id;

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
        priceHtml = '<div class="bulk-bottle__price" tabindex="0">À partir de ' + B.fmtPrice(lowestTier.price) + '/u' +
          '<span class="bulk-bottle__tiers-tooltip">';
        b.price_tiers.forEach(function (t) {
          priceHtml += '<span>' + t.min_qty + (t.max_qty ? '–' + t.max_qty : '+') + ' u → ' + B.fmtPrice(t.price) + '</span>';
        });
        priceHtml += '</span></div>';
      } else if (b.price_estimate) {
        priceHtml = '<div class="bulk-bottle__price">' + B.fmtPrice(b.price_estimate / 100) + ' HT/unité</div>';
      } else {
        priceHtml = '<div class="bulk-bottle__price" style="color:#888;font-style:italic;">Prix sur demande</div>';
      }

      var moqHtml = '';
      if (b.min_order_qty) {
        var setTotal = b.price_estimate ? (b.price_estimate / 100) * b.min_order_qty : 0;
        moqHtml = '<div class="bulk-bottle__moq">Minimum : ' + b.min_order_qty + ' unités (1 set)' +
          (setTotal > 0 ? '<br>Set complet : ' + B.fmtPrice(setTotal) : '') + '</div>';
      }

      var linkHtml = b.takemoto_url
        ? '<a href="' + B.esc(b.takemoto_url) + '" target="_blank" rel="noopener" class="bulk-bottle__link" onclick="event.stopPropagation()">Voir sur Takemoto <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 17L17 7M17 7H7M17 7v10"/></svg></a>'
        : '';

      html += '<div class="bulk-bottle' + (isSelected ? ' bulk-bottle--selected' : '') + '" data-bottle-id="' + B.esc(b.id) + '" data-material="' + B.esc(b.material) + '" data-color="' + B.esc(b.color) + '" data-eco="' + b.eco_label + '">' +
        badges +
        '<div class="bulk-bottle__img" data-zoom-images="' + B.esc(JSON.stringify(b.images_all || [b.image_url_600 || b.image_url_external || ''])) + '">' +
          (b.image_url_600 ? '<img src="' + B.esc(b.image_url_600) + '" alt="' + B.esc(b.name) + '" loading="lazy" class="bulk-bottle__img--loading" onload="this.classList.remove(\'bulk-bottle__img--loading\');this.classList.add(\'bulk-bottle__img--loaded\')" onerror="this.src=\'' + placeholderUrl + '\'">' :
           b.image_url_external ? '<img src="' + B.esc(b.image_url_external) + '" alt="' + B.esc(b.name) + '" loading="lazy" class="bulk-bottle__img--loading" onload="this.classList.remove(\'bulk-bottle__img--loading\');this.classList.add(\'bulk-bottle__img--loaded\')" onerror="this.src=\'' + placeholderUrl + '\'">' :
           '<img src="' + placeholderUrl + '" alt="Placeholder" class="bulk-bottle__img--loaded">') +
        '</div>' +
        '<div class="bulk-bottle__body">' +
        '<div class="bulk-bottle__name">' + B.esc(b.name) + '</div>' +
        '<div class="bulk-bottle__meta">' +
          '<span class="bulk-bottle__tag">' + (B.MATERIAL_LABELS[b.material] || b.material) + '</span>' +
          '<span class="bulk-bottle__tag">' + (B.CLOSURE_LABELS[b.closure_type] || b.closure_type) + '</span>' +
          '<span class="bulk-bottle__tag">' + (B.COLOR_LABELS[b.color] || b.color) + '</span>' +
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
        '<button type="button" class="bulk-bottles__page-btn" data-page-dir="prev"' + (B.bottleState.page <= 1 ? ' disabled' : '') + '>' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg> Précédent</button>' +
        '<span class="bulk-bottles__page-info">Page ' + B.bottleState.page + ' sur ' + totalPages + '</span>' +
        '<button type="button" class="bulk-bottles__page-btn" data-page-dir="next"' + (B.bottleState.page >= totalPages ? ' disabled' : '') + '>' +
        'Suivant <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></button>' +
        '</div>';
    }

    elBottlesGrid.innerHTML = html;
    elBottlesEmpty.style.display = visibleBottles.length === 0 ? '' : 'none';

    /* Bind pagination */
    elBottlesGrid.querySelectorAll('.bulk-bottles__page-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (btn.dataset.pageDir === 'prev' && B.bottleState.page > 1) B.bottleState.page--;
        if (btn.dataset.pageDir === 'next' && B.bottleState.page < totalPages) B.bottleState.page++;
        renderBottleGrid();
        var gridTop = elBottlesGrid.getBoundingClientRect().top + window.scrollY - 100;
        window.scrollTo({ top: gridTop, behavior: 'smooth' });
      });
    });

    /* Bind card click */
    elBottlesGrid.querySelectorAll('.bulk-bottle').forEach(function (card) {
      card.addEventListener('click', function () {
        var bid = card.dataset.bottleId;
        B.bottleState.selections[B.bottleState.activeFormulaId] = bid;
        renderBottleGrid();
        renderBottleTabs();
        renderBottleRecap();
      });
    });

    renderBottleRecap();
  }

  /* ══════════════════════════════════════════════
     FILTER CHIPS
     ══════════════════════════════════════════════ */
  function renderBottleFilterChips(format, compatClosures) {
    if (!B.bottlesData || !elBottlesMatFilter || !elBottlesColFilter) return;

    var activeF = B.state.formulas.find(function (x) { return x.id === B.bottleState.activeFormulaId; });
    var activeCategory = activeF ? activeF.category : '';
    var productFilter = activeCategory === 'creme_coiffage' ? 'creme' : activeCategory;

    var materials = {};
    var colors = {};
    var closures = {};
    B.bottlesData.bottles.forEach(function (b) {
      if (!b.compatible_formats || !b.compatible_formats.includes(format)) return;
      var prods = b.compatible_products || [];
      var prodOk = prods.indexOf(productFilter) !== -1 || (productFilter === 'shampoing' && prods.indexOf('shampoing-spray') !== -1);
      if (!prodOk) return;
      materials[b.material] = true;
      colors[b.color] = true;
      if (b.closure_type) closures[b.closure_type] = true;
    });

    /* Spray toggle */
    var sprayToggleEl = document.getElementById('bulk-bottles-spray-toggle');
    if (sprayToggleEl) {
      if (activeCategory === 'spray') {
        sprayToggleEl.style.display = '';
      } else {
        sprayToggleEl.style.display = 'none';
        B.bottleState.filterSprayOnly = false;
      }
    }

    var matHtml = '<button type="button" class="bulk-chip' + (B.bottleState.filterMaterial === 'all' ? ' bulk-chip--active' : '') + '" data-filter-material="all">Tous</button>';
    Object.keys(materials).forEach(function (m) {
      matHtml += '<button type="button" class="bulk-chip' + (B.bottleState.filterMaterial === m ? ' bulk-chip--active' : '') + '" data-filter-material="' + m + '">' + (B.MATERIAL_LABELS[m] || m) + '</button>';
    });
    elBottlesMatFilter.innerHTML = matHtml;

    var colHtml = '<button type="button" class="bulk-chip' + (B.bottleState.filterColor === 'all' ? ' bulk-chip--active' : '') + '" data-filter-color="all">Toutes</button>';
    B.COLOR_ORDER.forEach(function (c) {
      if (!colors[c]) return;
      var dot = B.COLOR_DOTS[c] || '#ccc';
      var border = c === 'clear' || c === 'white' ? 'border:1px solid #ccc;' : '';
      colHtml += '<button type="button" class="bulk-chip' + (B.bottleState.filterColor === c ? ' bulk-chip--active' : '') + '" data-filter-color="' + c + '">' +
        '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:' + dot + ';' + border + 'margin-right:6px;vertical-align:middle;"></span>' +
        (B.COLOR_LABELS[c] || c) + '</button>';
    });
    elBottlesColFilter.innerHTML = colHtml;

    /* Closure filter chips */
    if (elBottlesClosureFilter) {
      var closureHtml = '<button type="button" class="bulk-chip' + (B.bottleState.filterClosure === 'all' ? ' bulk-chip--active' : '') + '" data-filter-closure="all">Toutes</button>';
      B.CLOSURE_ORDER.forEach(function (ct) {
        if (!closures[ct]) return;
        closureHtml += '<button type="button" class="bulk-chip' + (B.bottleState.filterClosure === ct ? ' bulk-chip--active' : '') + '" data-filter-closure="' + ct + '">' +
          (B.CLOSURE_FILTER_LABELS[ct] || ct) + '</button>';
      });
      Object.keys(closures).forEach(function (ct) {
        if (B.CLOSURE_ORDER.indexOf(ct) === -1) {
          closureHtml += '<button type="button" class="bulk-chip' + (B.bottleState.filterClosure === ct ? ' bulk-chip--active' : '') + '" data-filter-closure="' + ct + '">' +
            (B.CLOSURE_FILTER_LABELS[ct] || '\uD83D\uDCE6 ' + ct) + '</button>';
        }
      });
      elBottlesClosureFilter.innerHTML = closureHtml;
    }

    /* Bind filter events */
    B.bindFilterEvents(elBottlesMatFilter, 'data-filter-material', function (val) {
      B.bottleState.filterMaterial = val;
      B.bottleState.page = 1;
      renderBottleGrid();
    });
    B.bindFilterEvents(elBottlesColFilter, 'data-filter-color', function (val) {
      B.bottleState.filterColor = val;
      B.bottleState.page = 1;
      renderBottleGrid();
    });
    if (elBottlesClosureFilter) {
      B.bindFilterEvents(elBottlesClosureFilter, 'data-filter-closure', function (val) {
        B.bottleState.filterClosure = val;
        B.bottleState.page = 1;
        renderBottleGrid();
      });
    }
  }

  /* ══════════════════════════════════════════════
     BOTTLE RECAP
     ══════════════════════════════════════════════ */
  function renderBottleRecap() {
    if (!elBottlesRecap) return;
    var formulas = B.getSelectedFormulasWithFormat();
    var html = '';
    formulas.forEach(function (f) {
      var bid = B.bottleState.selections[f.id];
      var bottleName = '';
      if (bid === 'standard') {
        bottleName = 'MY.LAB Standard';
      } else if (bid && B.bottlesData) {
        var b = B.bottlesData.bottles.find(function (x) { return x.id === bid; });
        if (b) bottleName = b.name;
      }
      var icon = bid
        ? '<svg class="bulk-bottles__recap-check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2d7a45" stroke-width="2.5"><path d="M5 12l5 5L19 7"/></svg>'
        : '<svg class="bulk-bottles__recap-pending" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="2"><circle cx="12" cy="12" r="8"/></svg>';
      var fmtLabel = B.state.formats[f.id] >= 1000 ? (B.state.formats[f.id] / 1000) + 'L' : B.state.formats[f.id] + 'ml';
      html += '<div class="bulk-bottles__recap-item">' + icon +
        '<div><span class="bulk-bottles__recap-formula">' + B.esc(f.name) + ' — ' + fmtLabel + '</span>' +
        (bottleName ? '<br><span class="bulk-bottles__recap-bottle">' + B.esc(bottleName) + '</span>' : '<br><span class="bulk-bottles__recap-bottle" style="color:#c0392b;">À choisir</span>') +
        '</div></div>';
    });
    elBottlesRecap.innerHTML = html;
  }

  /* ══════════════════════════════════════════════
     FILTER EVENT BINDINGS
     ══════════════════════════════════════════════ */
  if (elBottlesSprayFilter) {
    elBottlesSprayFilter.addEventListener('change', function () {
      B.bottleState.filterSprayOnly = elBottlesSprayFilter.checked;
      B.bottleState.page = 1;
      renderBottleGrid();
    });
  }

  if (elBottlesEcoFilter) {
    elBottlesEcoFilter.addEventListener('change', function () {
      B.bottleState.filterEco = elBottlesEcoFilter.checked;
      B.bottleState.page = 1;
      renderBottleGrid();
    });
  }

  if (elBottlesMoqFilter) {
    elBottlesMoqFilter.addEventListener('change', function () {
      B.bottleState.filterMoqCompat = elBottlesMoqFilter.checked;
      B.bottleState.page = 1;
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
     REGISTER MODULE
     ══════════════════════════════════════════════ */
  B.modules.bottles = {
    renderBottleTabs: renderBottleTabs,
    renderBottleGrid: renderBottleGrid
  };

})();
