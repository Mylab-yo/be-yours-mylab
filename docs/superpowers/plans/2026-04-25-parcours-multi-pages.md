# Parcours « Créons ensemble votre marque » — Multi-pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre la page monolithique `/pages/creons-ensemble-votre-marque` (1950 lignes dans `ml-cem-parcours.liquid`) en un parcours multi-pages aéré et ludique, avec 1 page par étape, validation par étape via add-to-cart immédiat, stepper partagé, et récap drawer dépliable.

**Architecture:** 5 pages Shopify natives (landing + 4 étapes), état partagé via cart Shopify (source de vérité), stepper + récap drawer en snippet partagé inclus globalement par `theme.liquid` avec gating sur path. JS vanilla IIFE dans `assets/ml-parcours.js` (pattern MyLab existant). DA strictement alignée sur la home : DM Sans + DM Mono uniquement, palette monochrome cream `#f5f0eb` / ink `#1a1a1a` / blanc — zéro or, zéro brick, zéro italique.

**Tech Stack:** Shopify Liquid · HTML/CSS vanilla · JS vanilla IIFE · Shopify CLI pour push. Pas de bundler, pas de test runner — vérification via `shopify theme push --development --nodelete` + smoke test manuel browser.

**Spec source:** `docs/superpowers/specs/2026-04-25-parcours-multi-pages-design.md`
**Prototype visuel de référence:** `docs/superpowers/prototypes/parcours-multi-pages.html`

---

## Conventions du projet

- Tous les nouveaux assets MyLab préfixés `ml-`
- JS en IIFE avec `'use strict'`, pas d'ES modules
- Classes CSS en BEM-like avec préfixe `ml-parcours__`
- Push toujours `--development --nodelete` sauf instruction explicite « push live »
- Pas de mock du cart Shopify — toujours fetch `/cart.js` réel
- Commit après chaque task validée

## File Structure

| Fichier | Rôle | Action |
| --- | --- | --- |
| `assets/ml-parcours.css` | Styles partagés des 5 pages parcours (topbar, stepper, drawer, sections content, mobile bottom CTA) | Créer |
| `assets/ml-parcours.js` | State global (lecture cart), sync stepper, drawer toggle, auto-add dossier, sortie parcours | Créer |
| `snippets/ml-parcours-shell.liquid` | Topbar parcours + stepper + récap drawer + mobile bottom CTA. Inclus conditionnellement par `theme.liquid` | Créer |
| `layout/theme.liquid` | Ajouter render conditionnel du shell + classe `body.is-parcours` | Modifier |
| `assets/ml-forfait-gate.js` | Étendre regex de détection path pour les 5 nouveaux paths du parcours | Modifier |
| `sections/ml-parcours-landing.liquid` | Hero + 4 cards preview étapes + CTA « Démarrer mon projet » | Créer |
| `templates/page.creons-ensemble-votre-marque.json` | Bascule landing existante sur la nouvelle section | Modifier |
| `sections/ml-parcours-dossier.liquid` | Étape 01 — 3 piliers DIP/CPNP/Tests + accordéon 8 docs | Créer |
| `templates/page.parcours-dossier.json` | Template étape dossier | Créer |
| `sections/ml-parcours-etiquette.liquid` | Étape 02 — 3 cards étiquette + bloc forfait + iframe modale configurateur Vercel | Créer |
| `templates/page.parcours-etiquette.json` | Template étape étiquette | Créer |
| `sections/ml-parcours-produits.liquid` | Étape 03 — tabs catégories + grid produits + paliers | Créer |
| `templates/page.parcours-produits.json` | Template étape produits | Créer |
| `sections/ml-parcours-recap.liquid` | Étape 04 — timeline + table récap + CTA « Valider notre projet » | Créer |
| `templates/page.parcours-recap.json` | Template étape récap | Créer |
| `sections/ml-cem-parcours.liquid` | Ancien monolithe — laissé en place pour rollback, ne pas supprimer | Conserver |

---

## Task 1 — Foundation CSS partagé

**Files:**

- Create: `assets/ml-parcours.css`

- [ ] **Step 1: Créer `assets/ml-parcours.css` avec les variables et la base.** Source de vérité = bloc `<style>` du prototype `docs/superpowers/prototypes/parcours-multi-pages.html`. Copier le bloc CSS entier dans le fichier asset. Modifier les sélecteurs racine pour qu'ils se scopent sous `.is-parcours` ou `.ml-parcours` afin d'éviter les fuites sur les autres pages du theme.

```css
/* En tête du fichier */
:root {
  --mlp-cream: #f5f0eb;
  --mlp-cream-2: #ede6dd;
  --mlp-cream-3: #e0d6c8;
  --mlp-ink: #1a1a1a;
  --mlp-ink-soft: #333333;
  --mlp-muted: #6b665e;
  --mlp-line: rgba(26,26,26,.10);
  --mlp-line-soft: rgba(26,26,26,.06);
  --mlp-line-strong: rgba(26,26,26,.20);
  --mlp-shadow-sm: 0 1px 0 rgba(26,26,26,.04);
  --mlp-shadow-md: 0 12px 40px -16px rgba(26,26,26,.18);
  --mlp-shadow-lg: 0 30px 80px -30px rgba(26,26,26,.25);
  --mlp-radius: 14px;
  --mlp-radius-lg: 24px;
  --mlp-ease: cubic-bezier(.22,1,.36,1);
}

/* Scope global */
body.is-parcours {
  background: var(--mlp-cream);
  color: var(--mlp-ink);
  font-family: 'DM Sans', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
```

Pour le reste : porter intégralement les règles du prototype en remplaçant chaque variable `--cream`, `--ink`, etc. par leur équivalent préfixé `--mlp-*` ; remplacer les classes `.topbar`, `.stepper`, `.recap`, `.page`, `.btn`, `.pillars`, `.label-cards`, `.product-tabs`, `.product-card`, `.recap-final`, `.timeline`, `.toast`, `.mobile-cta`, `.accordion`, `.forfait` par leur préfixe BEM `.ml-parcours__topbar`, `.ml-parcours__stepper`, etc. Le mapping complet est :

| Prototype class | Asset class |
| --- | --- |
| `.topbar` | `.ml-parcours__topbar` |
| `.brand` | `.ml-parcours__brand` |
| `.stepper` | `.ml-parcours__stepper` |
| `.step` | `.ml-parcours__step` |
| `.step__num` | `.ml-parcours__step-num` |
| `.step__line` | `.ml-parcours__step-line` |
| `.step__label` `.step__kicker` `.step__name` | idem préfixées |
| `.recap` | `.ml-parcours__recap` |
| `.page` | `.ml-parcours__page` |
| `.btn` `.btn--primary` `.btn--ghost` `.btn--ink` `.btn--big` | `.ml-parcours__btn` `--primary` etc. |
| `.pillars` `.pillar` | `.ml-parcours__pillars` `.ml-parcours__pillar` |
| `.accordion` `.accordion__item` `.accordion__header` `.accordion__body` | idem préfixées |
| `.label-cards` `.label-card` `.label-card--featured` | `.ml-parcours__label-cards` etc. |
| `.forfait` | `.ml-parcours__forfait` |
| `.product-tabs` `.product-tab` `.product-grid` `.product-card` `.tier` | `.ml-parcours__product-*` `.ml-parcours__tier` |
| `.recap-final` `.timeline` `.timeline-item` `.recap-row` `.recap-total` | `.ml-parcours__recap-final` etc. |
| `.toast` `.mobile-cta` | `.ml-parcours__toast` `.ml-parcours__mobile-cta` |
| `.page-kicker` `.eyebrow` `.lede` `.section-title` | `.ml-parcours__kicker` `.ml-parcours__eyebrow` `.ml-parcours__lede` `.ml-parcours__section-title` |
| `.container` `.container--narrow` | `.ml-parcours__container` `--narrow` |

Les classes media-query mobile (`@media (max-width:880px)`) restent intactes.

- [ ] **Step 2: Vérifier le fichier en local.** Ouvrir `assets/ml-parcours.css` et confirmer qu'il commence par les variables `--mlp-*`, qu'il n'y a aucune référence `var(--gold)` ou `var(--brick)`, et qu'aucune classe sans préfixe `ml-parcours` ne reste (sauf media queries et `:root`/`body`).

Run dans le terminal :

```bash
grep -E "var\(--gold|var\(--brick|c5a467|b85c4e" assets/ml-parcours.css
```

Expected: aucune sortie.

```bash
grep -cE "^\.ml-parcours" assets/ml-parcours.css
```

Expected: nombre > 30 (toutes les classes préfixées sont présentes).

- [ ] **Step 3: Commit.**

```bash
git add assets/ml-parcours.css
git commit -m "feat(parcours): add ml-parcours.css with shared styles for multi-pages"
```

---

## Task 2 — Foundation JS partagé

**Files:**

- Create: `assets/ml-parcours.js`

- [ ] **Step 1: Créer `assets/ml-parcours.js` avec l'IIFE et la lecture du cart.**

