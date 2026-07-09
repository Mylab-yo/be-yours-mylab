# Rupture de stock — backorder + capture prévenez-moi (SP1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher clairement les produits en rupture sur la fiche produit, la boutique pro et la commande express, permettre de les commander en backorder (« Commander et recevoir dès retour en stock »), et capturer les demandes « prévenez-moi » dans Airtable via un webhook n8n.

**Architecture:** `inventory_policy=continue` (sauf tag `no-backorder`) rend les ruptures commandables ; comme `available` reste vrai, la rupture se détecte par `inventory_quantity <= 0` côté serveur (Liquid). La fiche lit sa propre quantité ; la commande express lit un map `window.MlOos` rendu en Liquid (car `.js` n'expose pas la quantité) ; la boutique pro calcule ses badges en Liquid. La modale « prévenez-moi » POST vers un webhook n8n qui upsert dans Airtable.

**Tech Stack:** Liquid, JS vanilla IIFE (pas de bundler, pas de test runner), Shopify Admin REST API, n8n (MCP), Airtable (MCP). Vérification = QA navigateur sur le thème dev + revue subagents.

**Référence :** spec `docs/superpowers/specs/2026-06-11-rupture-stock-backorder-design.md`. SP2 (email auto au retour de stock) = hors de ce plan.

---

## File Structure

| Fichier | Action | Responsabilité |
|---|---|---|
| `scripts/shopify/set_backorder_policy.py` | Create | `inventory_policy` continue/deny sur les variantes de la collection |
| Airtable table `back-in-stock` | Create (MCP) | Stockage des demandes prévenez-moi |
| n8n workflow `back-in-stock-capture` | Create (MCP) | Webhook → upsert Airtable |
| `layout/theme.liquid` | Modify (l.109) | Global `window.MlNotify` (URL webhook) |
| `config/settings_schema.json` + `config/settings_data.json` | Modify | Réglage `notify_webhook_url` + valeur |
| `snippets/ml-notify-modal.liquid` | Create | Modale capture email (rendue globalement) |
| `assets/ml-notify.js` | Create | Ouverture modale + POST webhook |
| `assets/ml-notify.css` | Create | Styles modale + bandeau rupture |
| `sections/main-product.liquid` | Modify | Flags OOS/backorder + bandeau + CTA + bouton prévenez-moi |
| `assets/mylab-product.js` | Modify | Détecter rupture (data-attrs), basculer CTA |
| `sections/ml-collection-filterable.liquid` | Modify | Badges « Sur commande » / « Rupture » |
| `sections/ml-quick-order.liquid` | Modify | Maps `MlOos`/`MlNoBackorder` + logique backorder |
| `snippets/ml-qo-row.liquid` | Modify | Tag « sur commande » / lien prévenez-moi |

---

## Task 0 : Shopify — inventory_policy (backorder)

**Files:** Create `scripts/shopify/set_backorder_policy.py`

- [ ] **Step 1 : Écrire le script**

```python
"""Met inventory_policy=continue sur toutes les variantes des produits de
'boutique-adherents' SAUF ceux tagués 'no-backorder' (-> deny). Idempotent.
Token write_products auto-sélectionné (cf. create_pump_products.py)."""
import json, re, time, urllib.request
from pathlib import Path

STORE = "mylab-shop-3.myshopify.com"
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
API = f"https://{STORE}/admin/api/2024-07"

def candidate_tokens():
    return [m.group(1) for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
            for m in [re.match(r'\s*SHOPIFY_ADMIN_TOKEN\s*=\s*"?(shpat_[A-Za-z0-9]+)', line)] if m]

def api(token, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method,
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())

def token_scopes(token):
    r = urllib.request.Request(f"https://{STORE}/admin/oauth/access_scopes.json",
        headers={"X-Shopify-Access-Token": token})
    with urllib.request.urlopen(r) as resp:
        return [s["handle"] for s in json.loads(resp.read())["access_scopes"]]

TOKEN = next((t for t in candidate_tokens() if "write_products" in token_scopes(t)), None)
assert TOKEN, "pas de token write_products"
print(f"token {TOKEN[:10]}...")

# Récupérer les produits de la collection (id par handle)
cols = api(TOKEN, "GET", "/custom_collections.json?handle=boutique-adherents")["custom_collections"] \
     or api(TOKEN, "GET", "/smart_collections.json?handle=boutique-adherents")["smart_collections"]
col_id = cols[0]["id"]
print("collection id:", col_id)

prods, page = [], None
while True:
    path = f"/products.json?collection_id={col_id}&limit=250&fields=id,handle,tags,variants"
    if page: path += f"&page_info={page}"
    data = api(TOKEN, "GET", path)
    prods += data["products"]
    if len(data["products"]) < 250: break
    time.sleep(0.4)
print("produits:", len(prods))

changed = 0
for p in prods:
    tags = [t.strip().lower() for t in (p.get("tags") or "").split(",")]
    want = "deny" if "no-backorder" in tags else "continue"
    for v in p["variants"]:
        if v.get("inventory_policy") != want:
            api(TOKEN, "PUT", f"/variants/{v['id']}.json",
                {"variant": {"id": v["id"], "inventory_policy": want}})
            changed += 1
            time.sleep(0.4)
print(f"variantes mises à jour : {changed}")
```

- [ ] **Step 2 : Lancer**

Run: `python scripts/shopify/set_backorder_policy.py`
Expected : affiche la collection id, ~73 produits, et le nombre de variantes passées en `continue`.

- [ ] **Step 3 : Vérifier sur une rupture**

Run (remplacer par un produit réellement en rupture) :
`curl -s "https://mylab-shop.com/products/<handle-oos>.js" | python -c "import sys,json;d=json.load(sys.stdin);print('available',d['variants'][0]['available'])"`
Expected : `available True` (car continue) même en rupture → confirme que le backorder est autorisé.

- [ ] **Step 4 : Commit**

```bash
git add scripts/shopify/set_backorder_policy.py
git commit -m "feat(rupture): script inventory_policy=continue (backorder) sauf no-backorder"
```

---

## Task 1 : Backend capture — Airtable + webhook n8n

**Files:** Airtable table (MCP), n8n workflow (MCP). Pas de fichier repo (le workflow est géré côté n8n ; en noter l'ID dans le commit message de Task 2).

- [ ] **Step 1 : Créer la table Airtable `back-in-stock`**

Via MCP Airtable : dans la base MyLab (rechercher la base via `search_bases`), créer une table `back-in-stock` avec les champs :
- `email` (singleLineText)
- `handle` (singleLineText)
- `variant_id` (singleLineText)
- `product_title` (singleLineText)
- `status` (singleSelect: `pending`, `notified`)
- `created_at` (dateTime)

Noter le `baseId` et `tableId`.

- [ ] **Step 2 : Créer le workflow n8n `back-in-stock-capture`**

Via MCP n8n (suivre le SDK reference). Nodes :
1. **Webhook** (POST, path `back-in-stock-capture`) — reçoit `{ email, handle, variant_id, product_title }`.
2. **Code/Set** — valider email (regex simple) ; si invalide → répondre 400.
3. **Airtable Search** — chercher une ligne `email = {{email}} AND variant_id = {{variant_id}}` dans `back-in-stock`.
4. **IF** existe → ne rien créer (dédup) ; sinon **Airtable Create** `{email, handle, variant_id, product_title, status:"pending", created_at: now}`.
5. **Respond to Webhook** — 200 `{ ok: true }` (CORS : header `Access-Control-Allow-Origin: *`).

Placer le workflow dans le folder Yo (id `Z2t5yT17QDhgf2XO`, cf. convention). Activer. **Noter l'URL de production du webhook.**

- [ ] **Step 3 : Tester le webhook**

Run (remplacer URL) :
```bash
curl -s -X POST "<webhook-url>" -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","handle":"x","variant_id":"123","product_title":"Test"}'
```
Expected : `{"ok":true}` et une ligne `pending` apparaît dans Airtable. Relancer → pas de doublon.

---

## Task 2 : Global thème + modale prévenez-moi

**Files:**
- Modify: `config/settings_schema.json`, `config/settings_data.json`
- Modify: `layout/theme.liquid` (l.109)
- Create: `snippets/ml-notify-modal.liquid`, `assets/ml-notify.js`, `assets/ml-notify.css`

- [ ] **Step 1 : Ajouter le réglage `notify_webhook_url`**

Dans `config/settings_schema.json`, ajouter un nouvel objet dans le tableau racine (après le bloc `theme_info`, ou à la fin du tableau avant `]`) :

```json
,{
  "name": "MyLab — Back in stock",
  "settings": [
    { "type": "url", "id": "notify_webhook_url", "label": "Webhook n8n capture prévenez-moi" }
  ]
}
```

Dans `config/settings_data.json`, sous `"current": { ... }`, ajouter la clé avec l'URL réelle du webhook (Task 1 Step 2) :

```json
"notify_webhook_url": "<webhook-url-n8n>"
```

- [ ] **Step 2 : Exposer le global + charger les assets**

Dans `layout/theme.liquid`, après la ligne 109 (`window.MylabAssets = …`), ajouter :

```liquid
    <script>window.MlNotify = { webhook: {{ settings.notify_webhook_url | default: '' | json }} };</script>
    {{ 'ml-notify.css' | asset_url | stylesheet_tag }}
    <script src="{{ 'ml-notify.js' | asset_url }}" defer="defer"></script>
```

Et juste avant `</body>` (l.270), rendre la modale globale :

```liquid
    {% render 'ml-notify-modal' %}
```

- [ ] **Step 3 : Créer la modale `snippets/ml-notify-modal.liquid`**

```liquid
{%- comment -%} Modale « Prévenez-moi du retour en stock » — ouverte par ml-notify.js {%- endcomment -%}
<div class="ml-notify" id="ml-notify" inert aria-hidden="true">
  <div class="ml-notify__overlay" data-ml-notify-close></div>
  <div class="ml-notify__dialog" role="dialog" aria-modal="true" aria-labelledby="ml-notify-title">
    <button type="button" class="ml-notify__x" data-ml-notify-close aria-label="Fermer">&times;</button>
    <h2 class="ml-notify__title" id="ml-notify-title">Prévenez-moi du retour en stock</h2>
    <p class="ml-notify__sub" id="ml-notify-prod"></p>
    <form class="ml-notify__form" id="ml-notify-form">
      <input type="email" class="ml-notify__input" id="ml-notify-email" placeholder="votre@email.com" required>
      <input type="hidden" id="ml-notify-handle">
      <input type="hidden" id="ml-notify-variant">
      <button type="submit" class="ml-notify__submit">Me prévenir</button>
    </form>
    <p class="ml-notify__msg" id="ml-notify-msg" role="status"></p>
  </div>
</div>
```

- [ ] **Step 4 : Créer `assets/ml-notify.css`**

```css
/* Modale prévenez-moi */
.ml-notify { position: fixed; inset: 0; z-index: 9999; display: none; }
.ml-notify.is-open { display: block; }
.ml-notify__overlay { position: absolute; inset: 0; background: rgba(0,0,0,.45); }
.ml-notify__dialog { position: relative; max-width: 420px; margin: 12vh auto 0; background: #fff;
  border-radius: 14px; padding: 28px 24px; font-family: 'DM Sans', sans-serif; }
.ml-notify__x { position: absolute; top: 10px; right: 14px; border: none; background: none; font-size: 24px; cursor: pointer; color: #888; }
.ml-notify__title { font-size: 1.9rem; font-weight: 700; margin: 0 0 6px; color: #111; }
.ml-notify__sub { font-size: 1.3rem; color: #666; margin: 0 0 16px; }
.ml-notify__input { width: 100%; padding: 12px 14px; font-size: 1.4rem; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 12px; font-family: inherit; }
.ml-notify__submit { width: 100%; padding: 13px; font-size: 1.3rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: #fff; background: #111; border: none; border-radius: 50px; cursor: pointer; }
.ml-notify__submit:disabled { background: #ccc; }
.ml-notify__msg { font-size: 1.25rem; margin: 12px 0 0; text-align: center; }
.ml-notify__msg.is-ok { color: #2D4A2D; }
.ml-notify__msg.is-err { color: #8B1A1A; }

/* Bandeau rupture (fiche produit) */
.ml-oos-banner { display: flex; align-items: center; gap: 8px; padding: 12px 14px; margin: 0 0 16px;
  background: #fff7ed; border: 1px solid #fde6c8; border-radius: 8px; font-size: 1.25rem; color: #6b4517; }
.ml-notify-link { display: inline-block; margin-top: 10px; font-size: 1.25rem; color: #555; text-decoration: underline; cursor: pointer; background: none; border: none; padding: 0; font-family: inherit; }
```

- [ ] **Step 5 : Créer `assets/ml-notify.js`**

```javascript
'use strict';
/* Modale « prévenez-moi » — ouverte via [data-ml-notify-open] avec data-handle/-variant/-title.
   POST vers window.MlNotify.webhook. Dégrade : si pas de webhook, les déclencheurs sont masqués
   par les surfaces appelantes (elles testent window.MlNotify.webhook avant d'afficher le bouton). */
(function () {
  var modal = document.getElementById('ml-notify');
  if (!modal) return;
  var emailEl = document.getElementById('ml-notify-email');
  var handleEl = document.getElementById('ml-notify-handle');
  var variantEl = document.getElementById('ml-notify-variant');
  var prodEl = document.getElementById('ml-notify-prod');
  var msgEl = document.getElementById('ml-notify-msg');
  var form = document.getElementById('ml-notify-form');

  function open(data) {
    handleEl.value = data.handle || '';
    variantEl.value = data.variant || '';
    prodEl.textContent = data.title || '';
    msgEl.textContent = ''; msgEl.className = 'ml-notify__msg';
    modal.classList.add('is-open'); modal.removeAttribute('inert'); modal.setAttribute('aria-hidden', 'false');
    setTimeout(function () { emailEl.focus(); }, 50);
  }
  function close() {
    modal.classList.remove('is-open'); modal.setAttribute('inert', ''); modal.setAttribute('aria-hidden', 'true');
  }

  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-ml-notify-open]');
    if (trigger) {
      e.preventDefault();
      open({ handle: trigger.dataset.handle, variant: trigger.dataset.variant, title: trigger.dataset.title });
    }
    if (e.target.closest('[data-ml-notify-close]')) close();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var webhook = (window.MlNotify && window.MlNotify.webhook) || '';
    if (!webhook) { msgEl.textContent = 'Indisponible pour le moment.'; msgEl.className = 'ml-notify__msg is-err'; return; }
    var btn = form.querySelector('.ml-notify__submit');
    btn.disabled = true;
    fetch(webhook, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: emailEl.value, handle: handleEl.value, variant_id: variantEl.value, product_title: prodEl.textContent })
    })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function () {
      msgEl.textContent = 'C’est noté ! Vous serez prévenu(e) dès le retour en stock.';
      msgEl.className = 'ml-notify__msg is-ok';
      form.reset();
      setTimeout(close, 2200);
    })
    .catch(function () {
      msgEl.textContent = 'Erreur — réessayez.'; msgEl.className = 'ml-notify__msg is-err';
    })
    .finally(function () { btn.disabled = false; });
  });

  window.MlNotifyOpen = open;
})();
```

- [ ] **Step 6 : Commit**

```bash
git add config/settings_schema.json config/settings_data.json layout/theme.liquid snippets/ml-notify-modal.liquid assets/ml-notify.js assets/ml-notify.css
git commit -m "feat(rupture): modale prevenez-moi globale + global window.MlNotify (webhook n8n <ID>)"
```

---

## Task 3 : Fiche produit — bandeau rupture + CTA backorder + prévenez-moi

**Files:** Modify `sections/main-product.liquid`, `assets/mylab-product.js`

- [ ] **Step 1 : Calculer les flags OOS/backorder + data-attrs sur le root**

Dans `sections/main-product.liquid`, remplacer la ligne 705 par un calcul Liquid + data-attrs :

```liquid
            {%- liquid
              assign ml_v = product.variants.first
              assign ml_oos = false
              if ml_v.inventory_management == 'shopify' and ml_v.inventory_quantity <= 0
                assign ml_oos = true
              endif
              assign ml_backorder = true
              if product.tags contains 'no-backorder'
                assign ml_backorder = false
              endif
            -%}
            <div data-mylab-pricing data-product-handle="{{ product.handle }}" data-oos="{{ ml_oos }}" data-backorder="{{ ml_backorder }}" {{ block.shopify_attributes }}>
```

- [ ] **Step 2 : Ajouter le bandeau rupture + bouton prévenez-moi dans le CTA**

Dans le bloc CTA (l.793-800), remplacer par :

```liquid
              {%- comment -%} ====== CTA ====== {%- endcomment -%}
              {%- if ml_oos -%}
                <div class="ml-oos-banner">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  <span>{% if ml_backorder %}En rupture — expédié dès réapprovisionnement.{% else %}Produit momentanément en rupture.{% endif %}</span>
                </div>
              {%- endif -%}
              <div class="ml-cta">
                <button class="ml-btn-cart" id="ml-btn-cart"
                        data-variant-id="{{ product.variants.first.id }}"
                        aria-label="Ajouter au panier">
                  <span class="ml-btn-cart__text">{% if ml_oos and ml_backorder %}Commander et recevoir dès retour en stock{% else %}Ajouter au panier{% endif %}</span>
                  <span class="ml-btn-cart__pill" id="ml-cart-pill">—</span>
                </button>
                {%- if ml_oos -%}
                  <button type="button" class="ml-notify-link" data-ml-notify-open
                          data-handle="{{ product.handle }}" data-variant="{{ product.variants.first.id }}" data-title="{{ product.title | escape }}">
                    {% if ml_backorder %}Ou être prévenu du retour{% else %}Prévenez-moi du retour{% endif %}
                  </button>
                {%- endif -%}
              </div>
```

- [ ] **Step 3 : JS — masquer le bouton panier si rupture non-backorderable**

Dans `assets/mylab-product.js`, fonction `initBlock`, après `var cartBtn = q(root, '#ml-btn-cart');` (~l.228), ajouter :

```javascript
    var isOos = root.dataset.oos === 'true';
    var canBackorder = root.dataset.backorder === 'true';
    if (isOos && !canBackorder && cartBtn) {
      cartBtn.style.display = 'none';
    }
```

(Le bouton prévenez-moi est déjà câblé par `ml-notify.js` via `[data-ml-notify-open]`. En backorder, le bouton panier reste fonctionnel — l'ajout marche car `inventory_policy=continue`.)

- [ ] **Step 4 : Vérifier la syntaxe JS**

Run: `node --check assets/mylab-product.js`
Expected : aucune sortie d'erreur.

- [ ] **Step 5 : Commit**

```bash
git add sections/main-product.liquid assets/mylab-product.js
git commit -m "feat(rupture): fiche produit — bandeau + CTA backorder + bouton prevenez-moi"
```

---

## Task 4 : Boutique pro — badges « Sur commande » / « Rupture »

**Files:** Modify `sections/ml-collection-filterable.liquid`

- [ ] **Step 1 : Calculer le badge dans la boucle + l'injecter dans le `<li>`**

Dans `sections/ml-collection-filterable.liquid`, remplacer le `<li …>` + render (l.117-132) par :

```liquid
          {%- liquid
            assign cv = product.variants.first
            assign card_oos = false
            if cv.inventory_management == 'shopify' and cv.inventory_quantity <= 0
              assign card_oos = true
            endif
            assign card_backorder = true
            if product.tags contains 'no-backorder'
              assign card_backorder = false
            endif
          -%}
          <li class="flex-grid__item{% if card_oos %} ml-card-oos{% endif %}" data-tags="{{ product_tags_handleized }}">
            {%- if card_oos -%}
              <span class="ml-card-badge {% if card_backorder %}ml-card-badge--backorder{% else %}ml-card-badge--oos{% endif %}">
                {% if card_backorder %}Sur commande{% else %}Rupture{% endif %}
              </span>
            {%- endif -%}
            {% render 'card-product',
              card_product: product,
              card_collection: collection,
              media_size: section.settings.image_ratio,
              show_secondary_image: section.settings.show_secondary_image,
              show_vendor: false,
              show_rating: false,
              show_quick_buy: section.settings.show_quick_buy,
              enable_quick_view: section.settings.enable_quick_view,
              enable_color_swatches: false,
              enable_countdown: false,
              enable_image_fill: section.settings.enable_image_fill,
              section_id: section.id
            %}
          </li>
```

- [ ] **Step 2 : Ajouter les styles du badge**

Dans le `<style>` de la section (après les règles `.ml-filterable .card …`, vers la ligne 50), ajouter :

```liquid
  .ml-filterable .flex-grid__item { position: relative; }
  .ml-card-badge { position: absolute; top: 10px; left: 10px; z-index: 2; padding: 5px 11px;
    font-size: 11px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
    border-radius: 50px; font-family: 'DM Sans', sans-serif; }
  .ml-card-badge--backorder { background: #fff0dc; color: #8a3a00; border: 1px solid #ffd9a8; }
  .ml-card-badge--oos { background: #f2f2f2; color: #888; border: 1px solid #e0e0e0; }
```

- [ ] **Step 3 : Commit**

```bash
git add sections/ml-collection-filterable.liquid
git commit -m "feat(rupture): boutique pro — badges Sur commande / Rupture"
```

---

## Task 5 : Commande express — backorder vs no-backorder

**Files:** Modify `sections/ml-quick-order.liquid`, `snippets/ml-qo-row.liquid`

- [ ] **Step 1 : Rendre les maps `MlOos` / `MlNoBackorder` (Liquid)**

Dans `sections/ml-quick-order.liquid`, juste avant `<script src="{{ 'ml-utils.js' | asset_url }}"></script>` (l.443), insérer :

```liquid
    <script>
      window.MlOos = {};
      window.MlNoBackorder = {};
      {%- for product in collection.products -%}
        {%- assign qv = product.variants.first -%}
        {%- if qv.inventory_management == 'shopify' and qv.inventory_quantity <= 0 -%}
          window.MlOos[{{ product.handle | json }}] = true;
        {%- endif -%}
        {%- if product.tags contains 'no-backorder' -%}
          window.MlNoBackorder[{{ product.handle | json }}] = true;
        {%- endif -%}
      {%- endfor -%}
    </script>
```

- [ ] **Step 2 : Helper d'état rupture + style tag**

Dans le `<style>` de la section (après `.ml-qo__oos-badge`), ajouter :

```css
  .ml-qo__backorder-tag { display: inline-block; margin-top: 3px; padding: 2px 8px; font-size: 1rem;
    font-weight: 600; color: #8a3a00; background: #fff0dc; border: 1px solid #ffd9a8; border-radius: 50px; }
  .ml-qo__notify-link { display: inline-block; margin-top: 3px; font-size: 1.05rem; color: #555; text-decoration: underline; }
```

Dans le script IIFE, ajouter en haut (après `var U = window.MylabUtils;`) :

```javascript
        function mlIsOos(handle) { return !!(window.MlOos && window.MlOos[handle]); }
        function mlNoBackorder(handle) { return !!(window.MlNoBackorder && window.MlNoBackorder[handle]); }
```

- [ ] **Step 3 : Remplacer la décision OOS par la logique backorder (lignes de base)**

Dans `U.loadProductMap().then`, la boucle `rows.forEach` : aujourd'hui `populateSelect` appelle `applyOosTreatment` si `data-available==='false'`. On bascule sur les maps. Remplacer la fonction `populateSelect` (l.595-614) par :

```javascript
        function populateSelect(tr, tierStr) {
          var handle = tr.dataset.handle;
          if (mlIsOos(handle) && mlNoBackorder(handle)) {
            applyOosTreatment(tr);
            appendNotifyLink(tr);
            return;
          }
          var select = tr.querySelector('[data-qo-qty]');
          if (!select) return;
          select.innerHTML = '<option value="0">—</option>';
          tierStr.split(',').forEach(function (t) {
            var p = t.split(':');
            var opt = document.createElement('option');
            opt.value = p[0]; opt.dataset.price = p[1];
            opt.textContent = p[0] + ' unités';
            select.appendChild(opt);
          });
          tr.setAttribute('data-tier-data', tierStr);
          if (mlIsOos(handle)) appendBackorderTag(tr);
        }
```

Ajouter les deux helpers avant `populateSelect` :

```javascript
        function appendBackorderTag(tr) {
          var nameCell = tr.querySelector('.ml-qo__product-variant');
          if (nameCell && !tr.querySelector('.ml-qo__backorder-tag')) {
            nameCell.insertAdjacentHTML('afterend', '<span class="ml-qo__backorder-tag">sur commande</span>');
          }
        }
        function appendNotifyLink(tr) {
          var nameCell = tr.querySelector('.ml-qo__product-variant');
          if (nameCell && !tr.querySelector('.ml-qo__notify-link')) {
            nameCell.insertAdjacentHTML('afterend',
              '<a class="ml-qo__notify-link" href="/products/' + tr.dataset.handle + '">Prévenez-moi →</a>');
          }
        }
```

- [ ] **Step 4 : Même logique pour les lignes liées (`buildLinkedRow`)**

Dans `buildLinkedRow`, l'OOS est aujourd'hui basé sur `firstVar.available === false`. Comme `available` reste vrai en `continue`, on bascule sur les maps via le `handle`. Remplacer le calcul `var isOos = firstVar.available === false;` (l.622) par :

```javascript
          var handle = product.handle;
          var isOosNoBack = mlIsOos(handle) && mlNoBackorder(handle);
          var isBackorder = mlIsOos(handle) && !mlNoBackorder(handle);
          var isOos = isOosNoBack; /* grisé seulement si pas de backorder */
```

Puis, dans le HTML retourné, ajouter le tag backorder sous la variante. Remplacer la portion `'<div class="ml-qo__product-variant">' + sizeLabel + 'ml</div>'` par :

```javascript
            + '<div class="ml-qo__product-variant">' + sizeLabel + 'ml</div>'
            + (isBackorder ? '<span class="ml-qo__backorder-tag">sur commande</span>' : '')
            + (isOosNoBack ? '<a class="ml-qo__notify-link" href="/products/' + handle + '">Prévenez-moi →</a>' : '')
```

(Le reste de `buildLinkedRow` — `qtyCell`, badge OOS — reste piloté par `isOos`, qui ne vaut plus `true` que pour les no-backorder.)

- [ ] **Step 5 : Vérifier la syntaxe JS**

Run:
```bash
python -c "import re,pathlib,subprocess,tempfile,os; t=pathlib.Path('sections/ml-quick-order.liquid').read_text(encoding='utf-8'); js=re.findall(r'<script>\s*\n(.*?)</script>', t, re.S)[-1]; f=tempfile.NamedTemporaryFile('w',suffix='.js',delete=False,encoding='utf-8'); f.write(js); f.close(); r=subprocess.run(['node','--check',f.name],capture_output=True,text=True); print('OK' if r.returncode==0 else r.stderr); os.unlink(f.name)"
```
Expected : `OK`

- [ ] **Step 6 : Commit**

```bash
git add sections/ml-quick-order.liquid snippets/ml-qo-row.liquid
git commit -m "feat(rupture): commande express — backorder (sur commande) + lien prevenez-moi"
```

---

## Task 6 : Push dev + revue + QA

- [ ] **Step 1 : Push dev**

Run:
```bash
shopify theme push --store mylab-shop-3.myshopify.com --development --nodelete --only config/settings_schema.json,config/settings_data.json,layout/theme.liquid,snippets/ml-notify-modal.liquid,assets/ml-notify.js,assets/ml-notify.css,sections/main-product.liquid,assets/mylab-product.js,sections/ml-collection-filterable.liquid,sections/ml-quick-order.liquid,snippets/ml-qo-row.liquid
```
⚠️ Vérifier que les fichiers ont **réellement** été uploadés (le `--only` du CLI peut reporter un succès sans upload — cf. mémoire). Sinon, PUT via Admin API (pattern Task 1 pompes).

- [ ] **Step 2 : QA navigateur (client `dossier-valide`, thème dev)**

Choisir un produit réellement en rupture (ou mettre une variante à 0 en dev) :
1. Fiche backorderable → bandeau « expédié dès réapprovisionnement », CTA « Commander et recevoir dès retour en stock », ajout panier OK, lien « Ou être prévenu » → modale → email → ligne Airtable.
2. Fiche `no-backorder` → pas d'ajout, bouton « Prévenez-moi » seul → modale OK.
3. Boutique pro → badge « Sur commande » vs « Rupture ».
4. Commande express → ligne backorderable commandable + « sur commande » ; ligne no-backorder grisée + « Prévenez-moi → ».
5. Produit en stock → comportement inchangé partout.

- [ ] **Step 3 : Revue subagents (spec + qualité) sur le diff, corriger les blockers.**

- [ ] **Step 4 : Décision PUSH LIVE explicite par Yoann uniquement.**

---

## Self-Review (couverture spec)

- ✅ `inventory_policy=continue` sauf `no-backorder` → Task 0.
- ✅ Détection rupture par `inventory_quantity` (continue → available vrai) → Tasks 3/4/5 (Liquid) + map `MlOos` → Task 5.
- ✅ Fiche : bandeau + CTA backorder « Commander et recevoir dès retour en stock » + prévenez-moi → Task 3.
- ✅ Boutique pro : badges Sur commande / Rupture → Task 4.
- ✅ Commande express : backorder commandable + tag, no-backorder grisé + lien → Task 5.
- ✅ Capture prévenez-moi → webhook n8n → Airtable → Tasks 1 + 2.
- ✅ Dégradation : webhook vide → bouton masqué (le déclencheur ne POST pas ; ml-notify.js affiche « indisponible » — note : le bouton fiche est rendu en Liquid indépendamment ; si tu veux le masquer quand webhook vide, le wrap `{% if settings.notify_webhook_url != blank %}` — **ajouté ci-dessous**).
- ✅ Pas de date promise (message générique).
- ✅ SP2 (email auto) hors scope.

### Correctif self-review — masquer prévenez-moi si webhook absent
Dans Task 3 Step 2 et Task 5 Step 3/4, envelopper les déclencheurs prévenez-moi par une garde. Sur la fiche (Liquid) :
```liquid
{%- if ml_oos and settings.notify_webhook_url != blank -%} … bouton prévenez-moi … {%- endif -%}
```
En commande express (JS), garder `appendNotifyLink` derrière `if (window.MlNotify && window.MlNotify.webhook)`.
