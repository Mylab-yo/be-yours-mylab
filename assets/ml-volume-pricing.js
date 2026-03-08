'use strict';

/**
 * ML Volume Pricing — Tarifs dégressifs MyLab
 * Génère dynamiquement le tableau de prix dégressifs sur les pages produit.
 *
 * Les prix sont en centimes HT.
 * Le type de produit et le format sont détectés via les tags Shopify du produit.
 */

(function () {
  /* -------------------------------------------------------
     GRILLES TARIFAIRES (centimes HT, prix unitaire)
     ------------------------------------------------------- */
  const TIERS = {
    /* ---- SHAMPOINGS ---- */
    shampoing_200: [
      { qty: 6, price: 700 },
      { qty: 12, price: 665 },
      { qty: 24, price: 630 },
      { qty: 48, price: 560 },
      { qty: 96, price: 500 }
    ],
    shampoing_500: [
      { qty: 6, price: 1490 },
      { qty: 12, price: 1340 },
      { qty: 24, price: 1265 },
      { qty: 48, price: 1190 },
      { qty: 96, price: 1065 }
    ],
    shampoing_1000: [
      { qty: 1, price: 2490 },
      { qty: 3, price: 2365 },
      { qty: 6, price: 2100 },
      { qty: 12, price: 1865 }
    ],

    /* ---- MASQUES ---- */
    masque_200: [
      { qty: 6, price: 950 },
      { qty: 12, price: 900 },
      { qty: 24, price: 855 },
      { qty: 48, price: 760 },
      { qty: 96, price: 680 }
    ],
    masque_400: [
      { qty: 6, price: 1690 },
      { qty: 12, price: 1590 },
      { qty: 24, price: 1520 },
      { qty: 48, price: 1350 },
      { qty: 96, price: 1210 }
    ],
    masque_1000: [
      { qty: 1, price: 3290 },
      { qty: 3, price: 3125 },
      { qty: 6, price: 2790 },
      { qty: 12, price: 2465 }
    ],

    /* ---- CRÈMES SANS RINÇAGE ---- */
    creme_200: [
      { qty: 6, price: 850 },
      { qty: 12, price: 805 },
      { qty: 24, price: 765 },
      { qty: 48, price: 680 },
      { qty: 96, price: 610 }
    ],
    creme_400: [
      { qty: 6, price: 1690 },
      { qty: 12, price: 1590 },
      { qty: 24, price: 1520 },
      { qty: 48, price: 1350 },
      { qty: 96, price: 1210 }
    ],
    creme_1000: [
      { qty: 1, price: 3290 },
      { qty: 3, price: 3125 },
      { qty: 6, price: 2790 },
      { qty: 12, price: 2465 }
    ],

    /* ---- DÉJAUNISSEUR / COLORISTEUR (tarif spécial) ---- */
    dejaunisseur_shampoing_200: [
      { qty: 6, price: 750 },
      { qty: 12, price: 710 },
      { qty: 24, price: 675 },
      { qty: 48, price: 600 },
      { qty: 96, price: 540 }
    ],
    dejaunisseur_masque_200: [
      { qty: 6, price: 960 },
      { qty: 12, price: 910 },
      { qty: 24, price: 860 },
      { qty: 48, price: 765 },
      { qty: 96, price: 690 }
    ],
    dejaunisseur_shampoing_1000: [
      { qty: 1, price: 2890 },
      { qty: 3, price: 2745 },
      { qty: 6, price: 2450 },
      { qty: 12, price: 2160 }
    ],
    dejaunisseur_masque_1000: [
      { qty: 1, price: 3490 },
      { qty: 3, price: 3315 },
      { qty: 6, price: 2965 },
      { qty: 12, price: 2615 }
    ],

    /* ---- MASQUE RÉPARATEUR SPRAY ---- */
    spray_reparateur_200: [
      { qty: 6, price: 990 },
      { qty: 12, price: 940 },
      { qty: 24, price: 890 },
      { qty: 48, price: 790 },
      { qty: 96, price: 710 }
    ],

    /* ---- FINITION : SÉRUM 50ml ---- */
    serum_50: [
      { qty: 6, price: 850 },
      { qty: 12, price: 805 },
      { qty: 24, price: 765 },
      { qty: 48, price: 680 },
      { qty: 96, price: 610 }
    ],

    /* ---- FINITION : HUILE 50ml ---- */
    huile_50: [
      { qty: 6, price: 950 },
      { qty: 12, price: 900 },
      { qty: 24, price: 850 },
      { qty: 48, price: 760 },
      { qty: 96, price: 680 }
    ],

    /* ---- CIRES 50ml ---- */
    cire_50: [
      { qty: 6, price: 690 },
      { qty: 12, price: 660 },
      { qty: 24, price: 630 },
      { qty: 48, price: 600 }
    ],

    /* ---- HOMME : MASQUE INTENSE 500ml (tarif spécial) ---- */
    homme_masque_500: [
      { qty: 6, price: 1990 },
      { qty: 12, price: 1790 },
      { qty: 24, price: 1690 },
      { qty: 48, price: 1590 },
      { qty: 96, price: 1430 }
    ]
  };

  /* -------------------------------------------------------
     DÉTECTION DU TYPE DE GRILLE
     Utilise les tags Shopify réels du produit.
     Tags utilisés sur mylab-shop-3 :
       Type : "shampoing", "masque", "creme", "serum", "huile", "cire"
       Format : "200ml", "400ml", "500ml", "1000ml", "50ml"
       Gamme : "Les Nourrissants", "dejaunisseur", "coloristeur", etc.
       Spécial : "homme", "spray", "herborist"
     ------------------------------------------------------- */
  function detectTierKey(productData) {
    var tags = (productData.tags || []).map(function (t) { return t.toLowerCase().trim(); });
    var title = (productData.title || '').toLowerCase();
    var allTags = tags.join(' ');

    // --- Détecter le FORMAT depuis les tags puis le titre ---
    var format = '';
    tags.forEach(function (tag) {
      if (tag === '1000ml' || tag === '1l') format = '1000';
      else if (tag === '500ml' && !format) format = '500';
      else if (tag === '400ml' && !format) format = '400';
      else if (tag === '200ml' && !format) format = '200';
      else if (tag === '50ml' && !format) format = '50';
    });
    if (!format) {
      if (title.includes('1000') || title.includes('1l')) format = '1000';
      else if (title.includes('500')) format = '500';
      else if (title.includes('400')) format = '400';
      else if (title.includes('200')) format = '200';
      else if (title.includes('50ml')) format = '50';
    }

    // --- Détecter le TYPE depuis les tags puis le titre ---
    var type = '';
    if (allTags.includes('shampoing') || title.includes('shampoing') || title.includes('shampooing')) {
      type = 'shampoing';
    } else if ((allTags.includes('spray') || title.includes('spray')) && (allTags.includes('masque') || title.includes('masque'))) {
      type = 'spray_reparateur';
    } else if (allTags.includes('masque') || title.includes('masque')) {
      type = 'masque';
    } else if (allTags.includes('creme') || allTags.includes('crème') || title.includes('crème') || title.includes('creme')) {
      type = 'creme';
    } else if (allTags.includes('serum') || allTags.includes('sérum') || title.includes('sérum') || title.includes('serum')) {
      type = 'serum';
    } else if (allTags.includes('huile') || title.includes('huile') || title.includes('bain miraculeux')) {
      type = 'huile';
    } else if (allTags.includes('cire') || title.includes('cire')) {
      type = 'cire';
    }

    // --- Détecter la GAMME spéciale ---
    var gamme = '';
    if (allTags.includes('dejauniss') || allTags.includes('colorist') || title.includes('déjauniss') || title.includes('dejauniss') || title.includes('colorist')) {
      gamme = 'dejaunisseur';
    } else if (allTags.includes('homme') || allTags.includes('herborist') || title.includes('herborist')) {
      gamme = 'homme';
    }

    // --- Construire la clé et matcher ---
    if (gamme === 'dejaunisseur') {
      var key = 'dejaunisseur_' + type + '_' + format;
      if (TIERS[key]) return key;
    }

    if (gamme === 'homme') {
      var key2 = 'homme_' + type + '_' + format;
      if (TIERS[key2]) return key2;
    }

    if (type === 'spray_reparateur') {
      return 'spray_reparateur_200';
    }

    var baseKey = type + '_' + format;
    if (TIERS[baseKey]) return baseKey;

    // Dernier fallback : essayer sans format pour les 50ml
    if (!format && (type === 'serum' || type === 'huile' || type === 'cire')) {
      var key3 = type + '_50';
      if (TIERS[key3]) return key3;
    }

    return null;
  }

  /* -------------------------------------------------------
     RENDU DU TABLEAU
     ------------------------------------------------------- */
  function formatPrice(centimes) {
    return (centimes / 100).toFixed(2).replace('.', ',') + ' €';
  }

  function renderTable(container, tiers, tierKey) {
    if (!tiers || tiers.length === 0) {
      container.style.display = 'none';
      return;
    }

    var basePrice = tiers[0].price;
    var bestPrice = tiers[tiers.length - 1].price;

    var html = '<div class="ml-volume-heading">Tarifs dégressifs HT</div>';
    html += '<table class="ml-volume-table">';
    html += '<thead><tr><th>Quantité</th><th>Prix unitaire HT</th><th>Économie</th></tr></thead>';
    html += '<tbody>';

    tiers.forEach(function (tier, i) {
      var savings = Math.round((1 - tier.price / basePrice) * 100);
      var savingsHtml = '';
      if (savings > 0) {
        savingsHtml = '<span class="ml-savings">-' + savings + '%</span>';
      }

      var priceHtml = formatPrice(tier.price);
      if (i === tiers.length - 1) {
        priceHtml = '<span class="ml-price-best">' + formatPrice(tier.price) + '</span>';
      }

      var qtyLabel = tier.qty === 1 ? 'À l\'unité' : 'x' + tier.qty;

      html += '<tr>';
      html += '<td>' + qtyLabel + '</td>';
      html += '<td>' + priceHtml + '</td>';
      html += '<td>' + savingsHtml + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table>';
    html += '<p class="ml-volume-note">Prix HT par unité · Minimum de commande : ' + tiers[0].qty + ' unités</p>';

    container.innerHTML = html;
  }

  /* -------------------------------------------------------
     INIT
     ------------------------------------------------------- */
  function init() {
    var containers = document.querySelectorAll('[data-ml-volume-pricing]');
    if (!containers.length) return;

    var handle = window.location.pathname.split('/products/')[1];
    if (!handle) return;
    handle = handle.split('?')[0].split('#')[0];

    fetch('/products/' + handle + '.js')
      .then(function (r) { return r.json(); })
      .then(function (product) {
        var tierKey = detectTierKey(product);
        containers.forEach(function (container) {
          if (tierKey && TIERS[tierKey]) {
            renderTable(container, TIERS[tierKey], tierKey);
          } else {
            container.style.display = 'none';
          }
        });
      })
      .catch(function () {
        containers.forEach(function (c) { c.style.display = 'none'; });
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