```javascript
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

  function isEtiquette(item) {
    if (!item.product_type) return false;
    // We rely on the collection injected via ml-parcours-shell data attributes
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

  // Sync the recap drawer content
  function syncRecap(state) {
    const root = document.querySelector('[data-ml-parcours-recap]');
    if (!root) return;

    const fmt = cents => (cents / 100).toFixed(2).replace('.', ',') + ' €';
    const lines = [
      { name: 'Dossier cosmétologique', done: state.hasDossier, value: state.hasDossier ? '389,90 €' : '—' },
      { name: 'Étiquette & impression', done: state.hasEtiquette, value: state.hasEtiquette ? '✓' : '—' },
      { name: 'Produits sélectionnés', done: state.hasProduits, value: state.hasProduits ? '✓' : '—' }
    ];
    root.querySelector('[data-ml-recap-lines]').innerHTML = lines.map(l => `
      <div class="ml-parcours__recap-line ${l.done ? 'is-done' : 'is-pending'}">
        <span class="ml-parcours__recap-line-icon">${l.done ? '✓' : '·'}</span>
        <span class="ml-parcours__recap-line-label">${l.name}</span>
        <span class="ml-parcours__recap-line-value">${l.value}</span>
      </div>
    `).join('');

    const totalEl = root.querySelector('[data-ml-recap-total]');
    if (totalEl) totalEl.textContent = fmt(state.total);
  }

  // Toast feedback
  function showToast(msg) {
    let t = document.querySelector('.ml-parcours__toast');
    if (!t) {
      t = document.createElement('div');
      t.className = 'ml-parcours__toast';
      t.innerHTML = '<span class="ml-parcours__toast-icon">✓</span><span class="ml-parcours__toast-message"></span>';
      document.body.appendChild(t);
    }
    t.querySelector('.ml-parcours__toast-message').textContent = msg;
    t.classList.add('is-visible');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('is-visible'), 2400);
  }

  // Recap drawer toggle
  function bindRecapToggle() {
    const btn = document.querySelector('[data-ml-recap-toggle]');
    const drawer = document.querySelector('[data-ml-parcours-recap]');
    if (!btn || !drawer) return;
    btn.addEventListener('click', () => {
      const open = drawer.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      const label = btn.querySelector('[data-ml-recap-toggle-label]');
      if (label) label.textContent = open ? 'Masquer mon projet' : 'Voir mon projet en cours';
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
            await fetch('/cart/add.js', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({
                items: [{ id: window.MylabParcours.dossierVariantId, quantity: 1 }]
              })
            });
          }
          window.location.href = CONFIG.paths.dossier;
        } catch (err) {
          console.error('[ml-parcours] start error', err);
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
        const state = await readState();
        const items = state.cart.items || [];
        const toRemove = items.filter(it =>
          it.handle === CONFIG.handles.dossier ||
          it.handle === CONFIG.handles.forfaitStandard ||
          it.handle === CONFIG.handles.forfaitCouleur ||
          isEtiquette(it)
        );
        for (const it of toRemove) {
          await fetch('/cart/change.js', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ id: it.key, quantity: 0 })
          });
        }
        window.location.href = '/';
      });
    });
  }

  // Init
  async function init() {
    document.body.classList.add('is-parcours');
    const state = await readState();
    syncStepper(state);
    syncRecap(state);
    bindRecapToggle();
    bindStepperNav();
    bindStartCta();
    bindExitParcours();

    // Listen to cart updates
    document.addEventListener('cart:refresh', async () => {
      const s = await readState();
      syncStepper(s);
      syncRecap(s);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Smoke check syntaxe.** Charger le fichier dans node pour vérifier qu'il parse :

```bash
node --check assets/ml-parcours.js
```

Expected: aucune sortie (parse OK).

- [ ] **Step 3: Commit.**

```bash
git add assets/ml-parcours.js
git commit -m "feat(parcours): add ml-parcours.js with cart-based state sync"
```

---

## Task 3 — Snippet shell partagé + render conditionnel

**Files:**

- Create: `snippets/ml-parcours-shell.liquid`
- Modify: `layout/theme.liquid`

- [ ] **Step 1: Créer `snippets/ml-parcours-shell.liquid` avec topbar + stepper + récap drawer + mobile bottom CTA.**

```liquid
{% comment %}
  ml-parcours-shell.liquid — Topbar, stepper, récap drawer, mobile CTA
  Inclus globalement par theme.liquid sur les paths du parcours.
  Hydrate window.MylabParcours avec les handles produits/étiquettes pour le JS.
{% endcomment %}

{% liquid
  assign etiquettes_col = collections['modeles-detiquettes']
  assign produits_col = collections['boutique-adherents']
  assign dossier_product = all_products['creation-du-dossier-cosmetologique']
%}

<style>{{ 'ml-parcours.css' | asset_url | stylesheet_tag }}</style>

<script>
  window.MylabParcours = {
    dossierVariantId: {{ dossier_product.variants.first.id | default: 'null' }},
    etiquetteHandles: [
      {%- for p in etiquettes_col.products -%}
        "{{ p.handle }}"{%- unless forloop.last -%},{%- endunless -%}
      {%- endfor -%}
    ],
    produitHandles: [
      {%- for p in produits_col.products -%}
        "{{ p.handle }}"{%- unless forloop.last -%},{%- endunless -%}
      {%- endfor -%}
    ]
  };
</script>

<header class="ml-parcours__topbar">
  <a href="/" class="ml-parcours__brand">MY<b>.</b>LAB <small>· Création de marque</small></a>
  <div class="ml-parcours__topbar-right">
    <a href="#" class="ml-parcours__topbar-exit" data-ml-exit-parcours>Quitter le parcours</a>
  </div>
</header>

<nav class="ml-parcours__stepper" aria-label="Progression du parcours">
  <div class="ml-parcours__stepper-inner">
    <button type="button" class="ml-parcours__step" data-go="dossier">
      <span class="ml-parcours__step-num">
        <span class="ml-parcours__step-digit">1</span>
        <svg class="ml-parcours__step-check" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
      <span class="ml-parcours__step-label">
        <span class="ml-parcours__step-kicker">Étape 01</span>
        <span class="ml-parcours__step-name">Dossier</span>
      </span>
    </button>
    <span class="ml-parcours__step-line"></span>
    <button type="button" class="ml-parcours__step" data-go="etiquette">
      <span class="ml-parcours__step-num">
        <span class="ml-parcours__step-digit">2</span>
        <svg class="ml-parcours__step-check" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
      <span class="ml-parcours__step-label">
        <span class="ml-parcours__step-kicker">Étape 02</span>
        <span class="ml-parcours__step-name">Étiquette</span>
      </span>
    </button>
    <span class="ml-parcours__step-line"></span>
    <button type="button" class="ml-parcours__step" data-go="produits">
      <span class="ml-parcours__step-num">
        <span class="ml-parcours__step-digit">3</span>
        <svg class="ml-parcours__step-check" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
      <span class="ml-parcours__step-label">
        <span class="ml-parcours__step-kicker">Étape 03</span>
        <span class="ml-parcours__step-name">Produits</span>
      </span>
    </button>
    <span class="ml-parcours__step-line"></span>
    <button type="button" class="ml-parcours__step" data-go="recap">
      <span class="ml-parcours__step-num">
        <span class="ml-parcours__step-digit">4</span>
        <svg class="ml-parcours__step-check" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
      <span class="ml-parcours__step-label">
        <span class="ml-parcours__step-kicker">Étape 04</span>
        <span class="ml-parcours__step-name">Récap</span>
      </span>
    </button>
  </div>
  <div class="ml-parcours__stepper-toggle-wrap">
    <button type="button" class="ml-parcours__stepper-toggle" data-ml-recap-toggle aria-expanded="false" aria-controls="ml-parcours-recap-drawer">
      <span data-ml-recap-toggle-label>Voir mon projet en cours</span>
      <svg width="10" height="6" viewBox="0 0 10 6" fill="none" aria-hidden="true"><path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
  </div>
</nav>

<aside class="ml-parcours__recap" id="ml-parcours-recap-drawer" data-ml-parcours-recap aria-label="Récapitulatif du projet">
  <div class="ml-parcours__recap-inner">
    <div class="ml-parcours__recap-section">
      <div class="ml-parcours__recap-title">État de votre projet</div>
      <div data-ml-recap-lines></div>
    </div>
    <div class="ml-parcours__recap-section ml-parcours__recap-section--total">
      <div class="ml-parcours__recap-title">Total à ce stade</div>
      <div class="ml-parcours__recap-total" data-ml-recap-total>0,00 €</div>
    </div>
    <div class="ml-parcours__recap-quit">
      <a href="#" data-ml-exit-parcours>Abandonner et vider mon projet</a>
    </div>
  </div>
</aside>

<div class="ml-parcours__mobile-cta">
  <div class="ml-parcours__mobile-cta-inner">
    <div class="ml-parcours__mobile-cta-progress">
      <span>{% case template.suffix %}{% when 'dossier' %}Étape 01 / 04{% when 'etiquette' %}Étape 02 / 04{% when 'produits' %}Étape 03 / 04{% when 'recap' %}Étape 04 / 04{% else %}Démarrage{% endcase %}</span>
      <b>{% case template.suffix %}{% when 'dossier' %}Dossier cosmétologique{% when 'etiquette' %}Étiquette & impression{% when 'produits' %}Produits{% when 'recap' %}Récapitulatif{% else %}Bienvenue{% endcase %}</b>
    </div>
    <button type="button" class="ml-parcours__mobile-cta-btn" data-ml-recap-toggle>Voir récap</button>
  </div>
</div>

