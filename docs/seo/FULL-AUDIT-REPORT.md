# MY.LAB Shop — Audit SEO Complet

**Site :** mylab-shop-3.myshopify.com
**Date :** 2026-03-29
**Business type :** B2B Cosmetics — White-label hair care manufacturer (Cavaillon, France)
**Total URLs :** 159 (sitemap) + 41 noindexed size variants

---

## SCORE GLOBAL SEO : 47 / 100

| Catégorie | Poids | Score | Pondéré |
|-----------|-------|-------|---------|
| Technical SEO | 22% | 52/100 | 11.4 |
| Content Quality (E-E-A-T) | 23% | 49/100 | 11.3 |
| On-Page SEO | 20% | 45/100 | 9.0 |
| Schema / Structured Data | 10% | 65/100* | 6.5 |
| Performance (CWV) | 10% | 55/100 | 5.5 |
| AI Search Readiness (GEO) | 10% | 38/100 | 3.8 |
| Local SEO | 5% | 38/100 | 1.9 |
| **TOTAL** | **100%** | | **49.4** |

*Score Schema remonté à 65 après les corrections automatiques de l'agent (Service, SearchAction, VideoObject, BreadcrumbList fix).

---

## TOP 5 PROBLÈMES CRITIQUES

1. **Double domaine concurrent** — `mylab-shop.com` (WordPress) et `mylab-shop-3.myshopify.com` (Shopify) sont deux sites séparés qui se concurrencent. Les canonicals Shopify pointent vers le sous-domaine myshopify, pas vers le domaine custom.

2. **Liens sociaux pointent vers Shopify** — Les 4 liens sociaux (Facebook, Instagram, Twitter, Pinterest) dans la config du thème pointent vers `facebook.com/shopify`, `instagram.com/shopify` etc. Cela se propage dans les schemas Organization et LocalBusiness (`sameAs`), les Twitter Cards (`@shopify`), et les meta OG.

3. **Meta descriptions manquantes (~30% des pages)** — Aucune meta description sur les collections, plusieurs pages clés sans description. Le theme.liquid ne rend la balise que si `page_description` est défini dans l'admin.

4. **Image hero chargée en lazy + fetchpriority:low** — Le slideshow charge la première image visible avec `loading: 'lazy'` et `fetchpriority: 'low'`, ajoutant 2-4 secondes au LCP mobile.

5. **FAQ contient du contenu placeholder Dr. Barbara Sturm** — Les 6 Q&A de la page FAQ sont du texte demo Be Yours, pas du contenu MY.LAB. Le FAQPage schema génère du JSON-LD pour une marque étrangère.

---

## TOP 5 QUICK WINS

1. **Fix image hero loading** (`slideshow.liquid`) → LCP -2-3s (1 ligne de code)
2. **Charger mylab-product.css uniquement sur les pages produit** → -22KB render-blocking sur toutes les autres pages (1 ligne)
3. **Ajouter min-height aux conteneurs dynamiques** → CLS fix (2 lignes CSS)
4. **Ajouter openingHoursSpecification au schema LocalBusiness** → Local pack eligibility
5. **Corriger l'email NAP** (.com partout au lieu du mix .com/.fr)

---

## DÉTAIL PAR CATÉGORIE

### 1. Technical SEO — 52/100

| Sous-catégorie | Score | Statut |
|----------------|-------|--------|
| Crawlability | 72/100 | PASS |
| Indexability | 45/100 | FAIL — double domaine, meta desc manquantes |
| Security | 92/100 | PASS — HTTPS, HSTS, CSP, headers complets |
| URL Structure | 68/100 | OK — 1 typo URL "profesionnel" |
| Mobile | 82/100 | PASS — viewport, responsive, srcset |
| JS Rendering | 58/100 | WARN — pricing invisible aux crawlers |

**Problème majeur :** Le site WordPress sur `mylab-shop.com` est un site complètement séparé qui entre en concurrence avec le Shopify. Les collections retournent 404 sur WordPress. Il faut pointer le DNS vers Shopify OU mettre en place des canonical cross-domain.

### 2. Content Quality — 49/100

| Dimension E-E-A-T | Score |
|--------------------|-------|
| Experience | 52/100 |
| Expertise | 45/100 |
| Authoritativeness | 40/100 |
| Trustworthiness | 48/100 |

**Problèmes clés :**
- FAQ = placeholder d'une autre marque (Dr. Sturm) → **score FAQ : 5/100**
- Aucun blog (0 articles publiés)
- Pas de page "À propos" dédiée avec fondateur, équipe, certifications
- Témoignages homepage probablement fabriqués ("Sophie M.", "Marc D." — pas de photos ni liens)
- Product pages thin content (pricing tiers rendus en JS, invisibles aux crawlers)
- Page étapes création = la meilleure page du site (72/100)

### 3. Schema / Structured Data — 65/100 (post-fix)

