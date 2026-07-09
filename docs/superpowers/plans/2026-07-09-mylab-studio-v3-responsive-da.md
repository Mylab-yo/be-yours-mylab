# MY.LAB Studio — Passe responsive + DA mylab-shop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre toutes les surfaces Studio (admin + client) utilisables sur téléphone et aligner la direction artistique sur celle du parcours mylab-shop (DM Sans/DM Mono, crème/encre).

**Architecture:** Une passe transversale en 3 couches : (1) fondations — tokens CSS + polices next/font + refonte des classes globales + layout admin avec sidebar-drawer mobile ; (2) passe admin (pack, bat, formulaires) ; (3) passe client (/projet, wizard onboarding, BatPanel, PackGallery). Aucun changement de logique, de routes ou d'API — UNIQUEMENT du markup/CSS. Chaque tâche est vérifiée par tsc/lint/tests + une revue de code attentive aux breakpoints.

**Tech Stack:** Tailwind (classes utilitaires + tokens dans `globals.css` `@layer`), `next/font/google` (DM Sans, DM Mono), lucide-react (icône Menu).

**Déclencheur :** feedback Yoann 09/07 (screenshot iPhone : sidebar fixe ~1/3 écran, cartes/boutons coupés, badges tronqués) : « il faut absolument que l'interface soit 100% responsive » + « la DA n'est pas parfaitement celle de mylab-shop ».

## Global Constraints

- **Repo** : `d:\Projets mylab vs code\mylab-configurateur`, branche `feat/studio-responsive-da` (Task 0, depuis `main`).
- **DA de référence = la DA du PARCOURS mylab-shop** (règle documentée par Yoann, spec parcours §DA) : **DM Sans** (titres/corps/UI, hiérarchie par graisse 400/500/600/700), **DM Mono** (kickers, badges, codes, métas — uppercase letter-spacing 0.12-0.16em), palette **crème** `#f5f0eb` (fond) / `#ede6dd` (cards) / `#e0d6c8` (chips), **encre** `#1a1a1a` (texte, CTAs pleins), `#6b665e` (métas), lignes `rgba(26,26,26,.10)`. **Interdits : Cormorant, italique, or `#c5a467`, rouge saturé.** Boutons : pill (`rounded-full`), primaire fond encre texte blanc, secondaire outline encre.
- **AUCUN changement de logique** : mêmes composants, mêmes fetches, mêmes props, mêmes textes (sauf si un texte doit être tronqué responsivement). Un diff qui touche une route API ou un handler est un défaut.
- **Responsive cibles** : utilisable à 375px (iPhone) et propre à 320px. Mobile-first : grilles `grid-cols-1` par défaut puis `sm:`/`lg:` ; AUCUNE largeur fixe > écran ; textes longs `break-words`/`truncate` ; boutons pleine largeur sur mobile quand empilés ; touch targets ≥ 40px.
- **Sidebar admin mobile** : cachée par défaut sous `lg:` ; header mobile sticky avec hamburger (lucide `Menu`) → drawer overlay (fond `bg-black/40`, panneau sidebar coulissant, fermeture au clic overlay/lien). Desktop : inchangée (visible fixe). Les liens de la sidebar sont **filtrés par rôle** (session `useSession` : `graphiste` ne voit que « BAT Étiquettes » — backlog Lot 2 réglé au passage).
- Leçon récurrente : règle lint `react-hooks/static-components` — aucun sous-composant défini dans un render.
- Vérifs par tâche : `npx tsc --noEmit && npm run lint && npm test` (0 erreur fichiers touchés, suite verte 277). Git : commits `style(studio): …` ou `feat(studio): …`, merge après revue finale.

---

### Task 0: Branche

- [ ] `git checkout main && git pull && git checkout -b feat/studio-responsive-da`

---

### Task 1: Fondations — polices, tokens, classes globales, layout admin responsive

**Files:**
- Modify: `src/app/layout.tsx` (next/font DM Sans + DM Mono, variables CSS, classe sur body)
- Modify: `src/app/globals.css` (tokens + refonte `.card`/`.btn-gold`/`.btn-primary`/`.btn-secondary`/`.input`/`.kicker` aux couleurs/formes parcours)
- Modify: `src/app/admin/(dashboard)/layout.tsx` (structure responsive)
- Modify: `src/components/admin/AdminSidebar.tsx` (drawer mobile + filtrage par rôle)