<script src="{{ 'ml-parcours.js' | asset_url }}" defer></script>
```

- [ ] **Step 2: Modifier `layout/theme.liquid` pour render le shell conditionnellement.** Repérer la ligne juste après `{% sections 'header-group' %}` (ou après le `<body>` si pas de header-group). Ajouter le bloc suivant :

```liquid
{%- comment -%} Parcours multi-pages MY.LAB — render shell sur les paths concernés {%- endcomment -%}
{%- if template == 'page' and page.handle contains 'parcours-' or page.handle == 'creons-ensemble-votre-marque' -%}
  {% render 'ml-parcours-shell' %}
{%- endif -%}
```

**Vérifier en lisant le fichier** que l'inclusion est placée AVANT le `{{ content_for_layout }}` mais APRÈS le `<body>` ouvrant. La présence du shell impose `body.is-parcours` (ajouté par le JS au DOMContentLoaded).

- [ ] **Step 3: Push --development.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only snippets/ml-parcours-shell.liquid --only layout/theme.liquid --only assets/ml-parcours.css --only assets/ml-parcours.js
```

Expected: push success, URL preview affichée.

- [ ] **Step 4: Smoke test browser.** Ouvrir l'URL preview du dev theme à `/pages/creons-ensemble-votre-marque`. Le shell (topbar + stepper + récap drawer fermé) doit apparaître au-dessus du contenu existant (qui sera encore le monolithe `ml-cem-parcours` à ce stade — c'est normal).

Vérifier dans la console DevTools :

```javascript
window.MylabParcours
```

Expected: objet avec `dossierVariantId` (numérique), `etiquetteHandles` (array de handles), `produitHandles` (array de handles).

```javascript
document.body.classList.contains('is-parcours')
```

Expected: `true`.

Cliquer sur « Voir mon projet en cours » : le récap drawer doit se déplier.

- [ ] **Step 5: Commit.**

```bash
git add snippets/ml-parcours-shell.liquid layout/theme.liquid
git commit -m "feat(parcours): add shared shell snippet (topbar + stepper + recap drawer)"
```

---

## Task 4 — Section et template Landing

**Files:**

- Create: `sections/ml-parcours-landing.liquid`
- Modify: `templates/page.creons-ensemble-votre-marque.json`

- [ ] **Step 1: Créer `sections/ml-parcours-landing.liquid`.** Source HTML = bloc `<section class="page is-active" data-page="landing">` du prototype. Le porter en Liquid avec schema. Adapter le CTA pour utiliser `data-ml-start-parcours`.

```liquid
{% comment %} ml-parcours-landing.liquid — Hero + 4 cards preview + CTA {% endcomment %}

<section class="ml-parcours__page is-active">
  <div class="ml-parcours__landing-hero">
    <div class="ml-parcours__landing-hero-inner">
      <div class="ml-parcours__eyebrow">{{ section.settings.eyebrow }}</div>
      <h1 class="ml-parcours__display">{{ section.settings.heading }}</h1>
      <p class="ml-parcours__lede">{{ section.settings.lede }}</p>
      <button type="button" class="ml-parcours__btn ml-parcours__btn--primary ml-parcours__btn--big" data-ml-start-parcours>
        {{ section.settings.cta_label | default: 'Démarrer mon projet' }}
        <svg width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true"><path d="M1 6h14m0 0L10 1m5 5l-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
      <div class="ml-parcours__landing-hero-meta">
        <span><b>4 étapes</b> · validation guidée</span>
        <span><b>Sauvegarde auto</b> · à chaque étape</span>
        <span><b>Pas d'engagement</b> · jusqu'au paiement</span>
      </div>
    </div>
  </div>

  <div class="ml-parcours__landing-steps">
    <div class="ml-parcours__landing-steps-grid">
      {% for block in section.blocks %}
        <div class="ml-parcours__landing-step" {{ block.shopify_attributes }}>
          <div class="ml-parcours__landing-step-num">{{ block.settings.kicker }}</div>
          <div class="ml-parcours__landing-step-title">{{ block.settings.title }}</div>
          <div class="ml-parcours__landing-step-desc">{{ block.settings.desc }}</div>
          {% if block.settings.chip != blank %}
            <span class="ml-parcours__landing-step-chip {% if block.settings.chip_invert %}ml-parcours__landing-step-chip--invert{% endif %}">{{ block.settings.chip }}</span>
          {% endif %}
        </div>
      {% endfor %}
    </div>
  </div>

  <div class="ml-parcours__landing-cta">
    <h2>{{ section.settings.bottom_heading }}</h2>
    <p>{{ section.settings.bottom_text }}</p>
    <button type="button" class="ml-parcours__btn ml-parcours__btn--ink ml-parcours__btn--big" data-ml-start-parcours>
      {{ section.settings.bottom_cta | default: 'Je commence' }}
      <svg width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true"><path d="M1 6h14m0 0L10 1m5 5l-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
  </div>
</section>

{% schema %}
{
  "name": "Parcours · Landing",
  "settings": [
    { "type": "text", "id": "eyebrow", "label": "Eyebrow", "default": "Parcours guidé · 15 minutes" },
    { "type": "richtext", "id": "heading", "label": "Titre principal", "default": "<p>Créons ensemble<br/>votre <em>marque</em>.</p>" },
    { "type": "textarea", "id": "lede", "label": "Sous-titre", "default": "Un parcours en 4 étapes pour assembler votre dossier cosmétologique, choisir vos étiquettes, sélectionner vos produits et lancer votre ligne capillaire en marque blanche." },
    { "type": "text", "id": "cta_label", "label": "CTA principal", "default": "Démarrer mon projet" },
    { "type": "text", "id": "bottom_heading", "label": "Titre bas de page", "default": "Prêt à donner vie à votre ligne ?" },
    { "type": "textarea", "id": "bottom_text", "label": "Texte bas de page", "default": "Vous gardez la main à chaque étape. Rien n'est confirmé tant que vous ne validez pas l'étape 4." },
    { "type": "text", "id": "bottom_cta", "label": "CTA bas de page", "default": "Je commence" }
  ],
  "blocks": [
    {
      "type": "step_card",
      "name": "Card étape",
      "settings": [
        { "type": "text", "id": "kicker", "label": "Kicker", "default": "Étape 01" },
        { "type": "text", "id": "title", "label": "Titre", "default": "Dossier cosmétologique" },
        { "type": "textarea", "id": "desc", "label": "Description", "default": "DIP, CPNP et tests : la base réglementaire, prête à utiliser." },
        { "type": "text", "id": "chip", "label": "Chip (optionnel)", "default": "Inclus d'office" },
        { "type": "checkbox", "id": "chip_invert", "label": "Chip inversée (fond noir)", "default": false }
      ]
    }
  ],
  "max_blocks": 6,
  "presets": [
    {
      "name": "Parcours · Landing",
      "blocks": [
        { "type": "step_card", "settings": { "kicker": "Étape 01", "title": "Dossier cosmétologique", "desc": "DIP, CPNP et tests : la base réglementaire, prête à utiliser.", "chip": "Inclus d'office" } },
        { "type": "step_card", "settings": { "kicker": "Étape 02", "title": "Étiquette & impression", "desc": "Standard, Modèles ou Sur-mesure. Forfait d'impression annuel.", "chip": "3 options" } },
        { "type": "step_card", "settings": { "kicker": "Étape 03", "title": "Produits", "desc": "Shampoings, masques, soins. Quantités flexibles, paliers dégressifs.", "chip": "+50 références", "chip_invert": true } },
        { "type": "step_card", "settings": { "kicker": "Étape 04", "title": "Récap & validation", "desc": "Vue d'ensemble de votre projet, total HT, devis ou paiement.", "chip": "Engagement final" } }
      ]
    }
  ]
}
{% endschema %}
```

- [ ] **Step 2: Sauvegarder l'ancien template `templates/page.creons-ensemble-votre-marque.json` localement avant de le remplacer.**

```bash
cp templates/page.creons-ensemble-votre-marque.json templates/page.creons-ensemble-votre-marque.json.bak
```

- [ ] **Step 3: Remplacer `templates/page.creons-ensemble-votre-marque.json` par un template qui pointe sur la nouvelle section.** Préserver les autres sections du template (faq + cta_final) si présentes — vérifier en lisant le fichier d'abord. Le template final doit ressembler à :

```json
{
  "sections": {
    "parcours_landing": {
      "type": "ml-parcours-landing",
      "blocks": {
        "s1": { "type": "step_card", "settings": { "kicker": "Étape 01", "title": "Dossier cosmétologique", "desc": "DIP, CPNP et tests : la base réglementaire, prête à utiliser.", "chip": "Inclus d'office" } },
        "s2": { "type": "step_card", "settings": { "kicker": "Étape 02", "title": "Étiquette & impression", "desc": "Standard, Modèles ou Sur-mesure. Forfait d'impression annuel.", "chip": "3 options" } },
        "s3": { "type": "step_card", "settings": { "kicker": "Étape 03", "title": "Produits", "desc": "Shampoings, masques, soins. Quantités flexibles, paliers dégressifs.", "chip": "+50 références", "chip_invert": true } },
        "s4": { "type": "step_card", "settings": { "kicker": "Étape 04", "title": "Récap & validation", "desc": "Vue d'ensemble de votre projet, total HT, devis ou paiement.", "chip": "Engagement final" } }
      },
      "block_order": ["s1", "s2", "s3", "s4"]
    }
  },
  "order": ["parcours_landing"]
}
```

