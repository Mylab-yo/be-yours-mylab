# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Shopify theme export based on the **Be Yours** theme, customized for **MyLab Shop** — a B2B French cosmetics store. The theme is deployed via the Shopify admin (Theme Editor / Shopify CLI); there is no local build step or test runner.

## Deploying changes

Use the Shopify CLI to push/pull theme files:

```bash
# Pull current live theme
shopify theme pull --store mylab-shop-3.myshopify.com

# Push changes to development theme
shopify theme push --store mylab-shop-3.myshopify.com --development

# Start local dev server with live reload
shopify theme dev --store mylab-shop-3.myshopify.com
```

Assets (JS/CSS) are served directly by Shopify's CDN — there is no bundler. Edit source files in `assets/` directly.

## Architecture

### Directory layout

| Directory    | Purpose |
|--------------|---------|
| `layout/`    | Root HTML shell. `theme.liquid` wraps all pages; `password.liquid` is the coming-soon layout. |
| `templates/` | JSON files that compose sections onto a page type (e.g. `product.json`). |
| `sections/`  | Reusable Liquid section files, each with an embedded `{% schema %}` block for Theme Editor settings. |
| `snippets/`  | Partial Liquid fragments rendered via `{% render %}` — stateless, receive variables as arguments. |
| `assets/`    | Flat directory of JS, CSS, and SVG files. JS files are vanilla custom elements or IIFE modules. |
| `locales/`   | Translation strings (`en.default.json` is the source; `.schema.json` files control Theme Editor labels). |

### MyLab custom layer (prefixed `ml-` / `mylab-`)

The store has a **custom product pricing layer and cart drawer** overlaid on top of the Be Yours theme:

- **`assets/mylab-product.js`** — IIFE that drives volume pricing + custom cart drawer. Key responsibilities:
  - Fetches product JSON via `/products/{handle}.js` on init.
  - Hardcodes volume-pricing tiers per contenance in `window.MylabProductData.tiers`.
  - Renders quantity tier buttons and updates price display/savings on selection.
  - Adds to cart via `/cart/add.js`, then re-renders the custom drawer.
  - **Actively suppresses the native Be Yours `cart-drawer` web component** using a `MutationObserver` and by setting `style.display = 'none'` and overriding its `.open()`/`.close()` methods.
- **`assets/mylab-cart.js`** — cart refresh integration (quantity selectors, drawer re-render).
- **`assets/ml-volume-pricing.js`** — dynamic volume pricing tier display.
- **`sections/mylab-cart-drawer.liquid`** — custom cart drawer HTML (IDs prefixed `ml-drawer-*`). Included globally in `layout/theme.liquid` via `{% section 'mylab-cart-drawer' %}`.
- **`assets/mylab-product.css`** + **`assets/ml-volume-pricing.css`** — all styles for the MyLab layer using `ml-` BEM-style class prefix.

### Be Yours theme base layer

Standard Be Yours theme components remain intact for all non-product pages. Key files:

- `assets/global.js` — shared custom elements (`MenuDrawer`, `CartDrawer`, `SliderComponent`, `QuantityInput`, `VariantSelects`, etc.) used across sections.
- `assets/pubsub.js` — lightweight publish/subscribe bus used by Be Yours components to communicate (e.g. cart updates).
- `assets/modules-basis.js` — ScrollSnapSlider and basic modules.
- `assets/cart.js`, `assets/cart-drawer.js` — Be Yours's own cart logic (bypassed by the MyLab override).
- `assets/facets.js` — collection filtering logic.
- `assets/product-info.js`, `assets/product-form.js` — standard product page logic (used by `main-product` section).
- `assets/quick-view.js` — quick view drawer component.
- `assets/color-swatches.js` — color swatch selectors.

### Pricing logic (important)

Volume pricing is **hardcoded in JS** (`assets/mylab-product.js`), not stored in Shopify metafields or variant prices. Prices are in centimes (e.g. `700` = 7.00 €). The displayed subtotal in the cart drawer is recalculated client-side from these tiers — it does **not** match what Shopify charges. This is a B2B display layer; actual checkout pricing must be managed separately.

The "contenance" selector (`200ml`, `500ml`, `1000ml`) links to **separate product handles** (`shampoing-nourrissant`, `shampoing-nourrissant-500ml`, `shampoing-nourrissant-1000-ml`) rather than variants of a single product — each navigates to a new URL.

### Fonts

Two Google Font families are loaded in `layout/theme.liquid`: **Cormorant Garamond** (headings/body italic) and **DM Sans** (body). These are in addition to Shopify's theme font system variables.

## Key conventions

- All MyLab-specific CSS classes are prefixed `ml-`.
- MyLab JS is wrapped in an IIFE with `'use strict'` — no ES modules, no bundler.
- Be Yours native components use custom HTML elements (e.g. `<cart-drawer>`, `<product-info>`, `<variant-selects>`, `<menu-drawer>`).
- Section schemas define Theme Editor settings; snippets have no schema and accept only passed variables.
- The native Be Yours cart drawer is suppressed by `mylab-product.js` — do not re-enable it without removing the MyLab override logic.

## Odoo customizations

Des scripts Python XML-RPC pour déployer des customisations Odoo vivent dans `scripts/odoo/`. Ils couvrent :
- Champ `x_carton_capacity` sur `product.template` (capacité carton par produit)
- Action serveur "Répartir en cartons" sur `stock.picking`
- Template PDF bon de livraison custom avec détail par carton

Voir `scripts/odoo/README.md` pour l'ordre d'exécution. Tous les scripts sont idempotents.