**Déjà présent :**
- LocalBusiness (complet avec adresse, tel, email, geo)
- Organization (header.liquid)
- WebSite + SearchAction (ajouté par l'agent)
- Service (ajouté par l'agent)
- BreadcrumbList (corrigé — plus de doublon)
- FAQPage (fonctionne mais contenu placeholder)
- Product (natif Shopify)
- VideoObject x3 (ajouté par l'agent)

**Corrections appliquées par l'agent Schema :**
- Image URL protocol-relative → https
- sameAs array logic (anti trailing commas)
- BreadcrumbList duplicate éliminé
- SearchAction ajouté au WebSite
- Service schema ajouté (7 gammes produit)
- VideoObject pour les 3 témoignages vidéo

**Encore manquant :**
- HowTo (page étapes création)
- AggregateRating (pas de reviews)
- openingHoursSpecification dans LocalBusiness
- ContactPage type
- ItemList pour le catalogue

### 4. Performance (CWV) — 55/100 (estimé mobile)

| Métrique | Estimation | Cible | Statut |
|----------|-----------|-------|--------|
| LCP | 4.0-6.0s | ≤2.5s | FAIL |
| INP | 200-350ms | ≤200ms | WARN |
| CLS | 0.10-0.20 | ≤0.1 | WARN |

**Causes principales :**
- Hero image en `lazy` + `fetchpriority: low` (LCP killer)
- `mylab-product.css` (22KB) chargé sur TOUTES les pages
- `global.js` (109KB non minifié) — monolithe de 45 custom elements
- `ml-dossier-gate.js` monkey-patch `window.fetch()` sur toutes les pages
- Conteneurs dynamiques sans min-height (CLS)
- Transition overlay `.transition-cover` bloque le rendu LCP

### 5. AI Search Readiness (GEO) — 38/100

| Dimension | Score |
|-----------|-------|
| Citability | 35/100 |
| Structural Readability | 52/100 |
| Multi-Modal Content | 22/100 |
| Authority & Brand Signals | 28/100 |
| Technical Accessibility | 50/100 |

**Gaps majeurs :**
- Zéro présence YouTube (corrélation 0.737 avec citation IA)
- FAQ trop courtes (28 mots moy. vs 134-167 optimal)
- Pricing data invisible (JS-only)
- Pas de `llms.txt`
- Pas de blog (0 articles)
- Pas de Wikipedia, Reddit, LinkedIn company discernables

### 6. Local SEO — 38/100

**Problèmes critiques :**
- Liens sociaux → Shopify (confusion d'entité)
- Email NAP incohérent (.com vs .fr)
- Pas d'openingHoursSpecification dans le schema
- Pas de Google Maps embed (le section store-locator existe mais n'est pas déployé)
- Pas de reviews / AggregateRating
- Footer sans adresse ni téléphone

### 7. Sitemap �� PASS avec avertissements

- 159 URLs, structure valide, images incluses
- 41 variantes de taille noindexed (décision intentionnelle)
- Blog vide (1 URL index, 0 articles)
- Toutes les lastmod produits identiques (limitation Shopify)
- 4 pages localisation OK (sous le seuil de 30)

---

## CORRECTIONS APPLIQUÉES (par l'agent Schema)

1. ✅ `schema-seo.liquid` — Image URL https, sameAs logic, @id, Service schema
2. ✅ `breadcrumbs.liquid` — BreadcrumbList restreint aux pages produit, @context fix
3. ✅ `header.liquid` — SearchAction ajouté au WebSite schema
4. ✅ `schema-testimonials.liquid` — NOUVEAU fichier, VideoObject x3

---

## CORRECTIONS À APPLIQUER (code)

### CRITIQUES (implémentées dans cette session)

| # | Fix | Fichier | Impact |
|---|-----|---------|--------|
| C1 | Hero image loading: lazy→eager, low→high | `sections/slideshow.liquid` | LCP -2-3s |
| C2 | mylab-product.css conditionnel (product only) | `layout/theme.liquid` | -22KB render-blocking |
| C3 | Meta description fallback | `layout/theme.liquid` | SEO snippets pour 30%+ pages |
| C4 | openingHoursSpecification + geo precision + type | `snippets/schema-seo.liquid` | Local pack |
| C5 | Email NAP unifié (.com partout) | `sections/ml-contact.liquid`, `templates/page.contact.json` | NAP consistency |
| C6 | min-height conteneurs dynamiques | `assets/mylab-product.css` | CLS fix |

### HAUTES (à planifier)

| # | Fix | Effort |
|---|-----|--------|
| H1 | Résoudre double domaine (DNS mylab-shop.com → Shopify) | Admin Shopify/DNS |
| H2 | Mettre à jour liens sociaux dans le thème Shopify | Admin Shopify |
| H3 | Remplacer FAQ placeholder par contenu MY.LAB | Admin Shopify |
| H4 | Ajouter HowTo schema à la page étapes | Code |
| H5 | Refactorer ml-dossier-gate.js (arrêter monkey-patch fetch) | Code |
| H6 | Créer blog avec 10+ articles fondamentaux | Contenu |
| H7 | Ajouter meta descriptions à toutes les pages/collections | Admin Shopify |
| H8 | Créer page "À propos" avec fondateur, équipe, certifications | Contenu |

### MOYENNES (backlog)

| # | Fix |
|---|-----|
| M1 | Minifier global.js (109KB → ~55KB) |
| M2 | Rendre le pricing en HTML statique (progressive enhancement) |
| M3 | Ajouter Google Maps embed sur la page contact |
| M4 | Créer llms.txt |
| M5 | Ajouter NAP au footer |
| M6 | Corriger le typo URL "profesionnel" |
| M7 | Créer chaîne YouTube |
| M8 | Développer citations tier 1 (Pages Jaunes, Europages) |