- [ ] **Step 4: Push --development.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only sections/ml-parcours-landing.liquid --only templates/page.creons-ensemble-votre-marque.json
```

- [ ] **Step 5: Smoke test.** Ouvrir l'URL dev de `/pages/creons-ensemble-votre-marque`. La nouvelle landing doit s'afficher avec hero, 4 cards, et CTA. Cliquer sur « Démarrer mon projet » : doit ajouter le dossier au cart et rediriger vers `/pages/parcours-dossier` (404 attendu à ce stade — la page n'existe pas encore). Vérifier dans DevTools Network panel que le call `/cart/add.js` a bien eu lieu avec le bon variant.

- [ ] **Step 6: Commit.**

```bash
git add sections/ml-parcours-landing.liquid templates/page.creons-ensemble-votre-marque.json
git commit -m "feat(parcours): landing page hero + 4-steps preview + start CTA"
```

---

## Task 5 — Section et template Dossier (Étape 01)

**Files:**

- Create: `sections/ml-parcours-dossier.liquid`
- Create: `templates/page.parcours-dossier.json`

- [ ] **Step 1: Créer `sections/ml-parcours-dossier.liquid`.** Source HTML = bloc `<section class="page" data-page="dossier">` du prototype. Adapter en Liquid avec schema pour permettre l'édition des piliers + accordéon docs via Theme Editor.

```liquid
{% comment %} ml-parcours-dossier.liquid — Étape 01 — Dossier cosmétologique {% endcomment %}

<section class="ml-parcours__page is-active">
  <div class="ml-parcours__container ml-parcours__container--narrow">
    <div class="ml-parcours__kicker">Étape 01 / 04 — Dossier</div>
    <h1 class="ml-parcours__display">{{ section.settings.heading }}</h1>
    <p class="ml-parcours__lede">{{ section.settings.lede }}</p>

    <div class="ml-parcours__pillars">
      {% for block in section.blocks %}
        {% if block.type == 'pillar' %}
          <div class="ml-parcours__pillar" {{ block.shopify_attributes }}>
            <div class="ml-parcours__pillar-icon">{{ block.settings.icon }}</div>
            <div class="ml-parcours__pillar-title">{{ block.settings.title }}</div>
            <div class="ml-parcours__pillar-desc">{{ block.settings.desc }}</div>
          </div>
        {% endif %}
      {% endfor %}
    </div>

    <div class="ml-parcours__eyebrow">Ce que contient votre dossier</div>
    <h2 class="ml-parcours__section-title">{{ section.settings.docs_heading }}</h2>

    <div class="ml-parcours__accordion">
      {% for block in section.blocks %}
        {% if block.type == 'doc' %}
          <div class="ml-parcours__accordion-item" {{ block.shopify_attributes }}>
            <button type="button" class="ml-parcours__accordion-header">
              <span>{{ block.settings.title }}</span>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            </button>
            <div class="ml-parcours__accordion-body"><div class="ml-parcours__accordion-body-inner">{{ block.settings.body }}</div></div>
          </div>
        {% endif %}
      {% endfor %}
    </div>

    <div class="ml-parcours__page-footer">
      <a href="/pages/creons-ensemble-votre-marque" class="ml-parcours__page-footer-back">
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M13 5H1m0 0l4-4M1 5l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Retour à l'accueil
      </a>
      <a href="/pages/parcours-etiquette" class="ml-parcours__btn ml-parcours__btn--primary">
        J'ai compris, étape suivante
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M1 5h12m0 0L9 1m4 4L9 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </a>
    </div>
  </div>
</section>

<script>
(function(){
  document.querySelectorAll('.ml-parcours__accordion-item').forEach(item => {
    item.querySelector('.ml-parcours__accordion-header').addEventListener('click', () => {
      item.classList.toggle('is-open');
    });
  });
})();
</script>

{% schema %}
{
  "name": "Parcours · Dossier",
  "settings": [
    { "type": "richtext", "id": "heading", "label": "Titre", "default": "<p>Le socle de votre <em>marque</em>.</p>" },
    { "type": "textarea", "id": "lede", "label": "Sous-titre", "default": "Pas de mise sur le marché sans dossier réglementaire. Le vôtre est inclus d'office et déjà ajouté à votre projet." },
    { "type": "text", "id": "docs_heading", "label": "Titre section docs", "default": "8 documents prêts à l'emploi." }
  ],
  "blocks": [
    {
      "type": "pillar",
      "name": "Pilier",
      "settings": [
        { "type": "text", "id": "icon", "label": "Lettre/icône", "default": "D" },
        { "type": "text", "id": "title", "label": "Titre", "default": "DIP" },
        { "type": "textarea", "id": "desc", "label": "Description", "default": "Dossier d'Information Produit complet, validé par notre responsable qualifié CPNP." }
      ]
    },
    {
      "type": "doc",
      "name": "Document",
      "settings": [
        { "type": "text", "id": "title", "label": "Titre", "default": "Formules & INCI" },
        { "type": "textarea", "id": "body", "label": "Contenu", "default": "Liste complète des ingrédients pour chaque produit, formatée pour l'étiquette et la déclaration CPNP." }
      ]
    }
  ],
  "max_blocks": 20,
  "presets": [
    {
      "name": "Parcours · Dossier",
      "blocks": [
        { "type": "pillar", "settings": { "icon": "D", "title": "DIP", "desc": "Dossier d'Information Produit complet, validé par notre responsable qualifié CPNP." } },
        { "type": "pillar", "settings": { "icon": "C", "title": "CPNP", "desc": "Notification européenne déposée à votre nom, pour une mise en marché conforme." } },
        { "type": "pillar", "settings": { "icon": "T", "title": "Tests", "desc": "Stabilité, compatibilité packaging, microbiologie : tout est compris." } },
        { "type": "doc", "settings": { "title": "Formules & INCI", "body": "Liste complète des ingrédients pour chaque produit, formatée pour l'étiquette et la déclaration CPNP." } },
        { "type": "doc", "settings": { "title": "Évaluation de la sécurité", "body": "Évaluation par notre responsable qualifié, conforme au règlement (CE) n°1223/2009." } },
        { "type": "doc", "settings": { "title": "Tests de stabilité", "body": "Tests sur 3 mois en conditions accélérées pour valider la durée de vie minimale." } },
        { "type": "doc", "settings": { "title": "Compatibilité packaging", "body": "Vérification que la formule reste stable au contact du contenant choisi." } },
        { "type": "doc", "settings": { "title": "Tests microbiologiques (Challenge Test)", "body": "Vérification de l'efficacité du système conservateur contre les contaminations." } }
      ]
    }
  ]
}
{% endschema %}
```

- [ ] **Step 2: Créer `templates/page.parcours-dossier.json`.**

```json
{
  "sections": {
    "parcours_dossier": {
      "type": "ml-parcours-dossier",
      "blocks": {
        "p1": { "type": "pillar", "settings": { "icon": "D", "title": "DIP", "desc": "Dossier d'Information Produit complet, validé par notre responsable qualifié CPNP." } },
        "p2": { "type": "pillar", "settings": { "icon": "C", "title": "CPNP", "desc": "Notification européenne déposée à votre nom, pour une mise en marché conforme." } },
        "p3": { "type": "pillar", "settings": { "icon": "T", "title": "Tests", "desc": "Stabilité, compatibilité packaging, microbiologie : tout est compris." } },
        "d1": { "type": "doc", "settings": { "title": "Formules & INCI", "body": "Liste complète des ingrédients pour chaque produit, formatée pour l'étiquette et la déclaration CPNP." } },
        "d2": { "type": "doc", "settings": { "title": "Évaluation de la sécurité", "body": "Évaluation par notre responsable qualifié, conforme au règlement (CE) n°1223/2009." } },
        "d3": { "type": "doc", "settings": { "title": "Tests de stabilité", "body": "Tests sur 3 mois en conditions accélérées pour valider la durée de vie minimale." } },
        "d4": { "type": "doc", "settings": { "title": "Compatibilité packaging", "body": "Vérification que la formule reste stable au contact du contenant choisi." } },
        "d5": { "type": "doc", "settings": { "title": "Tests microbiologiques (Challenge Test)", "body": "Vérification de l'efficacité du système conservateur contre les contaminations." } }
      },
      "block_order": ["p1", "p2", "p3", "d1", "d2", "d3", "d4", "d5"]
    }
  },
  "order": ["parcours_dossier"]
}
```

- [ ] **Step 3: Création de la page côté admin Shopify (manual step).** Dans Shopify admin → Online Store → Pages → Add page :
  - Title : `Parcours - Dossier cosmétologique`
  - Handle : `parcours-dossier`
  - Theme template : `parcours-dossier`
  - Sauvegarder.

- [ ] **Step 4: Push --development.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only sections/ml-parcours-dossier.liquid --only templates/page.parcours-dossier.json
```