**Interfaces:**
- Consumes: session role (`useSession` — `Providers` enveloppe déjà l'app).
- Produces: variables `--font-dm-sans`/`--font-dm-mono` + tokens couleur (`--ml-cream`, `--ml-cream-2`, `--ml-chip`, `--ml-ink`, `--ml-muted`, `--ml-line`) utilisables partout ; classes globales relookées (tout consommateur existant hérite de la DA sans changement) ; `AdminSidebar` : prop AUCUNE (état drawer interne), export inchangé ; layout admin : `<main>` fond crème, padding réduit mobile (`p-4 lg:p-8`).

Détails imposés :
1. `layout.tsx` : `import { DM_Sans, DM_Mono } from "next/font/google"` (`subsets: ["latin"]`, DM Mono `weight: ["400","500"]`, `variable:` respectives), classes variables sur `<body>` + `font-[family-name:var(--font-dm-sans)]` via classe globale `body { font-family: var(--font-dm-sans), sans-serif; }` dans globals.
2. `globals.css` : `:root { --ml-cream:#f5f0eb; --ml-cream-2:#ede6dd; --ml-chip:#e0d6c8; --ml-ink:#1a1a1a; --ml-muted:#6b665e; --ml-line:rgba(26,26,26,.10); }`. `.card` → `background:var(--ml-cream-2); border:1px solid var(--ml-line); border-radius:1rem;` ; `.btn-gold`/`.btn-primary` → pill encre (`background:var(--ml-ink); color:#fff; border-radius:9999px;` hover translateY(-1px)) ; `.btn-secondary` → pill outline encre, hover inversé ; `.input` → fond blanc, bordure `var(--ml-line)`, focus bordure encre ; `.kicker` → DM Mono uppercase `letter-spacing:.14em; color:var(--ml-muted); font-size:.72rem;`. Si des pages utilisaient `bg-gray-50`/`mylab-*` incohérents dans le layout admin, le `<main>` passe à `background:var(--ml-cream)`.
3. `AdminSidebar` : état `open` (useState) ; rendu = (a) header mobile `lg:hidden` sticky top-0 (fond encre, logo texte « MY.LAB Studio » DM Mono, bouton `Menu`) ; (b) overlay + panneau `fixed inset-y-0 left-0 z-50 w-64 …` visible si open (translate-x), `lg:static lg:translate-x-0` ; fermeture au clic overlay et au clic sur un lien. Liens filtrés : `const links = ALL_LINKS.filter(l => role === "graphiste" ? l.href.startsWith("/admin/bat") : true)` (role depuis `useSession().data?.user?.role`). Sidebar garde son fond encre (cohérent DA).
4. Layout admin : `<div className="lg:flex">` — le main ne doit plus être compressé par la sidebar en mobile.

- [ ] Implémenter, vérifier (`tsc`/`lint`/`test`), commit `feat(studio): fondations DA parcours (DM Sans/Mono, creme/encre) + sidebar admin drawer mobile + filtrage role`

---

### Task 2: Passe admin — pack, BAT, formulaires

**Files:**
- Modify: `src/app/admin/(dashboard)/pack/page.tsx`, `pack/[projectId]/page.tsx`, `src/components/admin/PackReviewGrid.tsx`
- Modify: `src/app/admin/(dashboard)/bat/page.tsx`, `bat/[id]/page.tsx`, `src/components/admin/BatUploadForm.tsx`, `src/components/admin/BatCommentForm.tsx`
- Modify (si besoin léger): `src/app/admin/(dashboard)/page.tsx` (dashboard stats — grilles)

**Interfaces:** aucun changement de props/logique. Markup/classes uniquement.

Détails imposés :
- **Tables → cartes empilées sur mobile** : les `<table>` des listes (pack, bat) deviennent `hidden sm:table` + une liste `sm:hidden space-y-3` de cartes (mêmes données : commande, email `break-all`, compteurs, badge, bouton Ouvrir pleine largeur). Pas de scroll horizontal.
- **Fiche pack** : en-tête empilé (`flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between`), titre `text-lg sm:text-2xl break-words` (l'email passe à la ligne proprement), badge sous le titre sur mobile ; bouton « Publier au client » pleine largeur mobile. Grille assets `grid-cols-1 sm:grid-cols-2 xl:grid-cols-3` ; cartes : image `aspect-square object-cover w-full`, templateKey en `.kicker` DM Mono `truncate`, badge à côté SANS chevauchement (`flex items-center justify-between gap-2 min-w-0`), boutons Écarter/Relancer en `flex gap-2` pleine largeur (`flex-1`) sous la carte.
- **Fiche BAT** : le `grid lg:grid-cols-2` existant passe les blocs en pleine largeur mobile ; checkboxes/labels ≥40px ; badges `whitespace-nowrap` dans des lignes `flex-wrap`.
- Kickers/titres de sections admin adoptent `.kicker` DM Mono. Badges statut : garder les couleurs sémantiques actuelles mais en petites pastilles `rounded-full px-2.5 py-0.5 text-[11px] font-[family-name:var(--font-dm-mono)]`.

- [ ] Implémenter, vérifier, commit `style(studio): admin pack+bat responsives (tables->cartes, grilles, drawer-safe) et DA parcours`

---

### Task 3: Passe client — /projet, wizard onboarding, BatPanel, PackGallery

**Files:**
- Modify: `src/app/projet/page.tsx`, `src/app/projet/onboarding/[projectId]/page.tsx`
- Modify: `src/components/projet/OnboardingWizard.tsx`, `OnboardingStepBrandDna.tsx`, `OnboardingStepPhotos.tsx`, `OnboardingStepInfos.tsx`, `BatPanel.tsx`, `PackGallery.tsx`

**Interfaces:** aucun changement de props/logique.

Détails imposés :
- Remplacer la grammaire `neutral-*` par les tokens DA : fonds de page `var(--ml-cream)` (via classe utilitaire arbitraire `bg-[var(--ml-cream)]` ou classe globale), cards `bg-[var(--ml-cream-2)] border-[color:var(--ml-line)] rounded-2xl`, texte `text-[color:var(--ml-ink)]`, métas `text-[color:var(--ml-muted)]`, boutons → `.btn-primary`/`.btn-secondary` globales (pill encre). Émojis d'état conservés.
- **Stepper wizard** : `flex-wrap` + labels masqués sur ≤360px (`hidden min-[380px]:inline`) — règle le backlog 320px. Kickers d'étapes en DM Mono.
- **Écran photos** : vignettes `h-20 w-20` OK, mais conteneur `flex-wrap` déjà présent — vérifier à 320px ; boutons upload ≥40px.
- **Écran infos** : grilles `grid-cols-1 sm:grid-cols-2` déjà OK ; boutons empilés pleine largeur mobile (`w-full sm:w-auto`).
- **PackGallery** : grille `grid-cols-1 min-[420px]:grid-cols-2` ; compteur + bouton Valider sticky bottom sur mobile (`sticky bottom-3` dans un conteneur pill fond encre) pour rester accessible pendant le scroll ; vidéos pleine largeur.
- **BatPanel** : boutons Valider par référence ≥40px, lignes `flex-wrap`.
- **/projet** : titres `break-words`, timeline inchangée, bandeaux pleine largeur.

- [ ] Implémenter, vérifier, commit `style(studio): surfaces client responsives + DA parcours (tokens creme/encre, DM Sans/Mono, selection sticky)`

---

### Task 4: Déploiement + vérification visuelle (contrôleur puis Yoann)

- [ ] Revue finale de branche (diff complet, focus : aucune logique changée, breakpoints cohérents, interdits DA respectés — grep `Cormorant|italic|#c5a467` doit être vide sur les fichiers touchés)
- [ ] Merge main + push (deploy) 
- [ ] Vérification Yoann sur iPhone : /admin/pack (drawer, grille, publier), /projet (galerie, sticky), wizard onboarding.

## Hors scope

Les pages du configurateur public (`/configurateur/*`, studio IA) et `/admin/{designs,products,ranges,templates}` existants : ils gardent leur habillage actuel (chantier séparé si souhaité) — SEULES les surfaces Studio V3 (+ layout/sidebar communs) sont traitées. Les emails gardent Montserrat (rendu email ≠ web).

## Critères de succès

- iPhone 375px : aucune barre de scroll horizontale sur les surfaces traitées ; sidebar en drawer ; toutes les actions atteignables au pouce ; textes lisibles sans zoom.
- DA : DM Sans/DM Mono partout sur les surfaces traitées, palette crème/encre, zéro Cormorant/or/italique ; l'app est visuellement dans la continuité du parcours mylab-shop.
- `npx tsc --noEmit`, lint, 277 tests : verts. Aucune modification de route/handler/props.
