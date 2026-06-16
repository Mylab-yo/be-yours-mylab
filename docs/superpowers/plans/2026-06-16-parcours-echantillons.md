# Parcours « commander des échantillons » — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une sortie de secours dans le panier bloqué (drawer + page /cart) qui retire les articles de création de marque et redirige le client vers la boutique testeurs.

**Architecture:** Un snippet Liquid partagé calcule les `line keys` des articles marque-création et rend un lien à confirmation inline ; un handler JS (délégation d'événement) retire ces lignes via `/cart/update.js` puis redirige. Les deux sections panier (`mini-cart.liquid`, `main-cart-footer.liquid`) rendent le snippet sous leur CTA, conditionné à `ml_checkout_blocked`.

**Tech Stack:** Shopify Liquid (sections + snippet), vanilla JS IIFE (`mylab-cart.js`), CSS (`mylab-product.css`). Pas de build, pas de test runner — vérification manuelle navigateur. Déploiement via REST PUT (token `shpat_bb6245…`, thème dev `#198049268046` puis live `#184014340430`).

Spec de référence : `docs/superpowers/specs/2026-06-16-parcours-echantillons-design.md`

---

## Structure des fichiers

| Fichier | Responsabilité |
|---------|----------------|
| `snippets/ml-sample-exit.liquid` (créer) | Markup + calcul des line keys marque-création. Rend vide si non bloqué. |
| `assets/mylab-product.css` (modifier) | Styles `.ml-sample-exit*` (DM Sans, discret). Chargé globalement. |
| `assets/mylab-cart.js` (modifier) | Handler clic : confirm inline → `/cart/update` → redirect. |
| `sections/mini-cart.liquid` (modifier) | Rendre le snippet dans `.mini-cart__footer` sous le bouton. |
| `sections/main-cart-footer.liquid` (modifier) | Rendre le snippet sous `.cart__ctas`. |

Critères « article marque-création » (retiré du panier) :
- handle == `creation-du-dossier-cosmetologique`
- handle contient `impression` (forfait)
- handle == `frais-de-creation-design-etiquette`
- produit dans la collection `boutique-adherents` ou `modeles-detiquettes`

---

### Task 1 : Snippet `ml-sample-exit.liquid`

**Files:**
- Create: `snippets/ml-sample-exit.liquid`

- [ ] **Step 1 : Créer le snippet**

```liquid
{%- comment -%}
  Sortie « commander des échantillons » depuis le panier bloqué.
  Param: blocked (bool) — ne rend rien si faux.
  Calcule les line keys des articles marque-création (dossier + produits pro +
  forfait impression + étiquettes), les expose en data-attribute pour retrait JS,
  et redirige vers la boutique testeurs.
  Spec: docs/superpowers/specs/2026-06-16-parcours-echantillons-design.md
{%- endcomment -%}
{%- if blocked -%}
  {%- assign ml_remove_keys = '' -%}
  {%- for item in cart.items -%}
    {%- assign ml_is_mc = false -%}
    {%- if item.product.handle == 'creation-du-dossier-cosmetologique' -%}{%- assign ml_is_mc = true -%}{%- endif -%}
    {%- if item.product.handle contains 'impression' -%}{%- assign ml_is_mc = true -%}{%- endif -%}
    {%- if item.product.handle == 'frais-de-creation-design-etiquette' -%}{%- assign ml_is_mc = true -%}{%- endif -%}
    {%- for col in item.product.collections -%}
      {%- if col.handle == 'boutique-adherents' or col.handle == 'modeles-detiquettes' -%}{%- assign ml_is_mc = true -%}{%- endif -%}
    {%- endfor -%}
    {%- if ml_is_mc -%}
      {%- if ml_remove_keys == '' -%}
        {%- assign ml_remove_keys = item.key -%}
      {%- else -%}
        {%- assign ml_remove_keys = ml_remove_keys | append: ',' | append: item.key -%}
      {%- endif -%}
    {%- endif -%}
  {%- endfor -%}
  <div class="ml-sample-exit" data-ml-remove-keys="{{ ml_remove_keys }}" data-ml-redirect="/pages/boutique-testeurs">
    <a href="/pages/boutique-testeurs" class="ml-sample-exit__link" data-ml-sample-trigger>
      Vous vouliez seulement tester nos produits&nbsp;?
      <span class="ml-sample-exit__cta">Commander des échantillons&nbsp;&rarr;</span>
    </a>
    <div class="ml-sample-exit__confirm" hidden>
      <p class="ml-sample-exit__msg">Cela retirera vos produits pro du panier.</p>
      <div class="ml-sample-exit__actions">
        <button type="button" class="ml-sample-exit__go" data-ml-sample-confirm>Voir les testeurs</button>
        <button type="button" class="ml-sample-exit__cancel" data-ml-sample-cancel>Annuler</button>
      </div>
      <p class="ml-sample-exit__error" hidden>Une erreur est survenue, réessayez.</p>
    </div>
  </div>
{%- endif -%}
```

- [ ] **Step 2 : Vérifier**

Relire le fichier : balises ouvrantes/fermantes équilibrées, le `href` du lien pointe vers `/pages/boutique-testeurs` (fallback no-JS), `data-ml-remove-keys` présent sur le conteneur.

- [ ] **Step 3 : Commit**

```bash
git add snippets/ml-sample-exit.liquid
git commit -m "feat(echantillons): snippet sortie panier vers boutique testeurs"
```

---

### Task 2 : Styles `.ml-sample-exit`

**Files:**
- Modify: `assets/mylab-product.css` (ajouter à la fin)

- [ ] **Step 1 : Ajouter les styles en fin de fichier**

```css

/* ── Sortie « commander des échantillons » (panier bloqué) ── */
.ml-sample-exit {
  margin-top: 1.2rem;
  text-align: center;
  font-family: 'DM Sans', var(--font-body-family), sans-serif;
}
.ml-sample-exit__link {
  display: inline-block;
  font-size: 1.25rem;
  line-height: 1.4;
  color: rgba(var(--color-foreground), 0.7);
  text-decoration: none;
}
.ml-sample-exit__cta {
  font-weight: 600;
  color: #1a1a1a;
  text-decoration: underline;
  text-underline-offset: 2px;
  white-space: nowrap;
}
.ml-sample-exit__link:hover .ml-sample-exit__cta { color: #c5a467; }
.ml-sample-exit__confirm { margin-top: 0.4rem; }
.ml-sample-exit__msg {
  font-size: 1.2rem;
  color: rgba(var(--color-foreground), 0.7);
  margin: 0 0 0.6rem;
}
.ml-sample-exit__actions { display: flex; gap: 0.8rem; justify-content: center; }
.ml-sample-exit__go,
.ml-sample-exit__cancel {
  font-family: inherit;
  font-size: 1.2rem;
  font-weight: 600;
  padding: 0.6rem 1.4rem;
  border-radius: 50px;
  cursor: pointer;
  min-height: 40px;
}
.ml-sample-exit__go { background: #1a1a1a; color: #fff; border: 1px solid #1a1a1a; }
.ml-sample-exit__go[aria-busy="true"] { opacity: 0.6; cursor: wait; }
.ml-sample-exit__cancel { background: transparent; color: #1a1a1a; border: 1px solid rgba(0, 0, 0, 0.2); }
.ml-sample-exit__error { color: #b85c4e; font-size: 1.1rem; margin: 0.5rem 0 0; }
```

- [ ] **Step 2 : Commit**

```bash
git add assets/mylab-product.css
git commit -m "feat(echantillons): styles sortie panier testeurs"
```

---

### Task 3 : Handler JS

**Files:**
- Modify: `assets/mylab-cart.js` (ajouter dans l'IIFE, avant la fermeture `})();`)

- [ ] **Step 1 : Ajouter le handler en délégation d'événement**

Insérer ce bloc juste avant `})();` (la dernière ligne) de `assets/mylab-cart.js` :

```js
  /* -------------------------------------------------------
     SORTIE « COMMANDER DES ÉCHANTILLONS » (panier bloqué)
     1er clic sur le lien → confirmation inline
     Confirm → retire les articles marque-création via
     /cart/update.js puis redirige vers la boutique testeurs.
     ------------------------------------------------------- */
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-ml-sample-trigger]');
    if (trigger) {
      e.preventDefault();
      var box = trigger.closest('.ml-sample-exit');
      if (!box) return;
      trigger.hidden = true;
      var confirmEl = box.querySelector('.ml-sample-exit__confirm');
      if (confirmEl) confirmEl.hidden = false;
      return;
    }

    var cancel = e.target.closest('[data-ml-sample-cancel]');
    if (cancel) {
      var boxC = cancel.closest('.ml-sample-exit');
      if (!boxC) return;
      var confC = boxC.querySelector('.ml-sample-exit__confirm');
      var linkC = boxC.querySelector('[data-ml-sample-trigger]');
      if (confC) confC.hidden = true;
      if (linkC) linkC.hidden = false;
      return;
    }

    var go = e.target.closest('[data-ml-sample-confirm]');
    if (go) {
      e.preventDefault();
      var boxG = go.closest('.ml-sample-exit');
      if (!boxG) return;
      var redirect = boxG.getAttribute('data-ml-redirect') || '/pages/boutique-testeurs';
      var keysAttr = boxG.getAttribute('data-ml-remove-keys') || '';
      var keys = keysAttr.split(',').filter(Boolean);
      var errEl = boxG.querySelector('.ml-sample-exit__error');
      if (errEl) errEl.hidden = true;

      if (keys.length === 0) { window.location.href = redirect; return; }

      go.setAttribute('aria-busy', 'true');
      go.disabled = true;

      var updates = {};
      keys.forEach(function (k) { updates[k] = 0; });

      fetch('/cart/update.js', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates: updates })
      }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        window.location.href = redirect;
      }).catch(function () {
        go.removeAttribute('aria-busy');
        go.disabled = false;
        if (errEl) errEl.hidden = false;
      });
      return;
    }
  });
```

- [ ] **Step 2 : Vérifier**

Relire : le bloc est bien à l'intérieur de l'IIFE (avant `})();`), pas de collision de noms de variables avec le reste du fichier (`box`, `go`, `trigger` sont locaux au handler).

- [ ] **Step 3 : Commit**

```bash
git add assets/mylab-cart.js
git commit -m "feat(echantillons): handler retrait panier + redirect testeurs"
```

---

### Task 4 : Câbler dans le drawer (`mini-cart.liquid`)

**Files:**
- Modify: `sections/mini-cart.liquid` (entre la fermeture de `.button-container` ~ligne 1371 et la fermeture de `.mini-cart__footer` ~ligne 1372)

- [ ] **Step 1 : Insérer le render**

Remplacer :

```liquid
      </div>
    </div>
  </div>
</form>
```

par :

```liquid
      </div>
      {%- render 'ml-sample-exit', blocked: ml_checkout_blocked -%}
    </div>
  </div>
</form>
```

(Le premier `</div>` ferme `.button-container`, le `{%- render -%}` s'ajoute dans `.mini-cart__footer`. `ml_checkout_blocked` est déjà calculé plus haut dans la section.)

- [ ] **Step 2 : Vérifier**

`grep -n "ml-sample-exit" sections/mini-cart.liquid` → 1 occurrence, à l'intérieur du footer.

- [ ] **Step 3 : Commit**

```bash
git add sections/mini-cart.liquid
git commit -m "feat(echantillons): sortie testeurs dans le drawer bloque"
```

---

### Task 5 : Câbler dans la page panier (`main-cart-footer.liquid`)

**Files:**
- Modify: `sections/main-cart-footer.liquid` (après la fermeture de `.cart__ctas`, ligne 399)

- [ ] **Step 1 : Insérer le render après `.cart__ctas`**

Remplacer :

```liquid
              <button type="submit" class="cart__checkout-button button" name="checkout"{% if cart == empty or ml_checkout_blocked %} disabled aria-disabled="true"{% endif %} form="cart">
                {{ 'sections.cart.checkout' | t }}
              </button>
            </div>
```

par :

```liquid
              <button type="submit" class="cart__checkout-button button" name="checkout"{% if cart == empty or ml_checkout_blocked %} disabled aria-disabled="true"{% endif %} form="cart">
                {{ 'sections.cart.checkout' | t }}
              </button>
            </div>

            {%- render 'ml-sample-exit', blocked: ml_checkout_blocked -%}
```

- [ ] **Step 2 : Vérifier**

`grep -n "ml-sample-exit" sections/main-cart-footer.liquid` → 1 occurrence, sous le bloc `.cart__ctas`.

- [ ] **Step 3 : Commit**

```bash
git add sections/main-cart-footer.liquid
git commit -m "feat(echantillons): sortie testeurs sur la page panier"
```

---

### Task 6 : Déploiement + vérification end-to-end

**Files:** aucun (déploiement)

- [ ] **Step 1 : Déployer sur le thème de développement (#198049268046)**

Pousser les 5 fichiers via REST PUT (script Python type session drawer, token `shpat_bb6245…` lu depuis `.env.local`) OU :

```bash
shopify theme push --store mylab-shop-3.myshopify.com --theme 198049268046 --nodelete \
  --only snippets/ml-sample-exit.liquid,assets/mylab-product.css,assets/mylab-cart.js,sections/mini-cart.liquid,sections/main-cart-footer.liquid
```

Puis re-pull de contrôle (le `--only` peut no-op silencieusement) :
`shopify theme pull --store mylab-shop-3.myshopify.com --theme 198049268046 --only snippets/ml-sample-exit.liquid --path tmp/verify` et vérifier le contenu.

- [ ] **Step 2 : Vérification manuelle (preview thème dev, compte NON `dossier-valide`)**

1. Ajouter un produit `boutique-adherents` au panier → le dossier cosméto s'auto-ajoute → drawer passe à l'état bloqué.
2. La sortie « Commander des échantillons » apparaît sous le bouton « Passer la commande » désactivé.
3. Clic → la confirmation inline « Cela retirera vos produits pro… » s'affiche.
4. Clic « Annuler » → revient au lien.
5. Clic « Voir les testeurs » → spinner, le panier se vide des articles marque-création (les autres restent), redirection vers `/pages/boutique-testeurs`.
6. Vérifier que le dossier **ne revient pas** (pas de boucle gate) : rouvrir le panier après redirection.
7. Refaire le test sur la page `/cart` complète (mêmes étapes 2-6).

- [ ] **Step 3 : Promotion en live (#184014340430)**

Après validation sur dev, repousser les 5 mêmes fichiers sur le thème live via REST PUT, puis re-pull de contrôle d'un fichier. Re-save / toggle des sections si le cache de rendu ne se met pas à jour (note cache section connue).

- [ ] **Step 4 : Commit éventuel des JSON rapatriés**

Si un `shopify theme push` a été utilisé (rapatrie des JSON Theme Editor en local), `git restore` les JSON hors périmètre ; ne committer que les 5 fichiers voulus (déjà committés aux tâches 1-5).

---

## Self-review (couverture du spec)

- Déclencheur `ml_checkout_blocked` → snippet conditionné dessus (Task 1, câblé Tasks 4-5). ✓
- Emplacement drawer (footer sous CTA) → Task 4. ✓
- Emplacement page /cart → Task 5. ✓
- Confirmation inline 2 temps → snippet (confirm caché) + JS (toggle) Tasks 1, 3. ✓
- Articles retirés (dossier + pro + forfait + étiquettes) → critères snippet Task 1. ✓
- Retrait via `/cart/update.js {updates:{key:0}}` + redirect → JS Task 3. ✓
- Anti-boucle gate (retrait simultané, redirect avant 400 ms) → garanti par le retrait groupé Task 3. ✓
- Cas limites (dossier seul = non bloqué, échec réseau = pas de redirect) → snippet `if blocked` + JS `.catch`. ✓
- Styles DM Sans `ml-` → Task 2. ✓
- Déploiement dev→live + vérif manuelle → Task 6. ✓

Aucun placeholder. Noms cohérents (`data-ml-remove-keys`, `data-ml-redirect`, `data-ml-sample-trigger/confirm/cancel`, classes `.ml-sample-exit*`) entre snippet (Task 1), CSS (Task 2) et JS (Task 3).