- [ ] **Step 5: Smoke test.** Depuis `/pages/creons-ensemble-votre-marque`, cliquer « Démarrer mon projet » → redirect vers `/pages/parcours-dossier`. Vérifier l'affichage : 3 piliers, accordéon docs, CTA « J'ai compris ». Le stepper doit indiquer Étape 01 en current, étape 1 marquée ✓ done dans le récap drawer (puisque le dossier vient d'être ajouté).

- [ ] **Step 6: Commit.**

```bash
git add sections/ml-parcours-dossier.liquid templates/page.parcours-dossier.json
git commit -m "feat(parcours): step 1 — dossier cosmetologique page"
```

---

## Task 6 — Section et template Étiquette + Forfait (Étape 02)

**Files:**

- Create: `sections/ml-parcours-etiquette.liquid`
- Create: `templates/page.parcours-etiquette.json`

- [ ] **Step 1: Lire le bloc modale configurateur de `sections/ml-cem-parcours.liquid` et l'extraire.**

```bash
grep -n "ml-cem__modal\|openConfigModal\|closeConfigModal\|design:ready\|applyDesignToCard" sections/ml-cem-parcours.liquid
```

Repérer le bloc HTML de la modale (`<div class="ml-cem__modal">...`), le bloc CSS associé, et le bloc JS du listener `postMessage`. Ces blocs seront copiés tels quels dans la nouvelle section avec un namespace `.ml-parcours__modal` (renommer toutes les classes `ml-cem__modal*` en `ml-parcours__modal*`).

- [ ] **Step 2: Créer `sections/ml-parcours-etiquette.liquid`.** Le HTML reprend les 3 cards label + bloc forfait du prototype, avec ajout de la modale configurateur et du JS d'ouverture.

```liquid
{% comment %} ml-parcours-etiquette.liquid — Étape 02 — Étiquette & forfait + configurateur Vercel iframe {% endcomment %}

{% liquid
  assign etiquettes_col = collections['modeles-detiquettes']
  assign default_modele = section.settings.modele_default_product
  assign default_modele_variant_id = '55418309083470'
  if default_modele != blank and default_modele.variants.size > 0
    assign default_modele_variant_id = default_modele.variants.first.id
  endif
%}

<section class="ml-parcours__page is-active">
  <div class="ml-parcours__container">
    <div class="ml-parcours__kicker">Étape 02 / 04 — Étiquette & impression</div>
    <h1 class="ml-parcours__display">{{ section.settings.heading }}</h1>
    <p class="ml-parcours__lede">{{ section.settings.lede }}</p>

    <div class="ml-parcours__label-cards">
      <div class="ml-parcours__label-card" data-mode="standard">
        <div class="ml-parcours__label-card-visual">Aperçu Standard</div>
        <div class="ml-parcours__label-card-title">Standard</div>
        <div class="ml-parcours__label-card-price">Gratuit</div>
        <div class="ml-parcours__label-card-desc">Étiquette neutre noire, votre logo en bichromie. Idéal pour démarrer rapidement.</div>
        <div class="ml-parcours__label-card-actions">
          <button type="button" class="ml-parcours__label-card-btn" data-open-config="standard" data-default-variant="55418362003790">Choisir Standard</button>
          <a href="#" class="ml-parcours__label-card-link">En savoir plus</a>
        </div>
      </div>
      <div class="ml-parcours__label-card ml-parcours__label-card--featured" data-mode="template">
        <span class="ml-parcours__label-card-badge">Recommandé</span>
        <div class="ml-parcours__label-card-visual">Aperçu Modèles</div>
        <div class="ml-parcours__label-card-title">Modèles</div>
        <div class="ml-parcours__label-card-price">99 €</div>
        <div class="ml-parcours__label-card-desc">11 designs prêts à personnaliser dans le configurateur. Couleurs, typographies, finitions.</div>
        <div class="ml-parcours__label-card-actions">
          <button type="button" class="ml-parcours__label-card-btn" data-open-config="template" data-default-variant="{{ default_modele_variant_id }}">Ouvrir le configurateur</button>
          <a href="#" class="ml-parcours__label-card-link">En savoir plus</a>
        </div>
      </div>
      <div class="ml-parcours__label-card" data-mode="studio">
        <div class="ml-parcours__label-card-visual">Aperçu Sur-mesure</div>
        <div class="ml-parcours__label-card-title">Sur-mesure</div>
        <div class="ml-parcours__label-card-price">390 €</div>
        <div class="ml-parcours__label-card-desc">Création unique avec notre studio. Brief, allers-retours, design exclusif.</div>
        <div class="ml-parcours__label-card-actions">
          <button type="button" class="ml-parcours__label-card-btn" data-open-config="studio" data-default-variant="">Démarrer le brief</button>
          <a href="#" class="ml-parcours__label-card-link">En savoir plus</a>
        </div>
      </div>
    </div>

    <div class="ml-parcours__forfait">
      <div class="ml-parcours__forfait-head">
        <h3>Forfait d'impression annuel</h3>
        <span class="ml-parcours__forfait-chip">Inclus selon votre étiquette</span>
      </div>
      <div class="ml-parcours__forfait-pillars">
        <div class="ml-parcours__forfait-pillar">
          <h4>1 an d'impressions illimitées</h4>
          <p>Imprimez à la demande, sans seuil minimum, avec votre design validé.</p>
        </div>
        <div class="ml-parcours__forfait-pillar">
          <h4>Reconduction tacite</h4>
          <p>Renouvelé automatiquement chaque année. Annulable à tout moment.</p>
        </div>
        <div class="ml-parcours__forfait-pillar">
          <h4>Noir & blanc ou couleur</h4>
          <p>99 €/an pour étiquettes noires standards · 250 €/an pour étiquettes couleur.</p>
        </div>
      </div>
    </div>

    <div class="ml-parcours__page-footer">
      <a href="/pages/parcours-dossier" class="ml-parcours__page-footer-back">
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M13 5H1m0 0l4-4M1 5l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Retour à l'étape précédente
      </a>
      <a href="/pages/parcours-produits" class="ml-parcours__btn ml-parcours__btn--primary">
        Valider et choisir mes produits
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M1 5h12m0 0L9 1m4 4L9 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </a>
    </div>
  </div>
</section>

<!-- Modale configurateur Vercel — copiée et namespace de ml-cem-parcours.liquid -->
<div class="ml-parcours__modal" id="ml-parcours-config-modal" inert aria-modal="true" aria-label="Configurateur d'étiquette">
  <div class="ml-parcours__modal-backdrop" data-close-config></div>
  <div class="ml-parcours__modal-panel">
    <button type="button" class="ml-parcours__modal-close" data-close-config aria-label="Fermer le configurateur">×</button>
    <iframe class="ml-parcours__modal-iframe" data-config-iframe title="Configurateur"></iframe>
  </div>
</div>

<script>
(function(){
  'use strict';
  const modal = document.getElementById('ml-parcours-config-modal');
  const iframe = modal.querySelector('[data-config-iframe]');
  const allowedOrigin = 'https://mylab-configurateur.vercel.app';

  function openConfig(mode) {
    const parentOrigin = encodeURIComponent(window.location.origin);
    iframe.src = `${allowedOrigin}/configurateur?embed=1&mode=${mode}&parentOrigin=${parentOrigin}`;
    modal.removeAttribute('inert');
    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  }

  function closeConfig() {
    modal.classList.remove('is-open');
    modal.setAttribute('inert', '');
    iframe.src = 'about:blank';
    document.body.style.overflow = '';
  }

  document.querySelectorAll('[data-open-config]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const mode = btn.dataset.openConfig;
      if (mode === 'standard') {
        // Ajout direct du Standard sans configurateur
        const variantId = btn.dataset.defaultVariant;
        await fetch('/cart/add.js', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ items: [{ id: parseInt(variantId, 10), quantity: 1 }] })
        });
        document.dispatchEvent(new CustomEvent('cart:refresh'));
        return;
      }
      openConfig(mode);
    });
  });

  document.querySelectorAll('[data-close-config]').forEach(el => {
    el.addEventListener('click', closeConfig);
  });

  window.addEventListener('message', async (event) => {
    if (event.origin !== allowedOrigin) return;
    if (!event.data || event.data.type !== 'design:ready') return;
    const { variantId, reference, templateName, previewImageUrl, logoUrl, rangeNames } = event.data;
    // Ajouter au cart avec line item properties
    await fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        items: [{
          id: parseInt(variantId, 10),
          quantity: 1,
          properties: {
            'Référence design': reference || '',
            'Modèle': templateName || '',
            'Aperçu': previewImageUrl || '',
            'Logo': logoUrl || '',
            'Gammes': (rangeNames || []).join(', ')
          }
        }]
      })
    });
    closeConfig();
    document.dispatchEvent(new CustomEvent('cart:refresh'));
  });
})();
</script>

{% schema %}
{
  "name": "Parcours · Étiquette",
  "settings": [
    { "type": "richtext", "id": "heading", "label": "Titre", "default": "<p>L'identité de votre <em>flacon</em>.</p>" },
    { "type": "textarea", "id": "lede", "label": "Sous-titre", "default": "Trois options selon votre niveau d'investissement créatif. Le forfait d'impression annuel est inclus dans le choix de votre étiquette." },
    { "type": "product", "id": "modele_default_product", "label": "Produit modèle par défaut (Modèles card)" }
  ],
  "presets": [{ "name": "Parcours · Étiquette" }]
}
{% endschema %}
```

- [ ] **Step 3: Créer `templates/page.parcours-etiquette.json`.**

```json
{
  "sections": {
    "parcours_etiquette": {
      "type": "ml-parcours-etiquette"
    }
  },
  "order": ["parcours_etiquette"]
}
```

- [ ] **Step 4: Création de la page côté admin Shopify (manual step).** Online Store → Pages → Add page : title `Parcours - Étiquette & impression`, handle `parcours-etiquette`, template `parcours-etiquette`.

- [ ] **Step 5: Push --development.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only sections/ml-parcours-etiquette.liquid --only templates/page.parcours-etiquette.json
```

- [ ] **Step 6: Smoke test.** Depuis `/pages/parcours-dossier`, cliquer « J'ai compris, étape suivante ». Sur `/pages/parcours-etiquette` :
  - Vérifier les 3 cards (Standard / Modèles featured / Sur-mesure) et le bloc forfait
  - Cliquer Standard → ajout direct + cart refresh, étape 02 marquée ✓ dans le stepper
  - Cliquer Modèles → ouverture modale configurateur Vercel iframe (URL `?embed=1&mode=template`)
  - Cliquer Sur-mesure → ouverture modale configurateur Vercel iframe (URL `?embed=1&mode=studio`)
  - Vérifier le styling de la card featured (noir, badge « Recommandé », prix blanc)

- [ ] **Step 7: Commit.**

```bash
git add sections/ml-parcours-etiquette.liquid templates/page.parcours-etiquette.json
git commit -m "feat(parcours): step 2 — etiquette + forfait + configurateur iframe"
```

---

## Task 7 — Section et template Produits (Étape 03)

**Files:**

- Create: `sections/ml-parcours-produits.liquid`
- Create: `templates/page.parcours-produits.json`

- [ ] **Step 1: Repérer dans `sections/ml-cem-parcours.liquid` la logique des paliers produits + tabs catégories.**

```bash
grep -n "ml_tier_data\|product-tab\|paliers\|tier-button\|product-card" sections/ml-cem-parcours.liquid
```

La logique paliers (palier 6/12/24/48/96 par produit selon `cat × contenance × gamme`) doit être rapatriée telle quelle. Repérer les blocs Liquid de génération des cards et des tabs, et les copier dans la nouvelle section avec namespace `ml-parcours__`.

- [ ] **Step 2: Créer `sections/ml-parcours-produits.liquid`.**

```liquid
{% comment %} ml-parcours-produits.liquid — Étape 03 — Produits avec tabs + paliers {% endcomment %}

{% liquid
  assign pro_col = collections['boutique-adherents']
  assign extra_products = section.settings.extra_products
%}

<section class="ml-parcours__page is-active">
  <div class="ml-parcours__container">
    <div class="ml-parcours__kicker">Étape 03 / 04 — Produits</div>
    <h1 class="ml-parcours__display">{{ section.settings.heading }}</h1>
    <p class="ml-parcours__lede">{{ section.settings.lede }}</p>

    <div class="ml-parcours__product-tabs">
      <button type="button" class="ml-parcours__product-tab is-active" data-cat="all">Tous</button>
      <button type="button" class="ml-parcours__product-tab" data-cat="shampoing">Shampoings</button>
      <button type="button" class="ml-parcours__product-tab" data-cat="shampoing-rep">Repigmentants</button>
      <button type="button" class="ml-parcours__product-tab" data-cat="masque">Masques</button>
      <button type="button" class="ml-parcours__product-tab" data-cat="creme">Crèmes</button>
      <button type="button" class="ml-parcours__product-tab" data-cat="finition">Finition</button>
      <button type="button" class="ml-parcours__product-tab" data-cat="homme">Gamme Homme</button>
      <button type="button" class="ml-parcours__product-tab" data-cat="bac1000">Format 1000ml</button>
    </div>

    <div class="ml-parcours__product-grid">
      {% for p in pro_col.products %}
        {% render 'ml-parcours-product-card', product: p %}
      {% endfor %}
      {% for p in extra_products %}
        {% render 'ml-parcours-product-card', product: p, extra: true %}
      {% endfor %}
    </div>

    <div class="ml-parcours__page-footer">
      <a href="/pages/parcours-etiquette" class="ml-parcours__page-footer-back">
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M13 5H1m0 0l4-4M1 5l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Retour à l'étape précédente
      </a>
      <a href="/pages/parcours-recap" class="ml-parcours__btn ml-parcours__btn--primary">
        Voir le récap final
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M1 5h12m0 0L9 1m4 4L9 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </a>
    </div>
  </div>
</section>

<script>
(function(){
  'use strict';
  document.querySelectorAll('.ml-parcours__product-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const cat = tab.dataset.cat;
      document.querySelectorAll('.ml-parcours__product-tab').forEach(t => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      document.querySelectorAll('.ml-parcours__product-card').forEach(card => {
        card.style.display = (cat === 'all' || card.dataset.cat === cat) ? '' : 'none';
      });
    });
  });

  // Tier selection: click adds-or-updates the tier in cart
  document.querySelectorAll('.ml-parcours__product-card').forEach(card => {
    card.querySelectorAll('.ml-parcours__tier').forEach(tier => {
      tier.addEventListener('click', async () => {
        const variantId = card.dataset.variantId;
        const qty = parseInt(tier.dataset.qty, 10);
        if (!variantId) return;
        // Remove existing line for this variant first
        const cart = await (await fetch('/cart.js', { credentials: 'same-origin' })).json();
        const existing = (cart.items || []).find(it => it.variant_id == variantId);
        if (existing) {
          await fetch('/cart/change.js', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ id: existing.key, quantity: qty })
          });
        } else {
          await fetch('/cart/add.js', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ items: [{ id: parseInt(variantId, 10), quantity: qty }] })
          });
        }
        // Update visual state
        card.querySelectorAll('.ml-parcours__tier').forEach(t => t.classList.remove('is-active'));
        tier.classList.add('is-active');
        document.dispatchEvent(new CustomEvent('cart:refresh'));
      });
    });
  });
})();
</script>

{% schema %}
{
  "name": "Parcours · Produits",
  "settings": [
    { "type": "richtext", "id": "heading", "label": "Titre", "default": "<p>Composez votre <em>gamme</em>.</p>" },
    { "type": "textarea", "id": "lede", "label": "Sous-titre", "default": "Sélectionnez vos références et vos quantités. Plus vous prenez, moins ça coûte par flacon. Aucune obligation de tout choisir d'un coup." },
    { "type": "product_list", "id": "extra_products", "label": "Produits hors catalogue (bac 1000ml)", "limit": 50 }
  ],
  "presets": [{ "name": "Parcours · Produits" }]
}
{% endschema %}
```

- [ ] **Step 3: Créer `snippets/ml-parcours-product-card.liquid`** (rendu d'une card produit avec ses paliers, basé sur la logique existante `ml-cem-parcours.liquid`). Reprendre le bloc de génération de card du monolithe et adapter au namespace `ml-parcours__`. Inclure les attributs `data-variant-id`, `data-cat`, et un mapping de paliers via `data-qty` sur chaque `.ml-parcours__tier`.

```liquid
{% comment %} ml-parcours-product-card.liquid — Card produit avec paliers {% endcomment %}

{% liquid
  assign cat = 'shampoing'
  if product.tags contains 'masque' or product.title contains 'Masque' or product.title contains 'masque'
    assign cat = 'masque'
  elsif product.tags contains 'creme' or product.title contains 'Crème'
    assign cat = 'creme'
  elsif product.tags contains 'finition' or product.title contains 'Sérum' or product.title contains 'serum'
    assign cat = 'finition'
  elsif product.tags contains 'homme' or product.tags contains 'herborist' or product.title contains 'Barbe' or product.title contains 'Gel Douche'
    assign cat = 'homme'
  elsif product.tags contains 'dejaunisseur' or product.title contains 'jaune' or product.title contains 'Repigmentant'
    assign cat = 'shampoing-rep'
  endif

  assign variant = product.variants.first
  assign tiers = '6,12,24,48,96' | split: ','
%}

<div class="ml-parcours__product-card" data-variant-id="{{ variant.id }}" data-cat="{{ cat }}">
  <div class="ml-parcours__product-card-img">
    {% if product.featured_image %}
      <img src="{{ product.featured_image | image_url: width: 400 }}" alt="{{ product.title | escape }}" loading="lazy">
    {% else %}
      {{ product.title }}
    {% endif %}
  </div>
  <div class="ml-parcours__product-card-body">
    <div class="ml-parcours__product-card-title">{{ product.title }}</div>
    <div class="ml-parcours__product-card-sub">{{ product.metafields.custom.contenance | default: '200 ml' }}</div>
    <div class="ml-parcours__product-card-tiers">
      {% for q in tiers %}
        <div class="ml-parcours__tier" data-qty="{{ q }}">{{ q }}</div>
      {% endfor %}
    </div>
    <div class="ml-parcours__product-card-qty">
      {% if extra %}<small>Hors catalogue</small><br>{% endif %}
      <span data-qty-display>Aucune sélection</span>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Créer `templates/page.parcours-produits.json`.**

```json
{
  "sections": {
    "parcours_produits": {
      "type": "ml-parcours-produits"
    }
  },
  "order": ["parcours_produits"]
}
```

- [ ] **Step 5: Création de la page côté admin Shopify (manual step).** Online Store → Pages → Add page : title `Parcours - Produits`, handle `parcours-produits`, template `parcours-produits`.

- [ ] **Step 6: Push --development.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only sections/ml-parcours-produits.liquid --only snippets/ml-parcours-product-card.liquid --only templates/page.parcours-produits.json
```

- [ ] **Step 7: Smoke test.** Depuis `/pages/parcours-etiquette`, valider une étiquette puis cliquer « Valider et choisir mes produits ». Sur `/pages/parcours-produits` :
  - Vérifier les tabs catégories (Tous / Shampoings / etc.)
  - Cliquer un palier sur une card → ajout au cart, palier marqué actif
  - Cliquer un palier différent sur la même card → quantité mise à jour
  - Vérifier dans le récap drawer que l'étape 03 passe à ✓ done après le premier ajout produit

- [ ] **Step 8: Commit.**

```bash
git add sections/ml-parcours-produits.liquid snippets/ml-parcours-product-card.liquid templates/page.parcours-produits.json
git commit -m "feat(parcours): step 3 — produits with tabs and tiered quantities"
```

---

## Task 8 — Section et template Récap (Étape 04)

**Files:**

- Create: `sections/ml-parcours-recap.liquid`
- Create: `templates/page.parcours-recap.json`

- [ ] **Step 1: Créer `sections/ml-parcours-recap.liquid`.** Affiche la timeline 3 jalons + table des items du cart + total + CTA validation. La table est rendue côté client via JS qui lit `/cart.js`.

```liquid
{% comment %} ml-parcours-recap.liquid — Étape 04 — Récap final + validation {% endcomment %}

<section class="ml-parcours__page is-active">
  <div class="ml-parcours__container">
    <div class="ml-parcours__kicker">Étape 04 / 04 — Validation</div>
    <h1 class="ml-parcours__display">{{ section.settings.heading }}</h1>
    <p class="ml-parcours__lede">{{ section.settings.lede }}</p>

    <div class="ml-parcours__recap-final">
      <h2>{{ section.settings.recap_heading }}</h2>
      <div class="ml-parcours__timeline">
        {% for block in section.blocks %}
          <div class="ml-parcours__timeline-item" {{ block.shopify_attributes }}>
            <div class="ml-parcours__timeline-item-dot"></div>
            <h4>{{ block.settings.label }}</h4>
            <p>{{ block.settings.desc }}</p>
          </div>
        {% endfor %}
      </div>

      <div class="ml-parcours__recap-table" data-recap-table>
        <div class="ml-parcours__recap-row" data-empty>
          <span class="ml-parcours__recap-row-label">Votre projet est vide</span>
          <span class="ml-parcours__recap-row-value">—</span>
        </div>
      </div>

      <div class="ml-parcours__recap-total-final">
        <span class="ml-parcours__recap-total-label">Total HT</span>
        <span class="ml-parcours__recap-total-value" data-recap-total-value>0,00 €</span>
      </div>

      <div class="ml-parcours__recap-actions">
        <button type="button" class="ml-parcours__btn ml-parcours__btn--big" style="background:#fff;color:var(--mlp-ink)" data-validate-project disabled>
          Valider notre projet
          <svg width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true"><path d="M1 6h14m0 0L10 1m5 5l-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button type="button" class="ml-parcours__btn ml-parcours__btn--ghost ml-parcours__btn--big" style="border-color:#bdb3a3;color:#fff" data-request-quote>
          Recevoir le devis PDF
        </button>
      </div>
    </div>

    <div class="ml-parcours__page-footer">
      <a href="/pages/parcours-produits" class="ml-parcours__page-footer-back">
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M13 5H1m0 0l4-4M1 5l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Modifier mes produits
      </a>
      <a href="/pages/contact" class="ml-parcours__contact-link">Une question ? Prendre RDV</a>
    </div>
  </div>
</section>

<script>
(function(){
  'use strict';

  function fmtMoney(cents) {
    return (cents / 100).toFixed(2).replace('.', ',') + ' €';
  }

  async function renderRecap() {
    const cart = await (await fetch('/cart.js', { credentials: 'same-origin' })).json();
    const items = cart.items || [];
    const table = document.querySelector('[data-recap-table]');
    const totalEl = document.querySelector('[data-recap-total-value]');
    const validateBtn = document.querySelector('[data-validate-project]');

    if (items.length === 0) {
      table.innerHTML = '<div class="ml-parcours__recap-row" data-empty><span class="ml-parcours__recap-row-label">Votre projet est vide</span><span class="ml-parcours__recap-row-value">—</span></div>';
      totalEl.textContent = '0,00 €';
      validateBtn.disabled = true;
      return;
    }

    table.innerHTML = items.map(it => `
      <div class="ml-parcours__recap-row">
        <span class="ml-parcours__recap-row-label">${it.product_title}${it.quantity > 1 ? ' · ' + it.quantity + 'u' : ''}</span>
        <span class="ml-parcours__recap-row-value">${fmtMoney(it.line_price)}</span>
      </div>
    `).join('');
    totalEl.textContent = fmtMoney(cart.total_price);

    // Enable validate only if the 3 steps are done
    const hasDossier = items.some(it => it.handle === 'creation-du-dossier-cosmetologique');
    const etiquetteHandles = window.MylabParcours?.etiquetteHandles || [];
    const produitHandles = window.MylabParcours?.produitHandles || [];
    const hasEtiquette = items.some(it => etiquetteHandles.includes(it.handle));
    const hasProduits = items.some(it => produitHandles.includes(it.handle));
    validateBtn.disabled = !(hasDossier && hasEtiquette && hasProduits);
  }

  document.querySelector('[data-validate-project]').addEventListener('click', () => {
    window.location.href = '/checkout';
  });

  document.querySelector('[data-request-quote]').addEventListener('click', () => {
    window.location.href = '/pages/contact?subject=devis-parcours';
  });

  renderRecap();
  document.addEventListener('cart:refresh', renderRecap);
})();
</script>

{% schema %}
{
  "name": "Parcours · Récap",
  "settings": [
    { "type": "richtext", "id": "heading", "label": "Titre", "default": "<p>Votre <em>projet</em>, en un coup d'œil.</p>" },
    { "type": "textarea", "id": "lede", "label": "Sous-titre", "default": "Vérifiez chaque ligne. Une fois validé, votre devis est envoyé et votre projet entre en production sous 7 jours ouvrés." },
    { "type": "richtext", "id": "recap_heading", "label": "Titre du bloc récap dark", "default": "<p>Le lancement de votre <em>marque</em>, prêt à signer.</p>" }
  ],
  "blocks": [
    {
      "type": "timeline_step",
      "name": "Jalon timeline",
      "settings": [
        { "type": "text", "id": "label", "label": "Label", "default": "J0 — Validation" },
        { "type": "textarea", "id": "desc", "label": "Description", "default": "Devis envoyé. Acompte 30%. Coup d'envoi de la production." }
      ]
    }
  ],
  "max_blocks": 5,
  "presets": [
    {
      "name": "Parcours · Récap",
      "blocks": [
        { "type": "timeline_step", "settings": { "label": "J0 — Validation", "desc": "Devis envoyé. Acompte 30%. Coup d'envoi de la production." } },
        { "type": "timeline_step", "settings": { "label": "J+7 — Étiquettes", "desc": "Bon à tirer envoyé. Vous validez le rendu avant impression." } },
        { "type": "timeline_step", "settings": { "label": "J+21 — Livraison", "desc": "Vos cartons arrivent en boutique. Solde réglé à la livraison." } }
      ]
    }
  ]
}
{% endschema %}
```

- [ ] **Step 2: Créer `templates/page.parcours-recap.json`.**

```json
{
  "sections": {
    "parcours_recap": {
      "type": "ml-parcours-recap",
      "blocks": {
        "j0": { "type": "timeline_step", "settings": { "label": "J0 — Validation", "desc": "Devis envoyé. Acompte 30%. Coup d'envoi de la production." } },
        "j7": { "type": "timeline_step", "settings": { "label": "J+7 — Étiquettes", "desc": "Bon à tirer envoyé. Vous validez le rendu avant impression." } },
        "j21": { "type": "timeline_step", "settings": { "label": "J+21 — Livraison", "desc": "Vos cartons arrivent en boutique. Solde réglé à la livraison." } }
      },
      "block_order": ["j0", "j7", "j21"]
    }
  },
  "order": ["parcours_recap"]
}
```

- [ ] **Step 3: Création de la page côté admin Shopify (manual step).** Online Store → Pages → Add page : title `Parcours - Récap`, handle `parcours-recap`, template `parcours-recap`.

- [ ] **Step 4: Push --development.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only sections/ml-parcours-recap.liquid --only templates/page.parcours-recap.json
```

- [ ] **Step 5: Smoke test.** Depuis `/pages/parcours-produits`, valider sa sélection puis cliquer « Voir le récap final ». Sur `/pages/parcours-recap` :
  - Vérifier la timeline 3 jalons (J0/J+7/J+21)
  - Vérifier la table récap avec dossier + étiquette + forfait + produits sélectionnés
  - Vérifier le total HT cumulé
  - Le bouton « Valider notre projet » doit être actif si les 3 étapes sont validées, désactivé sinon
  - Cliquer « Valider notre projet » → redirect vers `/checkout`

- [ ] **Step 6: Commit.**

```bash
git add sections/ml-parcours-recap.liquid templates/page.parcours-recap.json
git commit -m "feat(parcours): step 4 — recap with timeline and validation CTA"
```

---

## Task 9 — Étendre ml-forfait-gate.js (paths du parcours)

**Files:**

- Modify: `assets/ml-forfait-gate.js`

- [ ] **Step 1: Lire le fichier actuel pour repérer la regex de détection path.**

```bash
grep -n "creons-ensemble-votre-marque\|pathname\|window.location.pathname\|cart:refresh\|open: false" assets/ml-forfait-gate.js
```

Repérer la condition qui aujourd'hui détecte uniquement `/pages/creons-ensemble-votre-marque`.

- [ ] **Step 2: Étendre la condition pour matcher aussi les 4 nouvelles pages.** La regex devient `/^\/pages\/(creons-ensemble-votre-marque|parcours-(dossier|etiquette|produits|recap))\/?$/`. Modifier dans le code :

```javascript
// AVANT (à remplacer)
const isParcoursPage = window.location.pathname.match(/\/pages\/creons-ensemble-votre-marque/);

// APRÈS
const isParcoursPage = window.location.pathname.match(
  /\/pages\/(creons-ensemble-votre-marque|parcours-(dossier|etiquette|produits|recap))\/?$/
);
```

Identifier toutes les occurrences de cette logique de détection dans le fichier (il peut y en avoir plusieurs : une pour `open: false` du drawer, une pour le blocker checkout, etc.) et les mettre à jour de la même façon.

- [ ] **Step 3: Ajouter la classe `body.is-parcours` (déjà ajoutée par `ml-parcours.js` au DOMContentLoaded, mais on peut renforcer côté `ml-forfait-gate` pour qu'elle soit appliquée plus tôt si possible).** Au début du fichier, après le check `isParcoursPage` :

```javascript
if (isParcoursPage) {
  document.documentElement.classList.add('is-parcours-active');
  // body class is also set later by ml-parcours.js — this is just a fallback for early CSS hooks
}
```

- [ ] **Step 4: Ajouter une règle CSS dans `assets/ml-parcours.css` pour masquer l'icône cart de la topbar Shopify standard sur les pages parcours.**

```css
body.is-parcours .header__icon--cart,
body.is-parcours cart-icon-bubble,
body.is-parcours [aria-controls="cart-drawer"] {
  display: none !important;
}

body.is-parcours .header,
body.is-parcours [data-section-type="header"] {
  display: none !important;
}
```

(Le shell parcours remplace la topbar standard sur ces pages.)

- [ ] **Step 5: Push --development.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only assets/ml-forfait-gate.js --only assets/ml-parcours.css
```

- [ ] **Step 6: Smoke test.** Sur chaque page du parcours (landing + 4 étapes) :
  - Vérifier que l'icône cart de la topbar Shopify standard n'est pas visible (la topbar standard elle-même devrait être masquée, remplacée par la topbar parcours)
  - Vérifier que cliquer un bouton qui ajoute au cart NE déclenche PAS l'ouverture automatique du cart drawer (le drawer doit rester fermé)
  - Sur une page hors parcours (ex : `/products/shampoing-nourrissant`), vérifier que la topbar standard est de retour et que le cart drawer s'ouvre normalement

- [ ] **Step 7: Commit.**

```bash
git add assets/ml-forfait-gate.js assets/ml-parcours.css
git commit -m "feat(parcours): extend ml-forfait-gate paths and hide standard topbar"
```

---

## Task 10 — Smoke test complet et edge cases

**Files:** aucun changement de code, validation seulement.

- [ ] **Step 1: Tester le flow complet desktop.** Ouvrir `/pages/creons-ensemble-votre-marque` (en navigation privée pour cart vide) :
  1. Cliquer « Démarrer mon projet » → toast « ✓ Dossier ajouté à votre projet » → redirect `/pages/parcours-dossier`
  2. Vérifier stepper : étape 01 ✓ done, étape 02 current, étapes 03-04 locked
  3. Cliquer « J'ai compris, étape suivante » → `/pages/parcours-etiquette`
  4. Cliquer card Modèles → modale configurateur s'ouvre → valider un design → toast « ✓ Étiquette validée » → modale ferme → étape 02 ✓ done
  5. Vérifier dans le récap drawer : dossier ✓, étiquette ✓, forfait ajouté automatiquement (par `ml-forfait-gate.js`)
  6. Cliquer « Valider et choisir mes produits » → `/pages/parcours-produits`
  7. Cliquer un palier sur 2-3 cards produits différentes → quantités enregistrées
  8. Cliquer « Voir le récap final » → `/pages/parcours-recap`
  9. Vérifier la table récap : dossier + étiquette + forfait + produits avec total HT correct
  10. Bouton « Valider notre projet » actif → cliquer → redirect `/checkout`

- [ ] **Step 2: Tester edge case « cart pré-existant ».** Vider le cart, ajouter un produit pro hors parcours (ex : `/products/<un-produit-pro>` → add to cart). Puis ouvrir `/pages/creons-ensemble-votre-marque`. Vérifier :
  - Le produit pro précédent est toujours dans le cart
  - L'étape 03 est marquée ✓ done dans le stepper (puisqu'un produit pro est déjà présent — comportement assumé)
  - Cliquer « Démarrer mon projet » → ajout dossier sans toucher au produit pro pré-existant

- [ ] **Step 3: Tester edge case « Quitter le parcours ».** Avec un cart contenant dossier + étiquette + forfait + 2 produits pro :
  - Cliquer « Quitter le parcours » dans la topbar parcours
  - Vérifier la modale de confirmation
  - Confirmer → vérifier que dossier, étiquette et forfait sont retirés
  - Vérifier que les 2 produits pro restent dans le cart
  - Redirect vers `/`

- [ ] **Step 4: Tester edge case « reload milieu parcours ».** Sur `/pages/parcours-produits` avec 1 produit sélectionné :
  - Reload (F5)
  - Vérifier que le palier sélectionné reste actif (lu depuis le cart)
  - Vérifier que stepper et récap drawer reflètent l'état correct

- [ ] **Step 5: Tester edge case « lien direct étape 03 sans 01/02 ».** Vider le cart. Ouvrir directement `/pages/parcours-produits` :
  - Pas de redirect (verrouillage soft)
  - Stepper : étape 03 current, étapes 01 et 02 locked
  - Récap drawer : tout en pending

- [ ] **Step 6: Tester mobile.** Ouvrir en émulation mobile (DevTools, viewport 375px) :
  - Topbar parcours visible
  - Stepper : labels masqués, juste les pastilles + lignes
  - Récap drawer : sticky, ouvre/ferme correctement
  - Bottom mobile CTA visible avec progression
  - Cliquer « Voir récap » sur le bottom CTA ouvre le récap drawer
  - Cards label, produits, etc. en colonne 1 par ligne

- [ ] **Step 7: Tester customer connecté avec tag `abo-impression-couleur`.** Se connecter avec un compte taggé. Sur `/pages/parcours-etiquette`, valider une étiquette modèle. Vérifier que le forfait n'est PAS auto-ajouté (logique existante de `ml-forfait-gate.js` skip).

- [ ] **Step 8: Si un test échoue,** noter l'observation, créer un fix dans la même branche, push --development, retester. Marquer ce step comme bloqué (in_progress) tant que tous les tests ne sont pas verts.

- [ ] **Step 9: Commit final si des fixes ont été apportés.**

```bash
git add -A
git commit -m "fix(parcours): smoke test fixes for edge cases"
```

---

## Task 11 — Push live (sur demande explicite uniquement)

**Files:** aucun changement de code.

- [ ] **Step 1: Demander confirmation explicite à Yoann.** Selon la règle stockée en mémoire (`feedback_shopify_push.md`) : « Live only on explicit PUSH LIVE ». Ne pas pusher live sans le mot-clé.

- [ ] **Step 2: Si confirmé, push live avec scope explicite.**

```bash
shopify theme push --store mylab-shop-3.myshopify.com --live --nodelete \
  --only assets/ml-parcours.css \
  --only assets/ml-parcours.js \
  --only assets/ml-forfait-gate.js \
  --only snippets/ml-parcours-shell.liquid \
  --only snippets/ml-parcours-product-card.liquid \
  --only layout/theme.liquid \
  --only sections/ml-parcours-landing.liquid \
  --only sections/ml-parcours-dossier.liquid \
  --only sections/ml-parcours-etiquette.liquid \
  --only sections/ml-parcours-produits.liquid \
  --only sections/ml-parcours-recap.liquid \
  --only templates/page.creons-ensemble-votre-marque.json \
  --only templates/page.parcours-dossier.json \
  --only templates/page.parcours-etiquette.json \
  --only templates/page.parcours-produits.json \
  --only templates/page.parcours-recap.json
```

- [ ] **Step 3: Smoke test prod.** Ouvrir `https://mylab-shop.com/pages/creons-ensemble-votre-marque` (ou domaine actuel) en navigation privée. Refaire le flow complet de la Task 10 Step 1 sur le live.

- [ ] **Step 4: Commit final + tag.**

```bash
git tag parcours-multi-pages-v1
git push origin master
git push origin parcours-multi-pages-v1
```

(Push remote uniquement si explicitement demandé.)

---

## Plan de rollback

En cas de régression critique en prod :

1. Repointer `templates/page.creons-ensemble-votre-marque.json` vers l'ancien template (sauvegarde `.bak` créée Task 4 Step 2)
2. Push live ciblé : `shopify theme push --live --only templates/page.creons-ensemble-votre-marque.json`
3. La page revient au monolithe `ml-cem-parcours.liquid` (toujours présent dans le repo)
4. Les 4 nouvelles pages parcours-* deviennent inaccessibles tant qu'on ne les retire pas côté admin Shopify, mais elles ne sont pas linkées depuis nulle part hors du shell — pas de souci SEO ni UX

## Self-review notes (pour information)

Vérifications faites :

1. **Spec coverage** : chaque décision du spec est mappée à une task (découpage 4 pages → T4-T8 ; verrouillage soft → JS T2 + stepper T3 ; cart Shopify état → T2 ; stepper + drawer → T3 ; pages natives → T4-T8 templates ; cart drawer invisible → T9 ; auto-add dossier + sortie → T2 + T4 + T9). DA strictement respectée dans T1 (CSS).

2. **Placeholders** : aucun TBD/TODO. Tous les blocs de code sont complets. Les manual steps Shopify admin sont explicites avec title/handle/template à entrer.

3. **Type consistency** : les classes CSS sont cohérentes entre snippet shell (T3), sections (T4-T8) et CSS (T1). Les data-attributes (`data-ml-recap-toggle`, `data-ml-start-parcours`, `data-ml-exit-parcours`, `data-open-config`, `data-validate-project`, `data-cat`, `data-qty`, `data-variant-id`) sont définis dans T2/T3 et réutilisés dans les sections content.

4. **Edge cases** : couverts en T10 (cart pré-existant, sortie, reload, lien direct, mobile, customer taggé).

5. **Manual steps** : la création des 4 pages côté admin Shopify est explicite à T5/T6/T7/T8 step 3 (handle, template à attribuer). Sans ces pages, les templates JSON n'ont pas de page hôte — étape obligatoire avant smoke test.
